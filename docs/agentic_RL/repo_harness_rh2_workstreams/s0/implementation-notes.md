# S0 implementation-notes（行车记录）

执行计划：`../01-s0-execution-plan.md`。本文分三节，发现即记，不事后补。规则：只记用户需要知道的事项（设计决策 / 偏离 / 权衡 / 开放问题），不记可自行判断的琐碎细节。

---

## Decisions（执行中做出的临时决策）

- [S0-0, 2026-07-07] AGENTS.md 采用"新内容置顶 + 旧章节原地保留标【legacy】"而非删除旧章节。理由：旧章节是理解被继承契约（五道防线、inspector 范式、原子语义）出处的最短路径，且删除会破坏旧 evidence 的上下文；代价是文件更长，已用标题前缀让新旧一眼可辨。
- [S0-0, 2026-07-07] 旧必读清单 B~G 未删除，段落标题全部改名（C 段显式标"已废弃"），置于"【legacy】旧架构选读清单"声明之下；段内条目的 ★ 标记在独立复核后二次清理（见 Deviations 第 1 条）。
- [S0-0, 2026-07-07] AGENTS.md"接手前最关键判断"从 3 条改为 4 条：新增第 4 条凭据安全（`deepseek_api.md` 只引路径不引内容），因为 rh2 阶段开始有真实 key 进入工作流。
- [S0-2, 2026-07-07] 上游 smoke 用装到 scratchpad 的 standalone uv 0.11.26 跑：`reference/verifiers` 的 pyproject 有 `[tool.uv] required-version = ">=0.11.1"`，与本机全局 uv 0.10.11 冲突。没有升级全局 uv（避免影响其他项目）、没有改 reference/ 下任何文件。GPU 机注意：跑 rh2 契约测试用 0.10.11 即可；若要在 GPU 机重复上游 smoke 需 uv>=0.11.1。
- [S0-2, 2026-07-07] TrainClient 契约测试的 renderer 选择：用确定性 FakeRenderer 覆写 `TrainClient._renderer_pool` 私有钩子，而不是下载 Qwen3-0.6B tokenizer。理由：真实 renderer pool 初始化会按模型名下载 HF tokenizer，违反"测试离线可重复"门槛；代价是依赖私有方法名——有意保留为升级哨兵（钩子改名/改签名测试立刻红），已记入 `contract_baseline.md` 发现 4。真实 renderer/tokenizer 的验证归 S0-4/S0-5。
- [S0-2, 2026-07-07] EnvServer 契约测试的 taskset 用 `rh2/tests/fixtures/` 下平面模块 + sys.path 注入提供（verifiers loaders 的本地插件协议：模块名即 taskset.id、`__all__` 导出恰好一个 Taskset 子类），不装任何环境包；health/info 往返在 in-proc ZMQ（127.0.0.1 临时端口）上完成。
- [S0-2, 2026-07-07] 执行计划把生命周期简写为 "setup → harness → finalize → score"；真实调用序在 taskset.setup 之后还有独立的 `harness.setup` 阶段，且 score 是 taskset.score 与 harness.score 两路并发 gather。契约测试按真实顺序断言（不算偏离计划，事实记录在 `contract_baseline.md` 发现 3；另核实 reference/verifiers 工作树的本地修改全部是注释/docstring，AST 与 pin 5885ab9c 逐节点一致，smoke 结果对 pin 有效）。
- [S0-4, 2026-07-07] 计划预留的 `uv add --group dev transformers huggingface_hub` 实际未执行：两包已由 verifiers 传递依赖带入 uv.lock（transformers 5.13.0 / huggingface_hub 1.22.0），rh2 的 pyproject/uv.lock 零改动；renderers 库经 `sys.path` 从 `reference/renderers`（HEAD 5904fa2）只读引用。
- [S0-4, 2026-07-07] 实验脚本落位 `rh2/experiments/s0_renderer/`（计划产出只要求报告文件）。理由：scratchpad 属会话级易失目录，而该脚本是 24 项断言的可重跑回归（renderers/transformers 任一升级后 `cd rh2 && uv run python experiments/s0_renderer/v2_renderer_experiment.py` 一分钟内复验）；目录命名沿用计划里 S0-5 的 `rh2/experiments/` 惯例。
- [S0-3, 2026-07-07] 玩具闭环矩阵用**进程内 mock OpenAI 兼容端点**完成结构层验收，而非真实 deepseek（原因见 Deviations：`deepseek_api.md` 的 deepseek key 为空）。mock 脚本化回放 bash/edit 工具调用，让 default 两题走"工具调用→结果→收尾"两轮、null 一轮结束，正好压出工具归属边界。V1 使用层"通过"的判定对象是 taskset×harness×runtime 组装 + `Environment.episode` 入口 + Trace 产出 + docker 生命周期，与模型提供方无关，故 mock 不影响该判定；真实 deepseek 连通性作为独立发现待补 key 复跑（`--endpoint deepseek`）。
- [S0-3, 2026-07-07] runner 落位 `rh2/experiments/s0_toy_loop.py`，taskset fixture 落位 `rh2/tests/fixtures/toy_taskset.py`（verifiers 本地插件 id=`toy-taskset`）。刻意**不进 `env.serving()`**：本 taskset 无 shared tools / user sim，走 per-rollout InterceptionServer，也让 macOS docker 网络 shim 只需覆盖 `reachable_url` 一个点。`@reward` 把"文件读失败"吞掉记 0 分（不抛错）：null harness 下文件必然不存在是预期得 0，不应污染 `trace.errors`。

