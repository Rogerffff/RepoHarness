# Python 异步、并发与消息传递基础学习笔记

```text
document_role: learning_notes
authority: non_authoritative
update_policy: user_confirmed_only
```

## 1. 文档用途

本文用于记录理解 RepoHarness 和 slime 代码所需的 Python、异步、并发、
消息队列、故障恢复与持久化基础知识。讲解应优先结合本项目中的真实代码，
而不是孤立罗列语言概念。

本文不定义 RepoHarness 的架构或训练语义。项目事实仍以真实代码、契约和
阶段权威文档为准。

## 2. 维护约定

- 讲解过程不自动写入本文。
- 只有用户明确提出需要记录，并与 codex 确认写入内容后才更新。
- 每个概念尽量包含：最小示例、项目代码锚点、常见错误和调试方法。
- 必须区分线程、进程、async task、Ray actor 和远程服务，不统称为“并发”。
- 不为了覆盖知识面而提前加入当前项目暂时用不到的内容。

## 3. 单个知识点的建议记录格式

```text
概念：
一句话解释：
最小 Python 示例：
RepoHarness/slime 代码锚点：
它解决的问题：
容易犯的错误：
如何观察或调试：
与当前设计决策的关系：
```

## 4. 待学习目录

### 4.1 同步调用、协程、`async` 与 `await`

待记录。

### 4.2 event loop、Task、Future 与 coroutine

#### 4.2.1 slime 的 `async_*` 不一定是 Python 协程

Python 协程通常由语法明确标识：

```python
async def work():
    result = await other_work()
```

但 slime 的 `RayTrainGroup.async_init()` 是普通 `def`。名称中的 `async` 只是
项目约定：它提交一批 Ray 远程调用并返回 ObjectRef，不在方法内部等待。

```python
def async_init(self, ...):
    return [actor.init.remote(...) for actor in self._actor_handlers]
```

外层再统一等待：

```python
refs = actor_group.async_init(...)
results = ray.get(refs)
```

这属于 Ray 的 **fan-out / gather**：

```text
fan-out
  先把任务提交给 rank 0、1、2、3

gather
  再等待四个 ObjectRef 全部完成
```

它没有使用 Python `asyncio` event loop。不能仅凭函数名含 `async`，就把它
当作 coroutine。

#### 4.2.2 调用 `async def` 只创建 coroutine，不会立即执行

定义异步函数：

```python
async def fetch_batch():
    return await queue.get()
```

调用它时：

```python
coro = fetch_batch()
```

`fetch_batch()` 不会像普通函数一样立即执行完整函数体。它先返回一个
**coroutine 对象**，表示“一项已经描述好、但还没有被 event loop 运行的异步
工作”。coroutine 必须通过以下方式之一交给 event loop：

```python
# 已经位于异步函数中
result = await coro

# 当前线程没有运行中的 event loop，启动一个临时 loop 直到任务完成
result = asyncio.run(coro)

# 把任务提交给另一个线程中已经运行的 event loop
future = asyncio.run_coroutine_threadsafe(coro, loop)
result = future.result()
```

最后一种形式包含两个不同动作：

```text
run_coroutine_threadsafe
  把 coroutine 安全地提交给另一个线程的 event loop。

future.result
  阻塞当前调用线程，等待异步任务完成。
```

因此可以同时出现：

```text
调用线程：同步阻塞等待结果
event loop 线程：继续调度多个 asyncio Task
```

slime 的 `AsyncLoopThread` 就是这种同步到异步的桥：

```python
class AsyncLoopThread:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._thread.start()

    def run(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop).result()
```

RepoHarness 的 slime rollout 插件入口必须是普通同步函数，因为 slime 的
`call_rollout_fn()` 只执行普通调用，不会 `await` 返回值：

```python
def generate_rollout(...):
    coro = generate_rollout_async(...)
    return slime_run(coro)
```

这里的同步外壳不表示内部没有并发。它只表示调用方在接口边界等待完整结果；
后台 event loop 仍可以并发推进多个等待网络、容器或子进程 I/O 的 Task。

容易犯的错误：

- 把 coroutine 对象误当作异步函数的最终返回值。
- 在已经运行 event loop 的线程内再次调用 `asyncio.run()`。
- 认为 `asyncio.Task` 是一个新的操作系统线程。Task 只是 event loop 调度的
  coroutine 状态。
- 在 event loop 线程中调用长时间阻塞的普通函数，导致同一 loop 上的所有
  Task 都无法继续推进。

#### 4.2.3 aiohttp、HTTP Application 与网络 socket

RH2 需要让独立运行的 Claude Code 黑盒进程调用训练侧模型。Claude Code
不能直接调用 RolloutManager 进程中的 Python 方法，只会请求 Anthropic HTTP
API。因此 slime 使用第三方 Python 包 `aiohttp` 提供一个 Anthropic-compatible
HTTP 服务。

首先区分各层的所有者：

```text
Python 标准库
  asyncio / threading / socket

第三方依赖 aiohttp
  HTTP 请求解析、路由、异步 Web Server、JSON 与流式响应

slime
  BaseAdapter / AnthropicAdapter、协议转换、SGLang 调用、TrajectoryManager

RH2
  session guard、capture、model proxy、版本与训练资格治理
```

`aiohttp` 不是 Python 标准库，需要通过 `pip` 或 `uv` 安装。它建立在
`asyncio` 和操作系统网络 socket 之上，替应用处理 HTTP 协议和异步并发。

