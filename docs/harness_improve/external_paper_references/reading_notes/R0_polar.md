# R0 Polar：原生 harness 的代理捕获、轨迹重建与异步 RL

Polar 将既有 coding harness 留在原生运行环境内，在模型 API 边界捕获交互，再交给独立训练器。论文用 Qwen3.5-4B、293 个 SWE-Gym 任务和 Slime GRPO，分别在四个 harness 上训练；SWE-Bench Verified 增益为 22.6、4.8、0.6、6.2 个百分点。最具体的系统对照是三个训练步内，prefix merging 相比逐请求重建将墙钟从 189.5 降至 35.2 分钟，而非达到同等能力的总成本实验。另一条独立分支用固定 122B 模型生成 504 条合格轨迹，**未训练并验证下游 SFT 模型**。本笔记完整覆盖正文、附录与当前官方关键代码，保留数据表算术不一致、reward hacking 负结果及历史配方未披露项。

导航：[来源与覆盖](#source) · [运行与捕获](#runtime) · [重建与训练语义](#reconstruction) · [RL 实验](#rl-results) · [离线数据](#offline) · [代码与项目判断](#implementation)

<a id="source"></a>
## 1. 来源、版本与本次范围

**主来源 P。** Binfeng Xu、Hao Zhang、Shaokun Zhang、Songyang Han、Mingjie Liu、Jian Hu、Shizhe Diao、Zhenghui Jin、Yunheng Zou、Michael Demoret、Jan Kautz、Yi Dong，NVIDIA，*Polar: Agentic RL on Any Harness at Scale*。首次提交 2026-05-22；2026-09-07 查询 [arXiv 版本历史][P-abs]，只列 **`2605.24220v1`**。主读 [官方 PDF][P] 与 [HTML][P-html]。

PDF **17 页，正文 §1–5，附录 A.1–A.5**；实际共有 **6 幅编号图、4 张表、2 个代表性 JSON 框**。摘要页 comments 的“2 tables”没有计入附录 Table 3、4，本稿按实际文件覆盖。引用页码均为 PDF 物理页，与页脚对应；HTML 的 A.3/A.4 JSON 没有正常显示，本轮从 PDF 文本及截图补齐。原始 TeX、本机 PDF 下载未成功；这不影响本次已取得的正文、附录和关键图页，也不意味着作者没有公开源文件。

**配套代码 C。** [NVIDIA-NeMo/ProRL-Agent-Server][C0] 当前默认分支是 `stable`；本轮固定 **`6a1ead6bfac054fce6c1e62d1a77b330d96c58db`，2026-08-13**。只检查 §8 列出的路径与关键消费位置，不做整库审计。该提交晚于论文，**不把现代示例参数倒填为 2026-05 的历史实验配方**。Polar 是对前作 *ProRL Agent*（`2603.18815`）的重写，不是同一论文的新名字，也不是 prolonged RL 的 ProRL 方法。

**项目读取基线。** `Rogerffff/RepoHarness@miles-migration` 的 **`09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6`**。阅读前核对了 [Codex 质量反馈](reviews/15_O01_codex_quality_review_20260907.md)、[模板](NOTE_TEMPLATE.md) 和 [资料目录](SOURCE_CATALOG.md)。目录中的旧综合稿仅用于确认 R0 身份与问题线索；本篇方法和数字从一手原文恢复，不用旧模型调查代证。项目意义只在 §10 讨论。

### 1.1 原文覆盖表

| PDF 范围 | 原文章节／材料 | 本次处理与笔记位置 |
| --- | --- | --- |
| p.1–3 | 摘要、§1 Introduction、Fig.1–2 | 全读并核图；问题、贡献和接入边界 → §2–3 |
| p.3–4 | §2.1 Agent RL Systems；§2.2 Low-Intrusion Agent Instrumentation；§2.3 SWE Task Evaluation and Benchmark；§2.4 Token Fidelity | 全读；训练器／执行服务／评测框架的区别 → §2；历史比较与限制 → §2.2 |
| p.4–6 | §3.1 Architecture、Fig.3；§3.2 Harness and Proxy Capture，包括 adapter/runtime | 全读并核图；提交、gateway、协议、运行环境 → §3 |
| p.6 | §3.3 Asynchronous Rollout Staging | 全读；阶段池、预热、共享 deadline → §3.3 |
| p.7–8 | §3.4 Trajectory Reconstruction、Fig.4、四组展示公式、Fig.5 | 全读并目视公式／图；重建与保真边界 → §4；系统对照 → §6.3 |
| p.9 | Fig.6、§3.5 Evaluation and Reward Propagation | 全读并核曲线；reward 广播／逐 trace 奖励 → §5；训练曲线 → §6.2 |
| p.9–10 | §4.1 SWE-Gym GRPO、Table 1、builder ablation 与 reward hacking | 全读；配方 → §5；全部结果与负结果 → §6 |
| p.10–11 | §4.2 Offline Data Generation、Table 2、case study、released format | 全读并核表；生成、筛选、切分、成本及表内冲突 → §7 |
| p.12–14 | §5 Conclusion、References | 正文全读；参考文献核来源身份与尾部范围，未逐篇扩读引用作品 |
| p.15 | A.1 Framework Comparison／Table 3；A.2 Hyperparameters／Table 4 | 全读并核表；历史横比 → §2.2；完整已披露配方 → §5.1 |
| p.16–17 | A.3 Task Payload；A.4 Trace；A.5 Service API Summary | PDF 全读并核 JSON；示例与实验配置分开 → §3.4、§5.2 |

本篇没有另一组被省略的数学、偏好、安全、多模态或蒸馏训练结果。通用能力扩展主要是架构主张；实际实验是 **四个独立 SWE RL run + 一项离线轨迹生成**，不能为了填模板而添加不存在的后训练阶段。

## 2. 核心问题与系统定位

### 2.1 将最低接入边界移到模型 API

论文的问题不是重新实现 PPO/GRPO，而是：**既有 agent 的工具格式、上下文管理、子代理和执行循环都已经写在 harness 里，能否不重写它们也收集可训练经验？** 作者选择已有模型调用端点作为公共边界，将 CLI、SDK 或二进制程序留在原来的执行路径内，由代理层记录模型输入和采样输出。[P, §1–2，pp.2–4][P2]

这形成三类分工。原生 harness 负责计划、工具调用和上下文处理；Polar 管理运行环境、模型调用记录、轨迹重建及评分；Slime 等训练后端负责参数优化和与推理引擎的协调。**Polar 不是 Slime、Megatron 或 SGLang 的替代品。** 它也不是仅用于读取 agent 日志的评测器：训练需要采样 token、行为概率、mask 和奖励，而文本日志本身不保证这些字段可恢复。[P, §2.1–2.4][P3]

“无需修改 harness 内部代码”不等于零接入成本。用户仍需改正常配置／环境变量，使模型请求指向 gateway；adapter 可能安装配置、MCP server 或 skills，再返回启动命令。协议转换、模型替换和环境配置仍是系统行为的一部分。[P, §3.2][P6]

### 2.2 相关工作与附录比较：只能按作者当时的定义理解

前作 ProRL Agent 已采用 rollout-as-a-service；Polar 改变的是接入合同：从在服务中实现 agent handler，转为启动原生 harness 并从外部监听模型请求。作者将 SkyRL-Agent 视为拥有自身 agent/env 抽象的训练系统，将 PRIME-RL/Slime 视为训练与推理侧系统，将 Harbor 视为原生 harness 评测的重要近邻；具体差别在模型代理边界和训练数据合同，而非这些系统“不支持 agent”。[P, §2][P3]

附录 Table 3 的历史快照如下。四列分别指：生成期间可消费并有版本／陈旧度处理；rollout 各阶段独立调度；可脱离特定 trainer 的持久任务 API；不重写原生 harness 就能训练。[P, A.1，p.15][P15]

| 作者比较的系统 | Async RL | Rollout 分阶段 | Rollout 服务化 | 原生 harness 无关 |
| --- | --- | --- | --- | --- |
| Polar | ✓ | ✓ | ✓ | ✓ |
| ProRL Agent | ✓ | ✓ | ✓ | × |
| SkyRL-Agent | ✓ | ✓ | × | ● |
| PRIME-RL | ✓ | × | × | × |
| Agent Lightning（2025 引用） | ● | × | ● | ● |
| rLLM | ● | × | × | × |
| OpenClaw-RL | ✓ | × | × | ● |

**✓ 为主要能力，● 为部分或计划中支持，× 只是作者未找到该属性作为主要设计合同**，不是不存在任何相近机制。附录还明确承认 rLLM 有 fully asynchronous training 和 token/logprob gateway。因此不能将这张表改写成“只有 Polar 能异步训练”，也不能用其 2025 Agent Lightning 引用判断后来的 v1.0。本文未独立重审所有竞争框架的最新实现。

<a id="runtime"></a>
## 3. 从任务提交到结果返回

### 3.1 数据单位与责任边界

| 单位 | 本文中的意义 | 常见误读 |
| --- | --- | --- |
| `TaskRequest` | 一份 instruction/runtime/harness 配置，指定 `num_samples` | 不一定只有一条轨迹 |
| Session | 一次独立 harness 执行；有 task/session ID、预算与 callback | 它才是服务的调度单位，不是每个模型请求 |
| Completion | 该 session 中一次被 proxy 捕获的模型调用 | 可以包含主代理、子代理或压缩等不同调用 |
| `CompletionSession` | 一个 session 的有序 completion 记录 | 有序不代表只有一条线性对话 |
| `Trajectory` | builder 的 session 级产物，包含一个或多个 `Trace` | trace 数可变，不等于独立 rollout 数变多 |
| `Trace` | 一个训练片段：prompt、response、mask、概率、reward、metadata | 一次 session 拆成十条 trace，不能无条件当作十次独立采样 |

以上来自 [P, §3.1、§3.4、A.3–A.4][P5]。同题组的统计与 trainer 如何给这些 trace 加权，是另外的训练消费问题，见 §5 和 §8。

Rollout server 将请求展开为 sessions，分配 gateway，持久化紧凑终态结果，提供 polling 并接收 callback。Gateway 在本节点启动 runtime、准备 harness、执行、重建、评测、清理；同一 gateway 也承载 proxy，使调用记录与 session registry 相连。Trainer 通过异步服务边界取得结果，而不持有 harness 的 Python 主循环。[P, §3.1，pp.4–5][P5]

### 3.2 模型代理捕获的四步，以及兼容性的条件

代理先根据路径和请求头识别 **Anthropic Messages、OpenAI Chat Completions、OpenAI Responses、Google generateContent**；再将角色、内容块、工具定义／选择、停止条件和生成参数规范化为本地推理端消费的 Chat Completions 形状，并加入需要的概率字段。推理响应中的 prompt token IDs、原始 sampled response IDs、logprob 与 finish reason 进入 completion record，最后把响应转换回 harness 所需的 provider 形状。[P, §3.2，pp.5–6][P6]

**流式处理有一个明确取舍：上游先取得非流式完整响应，再向 harness 发送合成的 provider-style SSE stream。** 这简化了记录，但仅说明兼容某些期待 SSE 的客户端；不能进一步宣称首 token 延迟、实时中断、取消与真正端到端流式请求完全相同。

论文列出 `claude_code`、`codex`、`gemini_cli`、`qwen_code`、`opencode`、`pi` 六种 shortcut 和通用 shell harness。**六种接入入口不等于六种都做过本篇 RL 训练。** Runtime 支持 start/stop/exec/upload/download/cancel，第一版为 Docker 与 rootless Apptainer；这些是运行抽象与部署选项，不构成完整的沙箱安全审计。[P, §3.2.1–3.2.2][P6]

### 3.3 阶段池、预热与超时

Gateway 的 **INIT → READY → RUNNING → POSTRUN** 将环境启动／依赖准备、已启动环境等待、harness 执行、轨迹重建／评分／回调／清理拆开。READY 为有界缓冲，其他阶段有独立 worker pools。Fig.3 中画出的 pool 数量是示意，不是 Table 4 的生产参数。[P, Fig.3，p.5；§3.3，p.6][P5]

RUNNING 不应被理解为纯 GPU 工作：真实 harness 仍交替等待模型、shell、文件、外部工具等。这里的目的，是不让昂贵初始化和评分占住本可用于执行其他 session 的资源。若 evaluator 要求干净环境，可在 agent 运行时预热评分 runtime，从关键路径中移出部分等待。

每个 session 带一个共享 deadline。已捕获模型调用后即使 harness 超时，gateway 仍进入 post-run，尽可能保留 partial traces 并标终态 TIMEOUT。**这是失败后的记录恢复，不是跨策略继续 rollout，也不意味着这些 token 都会参加梯度。** 本篇未给所有超时情况下评分还能获得多少剩余预算或最终如何补采。[P, §3.3.2][P6]

### 3.4 两份代表性 JSON 与服务 API

A.3 示例包含 task ID、instruction、`num_samples=8`、`timeout_seconds=1200`、Docker/runtime 配置、Codex adapter、prefix-merging、fresh SWE evaluator 和 callback；metadata 中有 `group_id`、`policy_version`、`rollout_step`。**它只是代表性 payload：实际 RL 表是每题 16 次，离线生成是 3600 秒；不能把示例的 8/1200 写成历史训练参数。** 示例中的 host network 与 workspace 路径也不是普遍的安全推荐。[P, A.3，p.16][P16]

A.4 展示 `prompt_ids`、`response_ids`、mask、logprob、messages、tools、finish reason、reward 与 session/task/builder/harness metadata。数组含省略符，且概率对象示例与 response token 示例并非可直接校验的完整同一序列；它是字段说明，不是可运行 golden trace。当前代码的 `response_logprobs` 已是 float 列表，见 §8，不将 JSON 草图当成当前模型 schema。[P, A.4，pp.16–17][P17]

A.5 的入口为 `POST /rollout/task/submit`、`GET /rollout/task/{task_id}`、`GET /rollout/status`、`POST /callbacks/session_result`，以及节点 register/heartbeat。Gateway 另有 session 创建／状态／删除和 provider 请求代理；结果持久化后的 session 删除是 best-effort cleanup。**持久任务状态不等于已经证明训练 exactly-once 或 crash-resume 一致性。**[P, A.5，p.17][P17]

<a id="reconstruction"></a>
## 4. 轨迹重建：完整恢复方法，而不扩张“保真”的含义

### 4.1 Per-request：保守基线保留每次真实调用

`per_request` 将每个 completion 单独转换成 trace，保留该次实际输入和输出。它对单次调用是无损的，但重复的长前缀与大量短 sample 会增加训练端负担；复杂 coding session 可以产生数百个片段。**片段多与有效独立经验多不是同一件事。**[P, §3.4.1，p.7][P7]

### 4.2 Prefix-merging 的原文条件与公式

§3.4.2 定义 completion $C_i$ 的 prompt token 序列 $p_i$、原始采样响应 $a_i$、响应概率记录 $\ell_i$ 和消息 $m_i$。先将调用分为若干按调用序号递增的链：

$$
\mathcal G=\{G_1,\ldots,G_J\},\qquad
G_j=(C_{i^j_1},\ldots,C_{i^j_{K_j}}).
$$

**原文要求先由规范化 message-level key 找候选，再检查“前一 prompt 是后一 prompt 的精确前缀”**：

$$
p_{i_{m+1}}[1:|p_{i_m}|]=p_{i_m}.
$$

注意它不是要求 $p_{i_m}\Vert a_{i_m}$ 整体为下次 prompt 的前缀。原因是 harness 会把上次 assistant 输出重新写回历史；这部分经过服务端规范化后，其 tokenization 可能不同于原始采样输出。[P, §3.4.2，pp.7–8][P7]

对同一链简写为 $(p_m,a_m,\ell_m)$。取后一 prompt 在前一 prompt 之后的 canonical tail：

$$
t_m=p_{m+1}[|p_m|+1:].
$$

设轮末 token ID 为 $e$，找 $t_m$ 中第一次出现的 $e$。若 $a_m$ 已自然以 $e$ 结束，interstitial $u_m$ 取其后缀；否则从这个 $e$ 开始保留，补上当前 assistant 轮的关闭边界。最终链的 token 序列为：

$$
z^{(j)}=p_1\Vert a_1\Vert u_1\Vert a_2\Vert u_2\Vert\cdots\Vert a_K.
$$

以上是原文四组展示公式，**原文未编号，本文不编造 Eq.1–4 引用**。一个链输出一条 trace：首 prompt 存为 `prompt_ids`，剩余序列存为 `response_ids`。$a_m$ 来自实际采样，mask=1、使用原始 logprob；$u_m$ 是工具结果、用户插入或模板 glue，mask=0，概率位置用合成占位保持对齐。[P, §3.4.2，p.8][P8]

### 4.3 Compaction、分支与子代理

算法不假定整个 session 是一条不断追加的对话。上下文压缩、历史改写、子代理或并行分支可以形成新链。Fig.4 的示例包含三次主代理调用和一次子代理调用，其中主历史经历压缩；逐请求表示有四条 trace，合并后可追加的主链合为一条，子代理与压缩后的调用各自保留，共三条。[P, Fig.4，p.7][P7]

“摘要进入下次输入”不表示摘要 token 自动作为当前动作训练。只有它本身是被捕获模型调用的 sampled output，才有独立动作来源；来自外部工具或复制的摘要在后续输入中是条件。本文没有披露针对摘要的独立 reward、GAE 或 CompactionRL 类目标。

### 4.4 原文不变量与需要另外验证的条件历史

作者明确的不变量是：输出中每个可训练 token 都来自行为策略实际生成，非生成 token 被 mask。它直接针对 retokenization drift：**不能用解码后再编码的 assistant 文本替代实际 sampled IDs。**[P, §2.4、§3.4.2][P8]

下面是阅读者提出的范围检查，不是作者的额外结论或本轮复现实验：**目标 token 身份一致，并不能单独证明后续动作前的完整条件 token 历史一致。** 若上次实际输出是两个 token，而下次服务端 canonical rendering 将同一文本变成一个 token，合并序列仍保留前者；后续动作在训练时看到的前缀就未必逐 token 等于它生成时的 $p_m$。原文的 prompt-prefix 条件没有检查这一更强性质。

因此，不能从上述不变量直接推出“合并前后 logprob、梯度或所有 importance ratio 完全相同”。确切影响应在固定模型和同一捕获 session 上，比较 per-request 与 merged prefix 的逐调用输入、重新计算的概率和训练权重。本篇没有报告这样的等价性实验；这也是保留 per-request 基线的一个用途，而不是否定已经报告的训练增益。

## 5. 奖励、实际 RL 配方与未披露语义

### 5.1 四个独立 RL run，而非统一多 harness 模型

主实验从同一个 **`Qwen/Qwen3.5-4B`** checkpoint 出发，分别通过 Codex、Claude Code、Qwen Code、Pi 运行 GRPO。训练集为 **`NovaSky-AI/SkyRL-v0-293-data` 的 train split，293 个 SWE-Gym 任务**，最终评测使用 SWE-Bench Verified。不是 SkyRL-Agent 的 4.5K R2E-Gym，也不是将四个 harness 混入一个训练组。[P, §4.1、A.2][P9]

本篇没有新增的 SFT warm-start、教师 logits 或 OPD 阶段。§7 的 122B 数据生成是另一个固定模型实验，**不能把它连成“122B 蒸馏 → 4B RL”流程**。

附录 Table 4 的完整披露如下：[P, A.2，p.15][P15]

| 配置 | 原文值 |
| --- | --- |
| 输入模型 | Qwen/Qwen3.5-4B |
| 数据 | NovaSky-AI/SkyRL-v0-293-data，train，293 tasks |
| Trainer | Slime asynchronous GRPO |
| Epochs | 1 |
| Rollout batch size | 4 |
| Samples per prompt | 16 |
| Trace construction | prefix_merging |
| Optimizer | Adam |
| Learning rate | $10^{-6}$ |
| Weight decay | 0.1 |
| TIS | Enabled |

一次名义 rollout batch 是 $4\times16=64$ 个 sessions，**不是固定 64 条 trainable trace**。Table 4 还明确省略 cluster topology 与 worker placement，故当前官方示例的 4+4 GPU 不能回填为历史实验硬件。

### 5.2 Reward 由 evaluator 产生，广播并不等于解决信用分配

Evaluator 在 builder 之后消费 trajectory、session 工件和可选的干净 runtime。普通 outcome 可以广播到每条 trace；需要过程奖励时也可按 trace 单独赋值。内置 session-completion reward 只能确认 session 完成，不能代替 SWE 正确性；`test_on_output` 与 `swebench_harness` 才检查任务输出。注册表允许扩展规则、agent judge 和 shaping，**接口支持不等于本篇训练了过程奖励模型**。[P, §3.5，p.9][P9]

SWE RL 通过 fresh runtime 上的 `swebench_harness` 检查最终补丁。论文没有完整披露 agent 侧哪些测试可见、评分控制面如何隔离、合法替代解审计、flakiness 过滤或奖励漏洞修复。干净评分 runtime 是一种实质隔离措施，但不能自动推出完整反作弊保证。

### 5.3 不从“standard GRPO”填出整套优化器

原文没有给 GRPO 目标公式，未写清优势标准差归一化、trace/session/group 的 loss 分母、PPO clip 范围、TIS 的阈值和具体概率、KL/entropy 系数、每批参数更新次数、全局梯度归一化或完整 optimizer 参数。[P, §4.1、A.2；已查正文与全部附录][P15]

同样，metadata 中存在 `policy_version` 不证明它表示每次生成实际使用的权重，更不证明单条长轨迹内没有版本变化。论文支持异步服务和 Slime 异步训练，但没有披露完整的版本发布／暂停／陈旧样本处置实验。本稿不补写 miles 的 consume-time staleness、DIS 或 R3 为其方法。

对失败轨迹应分开问：是否保留工件／记录，是否参与组统计，是否自身产生梯度，是否补采。论文主要描述第一项的 timeout 恢复；当前 bridge 对后几项有具体实现，单列在 §8，而非冒充原文已披露。

<a id="rl-results"></a>
## 6. 训练结果、系统消融与负结果

### 6.1 SWE-Bench Verified：四组内的前后比较

Table 1 的原值如下，gain 单位是**百分点**。[P, Table 1，p.10][P10]

| 原生 harness | Qwen3.5-4B 基座 | 对应 Polar RL 模型 | 增益 |
| --- | ---: | ---: | ---: |
| Codex | 3.8% | 26.4% | +22.6 pp |
| Claude Code | 29.8% | 34.6% | +4.8 pp |
| Qwen Code | 34.6% | 35.2% | +0.6 pp |
| Pi | 34.2% | 40.4% | +6.2 pp |

每行是在对应 harness 上评测本行训练结果。**它没有给四个 checkpoint × 四个 harness 的交叉矩阵，也没有一个混合训练后在未见 harness 上的测试。** 可以说“接入不同原生 harness 后分别完成了有效训练”，不能说“已证明接口不变性”或“多 harness 混训优于单 harness”。

作者将 Codex 较大增益解释为对不熟悉工具 schema、复杂提示和执行路径的适应。基座在四个 harness 间的巨大差异支持接口条件值得重视，但未隔离 parser、提示、工具、上下文与权重训练各自贡献。[P, §4.1，p.10][P10]

原文没有重复 seeds、误差条、完整 eval manifest、精确 harness revision、逐任务结果、统一 token／wall-clock 预算的充分披露。因而 +0.6 pp 不能自动称为统计显著，跨行最高值也不能直接用于判断哪个 harness 普遍更好。

### 6.2 Fig.6：保留精确窗口均值，而不只写“曲线上升”

四图横轴为训练 step（画到约 70 多步），纵轴为 outcome reward，作者解释为 rollout pass@1。灰线为高波动逐步值，彩线更平滑，平滑核未披露。正文给出首／末十步窗口均值，优先于目测曲线终点：[P, Fig.6，p.9；§4.1，p.10][P9]

| Harness | 首十步均值 | 末十步均值 | 原图应保留的现象 |
| --- | ---: | ---: | --- |
| Codex | 9.5% | 54.5% | 从接近零起步，整体上升，中段仍有回落 |
| Claude Code | 28.8% | 67.0% | 上升明显，但中后段不是单调改善 |
| Qwen Code | 61.6% | 66.0% | 起点较高、噪声大，中段平台／回落，最后改善有限 |
| Pi | 61.6% | 76.2% | 高起点上继续改善，也有局部波动 |

这些是**训练 rollout 的奖励均值**，不是 SWE-Bench Verified 分数，也不是训练前基座的独立验证准确率。没有将曲线条数当作多随机种子重复。

### 6.3 Fig.5：重建方式改变训练端负担

作者说明在相同模型、硬件和 topology 下，只改变 `per_request` 与 `prefix_merging`。Fig.5(b) 覆盖相同的 **3 个 training steps**：[P, Fig.5，p.8；§4.1 builder ablation，p.10][P8]

| 指标 | Per-request | Prefix-merging |
| --- | ---: | ---: |
| 作者称 trainer stream 中的 updates | 1,185 request-level | 218 merged-trace |
| 墙钟 | 189.5 min | 35.2 min |
| 平均 rollout GPU utilization | 20.4% | 87.7% |
| 报告加速比 | — | 5.39× |

按表述数字复算 $189.5/35.2\approx5.384$，与 5.39 的差异属于报告精度范围，本文保留作者值。**“3 个 training steps”与“1,185 updates”同时出现，原文未充分定义后者是何种 trainer 内部计数**；不要把它改写为 1,185 个独立策略版本或完整优化大步。

Fig.5(a) 另画一段异步执行 profile：横轴标 Training step，约 0–320；rollout utilization 长时间接近 90–100%，trainer 在攒够已评分组后成段活跃。这里 90–100% 是原图目测量级，非作者另报的均值。Fig.5(b) 横轴为墙钟分钟，per-request 下训练 GPU 长时间活跃、rollout 间歇工作；合并缩短了这一段训练处理。

**这是局部系统消融，不是 time-to-equal-quality 实验。** 没有同时给两种重建的完整学习曲线、最终验证质量、梯度等价、训练总 GPU-hours 或全部 CPU/环境成本。减少 trainer-facing 片段及其重复处理有明确效率证据，但若 trace 权重也随表示改变，语义影响仍需单独核实。标题中的 at scale 也不能替代多节点 scaling curve。

### 6.4 不应遗漏的负结果：逐请求广播终局 reward

作者尝试给每条 per-request trace 广播整个 session outcome，观察到显著 reward hacking，解释为缺少适当 session normalization 或更细过程奖励时，调用片段获得了噪声信用。相关 PRM 与归一化工具被列为后续方向。[P, §4.1，p.10][P10]

本篇没有给攻击样本、发生率、类别或 hardening 对照。因此不能把它具体化为“删除测试”“读取答案”，也不能声称 prefix-merging 已系统性消除作弊。它最直接说明：**采集完整 token 还不够，训练样本的组织方式与奖励传播也会改变学习行为。**

<a id="offline"></a>
## 7. 离线轨迹生产：独立案例，不是已经验证的 SFT 方法

### 7.1 固定生成模型、任务与服务配置

§4.2 使用固定 **Qwen3.5-122B-A10B**，经 **SGLang 单个 8×H100 serving job、TP=8、`max_model_len=32768`**，运行 **pi-coding-agent v0.67.68**。从七个 SWE-Gym 仓库取 1,638 instances，每题使用基于参考镜像的 Apptainer SIF，安装 Node.js 22 和 harness，在目标 commit 的 fresh checkout 上执行 bash/read/edit/write。[P, §4.2，pp.10–11][P11]

提交设置为 `max_concurrent=5–8`、`max_retries=1`、每题 `timeout=3600s`。`empty_generation` 会重试一次，其余结果按生成结果交给评价；这不是其余轨迹都收入数据集。入集条件仍是 evaluator 认定最终 patch 解决全部 FAIL_TO_PASS，且所有 PASS_TO_PASS 保持通过。

这条流程复用已有 SWE-Gym 环境，不提供从原始 PR 候选、构建失败、oracle/no-op、flakiness 到合格任务的完整生产漏斗。其“single-bit filter”是作者主动保持的窄筛选，不是全面验证了 instruction-test 对齐、过程合法性或替代解接受率。

### 7.2 Table 2 原值与不能静默修正的算术冲突

| Repo | Attempts（原表） | Accepted（原表） | Rate（原表） |
| --- | ---: | ---: | ---: |
| getmoto/moto | 343 | 184 | 53.6% |
| python/mypy | 257 | 101 | 39.3% |
| conan-io/conan | 71 | 27 | 38.0% |
| pydantic/pydantic | 81 | 24 | 29.6% |
| iterative/dvc | 219 | 45 | 20.5% |
| pandas-dev/pandas | 477 | 98 | 19.7% |
| dask/dask | 141 | 25 | 17.7% |
| **Total** | **1,638** | **504** | **30.8%** |

来源为 [P, Table 2，p.11][P11]，已目视 PDF 原表并对照 HTML；不是提取时丢行。

**本轮独立算术检查发现两处不一致：**七行 Attempts 合计 **1,589**，比 Total 少 **49**；Accepted 合计确为 **504**。另外 $98/477\approx20.55\%$，不是 pandas 行的 19.7%。$504/1638\approx30.77\%$ 与总行 30.8% 相符。

正文也使用 1,638 instances/attempts，但没有足够日志或逐题资产解释差异。不能擅自认定缺少的 49 次都是 retry，也不能反算一个“正确的 pandas Attempts”后替作者改表。因此这里保留原表、单列差异，**不用这些相互不一致的字段生成更精确的任务产率或成本估计**。正文关于较难数据框任务“低于20%”的归纳也受到 pandas 行冲突影响，宜按作者解释而非经核实的普遍规律引用。

### 7.3 数据格式、长度、切分与未来用途

作者称最终得到 **504 条 accepted trajectories**。每条包含 `instance_id`、repo、problem statement、base commit、version，以及完整 OpenAI-style messages（role/content/tool_calls/tool_call_id），以产生合格补丁的 assistant turn 结束。报告均值为 **104 messages/session、51 assistant turns**，长尾超过 200 turns；这里没有把 messages、assistant turns、raw token 数混为一个预算。[P, §4.2 released format，p.11][P11]

论文称以 Apache-2.0 发布在 [该 Hugging Face 数据集][D-out]，采用按仓库分层的 **90/10 train/test split，使每个仓库在两边都有代表**。因此不是 repository-held-out，也未披露按派生 bug/PR 族进一步隔离。发布描述以 messages 为核心，不能据此推定每条下载资产都包含可直接用于 RL 的行为 logprob 和 token tape。

作者提出以后可扩到 SWE-Gym 全部 **2,438** instances，换更强 teacher／其他 harness，或保留失败轨迹做 verifier 训练与偏好配对。**这些是可扩展方向，不是本篇已经训练并评测的额外模型。** 504 条轨迹适合后续 SFT 的意图，与它们已经带来下游模型收益，是两个不同证据等级。

### 7.4 成本口径

原文报告约 **64 GPU-hours，interactive partition**，属于上述 122B 固定模型的数据生成案例。它不是四个 4B RL run 的总成本，更不是 64 小时墙钟。论文没有分解 CPU/镜像生产、评分、失败重试和集群等待费用；此处不换算成 GPU 租金或 RepoHarness 八卡训练预算。[P, §4.2，p.11][P11]

<a id="implementation"></a>
## 8. 配套代码：仅核承重路径，不用现代默认补历史配方

以下 C 链接全部固定到 **`6a1ead6bfac054fce6c1e62d1a77b330d96c58db`**。本轮是静态阅读，没有运行服务器、模型、沙箱、Slime reducer 或故障注入。主要目的是核查论文接口与实际数据消费之间是否还需额外条件，而非判断历史实验“是否有 bug”。

### 8.1 实际训练入口与参数所有权

[C1 `examples/swegym_slime_grpo/README.md`][C1] 提供单节点 8×H100/H200/B200、4 train + 4 serve 的示例，Slime 管理 SGLang 与逐步 NCCL 权重同步。启动器准备 293-task JSONL、SIF、CLI 和权重转换；Slime bridge 指南还要求对 Slime router 与 SGLang token metadata 路径打补丁，不能以普通 provider 文本响应代替原始 token 捕获。[C1；C2 `src/slime_bridge/README.md`][C2]

[C3 `examples/swegym_slime_grpo/run.sh`][C3] 真实调用 `train_async.py`，配置 `slime_bridge.rollout.generate_rollout_polar_async`、reward hook、`post_process_rewards` 和 dynamic history。它不是仅凭函数名含 async 的同步演示，但本轮没有把所依赖 Slime 的完整调度器和分布式 reducer 展开审计。

当前脚本还明确设置：rollout batch=4、每题16；TP2/SP、CP1；一轮 rollout 一次 step；TIS；KL `low_var_kl` 系数0.001；entropy0；clip0.2/0.28；Adam lr1e-6、betas0.9/0.98、weight decay0.1。**其中仅少数在原文 Table 4 披露，其余都是当前代码事实。**

长度有多层：当前 `max_tokens_per_gpu=30000`，SGLang context=50000，rollout prompt/response 字段分别32000/16000。bridge 的 `_resolve_max_tokens` 又用 `max_tokens_per_gpu × CP` 限制单 trace 总长。这些字段不能合并成一个“Polar训练窗口”。[C3；C8 `src/slime_bridge/rollout.py::_resolve_max_tokens`][C8]

[C4 `polar_config.yaml`][C4] 当前默认 Codex、prefix_merging、fresh SWE evaluator，使用 Apptainer；task/request timeout 为2400秒，`polar_max_async_level=2`、`polar_min_complete_accept_fraction=0.6`。这也不是 A.3 的1200秒示例或离线的3600秒。配置里的 provider model name 是 harness 接口配置，不能据它另造一个 OpenAI teacher 训练阶段。

### 8.2 输入 token 与 logprob 的实际来源

[C5 `src/polar/trajectory/builder/record_utils.py::build_trace_from_completion`][C5] 从响应的 `input_token_ids`／`prompt_token_ids` 取得 prompt；输出优先使用返回的 token IDs，再从 `logprobs.content` 或 SGLang `meta_info.output_token_logprobs` 取得成对 ID/prob。**只有候选概率所附的 IDs 与选择的 response IDs 完全一致，才将两者绑定。**没有在此用 messages 本地重新分词来补齐。

缺字段时可能产生空 IDs 或 `response_logprobs=None`，故“builder 能产出对象”仍不代表“可以训练”。下游 adapter 会继续检查。当前 root README 允许 vLLM/SGLang，但特定后端是否实际返回所需原始字段，还依赖服务版本与 metadata 接线；本轮未执行逐 token 对拍。

### 8.3 Prefix-merging：原文与当前实现的两个差异

[C6 `src/polar/trajectory/builder/prefix_merging.py`][C6] 实际 build 调用 `_find_extendable_chain`，只按 **上一 prompt 是当前 prompt 的非空 token 前缀，并选择最长匹配 tip** 路由。原文和同提交的 [builder README][C6-doc] 所述 message-level candidate gate，没有出现在这段实际路由中。它允许长度相等的 prompt；仅凭这个匹配不应推定所有相同输入的分支、retry 都能区分。这里只记录条件与复核需求，未运行反例测发生率。

`_finalize_chain` 从原始 response 拼 token，用 EOT 找 canonical interstitial；EOT 可配置，默认取链内首个自然停止响应的末 token。自然停止名包括 stop/tool_calls/stop_sequence。插入位置 mask0，采样位置保留真实概率；若有可训练 token 缺概率，最终 logprob 列表会为 None，等待下游拒绝。

另一个重要边界是 **重建提前中止**：当 EOT 不可取得、找不到分界或 prefix 检查失败时，当前函数 `break`，只返回已合并的 `chain[:kept]`；增加 `chains_reconstructed_truncated` 计数，**没有在同一函数把剩余 completion 重新输出为 per-request traces**。`build` 外层仍可返回 COMPLETED trajectory。故“服务成功完成”“trace 是所有调用的完整覆盖”“重建统计没有损失”是三个不同命题。相关代码存在不表示论文历史训练实际丢了多少数据。

### 8.4 从 trace 到 Sample：先看状态怎样被实际消费

[C7 `src/slime_bridge/adapter.py::session_result_to_samples`][C7] 将一条 session 的多个 trace 转为多个 Slime Sample。它们共享 `Sample.group_id=trajectory_index`，而 `group_index` 标同题 prompt group。Polar task metadata 的 `group_id` 与这个 Sample 字段含义不能直接混用。

当前状态传播和过滤如下：

| 实际输入条件 | adapter 行为 | 训练语义边界 |
| --- | --- | --- |
| prompt/response 空，或 trace 总长超过 max_tokens | 丢弃该 trace | 可能只剩 session 的部分 traces，不是整 session 原封保留 |
| 所有 traces 不可用 | 生成零 mask、reward0、ABORTED、`remove_sample=True` 的占位 | 防止空列表破坏下游；不是一条真实失败动作轨迹 |
| session/trajectory TIMEOUT | ABORTED，mask 全零 | 不等于 `finish_reason=length` |
| session/trajectory ERROR 或有 error | FAILED，mask 全零 | 后续 baseline 是否排除，还要看 reward postprocessor |
| 仅 trace `finish_reason=length` | TRUNCATED；不因这个状态自动清零 | 当前实现仍可训练其动作 token |
| 其他可训练 trace | 校验 mask、概率存在性及长度 | 原始 messages 保留作调试，实际训练输入为 tokens 与 logprobs |

这份表对应 `_sample_status → _loss_mask_from_trace → _extract_rollout_log_probs → Sample` 的实际顺序，不根据注释意图推断全部失败语义。可训练 token 缺概率或数组不对齐会抛 `RolloutLogprobError`；插入位置的0.0概率只是零 mask 的占位。

### 8.5 当前奖励后处理是 trajectory-aware LOO，不是未披露的论文公式

[C9 `src/slime_bridge/reward_post_process.py::post_process_rewards`][C9] 仅在 rewards normalization 开启、estimator 属 GRPO/GSPO/reinforce-plus-plus-baseline 时执行下面逻辑，否则返回原 reward。它按 `(group_index, group_id)` 收拢同题下各 session 的 traces；某 session 有 FAILED/ABORTED 成员，或没有可训练 token，就不作为有效 trajectory 计算 baseline。

对有效 session $j$，先对其有效 trace reward 求均值 $\bar r_j$；trace $k$ 的处理值为：

$$
\widetilde A_{j,k}
=\frac{r_{j,k}-\operatorname{mean}_{h\ne j,\ h\in V}\bar r_h}{s_{-j}}.
$$

**这是本文对固定代码的符号化说明，不是 Polar 论文展示的 loss。** $V$ 是有效 trajectory 集。没有其他有效 trajectory 时 baseline=0；若关闭 std normalization，$s_{-j}=1$；开启时使用“其他 trajectory 均值”的样本标准差加 $10^{-6}$，其他成员不超过一个时 scale也为1。失效 trajectory 的输出处理值为0。

因此，当前失败／超时记录不仅可能无自身梯度，还会从其他 session 的 baseline 中排除；这不同于 SkyRL-Agent 原文的“保留 horizon reward/group statistics，仅屏蔽自身梯度”。是否正确取决于声明的训练目标，不能将两者都简写成同一种 mask。

bridge 文档说 Slime 0.3.0 会依 `Sample.group_id` 将多个 trace 作为一个 trajectory 梯度单位，但**本轮没有审计该版本完整 reducer、TIS/KL 与并行归一化**。标识传入和 reward hook 已核，不等于已经证明最终所有 loss 项都获得相同 session 权重。若部分 trace 被长度过滤，其余 trace 的保留与 reward 均值变化也需要放进实际消费检查。

### 8.6 组准入、版本 metadata 与评分：只覆盖已追到的位置

[C8 `src/slime_bridge/rollout.py`][C8] 本轮阅读 **1–415 行**，确认入口辅助函数、结果转换、完成比例判断和 worker 初始结构；未完整审计剩余异步状态机。`_completed_trainable_session_count` 检查 session status=COMPLETED 且有可训练 token，阈值为 `ceil(返回 sessions 数 × 0.6)`。**这里“completed”不是 reward>0**：正常完成但没有修好问题的轨迹仍可能是合法失败样本。

该文件保存提交时 policy version，并可向 accepted samples 添加 staleness/rollout metadata。这个观察不足以恢复精确消费时陈旧度合同、每个 completion 的权重身份或暂停恢复语义；后几项保持未检查，不从配置值2推断其全部含义。

[C10 `src/polar/trajectory/evaluator/swebench_harness.py::_grade`][C10] 通过 SWE-Gym（或 SWE-bench fallback）构建 test spec、执行 eval script、解析测试日志并读取 `resolved`；不能只把 shell exit code=0 当成功。具体 patch 捕获／过滤／fresh runtime 管理由父类及 gateway 承担，本轮未完整追踪，所以不宣称全面审计了评分隔离。

当前 commit 新增 Harbor 与 rubric evaluator；[evaluator README][C10-doc] 中有 agent-judge、per-trace rubric 和失败回退行为。这是 **2026-08 的实现扩展**，不是本篇 2026-05 的 PRM 训练或 reward-hacking 消融结果。保持这一版本边界，比把所有现代功能拼成“论文完整能力”更重要。

## 9. 成本、开放资产与未知项

### 9.1 哪些材料实际取得了

| 资产 | 本轮状态 | 可支持的判断 |
| --- | --- | --- |
| arXiv v1 HTML、PDF 文本和技术图页 | 已取得并读完范围 | 方法、表图、完整附录；不需要用旧摘要补正文 |
| 原始 TeX、本机 PDF 文件 | 下载未成功 | 是本轮访问限制，不是作者未公开 |
| 官方 Polar `stable` 固定提交与 §8 指定代码 | 已读取 | 当前接口、示例、关键转换与部分消费路径 |
| 293-task 训练集 HF 页面 | 已取得，显示 train=293 rows、两个 split；无独立 dataset card | 与论文使用的 train 数相符；未下载并冻结全量资产 revision |
| 作者发布的504轨迹 HF 入口 | 本轮返回429／未取得数据内容 | 仅按论文记录发布主张，不宣称核验了逐行质量、切分和实际许可文件 |
| RL 后四个 checkpoint、完整日志与逐题评测资产 | 本轮未取得已验证 manifest | 不宣称已具备一键复现或已下载模型 |
| 沙箱、训练、梯度对照实验 | 未运行 | 静态检查和算术检查不算独立实验复现 |

训练集入口为 [SkyRL-v0-293-data][D-in]；输出集为 [Polar offline dataset][D-out]。当前代码仓库标 Apache-2.0；论文与各模型、数据集、基础仓库的许可各自独立，代码仓库许可不能自动覆盖全部训练资产。

### 9.2 最影响复用的未知和冲突

| 问题 | 类型 | 已查范围与不能代填的内容 |
| --- | --- | --- |
| 四个RL run的硬件型号/数量、总时长/GPU-hours | 原文未披露 | A.2明确省略；不能拿离线8H100/64GPU-h或现代4+4脚本代填 |
| 原始 GRPO/TIS 概率、clip、mask、分母与有效组消费 | 原文未完整披露 | §4.1、A.2–A.4；现代LOO hook单列为代码事实 |
| 训练/评测的精确 harness revision、token和时间预算、重复次数 | 原文未充分披露 | 全文及附录；不借一般benchmark默认设置补齐 |
| Prefix-merging 与 per-request 的同目标／梯度等价 | 没有相应实验披露 | Fig.5提供速度，未给完整质量对照或fixed-weight replay |
| 动态历史、同prompt分支、重建截断的损失率 | 原文未披露；现代代码只有机制与计数 | 不以接口设计证明零漏样本 |
| Table2逐仓Attempts与总计、pandas Rate | 原文内部不一致 | PDF与HTML均核；不自行猜哪一栏笔误或用retry解释 |
| 原文 message gate 与现代实际路由 | 版本／文档差异 | C6和C6-doc；不能反向判断历史训练缺该gate |
| Reward hacking 的具体机制、频率与最终抑制效果 | 原文未披露 | §4.1只有现象和解释；不补攻击taxonomy或修复成绩 |
| 最终Slime reducer及完整async状态机 | 本轮未检查 | 已核bridge关键字段，不称端到端数值/版本审计 |
| 独立复现／独立 reviewer | 本轮未完成 | 作者自查状态与独立审查分开 |

预算应按四类分别记录：环境资产构建未单列；4B RL 总成本未给；122B 离线生成约64 GPU-hours；最终 benchmark 评测成本未给。三训练步的189.5/35.2分钟只是一个局部对照，不能把这些数合成一份“Polar完整训练总账”。

## 10. 对 RepoHarness 项目一的有限判断

映射日期：2026-09-07；参考 [当前状态简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)。当前组合为 miles/SGLang、vendored slime adapter 与真实 Claude Code；rh2 负责环境入口、评分与合法训练消费。目标是单节点8×96GB、约30B-A3B，尚不能据旧probe或本地单测宣称正式训练增益。本节是设计层候选，未重新审计本项目全部实现。

### 10.1 这篇改变什么，不要求改变什么

**它支持把原生 harness 接入和训练消费作为研究工程问题，而不要求自研训练内核。** 四个小模型实验也说明原生接口适应可以带来差异很大的收益。但这既不能保证30B-A3B会有相同幅度，也不能把“接入更多harness”本身视作跨接口能力研究的结论。

**它同时削弱一种简单说法：只要精确抓到token，训练语义就已经正确。** 逐请求奖励广播的负结果、trace fan-out和现代bridge归一化都说明，奖励归属、逻辑采样单位和loss权重仍然重要。这些是与现有rh2边界直接相关的问题，不是另建平台的理由。

| 候选借鉴 | 来源依据 | 对本项目的边界 | 最小对照 |
| --- | --- | --- | --- |
| 真实harness接入后检查实际输入与样本消费 | §3.2–3.4；C5–C9 | 先验证已有miles/adapter，不能将上游捕获接口记为自行发明 | 固定session比较每次调用、重建trace、进入loss的数据；包括历史重写和分支 |
| 轨迹切分与reward/group权重共同验证 | per-request hacking；现代trajectory-aware hook | 不照搬现代LOO替换当前已约定GRPO/DIS；先明确目标 | 相同逻辑rollouts不同表示，核reward组、动作mask、各loss分母和真实梯度贡献 |
| 分阶段减少环境／评分等待 | §3.3与局部profile | miles与已有评分队列可能已经覆盖，测瓶颈后才改 | 同任务/资源上限，报告有效逻辑组吞吐与最终质量；不要只计trace数 |
| 原生harness前后训练结果 | Table1/Fig6 | 本文是分别训练，不是混训或迁移证据 | 固定主评测面；第二harness单列，区分parser/config修复与权重收益 |

这篇最值得带入下一次项目讨论的控制变量是：**减少训练片段以后，是否仍在优化声明的同一目标；系统节省的时间能否转成更多可信学习，而非仅改变了每条经验的权重。** 先做固定样本诊断，再做有限在线对照，比直接复制整套Polar服务更适合当前资源和已有基座。

最后，数据供给方面本篇证明的是复用环境生成可评分轨迹；它不单独支持上线动态curriculum、长期自动生成任务或训练一个新的verifier。对这些候选，应继续使用其他专项来源和本项目实际失败分布判断。

## 11. 快速定位与关联阅读

| 常见问题 | 本篇位置 | 原文位置 |
| --- | --- | --- |
| 黑盒harness怎样进入RL？ | §2–3 | §1–3.2，Fig.1–3 |
| 训练token从哪里来，何时合并？ | §4、§8.2–8.3 | §3.4，Fig.4，pp.7–8 |
| 293题与每组16次配方 | §5 | §4.1、A.2/Table4 |
| +22.6等增益代表什么？ | §6.1–6.2 | Table1、Fig.6，pp.9–10 |
| 5.39×有没有等质量对照？ | §6.3 | Fig.5、builder ablation |
| 504轨迹、64GPU-hours与数据表冲突 | §7 | §4.2/Table2，p.11 |
| timeout与length当前怎样消费？ | §8.4–8.6 | 固定C7/C8/C9，不是原文完整规则 |
| 示例JSON与训练预算不同怎么办？ | §3.4、§5 | A.2–A.5，pp.15–17 |

已存在的关联笔记：[SkyRL-Agent](O01_skyrl_agent_sa_swe.md)、[miles接入专题](N11_miles_agentic_rollout.md)、[SWE-smith](E5_swe_smith.md)、[R2E-Gym](O03_r2e_gym.md)。它们可提供对照，但不用于替Polar补写未披露参数。其他并行新笔记由汇总线程登记，本稿不猜测文件名或更改共享索引。

## 12. 作者自查与交付状态

**本篇正文与附录精读、重要图表目视核对、关键现代代码定点检查已完成。** 全部差值、Table2逐行合计、百分比及速度比在本地独立算术检查；不是GPU实验、环境测试或模型训练复现。

没有独立审查子agent或外部reviewer，本稿状态为 **作者自查完成，待独立复查**。详细检查范围和修正见 [R0作者自查记录](reviews/R0_polar_self_check_20260907.md)。本任务只维护本篇与该记录，不修改其他来源笔记、README、catalog、批次状态、训练实现或项目定案。

## 一手来源链接

[P-abs]: https://arxiv.org/abs/2605.24220
[P]: https://arxiv.org/pdf/2605.24220v1
[P-html]: https://arxiv.org/html/2605.24220v1
[P2]: https://arxiv.org/pdf/2605.24220v1#page=2
[P3]: https://arxiv.org/pdf/2605.24220v1#page=3
[P5]: https://arxiv.org/pdf/2605.24220v1#page=5
[P6]: https://arxiv.org/pdf/2605.24220v1#page=6
[P7]: https://arxiv.org/pdf/2605.24220v1#page=7
[P8]: https://arxiv.org/pdf/2605.24220v1#page=8
[P9]: https://arxiv.org/pdf/2605.24220v1#page=9
[P10]: https://arxiv.org/pdf/2605.24220v1#page=10
[P11]: https://arxiv.org/pdf/2605.24220v1#page=11
[P15]: https://arxiv.org/pdf/2605.24220v1#page=15
[P16]: https://arxiv.org/pdf/2605.24220v1#page=16
[P17]: https://arxiv.org/pdf/2605.24220v1#page=17
[D-in]: https://huggingface.co/datasets/NovaSky-AI/SkyRL-v0-293-data
[D-out]: https://huggingface.co/datasets/nvidia/polar-swegym-pi-qwen35-122b-a10b-trajectories
[C0]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/README.md
[C1]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/examples/swegym_slime_grpo/README.md
[C2]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/slime_bridge/README.md
[C3]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/examples/swegym_slime_grpo/run.sh
[C4]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/examples/swegym_slime_grpo/polar_config.yaml
[C5]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/builder/record_utils.py
[C6]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/builder/prefix_merging.py
[C6-doc]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/builder/README.md
[C7]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/slime_bridge/adapter.py
[C8]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/slime_bridge/rollout.py
[C9]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/slime_bridge/reward_post_process.py
[C10]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/evaluator/swebench_harness.py
[C10-doc]: https://github.com/NVIDIA-NeMo/ProRL-Agent-Server/blob/6a1ead6bfac054fce6c1e62d1a77b330d96c58db/src/polar/trajectory/evaluator/README.md
