# verifiers v0.3.1 升级影响面 + prime-rl v0.9.0 admission gates 摘录（2026-09-02）

> 调查性质：只读对照。新仓库 checkout 在 scratchpad（`scratchpad/verifiers-latest` = tag v0.3.1 → commit b2e4e8157783，2026-08-24；`scratchpad/prime-rl-latest` = tag v0.9.0 → commit ab5de8fff44b，2026-08-25），本报告中以 `verifiers-latest/...`、`prime-rl-latest/...` 表示 scratchpad 相对路径。我方锚点：pin = 5885ab9c54152e707af2a11797aa52c3eb1752da（2026-07-03，`rh2/pyproject.toml:50-51`），本地对照副本 `reference/verifiers/`（只读，未改动）。

## 0. 版本时间线（先定坐标，破坏不是一次发生的）

| 版本 | 日期 | 与我们相关的变化 |
|---|---|---|
| （我们的 pin） | 2026-07-03 | v0.1.14（2026-05-07）之后、v0.2.0 之前一周的开发快照。Taskset 携带生命周期钩子，Task 是 pydantic 数据模型 |
| v0.2.0 | 2026-07-10 | **task-centric 重写**：`TaskData`（可序列化行数据）与 `Task`（携带 setup/finalize/score/tools 的行为类）分离，钩子从 Taskset 迁到 Task。我们锚定的 Taskset 形态在 pin 一周后就被推翻 |
| v0.2.x（untagged release，2026-07-20） | 2026-07-20 | `Taskset.load()` 惰性化（可 yield 无限任务流）；`default` harness 改名 `bash`；interception 变成可插拔配置 |
| v0.3.0 | 2026-08-07 | **多智能体**（`Agent`/`Env`/`Episode`）；**client-side tasksets**（wire 协议换血：trainer 持有 taskset，按 `task_data` 整体寄给无状态 env server）；**执行期网络隔离**（#2024、#2115：Docker/Prime 的 egress allow/block）；Trace API 改名（`error`→`last_error` 等） |
| v0.3.1 | 2026-08-24 | `@vf.intercept`/`@vf.stop` 请求拦截改写；v0 老 API 整体搬进 `verifiers.legacy`；episode/run 训练原生工件（policy span、loss-weight、稳定 task key）；ACP 持久会话 |

**先回答任务问题 3a 的总判**：`verifiers.v1` **没有**搬进 `verifiers.legacy` —— 进 legacy 的是 v0 老 API（老顶层 `verifiers/{envs,rubrics,parsers,rl,...}` → `verifiers-latest/verifiers/legacy/`，release notes v0.3.1 #2303）。v1 命名空间原地保留（`import verifiers.v1 as vf` 依然成立），但 v1 自身在 pin 之后经历了 v0.2.0/v0.3.0/v0.3.1 三轮结构重写，我们锚定的 API 大半改形。

---

## 1. 升级破坏面清单（taskset 薄壳 + 四个契约测试逐项）

判定用语：**兼容** = import 路径与语义均不变；**需改** = 概念还在但路径/签名/形态变了；**已删** = 概念本身被移除，无直接替代或替代语义不同。

### 1.1 taskset 薄壳 `rh2/src/repoharness2/taskset/swebench_smoke.py`

这是唯一的生产 import 面（envpack 库层不 import verifiers，由 `rh2/tests/envpack/test_no_verifiers_import.py` 钉死）。

