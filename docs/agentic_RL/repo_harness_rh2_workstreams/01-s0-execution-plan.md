# 01 — S0 执行计划：可行性验证（rh2 新架构第一阶段）

本文是 rh2 新架构的第一份执行计划，细化实施计划总纲（`docs/harness_improve/repo_harness_implementation_plan_v1.md`）的 S0 阶段。时间盒 1~2 周（E8）；到期未完成项显式降级为"带风险进 S1"或砍掉，写进 implementation-notes。

**协作纪律**（本阶段起生效，贯穿 rh2 全程）：

1. 本目录维护 `s0/implementation-notes.md`：设计决策、偏离计划、权衡、开放问题——发现即记，不事后补。
2. 未知消除优先：每个任务的验收产出里都包含"该任务消除了哪些未知"；新发现的未知进本文第 6 章清单（编号 U-x），消除一个划掉一个。计划允许微调，但微调必须留痕。
3. 需要用户决策的事项走第 5 章 C 编号，不擅自替用户定；用户未答复时选保守项并记录。

---

## 1. 本轮代码核查已消除的未知（写计划前的事实基础）

以下全部为本轮逐源码核实的事实，不是转述。它们直接修正了总纲里几处过时或过严的假设：

| # | 事实 | 证据 | 对计划的影响 |
| --- | --- | --- | --- |
| F1 | **`/inference/v1/generate` 是新版原生 vLLM 的 token-in/token-out 端点**（`vllm.entrypoints.serve.disagg.serving.ServingTokens`），prime-rl 只是子类化扩展（加 routed_experts 导出与 prefix-cache salting） | `prime-rl/src/prime_rl/inference/vllm/serving_tokens.py:45`（import 自 vllm）、`:53-57`（PrimeRlGenerateResponse 加 routed_experts 字段） | V3 难度直降：TrainClient 直连新版 vLLM 可能原生工作，不必先写 shim；shim 只在 SGLang 侧需要。残余未知 U-A：哪个 vLLM 版本起有此层 |
| F2 | prime-rl 的 vLLM 扩展**响应里带 per-choice `routed_experts`**（`enable_return_routed_experts` 开启时），且带 `prompt_logprobs` | 同上 `:314-348` | 形态 A 的 routing 透传存在官方通道——但推理引擎得是 prime 的 vLLM 扩展；若训练后端是 slime/SGLang，形态 A 仍需 shim 映射。写入形态评估报告的对比项 |
| F3 | **verifiers 的 prime_sandboxes import 是方法内惰性的**（`runtimes/prime.py:76,223`），模块级不 import | 源码 | V1 判定标准放宽（见 S0-1）：第一版只用 docker runtime，prime runtime 可用性降为可选项，不阻塞方案 A |
| F4 | slime 的 routed_experts 采集链：server 侧 `enable_return_routed_experts`（`sglang_engine.py:626`）+ 请求侧 `return_routed_experts`（`sglang_rollout.py:181`）+ `Sample` 解码（`utils/types.py:352`） | 源码 | 形态 B 动态验证（S0-6）的具体开关已知。残余未知 U-B：该 flag 是否依赖 slime docker 里的 sglang patch |
| F5 | **renderers 有 `qwen3.py` 和 `qwen35.py`** hand-coded renderer | `reference/renderers/renderers/` 目录 | V2 大概率通过；S0-4 只需核实 30B-A3B 变体（tokenizer/chat template/thinking 处理）与 bridge 支持 |
| F6 | verifiers in-process 入口是 `Environment.episode(task, ctx, n)`（`env.py:376`）；harness 为 `default`（bash+默认 edit+可选 search）与 `null`；`Taskset.setup(task, trace, runtime)` 多了 trace 参数 | `5885ab9c` 源码 | S0-2/S0-3 的代码骨架依据 |
| F7 | verifiers 包名就是 `verifiers`（pyproject `name = "verifiers"`） | pyproject.toml | C1 的 uv pin 写法 |

---

## 2. 任务总览

