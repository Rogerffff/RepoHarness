# N10 Forge: Scalable Agent RL Framework and Algorithm：后训练与项目一精读

Forge 是 MiniMax 对 M2.5 内部 agent RL 系统的官方介绍。文章把吞吐、训练稳定性、agent 灵活性放在一起设计：Gateway/Data Pool 解耦真实 harness 与训推引擎；Windowed FIFO 限制训练消费的乱序范围；prefix tree merging 减少训练中的重复前缀计算；CISPO 配合过程、时间及任务奖励。最明确的工程启发是“实际进入训练的分布和 token 语义必须一起看”。但文章没有公开完整训练配置、失败/重试合同或可运行 Forge 代码；40× 和百万量级日处理样本也没有足以复现实验的分母。黑盒 reward 图呈总体改善与明显波动，不能当严格收敛或未见 scaffold 泛化的证明。

导航：[来源与覆盖](#source) · [系统与黑白盒](#architecture) · [Windowed FIFO](#fifo) · [前缀与推理优化](#prefix) · [算法与奖励](#algorithm) · [证据边界和项目映射](#project)

<a id="source"></a>
## 1. 来源、版本、日期与覆盖

- 正式标题：**Forge: Scalable Agent RL Framework and Algorithm**。作者为 MiniMax 官方 HF 组织 `MiniMax-AI`，页面共同作者列 Hyn、zhi zhang、Jiayuan Song、Da Chen、xkc、Yaoyao、kennyKK、zpysky1125；它是官方组织发布的 Community Article，不是独立同行评审论文。
- [官方文章](https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm)，页面日期 **2026-02-13**。2026-09-07 读取的 HTML JSON-LD 标明 `datePublished/dateCreated=2026-02-13T04:18:07.300Z`，`dateModified=2026-02-13T08:46:39.885Z`。只确认这些元数据，未获得当天编辑前版本，不能猜具体修改内容。
- [固定 HTML](sources/N10/forge.html)、[提取文字（含公式原始 TeX）](sources/N10/forge.txt)。本文用原网页 §号和图名定位；网页四张技术图均已实际目视，封面也已检查，见下表。HTML 正文未发现 tabs、details、select、iframe/video 或交互案例；不把评论回复折叠当技术内容。
- 本文指向 **M2.5 的 Forge**。独立来源 R4（2026-05-26 v1、2026-07-30 v2）的更多 MDP/奖励/数据细节见[R4 笔记](R4_minimax_m2_series.md)。R4 两版技术内容未变；**本篇不会用后来的报告悄悄补全早期文章**。
- 未精读 M2.1、M2-Her、M1、Magi Attention 配套论文或模型仓库；链接或名词只作导航，不能增加成品数量或继承配置。

| 原文章节 | 独立阅读覆盖 | 本文位置 |
|---|---|---|
| 引言和封面 | M2.5、十万量级 scaffold/environment、200k、百万量级 samples/day | §2、§7 |
| §1、§1.1–1.3 Problem Formulation | Effective Agent Training Yield、token 一致性、长尾/分布、稀疏信用、执行速度 | §2 |
| §2.1 RL System Design；`arch` 图 | Agent / Middleware / Engines 及同步权重、数据记录 | §3.1 |
| §2.2 White-Box CM | context rot、训练/推理 CM 分布差异、状态转移 | §3.2 |
| §2.3 Black-box；`black_rl` 曲线 | OpenCode、Truncate BC、无侵入接入、实验曲线限制 | §3.3、§7 |
| §3.1 Windowed FIFO；`window` 图 | 队列、窗口、局部 greedy、全局阻塞、lag 例子 | §4 |
| §3.2 两个子标题；`tree_merge` 图 | 重复计算、前缀树、attention primitives、还原 loss、40× | §5.1 |
| §3.3 Extreme Inference Acceleration | MTP/top-K KL、PD 分离、全局 L3 KV | §5.2 |
| §4.1 RL Algorithm | mixed-domain CISPO、完整公式、baseline/奖励项缺口 | §6.1 |
| §4.2 Dense and Efficiency-Aware Reward | 过程/时间信号、reward-to-go | §6.2 |
| §5 Conclusions | 系统联合设计的作者主张，无附录 | §7 |
| 文末推荐与评论 | 仅检查发布/资产线索，非额外方法来源 | §7.3 |

这是一篇系统/算法短文，没有另外的 SFT、数据生产或安全附录；没有因只关注 SWE 而忽略其 Reasoning/General QA 内容。

## 2. 要解决的问题与规模口径

文章引言称 M2.5 构建过程中经过**超过十万种不同真实 agent scaffolds 与 environments**，context 可达 **200k**，每天处理**百万量级 samples**。这几个量不能互换：没有 scaffold 与 environment 各自数量、唯一题数、每题采样数，也没说明 sample 是一次 completion、整条 episode、入池对象还是最终消费对象。百万 samples/day 不能除成已证实的训练 trajectories/s，更不能当 RL 总训练样本量。

§1 定义概念目标：
\[
\max_\theta J(\theta)=\operatorname{Throughput}(A)\operatorname{SampleEfficiency}(A),
\quad A\in\Omega_{agent},\quad E[\operatorname{UpdateVariance}]<\delta,
\quad E[\|J^{(T)}-J^*\|]<\epsilon.
\]

Throughput 指原始 token/s，受 rollout、training、data processing、I/O 四段制约；sample efficiency 是平均每样本的性能增益，取决于任务分布/质量、算法和 off-policy 程度。公式是设计目标和代理约束，未给 δ/ε、J* 的估计，也不是实测“有效产出”指标。

三类冲突为：（§1.1–1.3）

1. Agent 与训练共享内部状态会限制 CM、多 agent 等循环；TITO（Token-In-Token-Out）要求 agent 深度理解 token，复杂 CM 时高层逻辑与训练 token 难保持一致。作者批评这种耦合，**不是证明 token 一致性从此无需验证**。
2. 完成时间从秒到小时。按派发顺序严格 FIFO/同步会被最慢任务卡住；greedy/FFFO 先完成先取则可能先偏短/易、后集中难任务，引发分布偏移与梯度波动。短耗时与“容易”是作者描述的相关性，不是普适定义。
3. 长程任务数千动作的稀疏终局 reward 难做信用分配；只优化正确率又不激励减少实际工具与串行执行延迟。

<a id="architecture"></a>
## 3. 系统分工与真实 harness

### 3.1 三层架构与一条数据流

§2.1 的[架构图](sources/N10/arch.png)显示：

- **Agent Side** 是真实白盒/黑盒 agent 及其环境，编排思考、CM、工具和交互，作为轨迹生产者。
- **Middleware** 内 Gateway Server 通过标准协议路由 agent 的 completion 请求到模型；Data Pool 分布式异步收轨迹/报告，为生成与训练解耦并提供处理/组 batch 空间。图示 `Completions: prompt_ids, response_ids, …` 和 `Rewards: outcome, process`。
- **Engines** 中 Rollout Engine 生成 token；Train Engine 消费 Data Pool 序列、更新 policy，并向 Rollout Engine 同步权重。

这只给逻辑流程，不给逐 token 捕获时机、重分词规则或日志 schema。图中的标准接口不等于精确 OpenAI API 版本；Gateway 的 `prompt_ids/response_ids` 也不能证明所有改写前动作均被无重复捕获。所谓物理隔离是架构分离描述，不能推为安全沙箱、隐藏测试隔离或抗作弊保证。

作者称已集成数百种 scaffold、数千工具调用格式，与引言“十万量级 scaffold/environment”是不同集合和粗粒度单位。离线评测发现 scaffold 会明显改变表现，是多 scaffold 训练动机；未给每 scaffold 的 heldout 测试矩阵。（§2.1）

### 3.2 白盒：将 CM 放入 RL 交互分布

§2.2 指出 context rot 可在尚未超 context cap 时发生：重复 observations 与中间 reasoning 稀释注意力。只在部署阶段加入 CM 会让模型遭遇训练未见的上下文转换。Forge 把 CM 当驱动状态转移的功能动作，训练策略适应压缩/剪枝后状态，学习保留任务关键内容。

这是**作者机制解释**，没有 CM 具体阈值、summarizer 版本、压缩质量曲线，或独立 CM 改善数表；不能推成已披露的可微 memory policy、专门训练 CM 网络或梯度穿过任意字符串重写。后来的 R4 才更明确形式化生成接口 MDP；本篇应保留自己的披露层级。

### 3.3 黑盒：接请求而不改 agent 内部

§2.3 中 agent 把请求路由到 RL Gateway，训练框架负责收集和训练，支持 memory compression/history rewrite、Deep Think、多 agent 等内部循环。明确例子是把 **OpenCode Agent 完全作为黑盒训练**，以及使用激进上下文压缩的 **Truncate BC**；名称出现不等于给了它们的 commit、工具配置和输入语料。

[Black Box Agent RL 图](sources/N10/black_rl.png)横轴 Training Time (hours)，约 0–54h；纵轴 Reward。目视起点约 0.51、末点约 0.64，中间最高约 0.72，明显多次回落。这是图上近似读数，非作者数表。它支持“在某个黑盒训练实验中 reward 总体上升”的有限判断；没有任务身份/样本数、平滑方法、多个 seed、基线或独立评测曲线，不能证明所有黑盒都收敛、稳定单调，或未见 scaffold 泛化已被单独验证。

<a id="fifo"></a>
## 4. Windowed FIFO：选择已完成轨迹的可见范围

§3.1 明确约束的是 **Training Scheduler 从 global generation queue 取完成轨迹**，不是推理端按 token 长度安排请求。队列为 `Q=[T0,T1,…,T(N−1)]`，按生成派发次序，当前头为 i，窗口 W；只可取 `[Ti,…,T(i+W−1)]` 内已完成项。

- **窗口内局部 greedy**：允许后项先完成先取，不必等待绝对第一项。
- **窗口外全局阻塞**：即使完成，也不能抢先进入训练。
- **推进规则**：队头被消费后窗口才前移；因此长期 straggler 会在窗口内其他项耗尽后继续阻塞。

`W=0.3N` 是示例，**不是论文证明的最佳比例，也不是只取最短的 30%**。N 是 generation batch size，不是 CISPO 每题 rollout 数 G。源文范围上界为 `i+W−1`，但描述窗外的例句写 `j>i+W`，漏写恰好 `j=i+W`；本笔记按显式闭区间理解窗外从 `i+W` 起，保留该边界措辞缺口。

**阅读者例解。** i=0、W=4 时，仅 0–3 可消费；若 1–3 完成则可先取，4 即使完成也不可取；0 消费后向前推进。这保存派发顺序附近的分布，同时容忍有限乱序，无法消除所有长尾或保证每 batch 的类别比例一致。若任务永久挂起，文章没有提供窗口越过它的取消/超时规则。

[window 原图](sources/N10/window.png)用另一个示例 **N=8、W=4**，初始 0–7 来自 model version 0；当 0–10 除 7 外都完成训练，窗口剩余容量为 1，7 之后图示 11/12/13 仍不可越界。标注 Max Out-of-Order Tolerance=3=`4−1`、Max Off-Policy Lag=10=`8+3−1`。这说明作者考虑了策略滞后，但**没有给消费次数、optimizer update、权重版本发布的转换定义**；不得泛化为生产环境统一版本界 `N+W−2`，更不能替换 rh2/miles consume-time staleness。

没有 Windowed FIFO 对严格 FIFO/FFFO 的吞吐、任务分布距离、最终 reward 或同预算 benchmark 对照表；因此其定量收益未公开。相同任务最终全部消费和固定墙钟下实际消费是不同问题，窗口规则不能自动消除后者的选择偏差。

<a id="prefix"></a>
## 5. 训练前缀合并与推理优化

### 5.1 Prefix tree merging

§3.2 两个小节指出多轮 append、不同 sampling branches、CM/summary 后请求仍可共享很长 prefix，逐样本独立算前缀浪费算力。合并把这些请求组织为树，共同部分 forward 一次、后续分支分别算，用 attention primitives（举 Magi Attention）保持标准 forward 的逻辑；随后按 metadata 拆回样本计算 loss。[原图](sources/N10/tree_merge.png)有共享 `long common context`、`seq1` 与 `seq2→seq3` 两条分支。

作者声称 **40× training speedup**，降低内存开销且与标准训练严格数学等价。直接 baseline 只是“每个样本独立重复计算共同前缀”的朴素方法，**没有公开硬件、长前缀比例、轨迹长度、batch、具体实现或端到端耗时**。这不是已测“RL 全流程加速 40×”，也不是同一硬件下优于成熟 miles/verl 内核 40×。R4 后来表述为 up to 40×，不能偷偷改成本文已带该限定的原句；本篇仍仅以局部作者声明引用。

**阅读者推论。** 必须保留原有 token、位置/因果可见性和独立样本 loss 权重，才能主张等价。计算一次共享 prefix 不代表这个 prefix 只应贡献一次 loss，也不授权把多个逻辑 episode 合成一个样本；共享 assistant response 在多少请求中训练，要由原有目标确定。本文未披露梯度累积、dropout/RNG、MoE routing、mask 和分母的实现一致性验证。

### 5.2 三项推理工程

| 原文 §3.3 技术 | 披露的机制 | 未披露的关键量 |
|---|---|---|
| MTP speculative decoding | draft heads 在 RL 中持续用 Top-K KL 微调以跟随变化中的 policy，维持接受率 | K、KL 方向/系数、teacher/主 policy 是否冻结、head 数、接受率和实测速度 |
| Heterogeneous PD disaggregation | 分开调度 Prefill/Decode，避开 MoE 混排干扰，各实例独立选并行策略 | GPU 类型/数量、TP/EP/DP、网络/KV 搬迁与尾延迟分布 |
| Global L3 KV Cache Pool | DFS-backed cache；group-level rollout 增 prefix 命中；路由权衡排队与迁移成本 | 容量、eviction、命中率、版本失效与收益数表 |

MTP top-K KL 属于追随 policy 的 draft 训练，不是披露“多领域专家 OPD”；不能从 M1/M2 架构或 serving 默认值补齐 Forge 文章参数。

<a id="algorithm"></a>
## 6. CISPO、混合领域和 reward

### 6.1 公式实际写了什么

§4.1 明确用 CISPO（Clipped Importance Sampling Policy Optimization），同时混 **Reasoning、General QA、Agent**，作者以它对比顺序多阶段域训练的干扰。文章没有 SFT→RL 详细阶段链；也不应将其“unified”措辞扩为 M2 全家族从未分阶段，R4 后来明确每阶段内混域的课程。

网页公式及 HTML 中原始 TeX 为：
\[
J_{\rm CISPO}(\theta)=\mathbb E_{(q,a)\sim D,\{o_i\}_{i=1}^G\sim\pi_{\theta_{old}}(\cdot|q)}\left[
\frac{1}{\sum_{i=1}^G|o_i|}\sum_{i=1}^G\sum_{t=1}^{|o_i|}
\operatorname{sg}(\hat r_{i,t}(\theta))\hat A_{i,t}\log\pi_\theta(o_{i,t}|q,o_{i,<t})\right],
\]
\[
\hat r_{i,t}=\operatorname{clip}(r_{i,t},0,1+\epsilon_{high}^{IS}),\qquad
\hat A_{i,t}=\sum_{p=t}^{T}(r_p^{speed}+r_p^{perf})-B_i.
\]

含义按公式可确定：新 policy 的 log-prob 梯度，被停止梯度的 clipped importance weight 与 advantage 缩放；上下界是 0 和 `1+ε`。这不是 PPO `min` surrogate，也不是超过 clip 就一律删 token。分母是所示组内全部输出长度总和，不能改成每轨迹等权均值。

披露边界：G/ε 未给数值；`r_{i,t}` 在本文未展开成策略比率定义；`B_i` 未定义计算方法，不能用 M1 的 group mean/std 补齐。`q,a,o_i` 关系、request/episode/turn 的组织、reward step 到 token 的映射、哪些 token 包含在 `|o_i|`、tool observation/thinking/CM masks、失败组统计都没有完整说明。R4 后来补了比例公式及 trajectory baseline 的文字，但仍不是本文证据。

### 6.2 三类奖励及公式/文字不一致

§4.2 的 process reward 处罚语言混用和特定工具调用错误，补终局反馈稀疏的问题；completion-time reward 使用相对完成时间，计入工具执行与 sub-agent 延迟，鼓励并行；reward-to-go 用于降方差、改善信用分配。

**公式只出现 speed+perf，正文另述 process reward**，没有交代 process 如何进入 `A` 或单独 loss。不能把 R4 的 `α process+β speed+perf` 移入本篇作为文章已公开公式；也没有 baseline 时间、shaping function、α/β、discount γ 或标准化方式。文字说 reward-to-go “normalize returns”，但所示公式是未来奖励求和减 baseline，不能据此推断 GRPO 标准差归一化。

没有公开三种奖励的独立消融、speed reward 对正确率影响、混域比例和遗忘测试。本文没有额外 role-play RLHF、偏好模型、安全对齐、SFT 或数据过滤部分；这些在 R4 中另有范围不同的描述。

## 7. 实验、成本与复现程度

### 7.1 证据清单

| 可引用声明/图 | 测量对象与边界 |
|---|---|
| 引言的百万量级 samples/day | 全系统日处理量级，sample 定义与 GPU 分母未给；不是有效训练样本吞吐 |
| §3.2 的 40× | 训练侧重复 prefix 计算优化的声明，没有匹配 workload 表；非端到端 RL |
| §2.3 black_rl | 单条 reward vs hours 曲线，约 54h；是一次黑盒案例，非全部 M2.5 训练时长 |
| 数百 scaffold / 数千 tool formats | 兼容性规模声明；没有各自测试结果或 unseen split |
| Windowed FIFO 的 W=0.3N / 图中 lag=10 | 设计例子；非模型成绩、最优超参或通用版本上界 |
| “解决 impossible triangle” | 作者对联合系统的总结，未给一般收敛证明或每组件受控增益 |

文章没有标准 benchmark 最终成绩表、模型准确 checkpoint、同底座同数据同算力对照、多次训练重复或方差。黑盒曲线明显起伏，应保留这个负面信号；也没有系统列出的失败实验。不要将缺少对照包装成已经证明“CISPO 比 PPO 更稳定”或“Windowed FIFO 在所有场景更快”。

### 7.2 训练资源与终止语义未知项

已查引言、§1–5、全部技术图和公式，没有披露：

- SFT/训练初始化、任务生产漏斗、训练题量与真正消费量、teacher 模型、任务/仓库/time split、污染防控、license 处理、gold/no-op/替代解验证及隐藏 grader 隔离。
- GPU 型号/数量、拓扑、精度、并行布局、optimizer/LR/steps/batch/minibatch、每题 rollout G、KL/entropy 主损失、速度/过程奖励权重。
- max_new_tokens、单次 context hard cap 配置、工具轮次/请求上限、wall-clock 训练 episode 预算；200k 是范围描述。
- rollout 失败/截断/工具超时/坏环境的 reward、group statistic、梯度 mask 和补采；取消、重试上限、幂等、partial rollout/resume、完成前 token 是否继续用于训练。
- sync weights 时机、policy-version 标记与跨版本 token spans、lag 单位、过期丢弃/重生成、recompute logprob、队列背压与永久 straggler 的退出语义。

因此环境/API、teacher、RL training、评测四类成本均无法由本文重建；黑盒图小时数不能充当全流程成本。

### 7.3 开放资产边界

正文把 Forge 称内部框架，没有给可运行源码/数据/环境/config 链接。评论区有 M2.5 模型/仓库发布线索，这只能证明页面有资产导航，不能证明开源了 Forge 训练实现。本次不下载权重、不检查整仓；“未见正文公开 Forge 实现入口”是检查范围内结论，不断言所有网络位置都不存在代码。

<a id="project"></a>
## 8. 对 RepoHarness 项目一的意义及旧稿校正

映射日期 2026-09-07；参考[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)和[项目一设计建议 §4–6](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)。主资料 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`；实际 miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`。本次仅窄查接口与职责，没有扩成全仓审计。

`reference/miles-rh2-integration/miles/rollout/fully_async_rollout.py::FullyAsyncRolloutFn` 持续派发并把完成组送入 buffer；同 commit 的 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py::DefaultDataBuffer` 以**完成入池顺序** FIFO，put 作 ABORTED/dynamic filter，get 作 consume-time staleness。文件中的 FIFO 是已完成组 FIFO，不能与 Forge 原始生成队列窗口混为同一算法。miles 已有 buffer capacity、unused handler 与关停接线，不能把这些列成 rh2 必须从头造的新平台。

| 借鉴候选 | 上游承担 / rh2 增量 | 最小验证 |
|---|---|---|
| 实际消费分布而不只看生成 TPS（§1、§3.1） | miles 管异步消费/版本；rh2 只补已有事件的离线分析 | 同任务池看派发→完成→消费按任务族/长度/耗时的分布，连同 stale drop、实际消费组/GPU-hour；先发现偏差再讨论 window |
| 黑盒请求流与 CM 训练一致性（§2） | 主仓 `rh2/src/repoharness2/adapters/slime/capture_wire.py::CaptureRegistry`、`rh2/src/repoharness2/adapters/miles/canonicalize.py::canonicalize_sample` 是现有接线 | 真实 Claude Code rewrite/fork/compaction trace，核生成动作和训练 token、mask、重复权重与行为概率；不是另造 Gateway |
| Prefix computation reuse（§3.2） | 训练 attention 和推理 KV 优化归后端 | 固定请求集验证 loss/梯度等价与 prefix 重复率，再量局部/端到端成本；不承诺 40× |
| 速度 reward 和多 scaffold（§4、§2.3） | 当前首训先用既定任务 reward；此处是以后候选 | 先把 tool/queue/inference/grade 时间分开测；第二 harness 先作等预算 eval，不能直接引入时间罚或多 agent 训练 |

旧[训练证据矩阵](../agentic_rl_training_recipe_evidence_matrix.md)把 M1/M2 并排只能作导航，M1 的 group-relative advantage 不应补本文 `B_i`；R4 的 192K 与 N10 的 200k 各有来源，不擅自统一为实际 hard cap。旧[infra 映射](../infra_mapping_for_repoharness_rl_serving.md)将前缀、KV、PD 交给上游的职责原则仍合理，但前缀 digest 或“支持黑盒”不自动证明训练 token 与概率对齐。[设计建议 §4.2](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)“先测消费偏差、不先重写 scheduler”的判断有本文支持；未因此批准新的调度策略。

可支持简历叙事的是对真实 harness、队列选择偏差和 token loss 边界的理解。自己的吞吐、预算收益与 heldout 学习改善仍需要匹配实验，不能借 MiniMax 的规模声明代替。

## 9. 独立检查与修订记录

主任务 ID `01a07827-1e44-7133-85d7-658445c04597`，实际 `gpt-6-astra / high`，主派发线程已核验。与 R4 共用唯一一名干净上下文审查者，记录见[09 审查](reviews/09_R4_N10_review.md)。固定初稿副本 `sources/N10/N10_minimax_forge.draft-20260907.md`；来源为 2026-09-07 抓取、元数据最后修改 2026-02-13 的官方 HTML，初稿日期 2026-09-07。2026-09-07 已收到完整审查：审查者 ID `01a07831-76f5-7ae1-8211-2dc348e68bbd`，实际 `gpt-6-astra / high`、`fork_turns="none"`，会话日志核实身份与配置。N10 未发现必须修订的事实错误或整块遗漏；R4 的三项发现已逐项修订，处理见审查记录。N10 仅补本审查状态，原有披露边界继续保留。