##### `web.Application` 是服务定义，不是已经运行的服务

最小 aiohttp 服务如下：

```python
from aiohttp import web


async def hello(request: web.Request):
    return web.json_response({"message": "hello"})


app = web.Application()
app.router.add_get("/hello", hello)

web.run_app(app, host="127.0.0.1", port=8080)
```

其中：

```text
web.Application
  保存路由、middleware、生命周期回调和应用状态。

app.router.add_get("/hello", hello)
  建立“GET /hello -> hello(request)”的映射。

web.run_app(...)
  真正建立监听端口并持续运行服务。
```

只执行 `web.Application()` 不会监听任何端口。它更像一份 HTTP 服务定义，
而不是桌面应用或已经启动的网络进程。

slime 的 `BaseAdapter` 构造时创建同一个 application，并先注册公共路由：

```python
self.app = web.Application(client_max_size=64 * 1024 * 1024)
self.app.router.add_get("/healthz", _health)
self.app.router.add_get("/v1/models", _health)
self._register_routes(self.app)
```

`_register_routes` 不是 aiohttp 内置 API，而是 slime 定义的子类扩展点。父类
只负责协议共有行为，子类负责注册协议专属路径：

```python
class BaseAdapter:
    def _register_routes(self, app):
        raise NotImplementedError


class AnthropicAdapter(BaseAdapter):
    def _register_routes(self, app):
        app.router.add_post("/v1/messages", self._run_turn)
        app.router.add_post("/v1/messages/count_tokens", _count_tokens)


class OpenAIAdapter(BaseAdapter):
    def _register_routes(self, app):
        app.router.add_post("/v1/chat/completions", self._run_turn)
```

创建 `AnthropicAdapter(...)` 时，`BaseAdapter.__init__()` 中的 `self` 仍是
AnthropicAdapter 实例，因此：

```python
self._register_routes(self.app)
```

会动态分派到 `AnthropicAdapter._register_routes()`。这属于方法重写，也是
常见的 template method 结构。`self._run_turn` 是绑定方法，处理请求时可以
访问当前 adapter 的 tokenizer、SGLang URL、session store 和 trajectory
manager。

##### socket、IP、端口和 HTTP 的关系

Socket 是程序使用操作系统网络能力的接口。一个 TCP 服务端点通常表示为：

```text
IP 地址 + 端口
127.0.0.1:8080
```

- `127.0.0.1` 只表示当前机器的 loopback 网络接口。
- `8080` 区分当前机器上的某个网络服务。
- `0.0.0.0` 表示监听当前机器的所有网络接口，而不是某台具体远端机器。
- 配置 `port=0` 时，操作系统会选择一个当时空闲的端口。

服务启动后，操作系统先创建一个 listening socket。客户端连接时，双方形成
一条 TCP 连接，例如：

```text
Claude Code 客户端 127.0.0.1:53142
              ->
Adapter 服务端 127.0.0.1:8080
```

TCP/socket 只负责可靠传输字节；HTTP 在这些字节之上规定 method、path、
headers 和 body 的格式：

```http
POST /v1/messages HTTP/1.1
Host: 127.0.0.1:8080
Content-Type: application/json

{"messages": []}
```

aiohttp 将 socket 中的字节解析为 `web.Request`，应用可以读取：

```python
request.method
request.path
request.headers
body = await request.json()
```

handler 返回 `web.Response` 或 `web.StreamResponse` 后，aiohttp 再将它编码为
HTTP 字节，通过 socket 发回 Claude Code。Anthropic 的流式响应使用
`text/event-stream`（SSE），由 slime 按 Anthropic 事件格式组织内容。

##### `web.run_app()` 与 `AppRunner + TCPSite`

`web.run_app()` 是 aiohttp 的高层便利函数，大致替调用方完成：

```python
loop = asyncio.new_event_loop()
runner = web.AppRunner(app)
await runner.setup()
site = web.TCPSite(runner, host, port)
await site.start()
loop.run_forever()
```

各对象的职责是：

```text
event loop
  调度异步任务，持续处理网络事件。

AppRunner
  管理 Application 的 startup、正在处理的请求和 cleanup 生命周期。

TCPSite
  声明 runner 要通过 TCP 在哪个 host:port 提供服务。

site.start()
  请求操作系统创建并绑定 listening socket，开始接收连接。

loop.run_forever()
  持续接受连接、读取请求、运行 middleware/handler 并发送响应。
```

两种启动方式使用的是同一套 aiohttp 能力：

```text
web.run_app(app, ...)
  适合独立 Web 服务；占用当前线程直到服务关闭。

AppRunner + TCPSite + 自己管理 event loop
  适合需要控制线程、端口、启动证据和关闭时序的嵌入式服务。
```

slime 不能让 HTTP Server 永久占用 RolloutManager Actor 主线程，因此
`run_app_in_thread()` 会创建名为 `rh2-anthropic-adapter` 的后台线程，并在
该线程中创建独立 event loop、`AppRunner` 和 `TCPSite`。它返回的
`AppHandle` 保存实际端口、线程、loop 和 runner，供主逻辑观察与关闭。

一次真实请求的路径是：

```text
Claude Code 独立进程或 sandbox
  -> TCP socket
  -> rh2-anthropic-adapter 线程中的 aiohttp Server
  -> middleware
  -> router 匹配 POST /v1/messages
  -> AnthropicAdapter._run_turn()
  -> RH2 capture / model proxy
  -> SGLang /generate
  -> Anthropic JSON 或 SSE 响应
  -> Claude Code
```