| # | 任务 | 执行位置 | 前置 | 主要产出物 |
| --- | --- | --- | --- | --- |
| S0-0 | 文档与接手上下文切换 | 本机 | 无 | AGENTS.md / README 新版 |
| S0-1 | 依赖底座（rh2 子项目 + verifiers pin） | 本机（docker 验证部分在 GPU 机） | C1/C2 定 | `rh2/` 工程 + deps_report |
| S0-2 | verifiers 行为契约测试 | 本机 | S0-1 | 四个契约测试全绿 + contract_baseline.md |
| S0-3 | 玩具闭环（default + null harness） | 本机 subprocess；docker 分支 GPU 机 | S0-1，C5 定 | trace dump + 字段核对记录 |
| S0-4 | V2：renderer 覆盖核实 | 本机 | 无 | V2 结论 |
| S0-5 | V3：token 协议链路 | **GPU 机** | S0-1/2，C3/C4 定 | V3 结论 + shim 原型（验证级） |
| S0-6 | V4：MoE 张量穿透 + 形态评估 | **GPU 机** | S0-5 | V4 结论 + **形态 A/B 评估报告** |
| S0-7 | SWE smoke taskset（5~10 题） | **GPU 机** | S0-3，C6 定 | 题单 + 每题成功 rollout + 评分记录 |
| S0-8 | 实验设计文档复核收口 | 本机，与 GPU 步骤并行 | S0-4/5/6 结论 | 实验设计文档定稿 |

依赖关系要点：S0-0/1/2/3(subprocess)/4 可立即在本机推进；S0-5/6/7 等 GPU 整机（8×RTX Pro 6000）就绪；S0-8 收口需要 V2~V4 结论。

---

## 3. 逐任务详细计划

### S0-0 文档与接手上下文切换（半天）

按 C7（推荐幅度）改写：

1. **AGENTS.md**：
   - "当前进度"章节整体替换：声明 16G.3~16G.6 阶段线由设计文档 2 取代不再执行；17B/20/21 旧闸门作废，新闸门为 `rh2_s0_complete → rh2_s1_closed_loop → rh2_s2_signal_trusted → rh2_formal_training_allowed`（当前全 false）；当前任务 = 本计划 S0。
   - "新接手必读清单"替换为：设计文档 2 → final review → 实施计划总纲 → 本计划 →（若做实验）实验设计文档。
   - 旧"关键代码架构"“5 道防线”等章节保留但顶部加一行：`【legacy】以下描述冻结的 src/repo_harness 旧实现，新架构见 rh2/`。
   - "两个 worktree 协作"章节标注 evaluation worktree 已搁置（指向设计文档 2 §1.5）。
2. **README.md**：进度指针指向 AGENTS.md 新章节。
3. 创建 evidence 目录骨架：`docs/agentic_RL/repo_harness_rh2_workstreams/s0/`（含空 implementation-notes.md 开档）。

验收：模拟新线程视角——只读 AGENTS.md 能在 3 分钟内定位到"当前做 rh2 S0、旧线已冻结"，不会误入 16G.3。

### S0-1 依赖底座（1 天，本机为主）

按 C2 建 `rh2/` 独立子项目（不动根 pyproject，旧包冻结）：

```text
rh2/
  pyproject.toml        # name="repoharness2"（E1 暂定名），requires-python 对齐 verifiers
  src/repoharness2/     # 先空壳 + __init__.py（S1 才填实现）
  tests/
    contract_verifiers/ # S0-2 落这里
  .python-version
```

步骤：

1. `uv init` + 依赖（C1 定案后）：`verifiers @ git+https://github.com/PrimeIntellect-ai/verifiers@5885ab9c`、`pytest`、`pydantic>=2`。锁定 `uv.lock`。
2. `uv run python -c "import verifiers.v1; import renderers"` 通过；记录随 verifiers 拉入的 prime-sandboxes / prime-tunnel / renderers 实际版本。
3. **V1 判定（较总纲放宽，依据 F3）**：
   - 安装层（本机，必须过）：全部依赖可安装、verifiers 可 import。
   - 使用层（GPU 机）：DockerRuntime 起容器执行 `run()` 成功（S0-3 docker 分支顺带验证）。
   - prime runtime 实际调用（需 Prime API key）：**可选，不阻塞**——第一版只用 docker runtime。若未来要用 prime sandbox 再验。
4. 失败预案：git pin 拉取失败 → 临时改用本地路径 `reference/verifiers`（记 deviation，不长期化）；依赖冲突 → 记录冲突面，评估是否触发方案 B。

产出：`rh2/` 工程 + `s0/deps_report.md`（版本清单 + V1 安装层结论）。

### S0-2 verifiers 行为契约测试（1~2 天，本机，不需要模型）

四个测试文件，每个断言"我们依赖的行为"而不是 verifiers 的全部行为。写测试前先跑一遍上游 `tests/v1/test_graph.py`、`test_trace.py` 作 smoke（确认 pin commit 自身健康）。

