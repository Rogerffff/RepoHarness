# S0-2 verifiers 行为契约基线（contract_baseline）

日期：2026-07-07。pin：`verifiers @ 5885ab9c54152e707af2a11797aa52c3eb1752da`（rh2/pyproject.toml git 依赖）。

本文是升级 verifiers 前的核对表：`rh2/tests/contract_verifiers/` 下四个测试文件断言的是"rh2 依赖的 verifiers 行为"，不是 verifiers 的全部行为。**升级 verifiers 时先跑这套测试（`cd rh2 && uv run pytest tests/contract_verifiers -q`），任何一条失败都说明我们依赖的行为变了，必须先评估再升级。**

---

## 1. 上游 smoke 结果

按计划先在 `reference/verifiers` checkout 里跑上游自带测试（git 依赖安装不带 tests 目录，所以必须在 checkout 里跑）：

```bash
cd reference/verifiers
uv run --frozen pytest tests/v1/test_graph.py tests/v1/test_trace.py -q
# 结果：9 passed in 0.01s（test_graph.py 6 个 + test_trace.py 3 个，全绿）
```

两点环境事实（详见第 4 节发现 1/2）：

- verifiers pyproject 有 `[tool.uv] required-version = ">=0.11.1"`，本机全局 uv 是 0.10.11，直接跑会被拒。smoke 用的是装到 scratchpad 的 standalone uv 0.11.26（未改动全局 uv；rh2 自己的环境在 uv 0.10.11 下正常工作）。
- `reference/verifiers` 工作树带本地中文阅读注释（git status 显示 9 个文件 modified）。已用 AST 对比逐文件核实：与 HEAD（5885ab9c）相比**只有注释/docstring 差异，无任何代码逻辑差异**，因此 smoke 结果对 pin 的干净版本有效。核对方法：对每个 modified 的 .py 文件，把 `git show HEAD:<file>` 与工作树版本分别 `ast.parse` 后清空 docstring 再 `ast.dump` 对比，全部输出 SAME。

## 2. rh2 契约测试全景

位置：`rh2/tests/contract_verifiers/`（4 个文件、17 个用例）+ 两个 fixture 插件模块 `rh2/tests/fixtures/contract_wire_taskset.py`、`contract_wire_group_taskset.py`。

运行条件：纯本机——不调任何网络模型 API、不需要 docker（runtime 只用 subprocess）、不下载 tokenizer（renderer 用确定性 fake）。唯一的"网络"是 127.0.0.1 上的 ephemeral 端口（interception server、假 generate 引擎、ZMQ EnvServer）。

## 3. 依赖行为清单（升级 verifiers 时逐条核对）

### 3.1 test_graph_token_identity.py — Trace 图的 token identity（4 用例）

| # | 我们依赖的行为 | 出处（5885ab9c） |
| --- | --- | --- |
| G1 | message 文本相同（`graph.message_hash` 相等）但 token ids 漂移时，`PendingTurn.commit` 按 token identity 在分歧节点 fork 出新分支（`num_branches` 从 1 变 2），**绝不静默复用旧前缀** | `graph.py:_commit_turn` 的 token-based prefix reuse 段（约 449-475 行） |
| G2 | fork 后：原采样 assistant 节点的 token_ids/mask/logprobs 原样保留；漂移版本以输入消息身份入图（`sampled=False`、mask 全 False、无 logprobs）——漂移 token 永不进入可训练区 | 同上 |
| G3 | 沿一条 Branch 依次拼接节点 `token_ids`，精确等于该轮模型看到的 `prompt_ids + completion_ids`；节点存的是"自己新增的 token 增量"（前导脚手架并入下一条消息，generation prompt 归 assistant 节点） | `graph.py` 模块 docstring + `_commit_turn` |
| G4 | 节点级对齐：assistant 节点 `mask == [False]*len(gen_prompt) + [True]*len(completion)`；`len(node.logprobs) == sum(node.mask)`；输入节点 mask 全 False、logprobs 空 | `graph.py:_commit_turn` assistant 节点构造 |
| G5 | 分支级对齐：`len(token_ids) == len(sampled_mask) == len(logprobs)`；logprobs 只在采样位有值、其余补 0.0、顺序与采样顺序一致（注意分支级属性名是 `sampled_mask`，节点级才叫 `mask`） | `trace.py:Branch.token_ids/sampled_mask/logprobs` |
| G6 | prompt 里伪造的 assistant/tool 消息（few-shot / fabricated context）`sampled=False`，不计入 `num_turns`、不进 `assistant_messages`——`sampled` 是采样出处标记，不能靠 role 推断 | `graph.py:MessageNode.sampled` docstring |