同一 adapter 线程通常只有一个 event loop；每个 HTTP 请求成为一个
`asyncio.Task`，不是每个请求新建一个线程。handler 等待 SGLang 网络响应时，
`await` 会让出 event loop，使其他请求可以推进；如果 handler 直接执行长时间
CPU 计算或阻塞函数，则会阻塞同一 loop 上的全部请求。

项目代码锚点：

- `reference/slime/slime/agent/adapters/common.py`：`BaseAdapter` 和
  `web.Application`。
- `reference/slime/slime/agent/adapters/anthropic.py`：Anthropic 路由、请求
  转换和 SSE 响应。
- `reference/slime/slime/agent/aiohttp_threaded.py`：后台线程中的
  `AppRunner + TCPSite` 启动和关闭。
- `rh2/experiments/s1_7a_bringup/glue.py`：创建 adapter、挂 middleware、启动
  `rh2-anthropic-adapter` 线程并生成 `adapter_url`。

容易犯的错误：

- 以为创建 `web.Application` 就已经监听端口。
- 把 HTTP route 注册误解成一次立即执行的函数调用；它只是保存未来请求的
  分派规则。
- 把 `self._register_routes` 当成 aiohttp API；它是 slime 的子类扩展点。
- 认为 aiohttp 每个请求创建一个线程；默认并发单位是 event loop 上的 Task。
- 在 event loop handler 内使用阻塞 I/O 或长时间 CPU 计算。
- 混淆 `127.0.0.1`、`0.0.0.0` 和容器内可达地址；服务监听成功不等于 sandbox
  一定能够访问。

观察和调试方法：

```bash
# 检查健康接口和实际端口是否可达
curl -v http://127.0.0.1:<port>/healthz

# 查看端口由哪个进程监听（Linux）
ss -ltnp | grep <port>

# 验证路由是否存在；未知路径应按 RH2 安全策略返回明确错误
curl -v http://127.0.0.1:<port>/unknown
```

还应同时观察 adapter access log、middleware 拒绝计数、请求 cancellation、
SGLang request id 和 RH2 capture ledger，不能只凭“端口能连通”判断训练链路
正确。

### 4.3 线程、进程、GIL 与 Ray actor

#### 4.3.1 Ray Driver、Ray Actor 与普通 Python 进程

在 slime 中，运行 `train_async.py` 的 Python 进程是 **Ray Driver**。它主要
负责创建远程组件、提交任务和等待结果，本身不执行 Megatron 的模型前向、
反向传播或者 SGLang 推理。

Ray Actor 是由 Ray 启动和管理的长生命周期 Python 工作进程。例如：

```text
Ray Driver 进程
  ├─ RolloutManager Ray Actor（CPU 编排进程）
  ├─ MegatronTrainRayActor rank 0（训练 GPU）
  ├─ MegatronTrainRayActor rank 1（训练 GPU）
  ├─ MegatronTrainRayActor rank 2（训练 GPU）
  ├─ MegatronTrainRayActor rank 3（训练 GPU）
  └─ SGLangEngine Ray Actors（rollout GPU）
```

这些 Actor 是不同的操作系统进程，所以不共享普通 Python 对象。跨 Actor
调用通过 Ray 完成：

```python
result_ref = actor.method.remote(argument)
result = ray.get(result_ref)
```

- `.remote(...)` 提交远程调用并立即返回 `ObjectRef`。
- `ObjectRef` 是未来结果的句柄，不是结果本身。
- `ray.get(...)` 阻塞当前调用方，等待远程结果完成。

因为 Ray Actor 是独立进程，它们不共同受 Driver 进程的 Python GIL 限制。
但是每个 Actor 进程内部仍有自己的 Python GIL、线程和 event loop。

代码锚点：

- `reference/slime/train_async.py`
- `reference/slime/slime/ray/placement_group.py`
- `reference/slime/slime/ray/actor_group.py`
- `reference/slime/slime/ray/rollout.py`

#### 4.3.2 Placement Group：预留并固定一整套资源

Placement Group 可以理解为 Ray 中的一组资源预订。slime 会先创建多个
bundle，每个 bundle 表示一个资源槽位：

```python
bundles = [
    {"GPU": 1, "CPU": 1},
    {"GPU": 1, "CPU": 1},
    # ...
]
```

它解决两个问题：

1. **整体调度**：训练和推理需要的资源要么全部准备好，要么整个作业等待，
   不出现训练先占住部分 GPU、rollout 永远凑不齐剩余 GPU 的死等状态。
2. **固定位置**：创建 Ray Actor 时可以声明必须进入某个 bundle，从而稳定
   地把训练 rank 和 SGLang engine 绑定到选定 GPU。

Placement Group 本身不是进程，也不存放 rollout 或训练数据。它只是 Ray
调度器中的资源预留和放置约束。

创建 Actor 时的绑定形状是：

```python
PlacementGroupSchedulingStrategy(
    placement_group=pg,
    placement_group_bundle_index=bundle_index,
)
```

Ray 负责决定 bundle 最终落在哪个节点和哪张物理 GPU；slime 负责决定某个
bundle 用于训练还是 rollout。

Ray 的原始 bundle index 不保证与物理 GPU ID 同序。slime 会在每个 bundle
临时启动 `InfoActor`，查询 `(node_ip, gpu_id)`，按节点和 GPU ID 排序后得到：