| 我们用的 API | 旧路径（pin） | v0.3.1 现状 | 判定 |
|---|---|---|---|
| `import verifiers.v1 as vf` | `verifiers/v1/__init__.py` | 原地保留 | 兼容 |
| `vf.TasksetConfig` | `verifiers/v1/taskset.py:39` | 移到 `verifiers-latest/verifiers/v1/configs/taskset.py`，字段面重构为 `{id, task: TaskConfig, system_prompt}`；仍从 `vf.*` 导出 | 需改（子类自定义字段 `tasks_file/frozen_file/subset/eval_log_dir` 需按新基类重挂） |
| `vf.Task`（pydantic 模型，携带 idx/name/prompt/system_prompt/image/workdir + 我们的 instance_id 等标识字段） | `verifiers/v1/task.py` | **重写**：`Task(Generic[DataT, StateT, ConfigT])` 变成行为类，数据在 `task.data: TaskData`（`verifiers-latest/verifiers/v1/task.py:80,137`）。`SweSmokeTask` 需拆成 `SweSmokeData(TaskData)` + `SweSmokeTask(Task)` 两件套 | 需改（结构性） |
| `vf.Taskset.load_tasks() -> list` | `verifiers/v1/taskset.py:119` | `Taskset.load() -> Iterable`（可 yield，`verifiers-latest/verifiers/v1/taskset.py:51`），新增 `view/head/shuffle` | 需改 |
| `Taskset.setup/finalize(task, trace, runtime)` | `verifiers/v1/taskset.py:145,157` | **从 Taskset 移除**，变成 `Task.setup(self, trace, runtime)` / `Task.finalize(self, trace, runtime)`（`verifiers-latest/verifiers/v1/task.py:170,173`；task 即 self，不再作为参数注入） | 需改（结构性） |
| `@vf.reward` 挂在 Taskset 方法上 | `verifiers/v1/decorators.py` | 装饰器保留，移到 `verifiers-latest/verifiers/v1/utils/decorators.py`，新增 `weight`/`priority` 参数；但附着对象变成 **Task 方法**，由 `Task.score` 驱动（`verifiers-latest/verifiers/v1/task.py:179`）。注入名 `task` 现在拿到的是 `self.data`（TaskData）而非 Task 实例 | 需改 |
| `NEEDS_CONTAINER = True`（Taskset 类属性） | `verifiers/v1/taskset.py` 一带 | 移到 `Task.NEEDS_CONTAINER`（`verifiers-latest/verifiers/v1/task.py:139`） | 需改 |
| `trace.info` / `trace.record_metrics` / `runtime.write/run` | 各处 | `info`/`record_metric(s)`/`record_reward` 均保留（`verifiers-latest/verifiers/v1/trace.py:407,577-584`）；`runtime.write/run` 保留 | 兼容 |

新增且与我们相关的行为（升级时是收益也是语义变化）：
- `Task.score(trace, runtime: Runtime | None)` 支持 **runtime=None 离线评分**：runtime 依赖的 reward/metric 被跳过并打日志（`verifiers-latest/verifiers/v1/task.py:179-220`）。我们契约测试 2 断言 3（"score 在 runtime 存活期执行"）的语义仍成立于在线路径，但"评分必须有 runtime"不再是框架不变量。
- `trace.rewards` 从 `dict[str, float]` 变成 `dict[str, Reward | None]`（`Reward{score, weight}`，`verifiers-latest/verifiers/v1/trace.py:402` 与 Reward 类定义）；未评分的键先 seed 为 None。所有直接比对 rewards dict 的代码要跟着改。
- `TaskData` 新增 `network_allow/network_block`（见 §2）与 `artifacts: list[Artifact]`（声明的路径从一个 runtime 收集、在另一个 runtime 恢复，外加 `/logs/artifacts/` 约定目录，`verifiers-latest/verifiers/v1/task.py:108-115` + `verifiers/v1/utils/artifacts.py` 的 `collect/restore`）。后者正对我们 S1-4 "clean-checkout 重放评分"的搬运需求。

### 1.2 契约测试 1：`rh2/tests/contract_verifiers/test_graph_token_identity.py`