### 3.2 test_rollout_lifecycle.py — Rollout 生命周期与 runtime 归属（4 用例）

用自写 SpyTaskset + FakeHarness（不调模型）驱动真实 `Rollout.run()`，subprocess runtime。

| # | 我们依赖的行为 | 出处 |
| --- | --- | --- |
| R1 | 调用序固定：`taskset.setup → harness.setup → harness.launch → taskset.finalize → taskset.score(@reward)`（比执行计划的简写多一个 `harness.setup` 阶段，见发现 3） | `rollout.py:Rollout.run` |
| R2 | `Taskset.setup` 基类签名是 `(self, task, trace, runtime)`（F6 的 trace 参数），框架用 `invoke()` 按参数名注入——trace 在 setup 时已存在，taskset 可以往 trace/state 写 per-rollout 状态；setup 收到的 trace 就是 run() 最终返回的对象 | `taskset.py:145`、`decorators.py:invoke`、`rollout.py:199-202` |
| R3 | harness.launch 收到 Rollout 注入的 interception `endpoint`（`http://127.0.0.1:<port>/v1`）与非空 bearer `secret`——黑盒 harness 可训练的边界 | `rollout.py:_serve_interception` |
| R4 | harness 抛错：错误经 boundary 归因为 `HarnessError` 记到 `trace.errors`（`trace.error.type == "HarnessError"`、`stop_condition == "error"`、`is_completed == True`），`Rollout.run()` **正常返回 trace 不向外抛**（坏 rollout 是数据不是 crash）；finalize/score 被跳过 | `rollout.py:314-324`、`errors.py:boundary` |
| R5 | 无论成败，runtime 都在 `finally` 中 teardown（subprocess：`/tmp/<trace.id>` workdir 被删除；`rollout.runtime` 引用在创建瞬间就已设置、始终可 teardown） | `rollout.py:325-343`、`runtimes/subprocess.py:cleanup` |
| R6 | per-rollout scoring 在 runtime 存活期执行：`@reward` 声明 `runtime` 参数即可在评分时 `runtime.run()` 真实执行命令（rh2 评分设计 5.2 的前提）；reward 以函数名记入 `trace.rewards` 并求和进 `trace.reward` | `rollout.py:298-312`、`taskset.py:score` |
| R7 | 正常完成路径：harness 程序 exit 0 后 `trace.stop_condition == "agent_completed"` | `harness.py:Harness.run` |

### 3.3 test_envserver_wire.py — EnvServer/EnvClient wire 协议（6 用例）