```python
reordered_bundle_indices: list[int]
```

例如原始放置为：

```text
bundle 0 -> node-B GPU 2
bundle 1 -> node-A GPU 3
bundle 2 -> node-A GPU 0
bundle 3 -> node-B GPU 0
```

排序结果可能是：

```python
reordered_bundle_indices = [2, 1, 3, 0]
```

训练 rank 使用 `reordered_bundle_indices[rank]`，从而获得稳定的节点/GPU
顺序。逻辑 rank、原始 bundle index 与物理 GPU ID 是三个不同编号。

#### 4.3.3 4 张训练 GPU + 4 张 rollout GPU 的计算

示例参数：

```text
actor_num_nodes = 1
actor_num_gpus_per_node = 4
rollout_num_gpus = 4
colocate = false
```

这里的 `actor_num_nodes=1` 不是“整个集群只有一个节点，且只有 4 张卡”，
而是“训练模型使用 1 个节点”。训练 GPU 数量为：

```text
actor_num_gpus
  = actor_num_nodes × actor_num_gpus_per_node
  = 1 × 4
  = 4
```

非 colocate 模式下，rollout 另需 4 张 GPU，所以总资源为：

```text
4 张训练 GPU + 4 张 rollout GPU = 8 张 GPU
```

Ray 创建 8 个逻辑 bundle：

```text
bundle 0  ┐
bundle 1  │
bundle 2  ├─ Megatron 训练使用
bundle 3  ┘

bundle 4  ┐
bundle 5  │
bundle 6  ├─ SGLang rollout 使用
bundle 7  ┘
```

`rollout_offset=4` 表示 rollout 的资源视图从逻辑 bundle 4 开始：

```python
rollout_bundle_indices = all_bundle_indices[rollout_offset:]
```

实际物理映射可能不是 `bundle 0 -> GPU 0`。Ray 可能先把 bundle 放到不同节点
或不同物理 GPU，slime 再通过短生命周期的 `InfoActor` 查询 IP 和 GPU ID，
按拓扑重新排序。因此应该区分：

```text
逻辑 bundle index
物理节点和 GPU ID
训练 global rank
```

三者有关联，但不是同一个编号概念。

#### 4.3.4 global rank、TP rank 与 DP rank

在分布式训练中，`rank` 首先表示一个工作进程的身份。假设有 4 个训练进程：

```text
global rank 0 -> 一张训练 GPU
global rank 1 -> 一张训练 GPU
global rank 2 -> 一张训练 GPU
global rank 3 -> 一张训练 GPU
```

Ray placement group 只负责把这些进程放到相应 GPU 槽位。Megatron 再根据
`TP`、`DP`、`PP`、`EP` 等配置，计算这些 rank 应该组成哪些通信组。

以 `TP=2、DP=2` 为例：

| global rank | DP rank | TP rank | 含义 |
|---:|---:|---:|---|
| 0 | 0 | 0 | 数据副本 0 的模型分片 A |
| 1 | 0 | 1 | 数据副本 0 的模型分片 B |
| 2 | 1 | 0 | 数据副本 1 的模型分片 A |
| 3 | 1 | 1 | 数据副本 1 的模型分片 B |

可以理解为：

```text
DP 副本 0
  ├─ global rank 0：TP 分片 A
  └─ global rank 1：TP 分片 B

DP 副本 1
  ├─ global rank 2：TP 分片 A
  └─ global rank 3：TP 分片 B
```

假设一个 batch 有 8 条样本：

```text
DP 副本 0 处理样本 0~3
DP 副本 1 处理样本 4~7
```

但在 DP 副本 0 内，rank 0 和 rank 1 **共同处理样本 0~3**。它们不是分别
再处理一半样本，而是各自计算模型的一部分，并通过 NCCL 通信组合出完整
前向和反向结果。

因此：

```text
DP 拆数据：
不同 DP 副本处理不同样本。

TP 拆模型计算：
同一个 DP 副本中的多个 TP rank 共同处理同一批样本。
```

反向传播后，相同模型分片的 DP ranks 要同步梯度：

```text
rank 0 <-> rank 2：同步模型分片 A 的梯度
rank 1 <-> rank 3：同步模型分片 B 的梯度
```

而 TP 组在模型计算过程中持续通信：

```text
rank 0 <-> rank 1：共同完成 DP 副本 0 的模型计算
rank 2 <-> rank 3：共同完成 DP 副本 1 的模型计算
```

#### 4.3.5 各层分别拥有哪项决定

最容易记忆的边界是：

```text
Ray Placement Group
  决定和约束资源槽位放在哪里。

slime 资源编排
  决定哪些 bundle 给训练，哪些给 rollout。

Ray Actor 创建参数
  把具体工作进程绑定到指定 bundle。

Megatron 并行配置
  决定 global ranks 如何组成 TP / DP / PP / EP 通信组。
```

容易犯的错误：

- 把 `actor_num_nodes` 理解成整个 Ray 集群的节点总数。它只描述训练 Actor
  使用多少节点。
- 把 global rank 0/1 直接理解成 TP 的两半。global rank 只是全局进程编号，
  它的 TP/DP 坐标由并行配置派生。
- 认为 TP rank 各处理一半样本。TP 拆模型；同一 DP 副本内的 TP ranks
  共同处理同一批样本。