| 锚定 API | v0.3.1 现状 | 判定 |
|---|---|---|
| `verifiers.v1.graph` 的 `prepare_turn/commit/message_hash` | 名称与职责保留（`verifiers-latest/verifiers/v1/graph.py:228,316,401`）；`PendingTurn` 加强为带 `prefix_node_ids/path_len/previous_token_ids`（renderer bridge 锚点） | 兼容（函数面） |
| `vf.Trace(task=vf.Task(idx=0, prompt="x"))` | `Trace.task` 变成 `TraceTask{type, data, key, hash}` 包装（`verifiers-latest/verifiers/v1/rollout.py:85-91` 的构造现场） | 需改（测试脚手架） |
| `vf.Response(id, created, model, message, finish_reason, tokens)` | 字段完全一致（`verifiers-latest/verifiers/v1/types.py` 的 `Response`） | 兼容 |
| `TurnTokens`（prompt_ids/completion_ids/completion_logprobs/message_spans） | 保留于 `verifiers/v1/types.py` | 兼容 |
| `MessageNode` 及 `sampled/mask/logprobs/token_ids` | 保留；基类从 StrictBaseModel 改 BaseModel，**新增训练字段** `advantages: list[float] | None`（`verifiers-latest/verifiers/v1/graph.py:104`）、`calls: list[ModelCall]` 等 | 兼容（断言面），注意新字段 |
| `num_branches/branches/nodes` 与三条不变量（drift fork / 拼接恒等式 / mask-logprobs 对齐） | 语义仍是框架核心不变量；Branch 新增 KeptTokens/ModelCall 归因 | 测试语义可整体迁移，构造代码需改 |

### 1.3 契约测试 2：`rh2/tests/contract_verifiers/test_rollout_lifecycle.py`

| 锚定 API | v0.3.1 现状 | 判定 |
|---|---|---|
| `vf.Rollout` + `Rollout(task, taskset, harness, ctx, runtime_config).run()` | 不再从 `vf.*` 导出；类原地重写为 open/step/abort/close 增量生命周期，构造签名 keyword-only：`Rollout(*, task, agent_config, harness, ctx: ModelContext, runtime_config, timeouts: RolloutTimeouts, limits: RolloutLimits, ...)`，**不再接 taskset**（`verifiers-latest/verifiers/v1/rollout.py:54-140`）。上层驱动者变成 `Env.run_episode`（`verifiers-latest/verifiers/v1/env.py:242`） | 需改（结构性重写） |
| `RolloutContext`（clients/client.py） | 已删，替代 `ModelContext`（`verifiers-latest/verifiers/v1/clients/client.py:84`） | 已删/改名 |
| 调用序 `taskset.setup → harness.setup → launch → finalize → score` | 阶段概念保留但归属重排：`task.setup → harness.setup → launch/session → task.finalize → task.score`；`Harness.launch` 签名新增 `data: TaskData` 参数（`verifiers-latest/verifiers/v1/harness.py:263-271`），并引入 `HarnessSession`/`resume`/`cleanup`（ACP 持久会话，v0.3.1 #2291） | 需改 |
| `trace.error.type == "HarnessError"` | `trace.error` → `errors: list[Error]` + `last_error` property（`verifiers-latest/verifiers/v1/trace.py:421,551`；v0.3.0 改名 `capture_error`→`record_error`）；`HarnessError` 本身保留（errors.py） | 需改 |
| `vf.Harness/vf.HarnessConfig/SubprocessConfig/ProgramResult` | 均保留（HarnessConfig 移到 `configs/harness.py` 但仍导出；runtimes 导出面不变） | 兼容 |
| `trace.rewards == {"name": 1.0}` | Reward 对象化（见 §1.1） | 需改 |

### 1.4 契约测试 3：`rh2/tests/contract_verifiers/test_envserver_wire.py`

破坏最彻底的一个 —— v0.3.0 "client-side tasksets"（#2039）把协议方向翻转了。