| # | 我们依赖的行为 | 出处 |
| --- | --- | --- |
| W1 | 请求打包：`msgpack.packb(req.model_dump(mode="json"))`；`method` 是 ClassVar 不进 payload（作为独立 ZMQ 帧路由：请求帧 `[request_id, method, payload]`）；`RunRolloutRequest.method == "run_rollout"`、`RunGroupRequest.method == "run_group"` | `serve/types.py:BaseRequest`、`serve/client.py:_request` |
| W2 | `RunRolloutRequest`（task_idx/client/model/sampling）msgpack 往返后逐字段相等；`client` 判别式 union 正确收窄回 `TrainClientConfig`（train 特有字段 pool_size 等不丢）；`SamplingConfig` extra="allow" 的透传字段（如 seed）无损 | `serve/types.py`、`clients/config.py`、`types.py:SamplingConfig` |
| W3 | 响应打包：`msgpack.packb(resp.model_dump(mode="python"), default=msgpack_encoder, use_bin_type=True)`；Trace 的训练关键字段全部无损往返：节点 token_ids/mask/logprobs/sampled/finish_reason/usage、rewards/reward、stop_condition/is_completed、info、trace.id；对端重算的派生量一致（num_branches/num_turns/branches[0].token_ids） | `serve/server.py:_handle`、`serve/types.py:RunRolloutResponse._ser_trace` |
| W4 | transient `state` 不上线（`model_dump` 排除）；客户端拿到 `Trace[WireTask]`，taskset 自有 Task 字段进 `task.model_extra`（不需要导入 taskset） | `trace.py:state Field(exclude=True)`、`task.py:WireTask` |
| W5 | 失败响应是数据：`BaseResponse(success=False, error=...)` 往返无损（EnvClient 对 success=False 抛 RuntimeError 而不是丢状态） | `serve/types.py:BaseResponse`、`serve/client.py:152-154` |
| W6 | in-proc `EnvServer(config, address="tcp://127.0.0.1:0")` 绑定后 `server.address` 解析出真实端口（不再以 `:0` 结尾）；`EnvClient.wait_for_server_startup`/`health()` 可用；`info()` 返回 `num_tasks == len(load_tasks())` | `serve/server.py:108-110`、`serve/client.py` |
| W7 | `info().requires_group_scoring == taskset 是否定义 @group_reward`（True 时调度器必须走 run_group） | `serve/server.py:94-96` |
| W8 | taskset 插件解析：本地平面模块（sys.path 可导入、`__all__` 导出恰好一个 Taskset 子类）可直接作 `taskset.id`；无 bundled harness 时默认 harness id 为 "default" | `loaders.py:_import_plugin/_plugin_class/default_harness_id` |

### 3.4 test_trainclient_protocol.py — TrainClient token-in/token-out（3 用例）

本地 aiohttp 假引擎记录请求；renderer 用确定性 FakeRenderer（选择理由见发现 4）。

| # | 我们依赖的行为 | 出处 |
| --- | --- | --- |
| T1 | 请求走 token-in：POST `{base_url 去掉 /v1}/inference/v1/generate`（挂服务根，不在 /v1 下），body 为 `{"model", "token_ids": <renderer 渲染的 prompt ids>, "sampling_params"}`，**不含文本 messages** | `renderers/client.py:generate`（246-281 行） |
| T2 | sampling_params：caller 参数透传（temperature/max_tokens），但 `stop_token_ids`（取自 renderer）与 `logprobs=1` 强制覆写，`skip_special_tokens` 默认 False | `renderers/client.py:241-244` |
| T3 | `session_id` 通过 `X-Session-ID` 头透传（rollout 亲和路由，KV cache 复用前提） | `clients/client.py:SESSION_ID_HEADER`、`clients/train.py:311` |
| T4 | 请求前会 GET `/v1/models` 预检 `max_model_len`（拿不到则缓存 None 静默禁用预检，不影响主请求） | `renderers/client.py:_resolve_max_prompt_len` |
| T5 | 响应解析：`choices[0].token_ids` → `Response.tokens.completion_ids`；`choices[0].logprobs.content[*].logprob`（ChatCompletionLogProbs 展平形状）→ `completion_logprobs`，长度与 completion_ids 一致、逐 token 对应；`prompt_ids` 回填渲染时的 token ids | `renderers/client.py:283-293`、`clients/train.py:response_from_generate` |
| T6 | assistant 消息内容来自 `renderer.parse_response(completion_ids)`（token-out 驱动，不是文本中继）；usage 由 token 计数得出；`Response.raw` 回填 chat.completion 兼容 dict（interception server 原样交给 harness 程序） | `clients/train.py:response_from_generate/serialize_completion` |
| T7 | renderer 归因（RenderedTokens）转成 `TurnTokens.message_spans`（每消息 token 区间；generation prompt 不归属消息） | `clients/train.py:121-127`、`renderers/base.py:message_token_spans` |
| T8 | 闭环：TrainClient 的 Response commit 进 Trace 图后，分支 token 拼接 == prompt_ids + completion_ids，sampled_mask/logprobs 落位正确（即 3.1 的不变量对 TrainClient 输出成立） | `graph.py` + `clients/train.py` |