- 假定逻辑 bundle 编号等于物理 GPU ID。Ray 调度和 slime 的拓扑重排可能
  让两者不同。
- 把 Ray Actor 上声明的 `num_gpus=0.2` 或 `0.4` 当成模型只能使用对应比例
  的显存。这个数首先是 Ray 调度配额；实际模型进程如何使用 GPU 还取决于
  placement group、可见设备和 SGLang/Megatron 的启动配置。

#### 4.3.6 普通对象、普通函数与 Ray Actor

“在 Actor 的构造函数里创建”不等于“创建出来的东西也是 Actor”。要看是否
调用了 Ray 的 `.remote()`。

```python
# 普通 Python 对象：只存在于当前进程内
self.data_source = DataSource(args)

# 普通 Python 函数对象：只在当前进程内被调用
self.generate_rollout = load_function(path)

# 新的 Ray Actor：Ray 会启动独立远程进程
self.lock = Lock.options(num_cpus=1).remote()
```

在 slime 中：

```text
RolloutManager Ray Actor 进程
  ├─ self.data_source          普通 Python 对象
  ├─ self.generate_rollout     普通函数对象
  ├─ self.servers              普通字典和 dataclass
  │    └─ 内部保存 SGLang engine ActorHandles
  └─ self.rollout_engine_lock  指向另一个 Ray Actor 的 ActorHandle
```

普通对象不能被其他进程直接访问。其他 Actor 如果需要访问 `DataSource`，
通常要远程调用其 owner，也就是 `RolloutManager`；或者由 owner 明确把可序列化
的数据副本传出去。

#### 4.3.7 `.options()`、`.remote()` 与资源调度

创建 Actor 常见的两步是：

```python
ConfiguredActor = SomeActor.options(
    num_cpus=1,
    num_gpus=0,
)
actor_handle = ConfiguredActor.remote(...)
```

- `.options(...)` 只声明资源、调度策略和运行环境，本身不启动进程。
- `.remote(...)` 才向 Ray 提交 Actor 创建请求，并返回 ActorHandle。

是否进入某个 Placement Group，取决于是否显式传入：

```python
scheduling_strategy=PlacementGroupSchedulingStrategy(...)
```

例如 `RolloutManager` 申请 `1 CPU / 0 GPU`，但没有指定 placement group，
所以使用普通集群 CPU 资源。它仍然可能物理运行在带 GPU 的节点上，只是没有
获得 GPU 调度配额，也不占用预留给训练和 rollout engine 的 GPU bundle。

普通实现类可以在运行时包装为远程类：

```python
actor_impl = MegatronTrainRayActor
RemoteActor = ray.remote(**common_options)(actor_impl)
handle = RemoteActor.options(**instance_options).remote(...)
```

三层分别是：

```text
actor_impl   普通 Python 类
RemoteActor  Ray 远程类工厂
handle       某一个远程实例的 ActorHandle
```

类级 `common_options` 适合放所有实例共享的 `runtime_env` 和可选 NIXL tensor
transport；实例级 `options` 适合放具体 bundle 和资源份额，并会覆盖同名默认值。

Ray 允许声明 `num_gpus=0.4` 这样的逻辑份额，使多个 Actor 可以被调度到同一
个 1-GPU bundle。例如 actor 和 critic 各申请 0.4，Ray 的资源账允许二者
共存。但这个数不限制 CUDA 只能使用 40% 显存；真实显存由模型、optimizer、
activation 和 offload 配置决定。

#### 4.3.8 ActorHandle 与 ObjectRef

两者都叫“句柄”，但指向的东西不同。

**ActorHandle 指向一个长期存活的远程 Actor：**

```python
engine_handle = SGLangEngine.remote(...)
```

以后可以反复通过它调用：

```python
engine_handle.init.remote(...)
engine_handle.update_weights.remote(...)
engine_handle.get_weight_version.remote(...)
```

**ObjectRef 指向某一次远程调用的未来结果：**

```python
init_ref = engine_handle.init.remote(...)
```

此时初始化在远程执行，当前进程立即得到 `init_ref`。调用：

```python
ray.get(init_ref)
```

会等待这次调用完成，并取得返回值或传播远程异常。

多个 engine 初始化时，经常保存一组 ObjectRef：

```python
init_refs = [engine.init.remote(...) for engine in engines]
ray.get(init_refs)
```

这表示显式等待所有 engine 就绪。它不是把 Actor 本身取回本地。

ActorHandle 可以作为远程方法参数或返回值，在 Driver 和其他 Actor 之间传递。
Ray 传递的是指向同一个 Actor 的远程引用，而不是复制 Actor 的内部状态：

```text
RolloutManager 保存 Lock ActorHandle
  -> Trainer 调用 RolloutManager 取得这个 handle
  -> 四个 Trainer 都指向同一个 Lock Actor
  -> `_locked` 状态仍只存在于唯一的 Lock Actor 进程
```

slime 的 `start_rollout_servers()` 返回值也可用这个区别理解：

```text
servers
  普通控制结构，内部长期保存 SGLang engine ActorHandles

init_handles
  engine.init.remote() 返回的一组 ObjectRefs，只用于等待初始化
```

#### 4.3.9 动态 Python 类路径与数据文件路径

下面两个配置解决不同问题：

```text
--data-source-path
  指定使用哪个 Python DataSource 类

--prompt-data
  指定这个类要读取的 JSONL 等任务数据
```

例如：

