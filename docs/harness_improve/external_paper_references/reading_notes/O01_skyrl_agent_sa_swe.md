# O01 SkyRL-Agent：多轮 Agent RL 的训练配方、流水线与证据边界

SkyRL-Agent 的主要贡献是训练内核之上的 agent 执行与轨迹组织层。作者用 4.5K R2E-Gym 任务，从 Qwen3-32B 直接进行 RL：训练期加入 AST 搜索与恢复提示，结合初始化／执行／评分流水线，在移除专用搜索工具的 Simple ReAct 评测中达到 SWE-Bench Verified 39.4%，基座为 24.4%。其 **1.55× 是 generation 阶段的调度对比；SWE 参数更新仍为 fully on-policy**。表中 4,601 对 9,180 H100-hours 约为两倍成本差，不能拆成 AST、提示和调度各自的因果收益。本文还完整覆盖深度研究、记忆和计算机使用的独立训练案例，保留 judge 敏感性、服务故障、答案泄漏与 OSWorld 验证不改善等结果；当前官方代码另列，不倒填 2025 年实验。

导航：[来源与覆盖](#source) · [架构与调度](#architecture) · [SWE 数据与训练](#swe) · [评测与成本](#evaluation) · [其他三类 Agent](#other-agents) · [官方代码核查](#code) · [未知项与项目意义](#project)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**主来源 P。** Shiyi Cao、Dacheng Li、Fangzhou Zhao、Shuo Yuan、Sumanth R Hegde、Connor Chen、Charlie Ruan、Tyler Griggs、Shu Liu、Eric Tang、Richard Liaw、Philipp Moritz、Matei Zaharia、Joseph E. Gonzalez、Ion Stoica，*SkyRL-Agent: Efficient RL Training for Multi-turn LLM Agent*，NovaSky AI / UC Berkeley / Anyscale。首次提交 **2025-11-20**；2026-09-07 查询 [arXiv 版本历史][P-abs]，只列 v1。主读 [v1 PDF][P] 与 [v1 HTML][P-html]。PDF 共 **16 个物理页**，页眉注明 Work in Progress。**SA-SWE-32B 是模型名，不是论文标题；SkyRL-v0 是另一项较早工作。**

**范围。** 通读摘要、§1–5 全部正文，逐项核查 Table 1–3、Figure 1–7、Listing 1–3 和 §2 的公式；检查末尾致谢与参考文献，恢复正文省略的数据／方法引用身份。**该版本没有单列技术附录**：正文到 p.13，之后为致谢／参考文献，最后一页 p.16 仍是参考文献。这里的“全文精读”不表示又全文阅读了每篇参考文献。

PDF 图表实际通过网页截图查看。部分带 v1 的截图请求失败后，使用 arXiv 无版本 PDF 入口补读；该入口当时同样显示 v1 水印、16 页及相同正文。没有取得完整 TeX，也没有将 PDF、截图或第三方代码副本上传本库；以下定位均使用可独立访问的官方链接，不建立不存在的本地附件链接。

**代码来源 C。** 官方 `NovaSky-AI/SkyRL`，固定 main 提交 **`0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518`**，提交日期 2026-09-05。只检查 §8 所列路径与关键函数，不宣称整库审计或复现历史训练。此提交晚于论文约十个月，不能当作 SA-SWE 原始训练的已验证 revision。

**项目基线与旧稿。** 本项目读取基线为 `Rogerffff/RepoHarness@miles-migration` 的 **`458d3617c2494650c3fa98c3c7cdc848b825e275`**。复用 [旧 horizon 专题](../sa_swe_horizon_masking_analysis.md) 提出的问题与定位，不复制其过时 FA/slime 项目结论。当前映射只放在 §10；依据 [当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md) 与 [项目一建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)，不改实施定案。

### 1.1 原文覆盖表

| 原文位置（PDF 物理页） | 原文内容与本次处理 | 本笔记位置 |
| --- | --- | --- |
| p.1 摘要、Fig.1(a)(b) | 全读；目视训练曲线、generation 时间轴、硬件及 125-step 脚注 | 摘要、§3、§6 |
| p.2–3 §1 | 动机、三类贡献、4.5K 数据与跨域主张，全读 | §2、§4、§6 |
| p.3–4 §2、Table 1、POMDP 公式 | 全读并核原表；框架横比仅为作者当时的快照 | §2 |
| p.4–5 §3.1、Fig.2、Listing 1 | 工具、runtime、agent state 与后端分工，全读并核图／代码示例 | §2–3 |
| p.5–6 §3.2、Fig.3、Listing 2 | 三种 dispatch、信号量作用范围、1.55× 的分母，全读 | §3 |
| p.7–8 §3.3–3.4、Listing 3 | transition 捕获、动态打包、后端数据、终止与可恢复错误，全读 | §2.3、§5、§8 |
| p.8–9 §4.1–4.2、Fig.4 | 完整交互训练、AST、hints、LOO、horizon mask、thinking 模板，全读 | §4–5 |
| p.9–11 §4.3、Table 2–3 | 四项评测、全部表值、scaffold 差异、成本及迁移解释，全读并核原表 | §6 |
| p.11–12 §5.1、Fig.5 | 数据难度分层、GRPO、summarizer、judge、服务与泄漏，全读 | §7.1 |
| p.12 §5.2、Fig.6(a)(b) | Next 工具、文档分块、Tinker LoRA、verifier、不同来源参考结果，全读 | §7.2 |
| p.12–13 §5.3、Fig.7 | accessibility tree、32 题／32 VM、VeRL GRPO、验证负结果，全读 | §7.3 |
| p.13–16 致谢与参考文献 | 检查尾部完整性，定位 MegaScience、GeneralReasoner、MemAgent、DeepSWE 等依赖；不逐篇扩读 | §1、§7、§11 |

**定位注意。** HTML 把部分 Listing 排成 Figure，导致后续编号偏移。本文一律用 PDF 编号：PDF Fig.3 对应 HTML Fig.4，PDF Fig.4 对应 HTML Fig.7，PDF Fig.5/6/7 对应 HTML Fig.8/9/10；PDF Listing 1/2/3 在 HTML 显示为 Fig.3/5/6。HTML 的 MemAgent 交叉引用也有偏移，不能仅按网页“Fig.8”定位。

<a id="architecture"></a>
## 2. 论文解决什么问题：训练内核之外的 Agent 执行层

### 2.1 三个可分开的职责

作者没有再提出一套训练内核，而是将 agent 后训练拆为工具与任务接入、异构 rollout 调度、训练后端桥接。SkyRL-train、VeRL 和 Tinker 承担优势估计和参数更新；SkyRL-Agent 组织模型调用、环境动作、轨迹与结果。runtime 可以是 Ray、K8s 或远程服务。**结构上的模块化和在多个后端上提供案例，不等于已经对同一实验验证跨后端数值等价。** [P, §1–3, pp.2–7][P2]

原文 Table 1 的完整比较对象为：

| 框架（作者 2025 年快照） | Backend | Agent execution | Interface | Runtime scaling | Trajectory |
| --- | --- | --- | --- | --- | --- |
| VeRL-Tool | VeRL | Data-parallel | Tool | Ray | Mask |
| rLLM | VeRL | Data-parallel | Gym | K8s | Mask / Transition |
| GEM | Multi | Data-parallel | Gym | — | Transition |
| Agent-Lightning | Multi | Data-parallel | — | — | Transition |
| SkyRL-Agent | Multi | Data + Pipeline，可扩展 | Tool | Ray / K8s | Mask / Transition |

这张表是作者对当时实现的归纳，本文没有重新审计各竞争框架；不能用于声称它们在 2026-09 仍缺相应能力。[P, Table 1, p.3][P3]

### 2.2 Tool-centric 不只代表函数调用格式

原文将三类操作放入统一工具抽象：无状态计算、改变外部环境的 shell／编辑操作、改变 agent 自身上下文的摘要／历史裁剪。Gym 的 `env.step()` 也可封装成工具。新任务绑定工具、instruction builder 与 verifier，不要求改写整个主循环。OSWorld 的示例把生成的 PyAutoGUI 代码传给 runtime，由 runtime 返回 observation、reward、done 和 info。[P, §3.1, Listing 1, p.5][P5]

文中允许同一训练作业绑定多种任务，但实际结果不是“一个模型混训 SWE、搜索、记忆、GUI”：SA-SWE 与 §5 的三个 Qwen3-8B 实验是不同训练案例。把工程支持范围写成已验证的统一多任务配方，会夸大结论。

### 2.3 Transition 与真实模型输入

§2 唯一的展示公式是一般 POMDP 目标：

$$
J(\theta)=\mathbb{E}_{\pi_\theta}\left[\sum_{t=1}^{T}r_t\right].
$$

这里 $T$ 是 agent turns，不是 token 数。模型根据当前上下文 $o_t$ 采样动作；摘要、裁剪或角色变化使下一轮上下文不再必然等于整段历史的简单追加。论文因此记录每次模型调用的输入 token、输出 token、以及推理端**能够返回时**的 logprob，再组织为训练输入。[P, §2, pp.3–4；§3.3, p.7][P7]

`@record_transition` 是捕获边界；具有一致前缀的连续 transition 可合并，发生上下文变化则保留多段。Listing 3 输出 prompt/response token、logprob、loss mask、trajectory reward、trajectory index 与运行指标。工具观测不作为模型动作进入 policy gradient；其后模型基于该观测作出的决策才是动作。

论文讨论“可以借助记录的概率进行训推偏差校正”，并引用 Flash-RL。这是接口可支持的方法，不是已经披露 SA-SWE 使用了某个具体 Flash-RL 修正。相同地，合并可连续追加的 transition 不能自动解释成任意分支的 prefix-tree attention 加速。当前实现的真实条件见 §8。

## 3. 异步调度：重叠哪些工作，究竟加速了什么

### 3.1 三阶段与三种 dispatch

每条 rollout 分为 **Init → Run → Eval**。Init 创建执行环境；Run 交替执行模型生成和工具调用；Eval 运行结果评分。Run 并非纯 GPU 工作，工具调用仍可能阻塞 CPU、网络或其他服务。[P, Fig.2, p.4；§3.2, pp.5–6][P4]

| 方法 | 控制单位 | 适合的作者示例 | 主要取舍 |
| --- | --- | --- | --- |
| Async Batch | 同时启动完整轨迹 | 初始化和评分轻的搜索推理 | 重型 runtime 容易过载 |
| Async Batch (Bounded) | 一个并发槽覆盖整条 Init→Run→Eval | 固定 VM、重置较便宜的 computer use | 轨迹处于 CPU 阶段时仍占整条并发槽，可能使模型生成供给不足 |
| Async Pipeline | 分阶段调度并重叠不同轨迹的 Init／Run／Eval | 初始化／评分较重的 SWE | 需分别控制服务容量、排队和资源存活期 |

Listing 2 的信号量围住整条生命周期，而不是只限制模型请求。Fig.3 的示意说明：整条轨迹限流时，初始化和评分可能集中成 GPU 空洞；分阶段调度允许其他轨迹填入这些空洞。优先派发评分昂贵的任务只是原文给出的可扩展策略例子，**没有独立性能消融**。[P, Fig.3、Listing 2, p.6][P6]

### 3.2 1.55× 的严格口径

Fig.1(b) 固定 **64 个任务、每题 8 条 rollout，共 512 条，2×8 H100**，比较 Async Pipeline 与 Async Batch (Bounded) 的 generation 阶段。作者报告约 **1.55×** 加速、流水线生成期间 GPU utilization 约 **90%**。图中横轴是时间，纵轴是 GPU utilization；不是模型 FLOP 利用率，也不是每步 optimizer 耗时。[P, Fig.1(b), p.1；§3.2, p.6][P1]

这个实验不能直接证明总训练时间改善 1.55×：训练反向、权重发布、评测、任务构建等是否计入，要看各自成本口径。它也不能证明完全消除长尾；流水线消除了部分阶段等待，但一批任务最后的未完成轨迹仍可能决定 makespan。

**尤其重要：这里的 async 是 rollout 内／轨迹间执行并发，而不是参数更新期间允许旧策略轨迹持续流入 learner。** §4.2 明确称 SWE 训练 fully on-policy。论文没有报告 bounded-staleness 阈值、in-flight weight update 或跨策略 partial-rollout 恢复实验。当前所查 SWE trainer 也先等待一批生成完成，再更新和发布权重，见 §8.1。

### 3.3 原文没有隔离的因素

图注称有 ablations，但 Fig.1(a) 的 none-resolved 基线取自 DeepSWE 的 W&B 日志。原文没有完整的“相同模型、数据、预算下，AST 开关 × hints 开关 × dispatcher 开关”矩阵，也没有各改动独立的训练成本表。**系统局部对照、跨工作训练曲线、最终模型对照，是三种不同证据。**

<a id="swe"></a>
## 4. SWE 数据、环境与工具增强

### 4.1 训练阶段：不是重新预训练，也没有新增教师蒸馏阶段

主线为：**已有 Qwen3-32B → 在 R2E-Gym 上进行工具引导的 RL → 选 step 125 checkpoint 评测**。这里是 dense Qwen3-32B；不能按本项目 30B-A3B 的激活量推算同等训练成本。作者称 pure RL，含义是这一专项训练没有先加入强教师轨迹蒸馏，不是否认输入模型本身已有的训练历史。[P, 摘要、§1、§4；Fig.1(a)][P1]

论文复用 **4.5K R2E-Gym 实例**，与文中 DeepSWE 对比使用同一数据集名称。它不是一篇从原始 PR 到完整环境资产的生产论文。按本篇能恢复的漏斗如下：

| 对象 | 本篇披露 | 不能补写的内容 |
| --- | --- | --- |
| 原始仓库／PR 候选 | 引用 R2E-Gym，未展开 | 原始候选数、构建率、人工审计率 |
| 实际 SWE 训练任务 | 4.5K instances | 精确 task manifest、revision、仓库切分、重复／污染核验流程 |
| 单个正常训练 batch | 64 tasks × 8 rollouts | 每一步实际有效梯度轨迹数、horizon 命中率、重试尝试数 |
| 最终 checkpoint | step 125 用于评测 | 全部训练只运行 125 步、checkpoint 选择依据、所有失败作业成本 |
| 环境／verifier | 真实仓库交互，提交 patch 后以项目测试判断 | 完整 F2P/P2P 清单、评分隔离与反作弊机制、合法替代解审计、flakiness 数据 |

图1曲线延伸超过 125 步，不能把“评测选 step 125”写成“总共只运行 125 步”。R2E-Gym 的独立环境与数据细节见 [O03 笔记](O03_r2e_gym.md)，但引用它不能替本篇补出未披露的具体版本。

### 4.2 改善定位工具，而不只是增加 RL 采样

作者观察到，较弱模型反复使用 view 分块看文件，不善于用 grep/find 构造准确查询，导致无关内容占满上下文。其应对是加入借鉴 LocAgent 的 **AST 搜索**，支持模糊匹配与结构模式检索，并在搜索结果尾部给下一步查询提示。[P, §4.2, pp.8–9][P8]

这改变了训练时可用的动作与观察，不只是更换数据分布。所谓 bootstrapping 指改善当前策略找到成功路径的机会，**不是 SFT warm-start**。文中的 50/64 none-resolved 示例，应按任务组尺度理解，不能写成 512 条 rollout 中只有 50 条失败；原文未正式定义这个指标，图轴及当前代码的按 instance 统计与任务组解释一致。

原文报告训练期间平均搜索调用约从 3 增到 4，平均 turns 约从 18 增到 25。这说明模型使用更多交互，不能同时据此声称每条成功轨迹更短或推理总成本下降。[P, §4.3, p.11][P11]

### 4.3 恢复 hints 是环境反馈，不是已经披露的过程奖励

训练期提示包括：工具失败后的后续动作、临近 step/context 预算、缺失／错误函数调用、更仔细地检查失败编辑。它们将模型从无效循环拉回可执行轨迹。论文没有给 hints 的逐项触发率、每类单独增益，也未披露一个对这些动作逐步打分的 reward model。[P, §3.4、§4.2, pp.7–9][P9]

这与 agent 主动调用 AST 工具应分开：两者都改善可探索的执行分布，但不是同一个处理。评测移除 AST，也不自动意味着评测移除了全部错误提示、工具描述和预算提醒。

## 5. SWE 算法、horizon 与训练消费

### 5.1 原文可以确认的配方

| 项目 | 论文披露 | 证据边界 |
| --- | --- | --- |
| 策略与更新节奏 | fully on-policy；train batch = mini-batch = 64 | 未披露跨版本 stale 校正；不能由此断言目标里没有 PPO likelihood ratio |
| 每题采样 | 8 条 rollout | 不是 8 个时间段，也不是 8 个独立 prompt |
| 优势估计 | leave-one-out，去掉标准差和长度归一化 | 原文措辞针对 advantage computation；没有完整 loss 分母公式 |
| 学习率 | 1e-6 | 优化器类型、betas、梯度裁剪等未给 |
| KL / entropy | 关闭 KL 和 entropy loss | 不自动证明执行中不计算任何 KL 诊断 |
| 训练限制 | 32K context、50 turns | 没有精确拆出全局上下文、单次生成、wall-clock 和评测超时的所有配置 |
| 外部限制终止 | 不改 reward/advantage 估计，只屏蔽该样本梯度 | 不等同删样本、重置 reward 为零或按存活成员重建组 |
| 多轮 thinking | 修改 Qwen3 chat template，保留历史 thinking | 未提供历史实验模板 revision |

全部来自 [P, §4.2, p.9][P9]。本文不把这套配方直接命名为本项目的 GRPO + faithful DIS；原文没有给 DIS、PPO clipping 或 critic 的专项公式。

### 5.2 “保留组统计、屏蔽自身梯度”究竟表示什么

原文明确：因为达到外部 context／turn 限制而停止的轨迹，其 reward 与 advantage 估计不因 masking 改变，只不参与梯度。作者动机是避免系统性压制需要更多行动或思考的轨迹。**这里并未规定此类轨迹的 reward 必须为 0**，也未披露如何评价所有不完整 patch。

下面只是将 leave-one-out 用一般符号展开，**不是论文里的编号公式或完整优化器**。同一题原组有 $G$ 个成员、reward 为 $r_i$：

$$
A_i=r_i-\frac{1}{G-1}\sum_{j\ne i}r_j.
$$

设第四条轨迹撞到外部上限且其 reward 恰为 0，原组 reward 为 $(1,0,0,0)$。保留组统计时，成功轨迹优势为 1，两条仍更新的失败轨迹各为 $-1/3$；第四条自身不更新。若先删除第四条再算 LOO，失败轨迹各为 $-1/2$。这说明**“该轨迹无梯度”和“它对其他轨迹没有影响”不是同一回事**。

完整优化还需要一个明确分母 $D$：例如按有效动作 token、原始序列数或常数预算归一化，会使全零 mask 样本对其余梯度的尺度产生不同影响。原文没有给 $D$，也没有给全 masked 组的补采／调度处理。当前示例配置选了某个 reduction，不足以证明 2025 年训练使用完全相同的定义。

在固定成员集、无 std 归一化时，LOO 与减组均值的优势相差 $G/(G-1)$。这是代数关系，不是对 Adam、梯度裁剪、动态 batch 与有限精度下训练轨迹完全等价的证明。只有把成员、mask 和分母一起固定，比较才有意义。

### 5.3 不同失败不能借用同一个 mask 解释

| 情况 | 原文说明 | 不应得出的结论 |
| --- | --- | --- |
| 达到 context／turn 外部上限 | 停止；§4.2 的 horizon 样本屏蔽梯度但保留统计 | 应从原组删除，或必然给予失败 reward |
| 函数解析／参数错误 | §3.4 注入纠正信息并继续下一步 | 所有工具失败都是不可训练的 infra 错误 |
| Deep Research 工具服务不足引起 timeout | §5.1 描述异常轨迹污染与防护需要 | 与正常预算终止完全相同的 reward 语义 |
| 当前代码的运行、评分、循环等错误 | 使用更多 finish reason，见 §8 | 每一种当前代码处置都在论文中经过消融 |

论文没有给上述所有情形的统一状态机。因此本项目能借鉴的是区分责任与消费阶段，而不是照搬一份错误字符串名单。

<a id="evaluation"></a>
## 6. SWE 结果、外部迁移、消融与成本

### 6.1 Table 2：统一 Simple ReAct 与各作者 reported 不能混排

Simple ReAct 提供 **bash + file editor**，最大 **40K context / 100 steps**，每个实例只生成一份 patch；文件编辑器来自 OpenHands ACI。专用 AST 搜索不在此评测工具面中。[P, §4.3, pp.9–10][P10]

| 模型（沿用原表名称） | 规模 | 原表 Recipe | Simple ReAct Pass@1 (%) | 原工作 Reported (%) | H100-hours |
| --- | --- | --- | ---: | ---: | ---: |
| Qwen3-32B | 32B | — | 24.4 | — | — |
| Qwen3-Coder-30B | 30B | — | 45.0 | — | — |
| SWE-agent-LM-32B | 32B | Sonnet 3.7 distillation | 38.0 | 40.2 | — |
| SWE-Swiss | 32B | R1 distillation + RL | × | 45.0 | — |
| Kimi-dev | 72B | R1 distillation + RL | × | 48.6 | — |
| DeepSWE | 32B | RL | 36.4 | 42.2 | 9,180 |
| SA-SWE-32B | 32B | RL | 39.4 | — | 4,601 |

`×` 是原表省略结果，不是零分。正文说 SWE-Swiss/Kimi-dev 在此 ReAct 工具协议上表现较差，因此只列原作成绩；那些 reported 数字采用不同 scaffold，不能直接用于计算本方法增益。SWE-agent-LM 的来源是 Qwen2.5-Coder-32B-Instruct + 5,016 条 SWE-smith 的 Sonnet 3.7 轨迹；不是所有行同底座。[P, Table 2 及邻文, pp.9–10][P10]

同一 Simple ReAct 列中，SA-SWE 比 Qwen3-32B 高 **15.0 个百分点**，比 DeepSWE 高 **3.0 个百分点**，但仍低于表中 Qwen3-Coder-30B 的 45.0。作者的 state-of-the-art 表述有限定的 open-recipe、规模和时间背景，不能转述为当时所有开放模型第一，更不能作为当前榜单判断。

**AST 撤除实验的边界。** 结果支持“训练时工具增强之后，模型仍能在不含该专用工具的评测接口上工作”。它不是已披露的训练期 AST 开／关等预算消融，也没有隔离 hints 与其他配方变化。作者把表现解释为搜索行为的内化；机制解释仍应与表中直接观察分开。

### 6.2 Table 3：迁移是小幅正结果，不是全面可靠性证明

| 模型 | Terminal-Bench (%) | BrowseComp-Plus accuracy (%) | BrowseComp-Plus 平均 turns | WebArena (%) |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-32B | 13.75 | 18.1 | 3.68 | 15.8 |
| SA-SWE-32B | 16.25 | 19.4 | 4.60 | 17.0 |
| 本文算术差值 | +2.50 pp | +1.30 pp | +0.92 | +1.20 pp |

原表与运行说明位于 [P, Table 3, p.10；解释 p.11][P10]。

**Terminal-Bench** 使用 **v0.1.1、80 题、OpenHands agent**；不是 2.x/3.x/4.x，也不是所有 benchmark 都运行在同一个 Simple ReAct 中。**BrowseComp-Plus** 是 830 题、固定且经人工验证的支持／hard-negative 文档语料，检索器为 Qwen3-Embedding-8B、每次 top-5；不能替换成在线 BrowseComp 的结论。**WebArena** 被描述为 812 项电商、论坛、协作及内容管理任务；本篇没有给足其完整运行配置与逐题清单。

§4 的迁移结果来自仅在 SWE 上训练的 SA-SWE，而不是再用 §5 数据联合训练的模型。没有报告重复种子、误差条、跨 harness 完整矩阵或系统性回归套件。BrowseComp-Plus 更高分伴随更多 turns，也不能解释成等推理成本下的效率改善。

### 6.3 成本：保留原值，不把粗略 headline 精确化

按 Table 2 算术：$9180/4601\approx1.995$，$1-4601/9180\approx49.88\%$。因此更准确的摘要是 **“表中训练 H100-hours 约减半”**。摘要／引言使用“超过 2×”，正文又写“50% lower”；这是一处粗略措辞与表中精确数字的边界，本文不擅改原表。[P, 摘要、§4.3、Table 2][P1]

4,601 与 9,180 是作者报告的 GPU-hour 对照，不是本文复现。它没有拆出所有 CPU runtime、外部 API、任务构建、环境验证、评测和失败尝试费用；也没有一个充分匹配的因子实验将成本差分配给 AST、hints、dispatcher 或其他优化。Fig.1(b) 的 16 H100 是该生成对照的明确配置，不据此反推全部训练固定使用 16 卡、精确墙钟天数或八张 RTX PRO 6000 的运行时长。

<a id="other-agents"></a>
## 7. 其他后训练案例：三个独立实验，不是 SWE 主模型的后续阶段

### 7.1 Deep Research：难度分层、摘要服务和 judge 敏感性

**工具与数据。** ReAct 搭配 SerperAPI 搜索、Jina Reader 获取网页；缓存减少重复读取；长网页分块摘要后再合并，并保留引用。数据源在正文只写 Fan et al.，参考文献对应 **MegaScience**。从中取 **50K 候选问题**，用 thinking-mode Qwen3-8B 每题四次离线 rollout 估计难度，再按学科平衡。[P, §5.1, pp.11–12；References 中 Fan et al.][P11]

| 四次采样的成功数 | 作者命名 | 训练混合比例 |
| --- | --- | ---: |
| 0/4 | Impossible | 25% |
| 1/4 | Hard | 30% |
| 2/4 | Medium | 30% |
| 3/4 | Easy | 15% |
| 4/4 | Perfect | 不纳入所述混合 |

这些是有限采样的分类名称，0/4 并不证明任务客观不可解。该流程是离线构建分布，不是已经验证的在线自适应课程。**50K 是校准候选数，文中未给重组后最终训练题数**；也没有均匀采样、简单混合或其他比例的同预算消融。

**训练角色。** 目标 Qwen3-8B；SkyRL-train 后端；GRPO；global batch=mini-batch=64，每题 8 rollout；lr=5e-6。训练 reward 使用 GeneralReasoner 工作的 general verifier。网页 summarizer 是 **Qwen3-235B non-reasoning**。summarizer 提供环境中的压缩信息，不是将 token-level logits 蒸馏给策略的 OPD teacher；不能把这个实验称为“不使用外部强模型”。[P, §5.1, p.11][P11]

**评测。** HLE-500 使用 LLM-as-a-Judge。采用较宽松 general verifier 时，成绩 **12.6%→18.8%**；改用主要 judge gpt-oss-20b 时，原文写 **9.2%→10.2% / 11.0%**。斜杠两值未交代对应 checkpoint、重复运行或其他条件，本文保留而不平均、不擅选。Fig.5 展示 reward 和 eval 曲线，但没有把每个点的 judge／样本身份完整列出，不能用图终点替换文本结果。

**性能与故障。** 网页处理约 10k tokens/request，重型 summarizer 成为瓶颈。文中例子：单 H200 服务 Qwen3-32B 时约 **2,101.6 s/iteration**，改 Qwen API 后约 **592.1 s/iteration**，比值约 **3.55**。后期使用四个 GH200 和 data-parallel router。这段服务排障过程与前面的 Qwen3-235B summarizer 描述并未给出完整一一对应关系，不能把四个 GH200 认定为目标 policy 的全部训练硬件，更不能据速度推出总费用下降。[P, §5.1 Challenges, pp.11–12][P12]

作者观察到供给不足导致 timeout 污染 rollout，约第 30 步出现下降并用 30–33 步恢复，因而强调服务容量和异常处理。这是一个特定运行的故障复盘，不是普遍的训练阈值，也不是异常 mask 的独立对照。

**泄漏。** 在 GPQA-Diamond 的另一次评测观察中，在线检索能直接找到公开答案；作者屏蔽 Hugging Face、GitHub、GitLab、Chegg 等域名。它说明检索任务存在答案通道风险，不能推出所有 HLE-500 结果已因此得到完整去污染，也不能把 GPQA 观察写成该实验另一个有成绩表的主 benchmark。

### 7.2 Memory Agent：训练的是分块后的状态转换，不是超长单次上下文

采用 MemAgent 式递归阅读：模型以 `Next` 工具提交当前块摘要，下一轮上下文重置为摘要加新文档块。RULER-HotpotQA 提供支持段落和干扰段落，单块最多 **4K tokens**；训练处理文档累计最多 **28K**，评测最多 **112K**。后两个数字是分块处理的序列规模，不能称为一次生成的 context window。[P, §5.2、Fig.6, p.12][P12]

训练从 **Qwen3-8B non-thinking** 开始，后端 **Tinker**，**LoRA rank=128，batch=32，rollouts=8，每 turn 最多 8K tokens**；答案 verifier 为 **GPT-5-nano**。原文未将“每 turn 8K”完全拆成输入／输出限制，也未给本例优化目标的完整公式、学习率、成本和数据量。

Fig.6(b) 展示约 20 步范围内 reward 与 validation 上升；没有独立最终结果表和误差条，不将目视曲线读数包装成精确百分比。文中 **79.69%** 是引用的 **MemAgent 原作**结果：Qwen2.5-7B-Instruct、batch=128、group=16、exact-match verifier。**它不是本文 Qwen3-8B/Tinker 的成绩**，更不是只改后端的同条件比较。

该案例证实作者实际训练过上下文会被改写的 agent；不证实跨会话终身记忆、用户偏好保持，也不证明任意黑盒 compaction 已具有正确的跨段信用分配。

### 7.3 Computer Use：训练上升但验证不改善的完整负结果

OSWorld 工具执行模型生成的 PyAutoGUI 代码，反馈为桌面 **accessibility tree**。虽然动作包含点击、滚动和键盘输入，这个实验不能被直接称作基于截图视觉输入训练 VLM。[P, §3.1 Listing 1；§5.3, pp.12–13][P13]

作者沿 ARPO 思路，从 benchmark 筛出 Hard/Medium/Easy 的 **32 个训练任务**。目标模型 Qwen3-8B，GRPO，**VeRL** 后端；**batch=8、每题 8 rollout**；执行采用 **32 个固定虚拟桌面**与 Async Batch (Bounded)，VM 通过 Ray remote task 扩展，CPU 环境反馈与 GPU 生成分离。32 个任务、32 个 VM 和一个 batch 的 64 条 rollout 是不同计数，不能互换。

reward 来自环境 native evaluation。Fig.7 给出训练 reward 曲线，但正文明确说 **validation accuracy 几乎没有改善**；作者将其解释为任务对 Qwen3-8B 困难、学到的策略难以迁移出训练环境。没有给精确验证集大小、独立 final score 或置信区间。应保留这个负结果，不能把本节只写成“成功扩展到 GUI RL”。

### 7.4 四个训练案例的关系总表

| 案例 | 输入模型 | 后端（论文明确程度） | 数据与反馈 | 结果性质 |
| --- | --- | --- | --- | --- |
| SA-SWE | Qwen3-32B | 本篇正文未明确钉死具体后端 revision；当前有 SkyRL-train 脚本 | 4.5K R2E-Gym；测试结果、工具与 hints | 主要模型对照、generation 对照及有限跨域结果 |
| Deep Research | Qwen3-8B | SkyRL-train | MegaScience 分层；通用 verifier；外部 summarizer | 有训练及 HLE-500 结果，judge 敏感 |
| Memory | Qwen3-8B non-thinking | Tinker，LoRA | RULER-HotpotQA；Next；GPT-5-nano | 有曲线，非完整成本／控制变量研究 |
| Computer Use | Qwen3-8B | VeRL | OSWorld 子集；native evaluator | train reward 上升，validation 无明显提升 |

正文没有另一套偏好、安全对齐、部署量化或多教师整合阶段；这是检查全文后的范围结论，不按旗舰报告模板额外补写。

<a id="code"></a>
## 8. 官方实现定点核查：当前代码能补什么，不能补什么

所有 C 链接固定到 **`0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518`**。这里是静态阅读，不是运行验证、历史训练复现或完整 bug 审计。选择直接的 `skyrl-agent` 路径，而不是用同仓库其他 mini-SWE 示例代表本论文。

### 8.1 真实入口与训练时序

[C1: `examples/run_skyrl/run_skyrl_swe.sh`][C1] 指向 `skyrl_agent.integrations.skyrl_train.skyrl_train_main`，设置 Qwen3-32B、2 节点×8 GPU、FSDP2、SP4、4 个 TP4 推理 engine、colocate、prefix caching 和 NCCL 权重同步。固定依赖包括 vLLM 0.9.2、Transformers 4.53.0、Torch 2.7.0。

[C2: `skyrl_swe.yaml`][C2] 选择 **OHCodeActAgent** 与 SWEBenchTask，开启 bash/editor/cmd/finish/search，关闭 browsing/jupyter/视觉。配置 8 rollout、50 iterations、32,768 agent 长度字段，训练 temperature=1、top_p=1；`async_pipeline` 的 run/init 并发配置 96、eval 96。shell 另有 `max_prompt_length=8000`、generation max=32768 和 algorithm max_seq_len=40768。**多个层级的长度字段不是同一个概念**，不能只抄一个值便宣称恢复了论文全部 token budget。

[C3: `SkyRLAgentPPOTrainer.train()`][C3] 的顺序是：准备一批 → `await generate` → 处理与转换 → forward 概率／reward → advantage → 更新 → 权重发布。共置时生成后先 sleep 推理引擎。该路径保留 batch 屏障，不能因为文件里有异步函数或数据加载器支持 fully_async 参数，就叫当前 SWE 示例为 fully-async learner。

### 8.2 worker 有界，不等于等待队列有界

[C4: `dispatcher/dispatchers.py::async_pipeline_dispatcher`][C4] 的三个队列通过 `asyncio.Queue()` 创建，**没有 `maxsize`**；init/run/eval 的 worker 数分别受配置限制，全部任务先放入 init queue。三组 worker 先同时启动，再等待各队列 `join()`，所以确实有阶段重叠。

但原文“bounded queues”与这个提交的字面实现并不相同。有限 worker 限制正在执行的阶段数，不自动限制 run/eval 等待队列长度，也不等于已初始化且仍存活的环境总数有相同上界。这是**当前代码与论文高层表述的差异**，不是已证明 2025 年实验存在错误。

该函数的单个 stage worker 没有统一 `try/finally` 保证异常后的 `task_done()`；如果异常逃出，可能使 `join()` 等待。部分具体 trajectory 函数自身捕获异常，所以这里只记录条件性静态风险，不声称实际复现了死锁。

### 8.3 精确 token 路径与 OH 消息兼容路径并存

[C5: `functional/utils.py`][C5] 中，`record_transition` 读取调用前的 `input_ids` 与返回的 `output_tokens/logprobs`；`transitions_to_training_data` 只在已累积 token 序列确实是下一轮 observation 前缀时合并，否则产生新 datum。observation mask=0，action mask=1。一个逻辑 trajectory 因上下文改变拆成多个 datum，不代表采到了多条独立 rollout。

两个必须注意的边界：其一，输出 logprob 缺失时，该转换会用 0.0 占位，不能把它理解成真实行为策略概率；其二，transition 的 agent_id 追踪仍有 TODO，接口存在不能自动推出任意子 agent 身份已正确隔离。

[C6: `agents/base.py::_post_process_results`][C6] 还有 **无 transitions 时的 messages 兼容分支**：重新应用 chat template 获取 token/mask，logprob 为 `None`。而 [C7: `OHCodeActAgent.step()`][C7] 调用 token 输入接口之后主要保存 response string 到 messages；[C8: `CodeActTrajectory.generate_trajectory()`][C8] 的结果包含 messages，而没有像通用 ReAct 路径那样交付 transition 列表。C2 正好选择 OHCodeActAgent。就这些静态路径，不能把现代 SWE 示例自动算成“全程原始 token 与 rollout logprob 捕获已闭合”。没有执行逐 token 对拍，因此也不在此给出实际漂移幅度。

### 8.4 LOO、mask 和 reduction 要分三处查看

[C3 的 `compute_advantages_and_returns_loop`][C3] 按传入 `index` 分组，用总分减掉当前分，再除以其余成员数得到 LOO baseline；无 std 归一化，在 `torch.no_grad()` 内计算，之后乘 response mask。单成员组退回零 baseline 并打印提示。函数接收 `values/gamma/lambd` 不表示它使用了 critic／GAE。

C6 在 finish reason 属于 context、max iterations、runtime、evaluation、bad response、loop、cmd timeout 等集合时，将该 datum 的 loss mask 全置零，但输出仍保留 reward。C8 的评分异常分支会给 `False` 并记错误类型；缺 patch 与其他评分异常又有不同 finish reason。**“reward 是否可信”“是否参与组统计”“是否产生自身梯度”必须分别跟踪**，不是看到全零 mask 就证明其他影响已消失。

C1 当前选择 `policy_loss_type=dual_clip`、clip low/high=0.2/0.28、`loss_reduction=seq_mean_token_sum_norm`、max_seq_len=40768、`update_epochs_per_batch=1`、`use_kl_loss=false`。这些是**示例配置事实**，不在论文中。这里没有完整审计该版本训练后端所有归一化与分片调用，故不把名称进一步扩写成“已验证的实际全局分母”。

### 8.5 失败占位可能影响他人的组统计：值得单独验证的静态路径

C6 处理空 messages 时，会寻找同一 instance 的非空结果，或某个全局可用组，**深拷贝整个结果**作为 fallback，再将 `finish_reason` 改为 `error_runtime`。原始平均 reward 在替换前统计，但后续生成的 reward 列表来自替换后的结果；因此复制的 reward 也可能被带入下游。

即便该 fallback 样本随后无自身梯度，若其 reward 仍参加别人的 LOO，影响不会自动消失。这个风险以“确实触发 fallback，且下游仍按这些 reward 估计组统计”为前提；本轮没有运行整个训练路径，也没有证明它影响了论文结果。它提供的复核问题比笼统声称“框架会自动正确 mask 所有坏轨迹”更具体。

### 8.6 开放资产与复现程度

[官方 agent README][C0] 与 examples 目录实际提供 SWE、Web Research、MemAgent 入口；固定版本 README 的 **OSWorld Integration 仍是未勾选 roadmap**。这与论文报告内部 OSWorld 训练并不矛盾，但不能把四个论文实验都算成现成公开 recipe。

[SA-SWE-32B 模型入口][M] 可访问；本轮没有下载权重、核验 safetensors、冻结模型 revision 或运行评测。C1 的训练／验证 parquet 指向作者本地路径，不能代替公开的逐题 manifest。代码、模型入口存在，只能说明有复用基础，不等于历史训练具备一键可复现性。原始论文、模型、依赖代码和数据集的许可应分别确认，本轮不作整套资产使用许可判定。

## 9. 最影响复用的未知项与冲突

| 问题 | 当前证据状态 | 已检查范围／正确处理 |
| --- | --- | --- |
| 精确 SWE 数据和划分 | 原文未披露完整 manifest | §1、§4、全部尾页；当前本地 parquet 路径不补足 |
| 环境构建／筛选漏斗与评分隔离 | 本篇未展开 | 不从 R2E-Gym 名称继承全部安全与质量保证 |
| 原始 loss 分母、clip、optimizer、有效 batch | 论文未完整披露 | §4.2 无对应公式；当前 C1 只能单列配置 |
| horizon 命中率、被 masked 后实际消费量 | 未披露 | 图1与§4.2没有这一数字 |
| reward 为零、未完成 patch、超时与补采的完整合同 | 未完整披露 | 区分论文 horizon 描述与 C6/C8 当前错误逻辑 |
| AST／hints 的独立因果增益 | 未充分隔离 | 有机制描述、跨工作曲线与去 AST 评测，没有完整等预算因子对照 |
| 全流程总费用、训练／工具硬件映射 | 不完整 | H100-hours、局部 summarizer 排障各自保留分母 |
| Deep Research 的 10.2% / 11.0% | 原文含糊 | 不推定为 seeds、checkpoint 或平均值 |
| MemAgent 本文精确最终分数 | 没有单独数表 | 曲线与引用原作的 79.69% 分开 |
| 历史 queue／token 行为与当前实现 | 未验证一致 | 固定 C commit；不把现代发现归到历史实验 |
| 原始 TeX、下载到本机的 PDF | 本轮未取得 | HTML全文与关键 PDF 图页已读；不是“作者未公开” |
| 独立复现／独立审查 | 本轮均未完成 | 实验不复现；阅读检查是作者自查 |

<a id="project"></a>
## 10. 对 RepoHarness 项目一的意义：候选验证，不是实施批准

映射日期 **2026-09-07**。项目条件为 miles + SGLang + 外部 coding harness + rh2，单节点 8×96GB 目标为约 30B-A3B MoE。当前简报仍保留环境、评分、训练消费及正式 GPU 资格开放项；本篇不将历史 probe 或单元测试改写成学习结果。

### 10.1 它同时支持两种项目进阶，而不是只支持一种

**系统线**：即便不改变 RL 算法，初始化／生成／评分的合理重叠仍可能减少昂贵等待。**学习线**：即便不增加任务数量，改善模型取得关键信息的工具与反馈，也可能改变成功轨迹的供给。

这意味着“只能靠新的 curriculum 才能超过旧项目”并不成立；“只要 fully async 就自然解决学习效率”也不成立。SkyRL-Agent 的可借鉴之处，是把运行效率与可学习的轨迹放在同一个训练闭环里观察。其弱点是尚未完全隔离两者的因果贡献。

| 候选借鉴 | 来源支持 | 本项目职责与条件 | 最小辨识实验 |
| --- | --- | --- | --- |
| Init/Run/Eval 分段测量与容量配置 | Fig.1(b)、§3.2 | 先核 miles 和现有 grading queue 已做什么；不要重新造通用调度平台 | 固定任务、模型与资源上限，改变一个阶段并发／供给策略，测 generation makespan、有效组吞吐、失败与任务组成 |
| 更好的查询／错误恢复反馈 | §4.2 AST+hints；没有完整单因素消融 | 真实 harness 可能已有强搜索工具；先测失败是否仍是定位或工具误用 | 同一小批任务原生工具 vs 一项增强；先看 pass@8、成本和错误模式，再决定训练 |
| 分离 horizon 的 reward、组成员和梯度 | §4.2 的明确语义 | C 包和现有 loss 合同未必采用此规则；不能直接移植到 fully async + DIS | 固定小组做参考计算，比较保组屏蔽与删后重算；同时核分母和过滤后的真实组身份 |
| 按实际输入 token 构造可重建训练段 | §3.3；C5/C6 路径差异 | 优先验证 miles session 与 vendored adapter 的真实接线，而不是再造 IR | 同一多轮轨迹在调用端与训练端逐段比 token/mask/logprob，包含上下文改写 |
| 统一最小评测加小规模迁移探针 | Table 2–3 | 公开旧 benchmark 是历史坐标，不自动决定当前主指标 | 原模型与训练模型固定 harness/预算；第二任务面单列结果与成本，保留失败样本 |

以上都是本篇证据导出的设计候选，不是论文验证了它们在 RepoHarness 八卡配置上成立。特别是 **1.55× 与 4,601 H100-hours 不能作为项目预期收益或预算报价**。

### 10.2 最值得用于方案讨论的五个判断

第一，先确认瓶颈是执行供给，还是模型根本采不到成功路径。两者的干预与成本不同。

第二，比较工具增强时，不能只看训练 reward；至少要在相同最终评测面上比较，防止把更强 runtime 当成权重收益。专用工具撤除是有用检查，但不能替代训练对照。

第三，任何“无梯度”处理都需要问清其是否还影响别人的 baseline 和整个 batch 的归一化；这直接关系到 rh2 的正确消费，而不是外围日志。

第四，多后端／多任务支持是系统可扩展性证据，不能写成跨后端数值一致或一个多域模型已经训练成功。OSWorld 的负结果应进入项目风险判断。

第五，研究工程成果可以来自成熟上游之上的窄改进，但必须保留 workload、原始样本单位、成本分母和外部结果。这个叙事不需要将整个 SkyRL/miles 能力写成自己的原创。

## 11. 快速定位、关联阅读与本轮纠正

| 要查的问题 | 本笔记 | 一手位置 |
| --- | --- | --- |
| 1.55× 是哪个阶段？ | §3 | PDF Fig.1(b), p.1；§3.2, p.6 |
| train batch、LOO、horizon mask | §5 | §4.2, p.9 |
| AST 与 hints 实际改了什么？ | §4、§6.1 | §4.2, pp.8–9；§4.3, pp.9–11 |
| 统一评测与 reported 分数 | §6 | Table 2–3, p.10 |
| HLE judge 差异与 summarizer 成本 | §7.1 | §5.1, pp.11–12 |
| 112K 是不是单次上下文？79.69 属于谁？ | §7.2 | §5.2, Fig.6, p.12 |
| GUI 是否泛化成功？ | §7.3 | §5.3, pp.12–13 |
| 当前示例真的走 TITO 吗？队列真的有界吗？ | §8 | 固定 C1–C8 路径／符号 |

关联既有笔记：[miles 接入专题](N11_miles_agentic_rollout.md)、[R2E-Gym](O03_r2e_gym.md)、[SWE-smith](E5_swe_smith.md)、[Forge](N10_minimax_forge.md)。这里只建立问题索引，不以其他报告的默认配方补本篇缺项。

对 [旧 horizon 专题](../sa_swe_horizon_masking_analysis.md) 的维护说明：保留其“组统计、梯度与分母必须区分”的主结论；将“没有 importance sampling 修正”收紧为“未披露跨版本 stale 修正”，因为 on-policy 不能推出 PPO 比率不存在；当前代码核查直接追到 `skyrl-agent` 的示例入口、OH runner 与 trainer，不再只由同仓库其他示例代证。旧文档不在本轮改写，其历史 FA/slime 映射不代表当前 miles 候选链。

## 12. 作者自查与交付状态

**完成项**：v1 全部正文与尾部范围、3 张表、7 幅编号图及 3 个 Listing；关键数字、曲线标签和负结果回到 PDF 核对；定点核查固定官方代码；复算表中成本比和百分点差；将论文／当前代码／读者推论／项目建议分层成文。

**未完成项**：没有运行 GPU、沙箱或论文训练；没有下载和验证模型权重；没有取得原始 TeX；没有独立 reviewer。当前工具没有创建独立子 agent 的能力，**本稿是作者自查完成、待独立复查，不使用前两批的“独立审查通过”标签**。

详细范围、实际修正和建议后续抽查项见 [O01 作者自查记录](reviews/15_O01_self_check_20260907.md)。本稿是来源 O01 的正式维护入口；阅读不批准新算法、taskset 或项目范围。

## 官方来源链接

[P-abs]: https://arxiv.org/abs/2511.16108
[P]: https://arxiv.org/pdf/2511.16108v1
[P-html]: https://arxiv.org/html/2511.16108v1
[P1]: https://arxiv.org/pdf/2511.16108v1#page=1
[P2]: https://arxiv.org/pdf/2511.16108v1#page=2
[P3]: https://arxiv.org/pdf/2511.16108v1#page=3
[P4]: https://arxiv.org/pdf/2511.16108v1#page=4
[P5]: https://arxiv.org/pdf/2511.16108v1#page=5
[P6]: https://arxiv.org/pdf/2511.16108v1#page=6
[P7]: https://arxiv.org/pdf/2511.16108v1#page=7
[P8]: https://arxiv.org/pdf/2511.16108v1#page=8
[P9]: https://arxiv.org/pdf/2511.16108v1#page=9
[P10]: https://arxiv.org/pdf/2511.16108v1#page=10
[P11]: https://arxiv.org/pdf/2511.16108v1#page=11
[P12]: https://arxiv.org/pdf/2511.16108v1#page=12
[P13]: https://arxiv.org/pdf/2511.16108v1#page=13
[M]: https://huggingface.co/NovaSky-AI/SA-SWE-32B
[C0]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/README.md
[C1]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/examples/run_skyrl/run_skyrl_swe.sh
[C2]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/examples/run_skyrl/skyrl_swe.yaml
[C3]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/skyrl_agent/integrations/skyrl_train/trainer.py
[C4]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/skyrl_agent/dispatcher/dispatchers.py
[C5]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/skyrl_agent/functional/utils.py
[C6]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/skyrl_agent/agents/base.py
[C7]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/skyrl_agent/agents/oh_codeact/codeact_agent.py
[C8]: https://github.com/NovaSky-AI/SkyRL/blob/0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518/skyrl-agent/skyrl_agent/agents/oh_codeact/codeact_runner.py