## 4. 发现（与执行计划描述不符 / 执行中确认的事实）

1. **上游 smoke 的 uv 版本门槛**：计划写"在 reference/verifiers 里 `uv run pytest`"，但该 checkout 的 pyproject 有 `[tool.uv] required-version = ">=0.11.1"`，本机全局 uv 0.10.11 直接被拒（`error: Required uv version >=0.11.1 does not match ...`）。处理：装 standalone uv 0.11.26 到 scratchpad 只用于该 checkout（`curl -LsSf https://astral.sh/uv/install.sh | UV_INSTALL_DIR=<scratchpad> sh`），未动全局 uv、未改 reference/ 任何文件。**GPU 机注意**：租机 checklist 第 6 步跑的是 rh2 契约测试（uv 0.10.11 即可）；若还要在 GPU 机重复上游 smoke，需要 uv>=0.11.1。附带发现：uv 0.11.x 的项目 `.venv` 是指向中央缓存（`~/.cache/uv/environments-v2/verifiers-...`）的**符号链接**，而 verifiers 的 .gitignore 写的是目录模式 `.venv/`，匹配不到符号链接 → 会在 `git status` 里出现 `?? .venv` 噪声。本次跑完已删除该符号链接恢复原状（中央缓存里的环境仍在，复跑 smoke 会瞬间重建链接并复用已装包）。
2. **reference/verifiers 工作树非干净**：带前期阅读线程留下的中文注释（9 个文件 modified）。AST 对比证实全部为注释/docstring 差异、代码与 5885ab9c 逐节点一致（方法见第 1 节），故 smoke 与源码研读结论对 pin 有效。
3. **生命周期调用序比计划简写多一环**：计划写 "setup(task,trace,runtime) → harness → finalize → score"；真实顺序是 `taskset.setup → harness.setup(runtime) → (interception/tool/user 服务建立) → harness.run→launch → taskset.finalize → taskset.score 与 harness.score 并发 gather`。即 harness 有独立的 setup 阶段（安装 CLI 等，不计入 harness timeout），且 score 是 taskset/harness 两路并发。测试按真实顺序断言，不是偏差、是计划语言的粗粒度。
4. **TrainClient 没有公开的 renderer 注入口**（renderer 选择的记录）：构造参数只接受 `RendererConfig`，真实路径 `_renderer_pool()` 会按模型名 `create_renderer_pool` 下载 HF tokenizer——引入网络/缓存依赖，违反"测试可重复、不依赖网络"的门槛。选择：测试里用确定性 FakeRenderer 子类覆写**私有钩子** `TrainClient._renderer_pool`（而不是下载 Qwen3-0.6B tokenizer）。代价与风险：依赖私有方法名，升级 verifiers 若改名/改签名该测试会立刻失败——这是有意的哨兵（视为"依赖行为清单"的一部分：T1-T8 的验证入口依赖此钩子存在）。真实 renderer + 真实 tokenizer 的验证归 S0-4（渲染对照）与 S0-5（真端点全链）。
5. **`/inference/v1/generate` 挂在服务根**：`renderers.client.generate` 用 `str(client.base_url).rstrip("/").removesuffix("/v1")` 拼接绝对 URL，即端点不在 OpenAI 的 `/v1` 前缀下；并且发请求前先 GET `/v1/models` 预检 max_model_len（失败静默禁用）。S0-5 搭 vLLM/shim 时路由必须按这个形状（shim 若只实现 `/v1/...` 前缀会 404）。
6. **logprobs 的 wire 形状**：generate 响应里是 `choices[0].logprobs.content[*].logprob`（ChatCompletionLogProbs 展平形状），不是裸浮点数组。SGLang shim（C4）转译时要按这个形状构造。
7. **术语对齐**：token 对齐三元组在节点级叫 `MessageNode.mask`，分支级叫 `Branch.sampled_mask`；`Branch.logprobs` 是"展开到全长、非采样位补 0.0"的形状（与节点 `logprobs`"只存采样 token"不同）。写 rh2 侧消费代码时别混。
8. **subprocess runtime 会剥离 API key**：`SubprocessRuntime.run` 继承宿主环境但剔除名字含 `API_KEY` 的变量（`runtimes/subprocess.py:60`）。对本测试无影响，但 S0-3 在 subprocess 里跑需要真实 key 的工具时要注意（harness 的 key 走 argv/CLI 注入，不走环境继承）。