```bash
--data-source-path slime.rollout.data_source.RolloutDataSourceWithBuffer \
--prompt-data /data/swe_gym_train.jsonl
```

执行过程是：

```text
load_function(data_source_path)
  -> 得到 Python 类

data_source_cls(args)
  -> 类读取 args.prompt_data
  -> 得到包含数据、游标和 group 身份状态的实例
```

同理，`--rollout-function-path` 指定的是可导入的 Python 函数，不是数据文件：

```text
module.submodule.generate_rollout
```

#### 4.3.10 `__init__` 与业务 `init` 是两个方法

Ray 创建训练 Actor 时自动执行 Python 构造函数：

```python
TrainRayActor.__init__(world_size, rank, master_addr, master_port)
```

它只建立远程进程的基本身份和环境变量。之后 Driver 显式提交：

```python
actor.init.remote(args, role, ...)
```

才进入 `MegatronTrainRayActor.init()`。其中 `super().init()` 调用的是基类的
普通 `TrainRayActor.init()`，不是再次执行 `__init__()`，也不会创建新进程。

```text
远程进程创建
  -> TrainRayActor.__init__

稍后初始化训练运行时
  -> MegatronTrainRayActor.init
     -> TrainRayActor.init
```

`os.environ` 属于当前 Actor 操作系统进程。一个 Actor 设置 `RANK` 或
`LOCAL_RANK`，不会直接修改 Driver 或其他 Actor 的环境变量。

#### 4.3.11 PyTorch distributed rendezvous

多个独立进程刚启动时不知道其他进程在哪里，所以需要 rendezvous 集合点：

```text
MASTER_ADDR  集合服务所在机器的网络地址
MASTER_PORT  该机器上具体服务的 TCP 端口
WORLD_SIZE   应到的总进程数
RANK         当前进程的全局编号
LOCAL_RANK   当前节点/可见设备集合内的 GPU 编号
```

slime 先创建 rank 0，由它选择可访问 IP 和空闲端口；Driver 取回该地址后传给
其余 ranks。所有 rank 并发执行 `dist.init_process_group()`，互相发现并交换
通信初始化信息。即使都在同一台机器，它们也是独立地址空间，仍需要进程间
集合机制。

rank 0 是启动协调者，不是所有训练数据的中转站。集合完成后，NCCL 会根据
TP/DP/PP/EP 通信组在相应 GPU ranks 之间直接传输张量。

#### 4.3.12 Python 模块、动态导入与模块生命周期

一个 `.py` 文件被 Python 导入后，会在当前解释器中形成一个**模块对象**。
模块对象有自己的命名空间，用来保存该文件顶层定义的名字：

```python
# example_module.py
DEFAULT_LIMIT = 8

class Worker:
    pass

def run():
    pass
```

导入：

```python
import example_module
```

之后可以把模块内存近似理解为：

```text
example_module 模块命名空间
  ├─ DEFAULT_LIMIT -> 整数对象 8
  ├─ Worker        -> 类对象
  └─ run           -> 函数对象
```

首次导入模块时，Python 会执行模块顶层语句。需要区分：

- `def` 语句会创建函数对象，但不会执行函数体；函数体要等真正调用时执行。
- `class` 语句会执行类定义体来创建类对象，但不会自动创建该类的实例。
- 模块顶层赋值会立即执行，例如 `_SERVICE = None`。
- 模块顶层的其他 `import` 会继续按需导入依赖模块。

Python 不会在程序启动时自动导入整个项目。它主要导入：

```text
代码显式 import 的模块
动态 import 指定的模块
这些模块在导入过程中继续依赖的模块
```

动态插件路径通常写成字符串：

```text
fa_bringup.rollout_entry.generate_rollout
```

可以通过 `importlib` 解析：

```python
def load_function(path):
    module_path, _, attr = path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, attr)
```

执行结果是：

```text
导入 fa_bringup.rollout_entry 模块
-> 执行该模块顶层代码
-> 从模块命名空间取出 generate_rollout 函数对象
```

同一 Python 进程中，成功导入的模块通常会缓存在 `sys.modules`。再次导入同名
模块时通常复用原模块对象，不重新执行所有顶层代码。因此模块级状态可以在
多次函数调用之间保留。

但是 `sys.modules` 和模块内存都属于当前 Python 进程：

```text
RolloutManager Actor A 进程 -> 自己的模块对象和模块变量
RolloutManager Actor B 进程 -> 另一份模块对象和模块变量
```

Actor 进程崩溃并重启后，新解释器会重新导入模块，模块级变量也会重新初始化。
所以模块变量可以提供“当前进程生命周期内的状态”，但不是跨进程或跨故障的
持久化状态。

代码锚点：

- `reference/slime/slime/utils/misc.py::load_function`
- `reference/slime/slime/ray/rollout.py::RolloutManager.__init__`
- `rh2/experiments/fa_bringup/rollout_entry.py`

#### 4.3.13 局部变量、模块变量、类变量与实例变量

四种常见变量位置具有不同的 owner 和生命周期：

| 类型 | 最小例子 | 主要生命周期 |
|---|---|---|
| 局部变量 | 函数中的 `coro` | 一次函数调用 |
| 模块变量 | `rollout_entry._SERVICE` | 模块所在的当前进程 |
| 类变量 | `BringupService._instance` | 当前进程中的类对象 |
| 实例变量 | `service._worker` | 某个具体实例 |

模块变量写在函数和类外部：

```python
_SERVICE = None

def get_service():
    return _SERVICE
```