## Deviations（S0-3 追加）

- [S0-3, 2026-07-07] **C5 假定不成立：`deepseek_api.md` 里 deepseek key 为空**。该文件 `DEEPSEEK_API_KEY:` 行没有值，只有 OPENAI/CLAUDE key 有值。→ 玩具闭环无法用真实 deepseek 跑模型对话，改用 mock 端点完成结构层验收（见上）。属"key 问题"非"verifiers 组装问题"。**待用户补 `DEEPSEEK_API_KEY: <值>` 后复跑 `--endpoint deepseek` 复核。**
- [S0-3, 2026-07-07] **[安全] key 解析器换行跨行 bug 已修复**：runner 首版用 `\s*`（含换行）取冒号后的值，遇到空的 deepseek 行会跨行吃到下一行的 OPENAI key，把 OpenAI 凭据发到了 deepseek 端点（deepseek 401 回显了以 `r-sA` 结尾的 OpenAI key 尾）。已改为同行匹配 `[ \t]*`，缺 key 时正确判 `missing`、端点只收到 `EMPTY`，确认不再发送任何真实 key。全程 key 未落盘/未打印/未进 argv。教训：读凭据文件取值只能吃水平空白，绝不用 `\s`。
- [S0-3, 2026-07-07] **macOS Docker `--network host` 不通宿主 loopback**：verifiers `DockerRuntime.is_local=True` 假定容器可用 `127.0.0.1` 直连宿主（Linux 成立）；本机 Docker Desktop（aarch64）实测 `127.0.0.1` 连不到宿主 loopback 端口，需 `host.docker.internal`。runner 仅在 macOS 下实验层 monkeypatch `verifiers.v1.rollout.reachable_url` 绕过（**未改 `reference/` 与 site-packages**）；Linux GPU 机不触发该 shim，走原生 127.0.0.1。

## New-Unknowns（S0-3 追加）

- [S0-3, 2026-07-07] docker 分支用 mock 端点验证了 V1 使用层与 runtime 生命周期；**真实模型经 EvalClient 在 docker 容器内到宿主 interception server 的往返**尚未用真实 deepseek 跑过（因缺 key）。补 key 后应复跑 `--harness default --runtime docker --endpoint deepseek` 消除此未知。