## 5. 自检（pytest 输出）

上游 smoke（reference/verifiers，standalone uv 0.11.26，python 3.12）：

```text
$ uv run --frozen pytest tests/v1/test_graph.py tests/v1/test_trace.py -q
.........                                                                [100%]
9 passed in 0.01s
```

rh2 契约测试（rh2/，uv 0.10.11，python 3.12.13；连跑 3 次结果一致）：

```text
$ uv run pytest tests/contract_verifiers -q
.................                                                        [100%]
17 passed in 0.63s

$ uv run pytest tests/contract_verifiers -v
tests/contract_verifiers/test_envserver_wire.py::test_run_rollout_request_msgpack_roundtrip_preserves_fields PASSED
tests/contract_verifiers/test_envserver_wire.py::test_run_group_request_msgpack_roundtrip_preserves_n PASSED
tests/contract_verifiers/test_envserver_wire.py::test_run_rollout_response_trace_survives_msgpack_roundtrip PASSED
tests/contract_verifiers/test_envserver_wire.py::test_run_group_response_and_error_response_roundtrip PASSED
tests/contract_verifiers/test_envserver_wire.py::test_envserver_health_info_roundtrip_in_proc PASSED
tests/contract_verifiers/test_envserver_wire.py::test_envserver_info_reports_group_scoring PASSED
tests/contract_verifiers/test_graph_token_identity.py::test_token_drift_forks_instead_of_silently_reusing_prefix PASSED
tests/contract_verifiers/test_graph_token_identity.py::test_branch_concat_equals_prompt_plus_completion_across_turns PASSED
tests/contract_verifiers/test_graph_token_identity.py::test_mask_and_logprobs_align_with_sampled_tokens PASSED
tests/contract_verifiers/test_graph_token_identity.py::test_prompt_supplied_assistant_message_is_not_a_sampled_turn PASSED
tests/contract_verifiers/test_rollout_lifecycle.py::test_taskset_setup_signature_declares_trace_parameter PASSED
tests/contract_verifiers/test_rollout_lifecycle.py::test_lifecycle_order_setup_harness_finalize_score PASSED
tests/contract_verifiers/test_rollout_lifecycle.py::test_harness_error_recorded_and_runtime_still_torn_down PASSED
tests/contract_verifiers/test_rollout_lifecycle.py::test_score_runs_inside_live_runtime PASSED
tests/contract_verifiers/test_trainclient_protocol.py::test_request_carries_token_ids_not_messages PASSED
tests/contract_verifiers/test_trainclient_protocol.py::test_response_parses_token_ids_and_aligned_logprobs PASSED
tests/contract_verifiers/test_trainclient_protocol.py::test_response_commits_into_token_identical_branch PASSED

============================== 17 passed in 0.75s ==============================
```

本任务消除的未知：verifiers pin 版本的四个边界（Trace 图不变量、Rollout 生命周期、EnvServer wire、TrainClient 协议）行为已固化为可重跑断言；upstream 自测在本机通过（环境健康）。未新增 U-x 级未知（uv 版本门槛与私有钩子风险已在上文记录并有对策）。