函数需要重新给模块变量赋值时，要声明：

```python
def initialize():
    global _SERVICE
    _SERVICE = Service()
```

`global` 的准确含义是：这个函数中的 `_SERVICE` 指向当前模块命名空间中的
名字。它不表示：

```text
整个项目全局
整个 Ray 集群全局
所有机器和进程共享
```

如果没有 `global`，赋值通常会创建同名局部变量：

```python
_SERVICE = None

def broken_initialize():
    _SERVICE = Service()  # 这是新的局部变量，不会修改模块变量
```

还要注意，Python 变量通常保存的是**对象引用**。例如：

```python
service = Service()
_SERVICE = service
```

可以理解为：

```text
模块命名空间中的名字 _SERVICE
  -> 指向堆内存中的 Service 实例
```

赋值改变的是名字指向哪个对象，不是把完整对象内容复制进变量。多个名字可以
同时指向同一个可变对象；通过任一引用修改该对象，其他引用之后也会看到修改。

#### 4.3.14 进程隔离、线程共享与 event loop 所有权

操作系统进程默认拥有独立地址空间。普通 Python 对象不能被另一个进程直接
读取或修改：

```text
Driver 进程中的 dict
  不能被 RolloutManager Actor 直接访问。

RolloutManager 中的模块变量
  不能被 SGLang Actor 或 Trainer Actor 直接访问。
```

跨进程通信必须使用明确的通信机制，例如：

```text
Ray RPC / ObjectRef
HTTP
socket / pipe
共享内存
消息队列
文件或数据库
```

同一进程内的线程共享该进程的模块对象和普通堆内存：

```text
一个 RolloutManager Actor 进程
  ├─ Actor 主线程
  ├─ AsyncLoopThread
  ├─ adapter HTTP 线程
  └─ 可选健康监控线程
```

这些线程理论上都能取得当前进程中的模块变量。但是 event loop 和 asyncio
对象通常有线程归属：一个 event loop 在某个特定线程中运行，Task、Queue、
Semaphore 等异步对象通常应该由所属 loop 创建和操作。

可以把层次关系记为：

```text
进程
  拥有独立内存和自己的 Python 解释器

线程
  共享所属进程的普通内存

event loop
  运行在某一个线程中

asyncio Task
  由该 event loop 调度，不是新的线程或进程
```

模块级服务对象若主要在一个 event loop 中使用，最清晰的规则通常是明确
**单 owner**：只允许所属 loop 的线程修改服务状态，其他线程通过线程安全回调
或消息传递请求操作，而不是直接修改内部字段。

#### 4.3.15 进程启动方不等于组件实现方

看分布式系统代码时，需要分开三个问题：

```text
谁创建和回收这个进程？
进程内运行的组件由谁实现？
运行时的具体决策由谁执行？
```

slime 中的 SGLang Router 是一个具体例子：

```text
slime RolloutManager
  -> 使用 multiprocessing.Process 创建 Router 子进程
  -> 给子进程传入 host、port、routing policy 和 PD 配置

Router 子进程
  -> 导入外部 sglang-router 包的 launch_router
  -> 运行 SGLang 提供的 HTTP 路由服务
  -> 根据 cache_aware / consistent_hashing 等策略选择 worker
```

因此，“Router 是 slime 启动的子进程”和“Router 路由逻辑由
SGLang 实现”同时成立。slime 拥有该实例的部署与生命周期编排；
SGLang 拥有 Router 组件和路由算法。这和应用程序启动 Nginx 或
PostgreSQL 时，应用程序并没有因此变成 HTTP 路由或数据库的实现方是
同一类区分。

项目代码锚点：

- `reference/slime/requirements.txt`：声明外部 `sglang-router` 依赖。
- `reference/slime/slime/ray/rollout.py::_start_router`：组装参数并创建子进程。
- `reference/slime/slime/utils/http_utils.py::run_router`：导入并调用
  `sglang_router.launch_router.launch_router`。
- `reference/slime/slime/backends/sglang_utils/sglang_engine.py::_register_to_router`：
  把真实 SGLang server 注册到 Router。

容易犯的错误：

- 看到 `multiprocessing.Process(target=run_router)` 就认为 Router 算法写在
  `run_router` 中。该函数只是外部组件的启动壳。
- 把“slime 选择 routing policy”误解为“slime 在每次请求时选择
  server”。slime 配置策略，运行中的 Router 执行每次 worker 选择。

### 4.4 跨线程调用与 `call_soon_threadsafe`

待记录。

### 4.5 回调、订阅和 completion callback

待记录。

### 4.6 队列、有界缓冲、生产者消费者与反压

待记录。

### 4.7 锁、临界区、竞态与单 owner 消息传递

#### 4.7.1 `threading.Lock` 只能保护同一进程

`threading.Lock` 用于协调同一 Python 进程内的多个线程：

```python
import threading

lock = threading.Lock()

with lock:
    update_shared_dict()
```

这些线程共享同一块进程内存，所以可以共同看到同一个 `lock` 对象。不同
Ray Actor 是不同操作系统进程，甚至可能位于不同机器，不能共享这个对象。

#### 4.7.2 用 Ray Actor 实现跨进程协调点

slime 的权重更新锁本身是一个独立 Ray Actor：

```python
@ray.remote
class Lock:
    def __init__(self):
        self._locked = False

    def acquire(self):
        if not self._locked:
            self._locked = True
            return True
        return False

    def release(self):
        self._locked = False
```