```text
rh2/tests/contract_verifiers/
  test_graph_token_identity.py
    断言 1：同一 message 文本、token ids 发生漂移时，graph 走 fork 而非静默
           复用旧前缀（参照上游 test_graph.py 的 renderer-level break 用例自写最小版）
    断言 2：沿 branch 拼接 token_ids 精确等于 prompt_ids + completion_ids
    断言 3：sampled/mask/logprobs 三者对齐关系
  test_rollout_lifecycle.py
    用自写 SpyTaskset + FakeHarness（最小 Harness 子类，不调模型）：
    断言 1：调用序 setup(task,trace,runtime) → harness.launch → finalize
           → score，且 setup 签名含 trace 参数（F6）
    断言 2：harness 抛错时 runtime 仍在 finally 中 teardown
    断言 3：score 在 runtime 存活期执行（5.2 评分设计的前提）
  test_envserver_wire.py
    in-proc 起 EnvServer + EnvClient：health / info 往返；
    断言 wire 类型（serve/types.py）的 msgpack roundtrip 字段不丢
  test_trainclient_protocol.py
    起本地 fake HTTP server 记录请求：
    断言 1：TrainClient 请求体走 token-in（含 token_ids）
    断言 2：响应解析出 token_ids + 逐 token logprobs 且对齐
    （纯协议层，无 GPU；真实端点验证归 S0-5）
```

产出：测试全绿 + `s0/contract_baseline.md`（我们依赖的 verifiers 行为清单——以后升级 verifiers 先跑这套）。

### S0-3 玩具闭环（1 天本机 + GPU 机半天）

1. 写 `ToyTaskset`（放 `rh2/tests/fixtures/`）：两题——"在 workspace 创建 hello.txt 内容为 X"（考 bash）、"把 a.py 中函数名 foo 改为 bar"（考 edit）；`@reward` 在 runtime 里 `read` 文件断言。
2. `default` harness（bash+edit）与 `null` harness（纯 chat，预期做不了文件题——用它验证"工具归属 harness 而非 taskset"的边界）各跑一次，入口 `Environment.episode(task, ctx, n=1)`。
3. 模型端点用 EvalClient 指向 C5 选定的 OpenAI 兼容便宜模型。
4. **检查项分两档（重要，防误判）**：EvalClient 是文本中继模式，**Trace 的 token 级字段在此模式下不完整是预期行为，不是 bug**；本任务只验收结构层（branches 拓扑、messages、工具调用往返、错误归因、RolloutLimits 生效）。token 保真验收归 S0-5 TrainClient。
5. runtime 矩阵：本机跑 subprocess；GPU 机跑 docker（同时完成 V1 使用层验证）。

产出：`s0/toy_trace_dump/`（两种 harness × 两种 runtime 的 Trace JSON + 字段核对记录）。

### S0-4 V2：renderer 覆盖核实（半天，本机）

1. 读 `renderers/qwen3.py`（必要时 `qwen35.py` 对照）：确认支持的 tokenizer/chat template、tool call 格式、thinking（`<think>`）在历史消息里的处理策略、`bridge_to_next_turn` 是否实现。
2. 下载 Qwen3-30B-A3B 的 tokenizer（仅配置文件，几 MB，本机可做）：对同一段多轮对话分别用 `transformers.apply_chat_template` 与 renderer `render_ids` 渲染，对比 token 序列一致性。
3. 明确判定：hand-coded renderer 覆盖 30B-A3B = V2 通过；仅 DefaultRenderer 可用 = V2 降级（记录影响：bridge 不安全 → token 保真受限），并把结论带进 S0-8 模型选型复核。

产出：`s0/v2_renderer_report.md`。

### S0-5 V3：token 协议链路（GPU 机，1~2 天）

依据 F1 更新过的方案（比总纲更省）：

1. **第一步核实 U-A**：GPU 机装最新 vLLM，确认 `vllm.entrypoints.serve.disagg` 存在、`/inference/v1/generate` 路由可起。若最新版没有 → 查 prime-rl 锁定的 vLLM 版本号照装。
2. **直连验证（先小后大，C3）**：vLLM 起 Qwen3-4B（dense）→ verifiers TrainClient + renderer 全链跑 ToyTaskset：验证 token_ids/logprobs 逐位对齐、bridge_to_next_turn 多轮不重渲染、Trace token identity 全绿。然后换 Qwen3-30B-A3B 重复（顺带记录推理显存占用，喂给 U-C）。
3. **SGLang shim 原型（验证级，C4）**：实现最小 `/inference/v1/generate` → SGLang `/generate` 转译（token_ids 进、token_ids+logprobs 出、`meta_info.routed_experts` 映射进响应扩展字段）；只求跑通 ToyTaskset 一次，证明可行性并测出透传缺口清单，不做产品化。
4. V3 判定：直连 vLLM 全链 token 保真成立 = V3 通过（形态 A 的推理侧路径存在）；shim 原型结论作为形态评估输入。