| 锚定 API | v0.3.1 现状 | 判定 |
|---|---|---|
| `verifiers.utils.serve_utils.msgpack_encoder` | 顶层 `verifiers/utils` 随 v0 进 legacy；训练侧编码器在 `verifiers-latest/verifiers/v1/serve/encoding.py:26`（同名函数） | 需改（import 路径） |
| `InfoRequest/InfoResponse`（num_tasks、requires_group_scoring） | **已删**。taskset 在 client 侧，server 无任务清单可报；group scoring 概念整体移除 | 已删 |
| `RunRolloutRequest{task_idx,...}` / `RunGroupRequest{task_idx, n,...}` | **已删**。替代：`RunRequest{task_data: dict, client, model, sampling}` —— client 把 TaskData 整体 dump 寄给 server，server 用 taskset 声明的类型 validate 重建（`verifiers-latest/verifiers/v1/serve/types.py:42-51`、`serve/server.py:79`）。task 身份从"行号"变成"内容"（resume 按 task content key 匹配） | 已删/换协议 |
| `RunRolloutResponse{trace}` / `RunGroupResponse{traces}` | **已删**。替代：`RunResponse{episode: WireEpisode}` —— 一次 env-rollout 返回一个 Episode（`{id, env, task, group, run, ok, errors, traces}`，`verifiers-latest/verifiers/v1/episode.py:86-103`） | 已删/换协议 |
| `method` 作为 ClassVar 走独立 ZMQ 帧路由、不进 payload | 机制原样保留（`verifiers-latest/verifiers/v1/serve/types.py:10-13`） | 兼容 |
| `EnvServer(EnvConfig(taskset={"id":...}), address="tcp://...:0")` + `:0` 端口解析 | 构造形态相近；`:0` 解析行为保留（`LAST_ENDPOINT`，`verifiers-latest/verifiers/v1/serve/server.py:60-63`）；新增 `max_concurrent` 与 `cancel` 方法（in-flight run 可中止） | 兼容（构造）/新增 |
| `EnvClient.health/wait_for_server_startup` | 保留；`info()` 已删，新 `run()`（`verifiers-latest/verifiers/v1/serve/client.py:140-161`） | 部分已删 |
| `@group_reward` / `score_group` / `requires_group_scoring`（fixture `contract_wire_group_taskset` 锚定） | **概念整体删除**（新 v1 全树 0 命中）。组级判断迁出 verifiers：进 `Env.finalize`（跨 agent 判定）或训练框架侧（prime-rl 的 `algo.finalize_group` + admission gate，见 §3） | 已删 |
| `WireTask` 吸收未知字段 | 改名 `WireTaskData`（`verifiers-latest/verifiers/v1/task.py:127`，extra="allow" 语义保留）；Episode/Trace 侧对应 `WireEpisode/WireTrace` | 需改 |
| taskset 插件按模块名解析（fixtures 挂 sys.path） | loaders 移到 `verifiers-latest/verifiers/v1/utils/loaders.py`；v0.3.1 起**不再自动安装 Hub 插件**，id 必须是已安装包（#2390）。本地 sys.path 注入方式需重验但原理仍在 | 需改（需验证） |
| `state` 不上线（transient） | Trace 仍以 state 为 transient；序列化面另有 `TRACE_VERSION` 版本号新增 | 兼容（需回归确认） |

### 1.5 契约测试 4：`rh2/tests/contract_verifiers/test_trainclient_protocol.py`（Form A：verifiers TrainClient + vLLM shim）

物理协议面（我们最关心的 wire 形状）**基本没动**，注入面全变。

| 锚定 API | v0.3.1 现状 | 判定 |
|---|---|---|
| POST `/inference/v1/generate` 挂服务根、token-in（`token_ids` 不带 `messages`） | 原样（`verifiers-latest/verifiers/v1/clients/train.py:1,307`） | 兼容 |
| `SESSION_ID_HEADER = "X-Session-ID"` | 原样（`verifiers-latest/verifiers/v1/clients/client.py:16`） | 兼容 |
| sampling_params 强制 `stop_token_ids` + `logprobs=1`、token-out 逐 token logprobs 对齐 | 该逻辑在外部 `renderers.client.generate` 中，机制保留（train.py:355,425 调用） | 兼容（依赖 renderers 版本） |
| `TrainClient(openai: AsyncOpenAI, pool_size=...)` | `TrainClient(config: TrainClientConfig)`，OpenAI client 内部构建（`verifiers-latest/verifiers/v1/clients/train.py:313`） | 需改 |
| 私有钩子 `_renderer_pool`（我们测试注入 FakeRenderer 的唯一口子） | **已删** —— 换成进程级 `ElasticRendererPool`（train.py:213），warm 由 config 驱动。我们测试 docstring 里"升级时若该钩子改名/改签名，本测试会立即失败提示适配"——正是现在 | 已删（注入面需重设计） |
| `get_response(dialect, body, model, sampling, session_id)` | `get_response(dialect, body, sampling, session_id, turn: PendingTurn | None, headers)` —— `model` 移进 config，新增 `turn`（拦截改写产物：被拦截轮已持有 typed prompt）；非 ChatDialect 显式 `NotImplementedError`（train.py:325-347） | 需改 |
| `TrainClientConfig`（base_url/api_key_var/pool_size） | 移到 `verifiers-latest/verifiers/v1/configs/client.py`；**`pool_size` → `multiplex`，语义反转**（旧 = renderer 数量；新 = 每 renderer 并发 rollouts，默认 256；v0.3.0 #2218 breaking 注明） | 需改（语义反转，值不能照抄） |
| interception endpoint/secret（lifecycle 测试断言 launch 收到 http endpoint + 非空 secret） | 单 secret → `Slot = (base_url, model_secret, state_secret)` 能力分离（model 推理与 task state 分开授权，`verifiers-latest/verifiers/v1/interception/base.py:30-33`）；`register` 返回二元组（server.py:183） | 需改 |