多个 trainer 都持有指向同一个 Lock Actor 的 ActorHandle：

```text
Trainer rank 0 ─┐
Trainer rank 1 ─┤
Trainer rank 2 ─┼─> 唯一的 Lock Actor
Trainer rank 3 ─┘
```

调用：

```python
acquired = ray.get(lock_handle.acquire.remote())
```

实际是通过 Ray RPC 在 Lock Actor 进程中检查并修改唯一的 `_locked`。Actor
默认串行处理这些普通方法调用，因此“检查未锁定并设为锁定”不会在多个
trainer 进程中各执行一份。

slime 使用它串行协调 trainer 向 SGLang engine 的 NCCL 权重传输：

```text
Trainer A 获得锁
-> 广播一段新权重
-> 等待远程更新完成
-> 释放锁

Trainer B 在此期间只能等待
```

这个锁不等于完整的 fully async 更新协议。它没有独立回答：

- 某个 SGLang generation 是否正在进行；
- 更新窗口开始后是否要暂停或 abort generation；
- rollout token 对应哪个 policy version；
- trainer 能否消费过度陈旧的轨迹。

这些问题需要 coordinator、版本事实、fencing 和 staleness 规则共同处理。

#### 4.7.3 锁保护的是临界区，不是整个业务正确性

锁只应围住必须互斥的最小操作。锁太小会留下竞态，锁太大会降低并发并可能
造成死锁。阅读代码时要明确：

```text
共享状态是什么？
哪些调用必须形成不可分割的临界区？
锁由谁创建和释放？
异常或取消时是否一定释放？
这个锁能否跨越当前进程边界？
```

对于跨进程复杂状态，长期更清晰的设计往往是“单 owner + 消息传递”：只有
一个组件修改状态，其他组件提交命令，而不是让许多进程共同操作分布式锁。

#### 4.7.4 共享内存只表示“能够访问”，不表示“并发安全”

同一进程的线程共享模块变量，但下面的代码仍然可能产生竞态：

```python
if _SERVICE is None:
    _SERVICE = build_service()
```

如果两个线程同时观察到 `_SERVICE is None`，它们可能各自创建一份服务，随后
其中一次赋值覆盖另一次。更复杂的共享 dict、队列和生命周期状态还可能出现：

- 检查时存在，使用时已经被另一个线程删除；
- 一个线程只完成一半更新，另一个线程读到不完整状态；
- 回调与清理同时运行，导致重复完成或悬挂记录；
- 异常发生后锁没有释放，造成死锁。

常见治理方式包括：

```text
单 owner
  只有一个线程或 Actor 修改状态，其他组件发送命令。

锁
  把必须不可分割的检查和修改放进同一个临界区。

线程安全队列
  生产者投递消息，owner 按顺序处理，而不是共同修改内部对象。

不可变快照
  发布完成后的只读状态，避免读者看到半完成修改。
```

如果状态天然属于某个 asyncio event loop，优先让该 loop 成为 owner。其他线程
需要触发操作时，可以使用：

```python
owner_loop.call_soon_threadsafe(callback)
```

或者：

```python
asyncio.run_coroutine_threadsafe(coro, owner_loop)
```

不能因为 CPython 有 GIL 就认为多步业务操作自动具有原子性。GIL 主要约束
同一解释器内 Python 字节码的执行，并不会把“检查条件、执行 I/O、修改多个
容器、写入证据”自动合成一个不可分割事务。

### 4.8 cancellation、timeout、deadline 与资源清理

待记录。

### 4.9 重试、指数退避、幂等与副作用

待记录。

### 4.10 checkpoint、WAL、ACK 与 crash consistency

#### 4.10.1 DataSource 游标不是训练消费进度

默认 DataSource 在调用 `get_samples()` 时就推进：

```text
sample_offset
epoch_id
sample_group_index
sample_index
```

但 fully async 中，取走任务后还要经历：

```text
已从 DataSource 取出
-> 已分派给 worker
-> 环境和 harness 正在执行
-> rollout 已完成
-> 已通过治理与组装
-> 已进入 ready queue
-> 已组成 TrainBatch
-> trainer 已确认消费
```

因此不能用 `sample_offset=101` 推断任务 100 已经进入训练。

例如任务 100 被取出后，系统在 rollout 完成前崩溃：

- 只恢复游标 101，任务 100 可能永久丢失；
- 恢复到游标 100，而任务 100 的结果其实已经持久化，可能造成重复执行。

可靠恢复至少需要同时回答：

```text
哪些任务只被分派但未完成？
哪些结果已经完成并持久化？
哪些 PromptGroup 已进入 ready queue？
哪些 batch 已经交给 trainer？
trainer 对哪些 batch 已经 ACK？
重放时用什么稳定身份去重？
```

这也是“状态保存”与“crash-consistent checkpoint”的区别。前者可能只保存
若干字段；后者要保证崩溃发生在任意一步时，恢复后不会静默丢失、重复消费或
把半完成状态误认为成功。RH2 的 fully async 身份、attempt manifest、队列
checkpoint 和消费 ACK 设计需要共同解决这件事。

### 4.11 at-most-once、at-least-once 与 exactly-once

待记录。

### 4.12 状态机、不变量、守恒式和故障注入

待记录。

### 4.13 性能观察：队列长度、等待时间与 GPU 空闲

待记录。

## 5. 待解释术语与问题

待记录。