产出：`s0/v3_protocol_report.md` + shim 原型代码（`rh2/experiments/s0_shim/`，标注验证级）。

### S0-6 V4：MoE 张量穿透 + 形态评估报告（GPU 机，1~2 天）

1. **形态 B 动态验证**：SGLang 起 Qwen3-30B-A3B（TP 按显存实测定），server 开 `enable_return_routed_experts`、请求带 `return_routed_experts`（F4）：验证 `meta_info` 返回 routed_experts 且 `decode_int32_meta_array` 解出的 element 数与 sample tokens 匹配（`types.py:358` 的校验路径）、`output_token_logprobs` 逐 token 对齐。**若 flag 在原生 sglang 不存在 → 确认 U-B（需要 slime 的 sglang patch/镜像），改用 slime docker 镜像重验。**
2. **形态 A 对照**：基于 F2——prime 的 vLLM 扩展有 routed_experts 通道，但意味着形态 A 用于 slime 训练时推理引擎要么换 prime-vLLM、要么 shim 补齐映射；把两条路的工程成本写进报告。
3. top-p mask：确认 SGLang 侧 top-p 采样信息的可得性与 slime `rollout_top_p_token_ids/offsets` 的生成点（loss.py:35-47 消费端已核实，生成端在 GPU 机上跑通一次）。
4. **产出 S0 最重要的单一文档：`s0/topology_ab_report.md`**——形态 A/B 在 token 保真、MoE 张量、工程成本、治理层接入点（都经 TrajectoryProjection 中立契约）四个维度的对比与推荐结论。

### S0-7 SWE smoke taskset（GPU 机，1~2 天）

1. 选题（C6）：SWE-bench Verified 中满足——官方预构建 x86_64 镜像存在、Python 仓库、单题测试 < 5 分钟、仓库主流（django/sympy/requests/astropy 类）——初选 8 题给用户过目后冻结。
2. 实现 `SweSmokeTaskset`（借 harbor taskset 的代码结构，`tasksets/harbor/taskset.py` 为模板）：per-task 官方镜像、prompt 用 problem statement、`score` 先同容器跑官方 eval 脚本读 F2P/P2P（**S0 不要求评分隔离**——隔离是 S2 的活，此处只为验证物化与评分解析）。
3. default harness + TrainClient（若 S0-5 已通）或 EvalClient 跑通每题一次。
4. 注意：SWE 镜像单个数 GB，8~10 题预留 ~50GB 磁盘；本机 Apple Silicon 不跑 x86 镜像（emulation 不可靠），全部在 GPU 机。

产出：`s0/swe_smoke_report.md`（题单、镜像 digest、rollout 与评分记录、日志解析要点——后者直接喂 S1 的 taskset 冻结）。

### S0-8 实验设计文档复核收口（与 GPU 步骤并行）

另一线程已产出草案 `docs/agentic_RL/training_design/repoharness_validation_experiment_design.md`（用户尚未检查）。本任务：

1. 先替用户做一轮审读：对照 final review §6.3 六项最小决策集查覆盖度，列出问题清单给用户。
2. 把 S0 实测结论回填：V2（renderer→模型定型）、V3/V4（形态定案）、U-C（30B-A3B 实测显存/吞吐→预算修正）。
3. 收口定稿（注意其内部 E1~E10 是实验层编号，与执行层 E1~E8 独立）。

---

## 4. GPU 整机首日 checklist（租机后第一件事）

```text
1. 基线：nvidia-smi 确认 8×RTX Pro 6000（96GB）、驱动/CUDA 版本记录
2. docker + nvidia-container-toolkit 装好，非 root 用户可用 docker
3. 磁盘：确认 ≥ 500GB 可用（模型权重 ~60GB×2 格式 + SWE 镜像 ~50GB + HF 缓存）
4. 拉取清单：vLLM 最新镜像（或 pip 装，U-A 核实用）、SGLang 镜像、
   slime docker 镜像（U-B 备用）、SWE-bench smoke 题镜像
5. 下载 Qwen3-30B-A3B 与 Qwen3-4B 权重到本地缓存
6. 同步 rh2/ 工程（git clone + uv sync），跑 S0-2 契约测试确认环境等价
7. 跑 S0-1 使用层验证（DockerRuntime）+ S0-3 docker 分支
8. 之后按 S0-5 → S0-6 → S0-7 顺序推进
```