## Deviations（偏离计划的地方及原因）

- [S0-0, 2026-07-07] **首版实现有遗漏，被独立复核抓出后修复**：B/C 段内部条目上的 4 处 ★ 标记（AGENTS.md 原 463/472/474/476 行）第一遍只改了段落标题、没清条目标记，且本文件 Decisions 首版声明"全部去掉 ★"与事实不符。已修复（legacy 区现在 0 个 ★）并订正声明。教训：对"清理某类标记"的任务，验收要用 `grep -c` 全文计数而不是目测。复核同时发现并修复：两处"当前主战场/当前训练链路主路径"的现行语气残留、"等待 16G.3 引入"的失真未来时、README 免责声明未覆盖"推荐阅读"节、README"3 个错误"未同步为 4 个。
- [S0-0, 2026-07-07] **commit 拆分说明**：S0-0 会话开始时工作树里还带着上一轮讨论对 `01-s0-execution-plan.md` 的修订（codex 建议吸收 + C 系列定案，属实施前讨论的产物，非 S0-0 交付物）。为遵守"每任务独立 commit"，拆为两个 commit：先 `rh2(plan)` 提交计划修订，再 `rh2(s0-0)` 提交 AGENTS/README/notes。

## New-Unknowns（执行中新发现的未知，待消除）

- [S0-4, 2026-07-07] **U-G：本地路径加载 tokenizer 会静默降级 DefaultRenderer。**renderers 的 auto 解析用 `tokenizer.name_or_path` 精确匹配 `MODEL_RENDERER_MAP`（base.py:1478）；GPU 机上用本地权重目录（如 `/models/Qwen3-30B-A3B`）加载时不命中 → 回落 DefaultRenderer 且只打 INFO 日志，bridge 恒 None、`sampled_mask/is_content` 为空，token 保真链路整体失效。规避已写进 `s0/v2_renderer_report.md` 第 4 节：用 HF id 或显式 `Qwen3RendererConfig()`，启动时断言 renderer 类名。归 S0-5 落地为守门检查。
- [S0-4, 2026-07-07] transformers 版本敏感性：parity 在 rh2 锁定的 5.13.0 实测通过（renderers 官方下限 4.50）；GPU 机若因 vLLM 0.24.x 约束改变 transformers 版本，需随 S0-5 重跑 `rh2/experiments/s0_renderer/v2_renderer_experiment.py` 复验。
- U-E 静态部分已在 S0-4 消除（thinking 剥离 = 模板窗口语义，bridge 在 query 边界 fail-closed，量化见 `s0/v2_renderer_report.md` 第 3 节）；动态部分（真实 vLLM 采样的 `<|im_end|>` 尾 token、TrainClient 回退行为、截断路径 logprobs 对位）留 S0-5 观察。
- [检查点2, 2026-07-07] 汇总复核（checkpoint2_review.md）判定"有条件通过"：条件一 OPENAI key 轮换（见下）；条件二 deepseek 实跑已由 ef726836 先行关闭。承认一处工作流偏离：S0-3 的 notes 条目被误并入 s0-2 commit a18fc381（本应随 810d0f0c），按 commit 逐个 diff 的对应关系在该处失真，不改写历史、以本条为准据更正；低severity 3 条留 S0-5 准备期处理。
- [安全, 2026-07-07] **用户行动项：轮换 OPENAI key**。S0-3 首版解析 bug 曾把完整 OPENAI key 外发到 api.deepseek.com 一次（bug 已修，key 本体未入 git，但 4 字符尾指纹随事件记录进了 git 历史）——按"已传输给第三方服务器即视为泄漏"原则应立即轮换。
- [S0-5 前, 2026-07-08] GPU 租用降配定案：8 卡缺货，S0-5/6/7 改用单卡 RTX PRO 6000（96GB）——同构 Blackwell 提前去风险 sm_120 软件栈（U-C 软件侧），96GB 可原生 bf16 跑 30B-A3B（无需量化混淆 V4 结论）；磁盘 200GB 是软肋，优先申请挂 volume，否则按 S0-5/6→清理→S0-7 顺序跑；8×整机推迟到 S4 前训练侧专项预实验（计划 U-C 原有安排）。