**3c 专答（v0.3.1 拦截改写 + episode artifacts 改了哪些文件、对 Form A 协议的影响）**：
- 拦截改写（#2164/2165/2166/2229/2178）：新增 `verifiers-latest/verifiers/v1/interception/base.py`（Interception 抽象 + 三种形态 Server/StaticPool/ElasticPool）、`interception/tool.py`（经拦截面提供 server-side tool）、`interception/tunnel/{base,custom,prime}.py`（远程 runtime 隧道）；`interception/server.py` 重写（`record_call` 把每次调用记成 `ModelCall` 入 trace、`mediate_capabilities`、双 secret）；`@vf.intercept`/`@vf.stop` 钩子挂在 Task 上，按 typed `vf.Request`/`vf.Response` 边界改写或截停（`verifiers-latest/verifiers/v1/utils/decorators.py:96-104`；Rollout 构造时 discover，`rollout.py:99-127`）。**对 Form A 契约的净影响**：`/inference/v1/generate` 请求体、X-Session-ID、token-in/out 形状不变；变的是拦截服务器与 TrainClient 的内部分工（PendingTurn 直通、raw 响应由框架序列化而非中继）以及自定义 Dialect 义务（必须实现 request/response rewriting，v0.3.1 breaking 注明）。另有一条行为红线：**retry 重放要求 `x-stainless-retry-count` 头，缺失则重采样而非重放**（#2368）——对训练一致性敏感，升级后要进契约。
- 训练原生 episode artifacts（#2278/2357/2358/2409/2429）：`verifiers-latest/verifiers/v1/episode.py`（Episode 必带 task；`TrainRunInfo/EvalRunInfo` + `TrainWorkInfo.step` + `PolicySpan{start,end}` 政策版本区间；run 数据从 `Trace.run` 移到 `Episode.run`）；`traces.jsonl` 每行一个 Episode；`MessageNode.advantages` 等训练字段进图（graph.py:104）。裸 trace JSONL 输入被移除 —— 任何消费我们 dump 的下游若对齐上游格式，都要按 Episode 重排。

---

## 2. 网络隔离结论（3b 专答）

**旧 pin 的已知问题确认**：`reference/verifiers/verifiers/v1/runtimes/docker.py:99-102`（`--network host` 参数对在 101-102 行，`docker run` 调用起于 98 行）无条件 `docker run --network host`（agent 容器与宿主同网络栈，零隔离）。

**v0.3.1 现状**（隔离主体在 v0.3.0 #2024/#2115 落地，v0.3.1 #2298/#2299 修补 CONNECT 与 provider escape）：