---

## 5. 需要用户确认的决策（C 系列）

| # | 决策 | 推荐 | 状态 |
| --- | --- | --- | --- |
| C1 | verifiers 安装方式 | git pin `verifiers @ git+https://github.com/PrimeIntellect-ai/verifiers@5885ab9c`（可复现、防误改）；`reference/verifiers` 仅作阅读。备选：本地路径依赖（离线但易被误改） | 待确认 |
| C2 | 工程布局 | 新建顶层 `rh2/` 独立子项目（own pyproject + venv），根 pyproject 与旧包完全不动。备选：uv workspace 改造根（动旧项目，不推荐） | 待确认 |
| C3 | S0-5 首个协议验证模型 | 先 Qwen3-4B（dense，协议正确性与显存问题解耦）再 30B-A3B | 待确认 |
| C4 | SGLang shim 深度 | 验证级最小实现（够出 V3/V4 结论即停），形态定案后再决定是否产品化 | 待确认 |
| C5 | S0-3 玩具闭环的 eval 模型 | 任一 OpenAI 兼容便宜模型即可（不影响结论）；具体用哪家、key 从哪来由你定 | ★需你提供 |
| C6 | smoke 题单 | 我按第 3 章标准初选 8 题列清单，你过目后冻结 | 流程确认 |
| C7 | AGENTS.md 改写幅度 | 进度/必读/闸门章节全换 + 旧架构导览保留标 legacy | 待确认 |

C1~C4/C6/C7 无异议即按推荐执行；C5 需要你给模型与 key 的选择。

---

## 6. 残余未知清单（只能在执行中消除）

```text
U-A vLLM 版本门槛：哪个版本起有 vllm.entrypoints.serve.disagg（/inference/v1/generate）
    —— S0-5 第一步消除
U-B SGLang 的 enable_return_routed_experts 是否需要 slime fork/patch
    —— S0-6 消除（预案：改用 slime docker 镜像）
U-C Qwen3-30B-A3B 在 8×PCIe（无 NVLink）上的真实显存/吞吐
    —— S0 只测推理侧（S0-5/6 顺带记录）；训练侧留 S4 前的专项预实验
U-D SWE 官方镜像在租机上的拉取速度与磁盘占用 —— S0-7 消除
U-E Qwen3 thinking 模式：renderer 对历史 thinking 的剥离策略是否破坏
    bridge/前缀 —— S0-4 静态核实 + S0-5 动态观察
U-F prime-sandboxes 实际调用可用性 —— 不阻塞（F3），有 Prime key 时顺手验
```

阅读 `agent_cowork.md` 后的补充说明：这张表就是本阶段的"unknown unknowns 减除器"。执行中任何一次"咦，和计划想的不一样"都必须变成新的 U-x 或 implementation-notes 里的 deviation 条目，而不是就地悄悄绕过。

---

## 7. 完成定义（DoD）与 evidence 清单

S0 完成 = 以下文件齐备且 `s0_acceptance_summary.json` 各项为真：

```text
docs/agentic_RL/repo_harness_rh2_workstreams/s0/
  implementation-notes.md      全程维护
  deps_report.md               V1 结论（安装层必过，使用层 GPU 机验证）
  contract_baseline.md         四契约测试全绿 + 依赖行为清单
  toy_trace_dump/              两 harness × 两 runtime 结构验收
  v2_renderer_report.md        V2 结论
  v3_protocol_report.md        V3 结论 + shim 原型缺口清单
  topology_ab_report.md        V4 结论 + 形态 A/B 推荐（S0 最重要产出）
  swe_smoke_report.md          题单 + rollout + 评分解析
  s0_acceptance_summary.json   最小版闸门账本：rh2_s0_complete 及各 V 项状态
                               （S0 用轻量校验脚本代替完整 inspector，
                                inspector 范式从 S1 起全量执行）
实验设计文档                    收口定稿（在 training_design/ 原位）
AGENTS.md / README             新版（S0-0）
```

失败路径的出口也预定义好：V1 安装层失败 → 触发方案 B 评估（fork/剥离）；V3 直连与 shim 双双失败 → 形态 B 定案、TrainClient 弃用；V4 形态 B 也拿不到 routing → 上报用户重议模型选型（dense 备选）——任何一条都不是"S0 失败"，而是 S0 完成了它的验证使命。