## Decisions（S0-5/6/7 远程 GPU 追加）

- [S0-5, 2026-07-07] **远程 GPU 机的基础栈可以作为后续 S0/S1 远程复验基线**：单卡 RTX PRO 6000 Blackwell 96GB、驱动 580.95.05、Docker 28.1.1、`nvidia-container-toolkit` 1.19.1、uv 0.11.26、Python 3.12.13。容器内 `nvidia-smi` 已通过，宿主 GPU 在停止推理服务后回到 0 MiB 使用量。后续正式远程 GPU 流程可以复用这一安装顺序，但应把命令固化到 runbook，避免靠临场修补。
- [S0-5, 2026-07-07] **vLLM 0.24.0 可以作为形态 A 的首个动态验证端点，但启动参数必须保守固定**：Qwen3-4B 与 Qwen3-30B-A3B 均需要 `--tokens-only`；Blackwell 上为避开 CUDA graph / FlashInfer sampler / MoE 后端问题，实测稳定组合为 `--enforce-eager`、`VLLM_USE_FLASHINFER_SAMPLER=0`、Qwen3-30B-A3B 额外 `--moe-backend triton`，并显式设置 CUDA 13 toolkit 路径。默认参数会在 CUDA graph 捕获或 FlashInfer/CUTLASS MoE 编译处失败，不能作为后续 runbook 的默认。
- [S0-5, 2026-07-07] **vLLM token/logprob 链路已动态通过**：Qwen3-4B 通过 verifiers `TrainClient` 直连 `/inference/v1/generate`，`prompt_token_count=13`、`completion_token_count=8`、completion logprob 数量对齐、Trace token identity 通过、renderer guard 通过。证据保存在 `remote_s0_5_7_evidence/trainclient_qwen3_4b_probe.json`。
- [S0-5/6, 2026-07-07] **vLLM MoE routing 不是零 shim 可用**：vLLM 0.24.0 的 `routed_experts` wire 形态是 base64 编码的 `.npy` 字符串，动态解码得到 `[20, 48, 8]`；而 verifiers 当前 `Trace.commit()` 期望的是 `{data, shape, start}` 字典。验证脚本已证明薄 shim 可以把 base64 `.npy` 转成 verifiers 期望形态，并保持 token identity，commit 后 `branch_routed_experts_shape=[21,48,8]`。决策：S1 的 `TrajectoryProjection` 或协议 shim 必须拥有该转换，不允许把这个转换散落在训练后端 adapter 中。
- [S0-6, 2026-07-07] **SGLang 路线可作为形态 B 的动态基线，但建议后续使用固定容器镜像**：SGLang 0.5.9 在这台机器上可跑 Qwen3-4B 与 Qwen3-30B-A3B，能返回 output token ids 与 output token logprobs；Qwen3-30B-A3B 返回的 routing tape 可解析为 `[20,48,8]`。但安装过程对 CUDA developer toolkit 路径非常敏感，临时方案依赖 vLLM 环境里的 CUDA 13 toolkit 路径与 `lib64/libcudart.so` 软链接。正式复验应改用预构建 SGLang/slime 容器或标准 CUDA 开发栈。
- [S0-6, 2026-07-07] **MoE 形态判断调整为“两条都可行，形态 B 更接近训练后端原生路径”**：形态 A（verifiers 中心 + vLLM 兼容端点）已经证明 token/logprob 与 routing 可透传，但需要 routing wire shim；形态 B（SGLang/slime 原生 generate）已经证明 token/logprob 与 routing 都能从服务端响应拿到，更贴近 slime `custom_generate` 的后端形态。后续设计不应押单一路径，治理层继续以中立 `TrajectoryProjection` 为输入。
- [S0-7, 2026-07-07] **本轮只关闭远程 Docker 前置验证，没有关闭 SWE-Bench smoke taskset**：远程 DockerRuntime toy loop 已通过，`default` harness 在 Docker 中两题 `reward=1.0`，`null` harness 两题 `reward=0.0`。这证明 Linux 远程 Docker runtime、容器生命周期、toy 工具循环与 trace dump 可用；但它不是 SWE-Bench Verified 题单验证。证据保存在 `remote_s0_5_7_evidence/remote_default_docker_s0_7.json`、`remote_s0_5_7_evidence/remote_null_docker_s0_7.json` 与 `remote_s0_5_7_evidence/s0_7/`。