1. **配置面**：`NetworkPolicyConfig`（`verifiers-latest/verifiers/v1/configs/runtime.py:32`）：`allow: ["*"]`（默认不限制）/`block: []`；`network_restricted` 当且仅当 allow 收窄或 block 非空；concrete allow 与 block 互斥（`[]`/`"*"` in block = framework-only）。`DockerConfig` 直接继承它（`verifiers-latest/verifiers/v1/runtimes/docker/__init__.py`，docker.py 已改为 `docker/` 目录）。**每任务叠加面**：`TaskData.network_allow/network_block`（`verifiers-latest/verifiers/v1/task.py:100-108`）—— 任务可申请/禁止执行期目的地，与 runtime 策略合成。
2. **强制机制**（restricted 时，`runtimes/docker/__init__.py:217-232,346-398`）：`--network bridge` + `--cap-drop NET_ADMIN,NET_RAW` + `--security-opt no-new-privileges` + 禁 IPv6；宿主进程内跑 `EgressProxy`（`runtimes/docker/egress.py` 的 `NetworkPolicy`，allowlist 判定 `permits(scheme, host, port)`）；Linux 用 fd-passing 把 proxy listener 塞进容器 netns，macOS 走 host-gateway。
3. **network cut**：`prepare_execution(routes)` 在 agent 启动前最后一步执行 —— 删默认路由、blackhole Docker DNS(127.0.0.11)、iptables OUTPUT 只放行 proxy —— 此后容器唯一出网通道是策略代理；framework routes（interception/MCP endpoint）是不可 block 的不变量（egress.py 注释明示）。setup 阶段保持 trusted 开放（`prepare_setup`，`runtimes/base.py:352-358`）。
4. **结论**：`--network host` 不再是唯一硬编码行为，但**默认配置（allow=["*"]）仍精确等价旧行为**（`__init__.py:233-234` 的 else 分支）。隔离是 opt-in：要收网必须显式配 `allow` 列表或 block。对 rh2 的意义：官方能力面首次覆盖我们 A4/安全边界关心的"agent 执行期断外网、评分链路白名单"，且与任务级声明（TaskData）打通；但它保护的是 egress，不解决我们同容器评分的篡改问题（那仍归 S1-4 clean-checkout 与 hygiene）。

---

## 3. prime-rl v0.9.0 admission gates / composable curricula / task sampling 摘录（3e 专答）

依赖关系先说清：prime-rl v0.9.0 要求 `verifiers[harbor]>=0.3.1`（`prime-rl-latest/pyproject.toml:29`）——它的 gate 直接消费 `vf.Episode`/`trace.agent.trainable`/`MessageNode.advantages`，**离开 v0.3.1 的 Episode 工件无法照搬**。

### 3.1 核心接口

**AdmissionGate**（`prime-rl-latest/src/prime_rl/orchestrator/curriculum/gates/base.py`）：

```python
class AdmissionGate:
    def admit(self, group: list[vf.Episode]) -> bool: ...   # 组粒度判定
    def state_dict(self) -> dict: ...                        # 断点续训状态
    def load_state_dict(self, state_dict) -> None: ...
    def metrics(self) -> dict[str, float]: ...               # 按 gate 命名空间上报
```

内置唯一实现 **AdvRangeGate**（`gates/adv.py`）：遍历组内所有"非 error 且 `trace.agent.trainable`"trace 的 `node.advantages`，若**全部**落在 `[reject_min, reject_max]`（默认 `[0,0]`）则拒——即 GRPO 组内 reward 全同、advantage 全零、无学习信号的组；没有 advantage 流的组放行。配置 `AdvRangeGateConfig{type:"advantage_range", reject_min, reject_max}`（`prime-rl-latest/packages/prime-rl-configs/src/prime_rl/configs/orchestrator.py:204`）。

**Curriculum 组合**（`curriculum/base.py`）：`Curriculum = 1 个 TaskSampler + N 个命名 gate（AND 合取）`，per-env 一个（`CurriculumConfig{sampler, gates: dict[str, GateConfig]}`，orchestrator.py:220）。`on_result(group)` 先做组一致性校验（非空、Task.key 齐一），**先 `sampler.observe(group)` 再评所有 gate** —— 也就是说被 gate 拒绝的组仍然喂给 curriculum 学习难度。

**TaskSampler**（`curriculum/samplers/base.py`）：`Iterator[vf.Task]` + `observe(group)` + `state_dict/metrics`。两个实现：
- `StandardSampler`（samplers/standard.py）：有限任务集按源序 cycle（key 唯一性校验），cursor 进 checkpoint；无限迭代器直接透传。
- `DifficultyPoolSampler`（samplers/pool.py）：每任务记"最近一组 trainable trace 的平均 reward"，按池阈值归池（默认 hard≤0.25 权重 0.2 / normal≤0.75 权重 1.0 / easy≤1.0 权重 0.2，orchestrator.py:170-176），加权随机采样；未见过的任务中性权重 1.0（观察即时生效，不用全集扫一遍）；`task_rewards` + RNG state 进 checkpoint。

### 3.2 在训练循环中的生效位置

链路（自上而下）：`TrainSource`（`prime-rl-latest/src/prime_rl/orchestrator/train_source.py`）按 `env.config.ratio` 加权混采多个 train env，每 env 持一个 Curriculum；`next_task(step)` 从对应 sampler 取任务发 dispatch。回程在 **TrainSink**（`prime-rl-latest/src/prime_rl/orchestrator/train_sink.py:226-292` 的 `process_group`）：

1. 组闭合（该 task 的全部 episode 到齐/取消/失败记账，n_owed 含取消尾巴）；
2. **stale 取消组旁路 curriculum**（"a pipeline decision is not a task result"——异策版本过期是管线决定，不进 sampler.observe 也不进 gate）；
3. `survivors` = 非 error 且 trainable 的 trace；
4. **先** `env.algorithm.finalize_group(group)` 算 advantage（写进 `MessageNode.advantages`，`orchestrator/algo/routing.py:33`）；
5. **后** `_admit(group)` → `TrainSource.on_result` → `Curriculum.on_result`（observe + gates AND）；
6. 拒绝组/无 survivor 组：静默排出 + `_record_zero_output` 记入零产出预算，连续零产出达到 batch 等价物上限触发告警/熔断（train_sink.py:317-345 的 `MAX_CONSECUTIVE_ZERO_OUTPUT_BATCH_EQUIVALENTS`）；
7. 通过才 `trace_to_samples` 进 pending batch。

### 3.3 与我们 TrainingEligibilityGate 七维的层次对比

我方实现：`rh2/src/repoharness2/governance/gate.py`（七维事实合取 → 三档资格 + 组修复信号，wrapper 唯一入口）；七维 = `token_provenance / logprob_alignment / loss_mask_integrity / reward_scope / security_and_leakage / clean_grading / policy_staleness`（gate.py:97-103），降级地板分两档（前者摧毁 online 资格落 `offline_or_sft_candidate`，后四维落 `audit_only_or_rejected`，gate.py:108-114）；06 计划附录 A 进一步把降级原因映射到三终态（① typed raise 停训 / ② ABORTED / ③ completed-ineligible 整组排除，`docs/agentic_RL/repo_harness_rh2_workstreams/06-first-training-local-execution-plan.md:148-167`）。

| 维度 | prime-rl AdmissionGate | rh2 七维 gate |
|---|---|---|
| 回答的问题 | "这组**值不值得学**"（学习信号/curriculum 价值） | "这条轨迹**有没有资格进 loss**"（token/reward/安全事实可信性） |
| 输入前提 | Episode 已被当作可信（仅 `has_error`/`trainable` 粗滤） | 不预设可信，逐维核事实，fail-closed |
| 粒度 | 组（list[Episode]）→ bool 二值 | 逐轨迹三档 + 组修复信号（GRPO n=8 降级对装配可见） |
| 失败处置 | 一律静默丢组 + zero-output 预算熔断 | 分责：系统坏 → fatal 停训；执行无产物 → ABORTED；完整但不合格 → ineligible 排除 |
| 覆盖面 | advantage 全零一种（可扩展但 v0.9.0 仅此一个） | provenance/logprob/mask/reward 归因/安全泄漏/评分链完好/staleness 七面 |
| 没覆盖的 | 样本可信性全部（provenance 污染的组只要 advantage 非零照进 batch） | advantage-zero 过滤与难度采样（我方设计里归算法语义 A6/A8 与数据侧，不在 gate 职责内） |
| checkpoint | sampler+gate state_dict 全量入 ckpt | EligibilityReport sidecar 以 id 关联 Trace/Sample |