## Deviations（S0-5/6/7 远程 GPU 追加）

- [S0-5, 2026-07-07] **vLLM 默认启动路径不可用**：Qwen3-4B 默认启动曾卡在 CUDA graph 捕获，改 `--enforce-eager` 后又遇到 FlashInfer sampler / CUDA header 不匹配；Qwen3-30B-A3B 默认 MoE 后端走 FlashInfer CUTLASS 编译失败。已用保守参数绕过，但这说明 Blackwell 软件栈不能只靠框架默认值验收。
- [S0-6, 2026-07-07] **SGLang 安装不是一次性开箱即用**：`deep_gemm`/JIT 路径需要可用 CUDA compiler 与 runtime library，远程机器默认没有完整 CUDA developer toolkit；最终借用 vLLM 环境里的 CUDA 13 toolkit 才跑通。这是环境工程风险，不是 SGLang 协议风险。后续若要节省 GPU 时间，应提前准备镜像。
- [S0-7, 2026-07-07] **原计划 S0-7 未执行到位**：执行计划要求“冻结 5 到 10 个 SWE-Bench Verified smoke 题单 + 实现 `SweSmokeTaskset` + 每题一次成功 rollout 与评分记录”。当前仓库尚无 `SweSmokeTaskset`，也没有冻结题单。本轮没有临时实现新 taskset，避免把一个边跑边写的未审实现伪装成计划验收。因此 S0-7 状态应写为“Docker 前置验证通过，SWE smoke taskset 未完成”。

## New-Unknowns（S0-5/6/7 远程 GPU 追加）

- [S0-5/6, 2026-07-07] **top-p tape 尚未动态验证**：本轮动态验证了 token ids、logprobs 与 MoE routing tape；没有验证 top-p ids / top-p probabilities 的后端返回与投影契约。若训练设计需要 OPD / MOPD 类张量，S1 前需要单独补一个最小探针。
- [S0-6, 2026-07-07] **SGLang routing 的最小必要开关仍需更精确复核**：保守实现应同时开启服务端 `--enable-return-routed-experts` 与请求侧 `return_routed_experts=true`。本轮保存的 30B 证据都包含 `routed_experts`，但没有完整保留 request body，不能从证据文件里严格区分“只开 server flag 是否足够”。后续 shim 测试应把 request body 一并落盘。
- [S0-7, 2026-07-07] **SWE-Bench Verified 官方镜像拉取速度、磁盘占用、评分解析仍未消除**：本轮只使用 `python:3.12-slim` toy Docker 镜像，没有拉取官方 SWE-Bench x86_64 镜像，也没有跑官方 eval 脚本。因此 U-D 仍然存在，必须在 `SweSmokeTaskset` 实现后用真实题单关闭。
- [S0-5/6, 2026-07-07] **单卡 RTX PRO 6000 只能证明推理侧可行，不能证明 S4 训练侧可行**：本轮没有测试多卡通信、权重同步、actor-rollout 切换、训练显存、PCIe 无 NVLink 带来的同步开销。8 卡整机风险仍保留到 S4 前专项预实验。