**结论：两层正交互补，不存在"他们的 gate 能替我们的 gate"**。prime-rl 的 admission 是 curriculum/训练价值层，站在我们 gate 的下游（等价于我们 ③ completed-ineligible 之后、装 batch 之前再加一道"有没有信号"的筛选）。可借鉴的具体件：
1. `state_dict/load_state_dict/metrics` 的极薄 gate 接口 + 按名字命名空间上报（`curriculum/gate/<name>/*`）——我们的 gate 若要进断点续训，这个形状值得抄；
2. **zero-output 预算熔断**（拒绝不是免费的：按 batch 等价物计数，连续零产出即告警/abort）——与我们协议"新增拒绝路径必须登记剔除面"同源，且给了一个可运行的量化实现；
3. **stale 旁路 curriculum** 的边界划分（管线决定不算任务结果）——对应我们维度 7 policy_staleness 的 finalize-time/consume-time 拆分（06 计划 D1②），双方结论一致，可作外部佐证；
4. advantage 在 admission **之前**算好、gate 读现成事实——与我们"gate 只合取事实、不产事实"的原则一致。

---

## 4. 升级建议

**背景事实**（决定权重）：Form B（slime `custom_generate` 直调 SGLang）是训练主线，Form A（verifiers TrainClient + vLLM shim）只是协议基线/调试路径（`docs/agentic_RL/repo_harness_rh2_workstreams/00-project-status.md:72`）；生产 import 面只有 `swebench_smoke.py` 一个文件，envpack 库层框架无关已钉死。

### 方案对比

**A. 现在升到 v0.3.1**
- 代价：一次吃下三轮重写。taskset 薄壳结构性重写（Taskset→Task+TaskData 两件套）；四个契约测试全部重写（其中 wire 测试是换协议级别）；`renderers` 需从 `>=0.1.8.dev40` 跟到 `>=0.1.10`（`reference/verifiers/pyproject.toml:54` vs `verifiers-latest/pyproject.toml:54`）；8 题 smoke 回归基线需重建可对照性。按协议这是 T0（改公共 schema/协议 + 重要依赖变更）。首训冻结期（06 计划 Wave 执行中）插入此变更与"先训起来"目标直接冲突。
- 收益：官方网络隔离（§2）、artifacts 跨容器搬运（对 S1-4 clean-checkout 是现成轮子）、离线重评分（score runtime=None）、Episode/PolicySpan 训练原生工件、`@intercept` 钩子、client-side taskset（trainer 持任务，与我们治理层站位同构）。

**B. 不升，pin 不动**
- 代价：上游 7 周三轮重写的速度意味着差距只会拉大；prime-rl 生态（admission gate 等）都建在 ≥0.3.1 上，想复用其代码必须跨版本。旧 pin 的 `--network host` 问题继续存在（但我们 agent 容器策略本就不依赖 verifiers 的 docker runtime 做安全边界）。
- 收益：零迁移成本，8 题回归基线与全部 S0/S1 契约保持有效；首训不受扰动。

**C. 部分升 / 思想先行（推荐）**
1. **首训冻结期内 pin 不动**（B 的纪律）：升级是 T0，且当前没有任何 Wave 依赖新版能力。
2. **本报告的 API 对照表入库作为迁移地图**（已完成，即本文件）：四个契约测试的 docstring 里"升级 verifiers 前必须重新验证"的清单，逐项有了新旧路径对照。
3. **训后窗口做受控升级 spike**：顺序建议 taskset 薄壳（Task/TaskData 拆分）→ 契约测试 1/4（语义不变量可整体迁移）→ 契约测试 2/3（按新生命周期与 Episode 协议重写）→ 8 题 smoke 全量回归对照。预期主要工作量在测试而非生产代码（生产面一个文件）。
4. **两件事不等升级、现在就吸收为设计输入**：(a) 网络隔离的配置形状（allow/block + 任务级声明 + framework routes 不可 block + trusted setup/cut 分相）可对照我们 W3b 正向能力事实的设计；(b) prime-rl 的 zero-output 预算熔断与 gate state_dict 形状，作为我们 gate 断点续训与剔除面监控的参考实现。均不产生依赖。
5. **若未来接 prime-rl 编排**（目前无此计划），verifiers ≥0.3.1 是硬前置，届时 A 的成本必须付——这是"以后还能改，但改的成本随上游继续漂移单调上升"的一项。

### 本次调查没有改变的已定案语义
- Form B 训练主线地位、envpack 不 import verifiers 的隔离、七维 gate 三档语义、8 题 smoke 冻结基线——均未受本报告影响；报告只新增外部事实，无任何仓库代码/配置改动（除本报告文件本身）。
