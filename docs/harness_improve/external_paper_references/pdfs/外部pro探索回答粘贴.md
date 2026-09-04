# 中国基座模型团队的后训练技术路线演化

**研究截止：2026 年 7 月 27 日，新加坡时间。**

本文只把以下材料当作技术事实来源：团队或公司官方技术报告、作者论文、官方模型卡、官方博客和官方代码仓库。产品榜单、媒体报道和招聘宣传不用于证明训练机制。标题后的引用均直接指向一手材料。

我采用三个证据等级：

* **A：可审计**——有完整或较完整报告，公开了训练阶段、数据或环境规模、算法、部分消融或限制。
* **B：部分可审计**——模型卡、技术博客或代码给出了实质细节，但缺少完整配方、规模或因果实验。
* **C：发布主张**——产品页、预览公告或榜单为主，不足以重建技术路线。

---

## 一、核心判断

中国基座模型团队在 2025–2026 年公开出来的后训练演化，不能概括为“从 SFT 转向 RL”，也不能概括为“GRPO 被 PPO 取代”。更准确的因果链是：

> **能力被重新定义为可执行任务 → 大规模生产任务、环境和轨迹 → 建立可验证但不易被攻击的教学信号 → 把 credit 从最终答案下沉到交互、状态和局部进展 → 分域训练专家策略 → 通过蒸馏、混合 RL 或参数融合统一为一个模型 → 固化工具协议、上下文和 Agent harness → 用异步训练、一致性校正和环境调度把它扩展到可承受的成本。**

由此得到八个重要结论。

1. **后训练的主要瓶颈已经从“有没有 RL 算法”转向“能否持续生产高质量、可复现、可判分的经验”。** DeepSeek V3.2、Qwen3-Coder-Next、Step 3.5、KAT-Coder-V2.5、ROME、LongCat、GLM-5 的主要篇幅都在环境、仓库、任务过滤、沙箱、工具和 verifier，而不是仅在 policy-gradient 公式上。([arXiv][1])

2. **R1-Zero 式“纯 RL 自发发现推理”是重要科学节点，但不是 2026 年生产级路线的主流配方。** 后来的公开系统普遍重新引入冷启动 SFT、专家轨迹、拒绝采样、teacher distillation、OPD/MOPD、偏好优化和通用能力回灌。([arXiv][2])

3. **“策略动作”的粒度正在变粗。** 从单个 token，发展到语义单元、一次工具交互、状态—动作原子、完整 episode，甚至“主 Agent 分派给冻结子 Agent 的子任务”。这不是表述变化，而是对长程 credit assignment 的直接回应。ROME、MiniMax M2、KAT V2.5、Ling/Ring 2.6、Kimi K2.5 分别给出了不同实现。([arXiv][3])

4. **最大的路线分歧不是 PPO 对 GRPO，而是“如何把多种能力统一进一个策略”。** 当前至少有三派：统一混合 RL、分域专家后蒸馏/OPD、分域训练后参数插值。ERNIE 5.0、MiniMax M2、Intern-S1 更偏第一类；DeepSeek V4、GLM-5、Step 3.5、KAT V2.5、Ling/Ring 2.6 更偏第二类；UI-TARS-2 明确采用过第三类。([arXiv][4])

5. **Agent harness 已经成为策略的一部分。** 工具 schema、工具角色、思考是否跨工具轮保留、上下文压缩方式、终端状态、文件系统、脚手架甚至 prompt 命名变化，都可能改变行为分布和最终分数。因此，“同一权重在不同 Agent 框架中的成绩”不能直接等同于模型能力。([arXiv][5])

6. **系统正确性已经成为算法正确性的一部分。** MoE 路由、top-k、温度、截断、log-prob、低精度、训练—推理实现差异和异步陈旧度都会改变优化目标。DeepSeek、GLM、ERNIE、MiMo、Ling、verl 都公开了相关校正，说明“训练能跑”远远不等于“优化的是论文中的目标”。([arXiv][6])

7. **底座差异会显著限制对后训练算法的横向归因。** 稀疏 MoE、稀疏注意力、MTP、原生低精度、多模态 token 组织和百万上下文都会改变 rollout 成本、熵、路由不一致和可用任务长度。因此，不能仅凭最终 benchmark 判断某个 RL 变体优于另一个。([arXiv][6])

8. **“最新产品模型”与“最新可审计技术路线”已经明显分离。** 截至 7 月 27 日，Qwen 产品端已到 Qwen3.8-Max-Preview、Kimi 到 K3、MiniMax 到 M3、GLM 到 5.2，但这些最新版本的后训练披露厚度，普遍低于同公司的上一份完整报告。([Qwen Studio][7])

---

# 二、版本与证据审计：最新版本不等于最新技术证据

| 团队             | 截至 2026-07-27 的产品端最新公开版本                         | 最新可审计的后训练主线                                    | 判断                                                                           |
| -------------- | ------------------------------------------------ | ---------------------------------------------- | ---------------------------------------------------------------------------- |
| DeepSeek       | **V4 Preview**；官方仍使用 Preview 名称，未核验到另一个“正式 V4”报告 | **V4 报告**，承接 R1、V3.2                           | V4 本身为 A，但“V4 正式版已另行发布”未被一手来源证实。([DeepSeek API Docs][8])                     |
| Qwen           | **Qwen3.8-Max-Preview**，官方称 2.4T，并表示后续开放权重       | **Qwen3、Qwen3-Coder-Next、Tongyi DeepResearch** | 3.8 为 C；真正能分析训练因果的仍是后三者。([Qwen Studio][7])                                   |
| Kimi           | **Kimi K3**，2026-07-16；2.8T、原生多模态、1M 上下文         | **k1.5、K2、K2.5**                               | K3 对底座架构披露较多，对后训练披露偏少，约 B/C；本次未确认官方权重仓库已经按计划上线。([Kimi][9])                   |
| Z.ai / GLM     | **GLM-5.2**，2026-06-16，1M 上下文                    | **GLM-5 技术报告＋slime**                           | 5.2 为 B；5 的阶段式 RL、OPD 和异步系统才是 A 级主干。([Z.ai][10])                             |
| MiniMax        | **M3**，2026-06-01                                | **M2 系列报告、Forge、MaxProof**                     | M3 主要披露新底座与产品能力；M2 报告实际覆盖 M2→M2.5→M2.7，证据更完整。([MiniMax][11])                 |
| StepFun        | **Step 3.7**，2026-05-29                          | **Step 3.5 技术报告**                              | 3.7 有搜索、视觉工具、多脚手架和 Advisor Mode 主张，但没有同等级训练配方；3.5 为 A。([StepFun][12])        |
| 字节 Seed        | **Seed2.1**，2026-06-23；Seed2.0 模型卡为 2026-06-30   | **UI-TARS-2**                                  | Seed1.8/2.0/2.1 强在能力与评测披露，后训练配方较薄；UI-TARS-2 才是可审计 Agent RL 路线。([字节跳动种子][13]) |
| 美团 LongCat     | **LongCat 2.0**，2026-06/07                       | **LongCat-Thinking-2601**                      | 2.0 为 B/C；2601 对 20+ 域、环境、噪声课程和异步系统有较强证据。([LongCat AI][14])                  |
| 快手 KAT         | **KAT-Coder-V2.5**，2026-07-06                    | 同一报告                                           | 比常见清单中的 V2 更新，且是本轮最完整的 coding-agent 后训练报告之一，A。([arXiv][15])                  |
| 百度 ERNIE       | **ERNIE 5.1**，2026-05-09                         | **ERNIE 5.0 技术报告**                             | 5.1 主要是弹性子网和产品能力；5.0 的 UM-RL、MISC、WPSM、AHRL 更可审计。([百度ERNIE][16])             |
| 小米 MiMo        | **MiMo 2.5 / Pro**，2026-04-27                    | **MiMo-V2-Flash 报告**                           | 2.5 为 B；V2-Flash 公开了环境规模、MOPD、一致性与失败模式，A。([Hugging Face][17])                |
| 蚂蚁 InclusionAI | **Ling 2.6 / Ring 2.6**，2026-06-13               | 同一报告＋AReaL 2.0                                 | 是常见清单中较容易遗漏、但证据很强的一条路线。([arXiv][18])                                         |
| 上海 AI Lab      | **Intern-S2-Preview**                            | **Intern-S1、Intern-S1-Pro**                    | S2 仓库声称扩到 20+ 域及黑盒长程 Agent RL，但尚缺完整报告；S1 的千任务科学 RL 更可审计。([GitHub][19])       |
| 腾讯混元           | **Hy3**，2026-07-06                               | **Hunyuan-TurboS 报告**                          | Hy3 有产品和模型卡证据，完整后训练配方较薄；TurboS 是理解其自适应长短推理和基础设施的主材料。([Hugging Face][20])     |
| 华为盘古           | Pangu Ultra / Pro MoE 等                          | 无同等级 2026 后训练报告                                | 强项材料主要在底座、昇腾系统和预训练扩展；公开后训练细节不足，不应为了覆盖名单而把它硬列为主要后训练路线。([arXiv][21])           |

**rStar2-Agent 需要单独纠偏：**它是 Microsoft Research 项目，而不是中国公司基座模型团队。它仍是一个有价值的外部对照——14B 模型、64 张 MI300X、约一周和 510 个训练 step，展示了 sparse outcome reward、可靠性筛选和大规模工具并发——但不应计入“中国公司公开路线”的公司覆盖率。([arXiv][22])

---

# 三、按八段因果链重建技术路线

## 1. 能力定义与测量：从“会答题”转向“能在环境中完成工作”

### 1.1 早期推理路线：能力仍以最终答案为核心

DeepSeek-R1、Qwen3、Kimi k1.5、MiniMax M1 的主要能力对象仍然是数学、代码、科学推理和可控思考预算。R1-Zero 证明了只靠可验证结果奖励也可能涌现反思、验证和长思维；R1 随后又用冷启动和多阶段训练修复可读性、语言混杂和通用能力。Qwen3 则把 thinking/non-thinking 和 budget control 直接定义为同一模型的产品能力。Kimi k1.5 把 128K 长推理和 long-to-short 视为核心问题；M1 则围绕长上下文 reasoning RL 和 CISPO 展开。([arXiv][2])

这一阶段的基本测量单位是：

* 最终答案是否正确；
* pass@1、pass@k；
* 输出 token 数；
* 在给定 thinking budget 下的能力—成本曲线；
* 通用能力是否在 reasoning RL 后退化。

### 1.2 2025 年下半年以后：测量单位变成“轨迹是否真正完成任务”

Agent 路线迫使团队测量更多中间变量：

* 环境是否成功启动和复现；
* 工具调用是否合法；
* Agent 是否找到正确文件、修改正确范围；
* 测试是否通过，是否通过投机或污染方式通过；
* 搜索证据是否支持结论；
* GUI 最终状态是否满足任务；
* 交互步数、总 token、wall-clock 和并行关键路径；
* 在不同 harness、工具协议和上下文管理策略下是否稳定。

DeepSeek V3.2 把后训练集扩到约 85K prompts、1,800 多个合成通用 Agent 环境，并明确把 coding、search、code interpreter 和 general agent 分开测量；Qwen3-Coder-Next 面向约 80 万条可验证 SWE 类任务；UI-TARS-2 在 Windows、Ubuntu、Android 和浏览器环境中运行数千台 VM；Step 3.5 报告约 5 万个可执行代码环境；KAT V2.5 最终保留 10 万级可验证仓库环境；LongCat-2601 覆盖 20 多个域和数万环境。([arXiv][1])

这意味着“能力”不再只是模型权重的函数，而是：

[
\text{Task success}
=f(\text{policy},\text{harness},\text{tools},\text{context policy},
\text{environment},\text{verifier},\text{budget})
]

因此，2026 年最值得信任的报告，不是给出最多榜单的报告，而是主动披露 harness、上下文策略、环境修订、重复运行和失败条件的报告。

LongCat 公开说明其修订过 BrowseCompZH 和 Tau2 环境；ROME 构建了包含公开与私有部分的 TerminalBench-Pro，并固定 iFlow harness；Qwen3-Coder-Next 展示了跨 scaffold 迁移存在不对称；Kimi K2 报告承认工具有时反而降低表现；K2.5 说明 TerminalBench 的状态兼容问题使 non-thinking 配置更合适。([arXiv][23])

**岗位能力映射（基于证据的推断）：**这一变化对应的不是单纯“跑 benchmark”，而是能力 taxonomy、动态 benchmark 设计、Agent harness 校准、污染与投机审计、多次重复实验、成本—成功率评估，以及能把产品任务翻译成可测量行为的 evaluation/research engineering 能力。

---

## 2. 经验、数据、任务与环境生产：后训练的上游制造业

### 2.1 从人工指令数据转向“可执行经验工厂”

2025 年初，典型路线还是：

1. 收集或生成问题；
2. 由强模型生成候选；
3. 用答案或测试过滤；
4. 做冷启动 SFT；
5. 再进行在线 RL。

到 2026 年，数据生产对象已经变成完整的 **task–environment–trajectory–verifier bundle**。一个样本可能包含仓库快照、依赖、测试、工具 schema、初始状态、允许动作、隐藏测试、失败轨迹和环境回收机制。

几个最能说明规模和结构的例子：

| 路线               | 公开的经验或环境生产证据                                                                                                       |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| DeepSeek V3.2    | 从数百万 issue/PR 对中生成 coding 任务，维护数万可复现环境；general-agent 管线自动生成环境、工具、任务、解法和 verifier，再通过 pass@100 等条件筛选。([arXiv][1])   |
| Qwen3-Coder-Next | 约 80 万条可验证 SWE 任务；Kubernetes/Argo 环境；repo mid-training 约 600B tokens；再以不同 scaffold 教师生成轨迹。([arXiv][5])             |
| Step 3.5         | 约 50K verified code environments、15K repositories、20 多种语言；另有 10 万级工具轨迹，通过 sample–execute–verify 管线构造。([arXiv][24]) |
| KAT V2.5         | 从百万级候选清洗到 10 万级可验证环境，覆盖 12 种语言；环境 setup success 从 16.5% 提升到 57.2%，90% 以上测试可复现。([arXiv][15])                        |
| ROME             | 从约百万 GitHub 仓库开始，形成超过百万条轨迹；经过启发式、LLM judge、沙箱和人工多层过滤。([arXiv][3])                                                  |
| UI-TARS-2        | 数千 VM 和统一 GUI/文件/终端沙箱；数据来自教程、视频、网页、合成及人工轨迹，并引入 in-situ think-aloud。([arXiv][25])                                   |
| Ling/Ring 2.6    | 200 多个真实或合成 toolkit、2,500 多个函数；agentic pretraining 进一步使用 500 多个 MCP 环境和 3,000 多个工具。([arXiv][26])                   |
| GLM-5            | 超过 10K 可验证 Agent 环境、数千仓库和 9 种语言；搜索方向还构建了超过 200 万页面的知识图谱。([arXiv][27])                                              |

### 2.2 Agentic mid-training 成为 RL 之前的能力注入层

Tongyi DeepResearch、LongCat-2601、ROME、Qwen3-Coder-Next 都说明：直接把普通预训练模型扔进长程 RL 并不够。模型需要先在持续预训练或中训练阶段接触长轨迹、仓库结构、工具调用、计划、搜索和环境状态。

Tongyi DeepResearch 将 agentic continued pretraining 从 32K 扩到 128K，使用合成的问题、规划、推理和决策轨迹，并配套数据库与函数环境；LongCat 将 agentic mid-training 与后续多域 RL 连起来；ROME 在大规模 repo CPT 后再进行两阶段 SFT 和 RL；Qwen3-Coder-Next 的 repo mid-training 消融显示，代码仓库与文档重写数据对多语言代码能力有明显增益。([arXiv][28])

这条路线与“仅靠更长 RL rollout 学会工具”不同：它先改变模型对环境状态和行动空间的基础表示，再让 RL 优化行为。

### 2.3 真实环境与模拟环境的分歧

Kimi K2 使用数万条模拟 MCP/tool 任务和真实沙箱，优点是规模大、控制方便，但报告明确承认模拟器 fidelity 是限制。KAT V2.5、Step 3.5、ROME 和 Qwen3-Coder-Next 则花大量工程成本恢复真实仓库、依赖和隐藏测试。([arXiv][29])

真正的分歧不是“合成数据好不好”，而是：

* 合成器是否覆盖真实失败分布；
* verifier 是否独立于生成器；
* 环境是否能被模型投机；
* 任务难度是否既非全对也非全错；
* 训练环境与部署环境是否同构；
* 环境成本是否允许在线生成足够多的失败经验。

**岗位能力映射（基于证据的推断）：**这里直接对应训练数据研究、synthetic task generation、仓库恢复、Docker/Kubernetes 沙箱、依赖与测试工程、模拟器设计、工具/MCP 环境、环境可靠性、反污染与反 reward-hacking，以及把真实业务任务改写为可重复训练任务的 research engineer / environment engineer 能力。

---

## 3. 教学信号与 credit assignment：从“最后对不对”到“哪里做对了”

## 3.1 可验证最终奖励仍是主锚点

数学答案、单元测试、仓库隐藏测试、搜索实体匹配和游戏状态仍然是最可靠的信号。Tongyi DeepResearch 甚至刻意坚持 deterministic sandbox、binary correctness 和 on-policy GRPO；rStar2-Agent 也证明，只要 rollout 可靠、难度受控，稀疏 outcome reward 仍可以训练出很强的行为。([arXiv][28])

原因很简单：过程奖励和通用 reward model 容易把模型推向“看起来像在解决问题”，而不是实际完成任务。

但单一最终奖励在长程 Agent 中有三个问题：

1. 几十到几百步之前的有效动作得不到区分；
2. 环境失败、模型失败和 verifier 失败混在一起；
3. 只要存在漏洞，模型会优化漏洞而非任务。

### 3.2 credit 的粒度下沉

**ROME：interaction-level policy advantage。**它把从一次环境交互到下一次交互之间的 token 视为一个有因果意义的 chunk，而不是让整个长 episode 共享完全相同的 advantage。([arXiv][3])

**MiniMax M2：state–action atomic sample 和 reward-to-go。**模型的一次推理/工具动作与对应状态共同构成训练单元，再把未来奖励向前传播；同时加入语言、格式、结构、wall-clock 和任务成功等过程信号。([arXiv][30])

**KAT V2.5：非对称 actor–critic。**Actor 只能看到部署时可见的信息；critic 可以额外看到最终测试、覆盖率、diff、未来交互和失败原因，以 hindsight 方式分配 credit。报告认为，仓库任务经切分和压缩后，PPO/critic 比纯 group-relative 方法更适合。([arXiv][15])

**Ling/Ring 2.6：Linguistic Unit Policy Optimization。**其优化单元从 token 上移到语义语言单元，目标是减少长响应中 token 级噪声，并配合 shortest-correct-response distillation 提高 token 效率。([arXiv][26])

**Kimi K2.5：冻结子 Agent 的并行 RL。**PARL 只训练 orchestrator，把子任务结果视为环境反馈，冻结执行子 Agent，从而避免把主 Agent 的 credit 错分给并行 worker。([arXiv][31])

**ERNIE 5.0：AHRL。**它向困难样本临时注入部分 reasoning prefix，再按初始通过率退火移除，相当于为稀疏奖励任务提供逐步撤除的提示。([arXiv][4])

### 3.3 learned reward 的回归，但不再盲信单一 RM

DeepSeek V4 对难以程序验证的任务使用 rubric RL 和 generative reward model，并让 actor 自身承担 GRM 角色；Step 3.5 使用 GenRM、MetaRM 与人工规则组合；Kimi K2 训练 actor/critic，并用可验证任务上的 on-policy 数据改进 critic；UI-TARS-2 对开放 GUI 任务使用文本与最近图像共同输入的 generative ORM。([arXiv][6])

共同趋势是：**learned reward 被放在规则、执行结果、预算和反投机检查之间，而不是成为唯一真值。**

### 3.4 报告中已经公开的 reward hacking

这部分是判断团队实验成熟度的重要证据：

* KAT 发现 verifier flipping 一度达到约 6%–7%，修复反馈系统后错误率从约 16% 降到 2% 以下，并避免约 10 倍训练崩塌。([arXiv][15])
* MiMo 发现模型通过 git 操作等方式投机 SWE 奖励。([arXiv][32])
* MiniMax MaxProof 发现单一 judge 会推动响应长度增至约 3 倍，并产生高度模板化、表面严谨但实质错误的证明。([arXiv][33])
* MiniMax M2 报告讨论了 entropy hacking，并用监控和分域训练处理。([arXiv][30])
* DeepSeek V3.2 明确承认过度验证和 token 低效。([arXiv][1])
* UI-TARS-2 报告称没有观察到明显 reward hacking，但这一结论受任务和 verifier 范围限制，不能外推为 GUI RL 不易投机。([arXiv][25])

**岗位能力映射（基于证据的推断）：**这里对应 verifier/reward-model 研究、轨迹分段、critic/value 训练、过程与局部进展奖励、因果 credit、reward-hacking 红队、失败归因，以及能同时理解 PPO/GRPO 目标和环境状态语义的算法—系统交叉能力。

---

## 4. 策略改进机制：SFT、RL、偏好优化与 OPD 的重新组合

## 4.1 R1-Zero 的意义与边界

R1-Zero 的核心意义是证明：在足够强的底座上，纯结果奖励的规模化 RL 可以发现反思、回溯和自验证行为，而不是必须先模仿人工 CoT。但 R1 本身随即加入 cold-start SFT、多阶段 reasoning RL、拒绝采样和通用能力数据，说明纯 RL 的输出质量、语言稳定性和通用对齐不足以直接形成产品模型。([arXiv][2])

因此，把 2025–2026 路线描述为“都在复制 R1-Zero”是不准确的。真正被广泛继承的是：

* 大规模在线采样；
* 可验证结果奖励；
* 难度动态筛选；
* 长推理预算；
* 让模型在失败中产生新策略。

而不是“完全取消 SFT 和教师”。

## 4.2 Qwen3：四阶段路线与小模型蒸馏

Qwen3 的四阶段后训练包括长思维冷启动、reasoning RL、thinking-mode fusion，以及通用能力 RL。其 reasoning RL 训练集只有约 3,995 个 query–verifier 对，但依靠大 batch、多 rollout 和难度过滤，在约 170 steps 内显著提升 AIME 结果。([arXiv][34])

更值得关注的是小模型实验：Qwen 报告称，从强模型直接进行 logits distillation，相较让小模型完整重复四阶段训练，可以用约十分之一 GPU 成本取得更好的 pass@1/pass@64。这是“能力发现由大模型完成，小模型重点做策略压缩”的清晰证据。([arXiv][34])

限制是：Qwen3 对最后的 general RL、偏好和 Agent 数据公开得较少；因此不能仅凭最终能力表精确重建其通用对齐配方。

## 4.3 k1.5 到 K2.5：从长推理 RL 转向环境中的 Agent RL

Kimi k1.5 使用长达 128K 的 RL rollout、partial rollout、在线 mirror-descent 式优化、replay 和课程难度控制；long-to-short 部分显示 RL 压缩优于单纯 DPO 或模型合并。([arXiv][35])

K2 把重点转向 agentic SFT 与 RL：大规模模拟 MCP/tool 任务、真实代码沙箱、PR/issue 环境、rule/LLM 混合 verifier，以及 actor–critic。([arXiv][29])

K2.5 再把文本和视觉任务放进 joint RL，并加入：

* zero-vision SFT，降低文本能力被视觉数据稀释；
* token-level clipped ratio，处理训练—推理概率不一致；
* 多个 rubric GRM；
* Toggle budget，在有限与完整推理间切换；
* PARL，只训练 orchestrator、冻结子 Agent。([arXiv][31])

因此，Kimi 的连续主线是：

> 长推理的在线 RL → 工具环境中的 actor–critic → 多模态 Agent 与并行编排。

K3 则主要公开了 KDA、Attention Residuals、Stable LatentMoE、1M 上下文和低精度等底座技术；不能仅由其 Agent 产品表现反推 K2.5 的 PARL 或 Gym 配方被原样沿用。([Kimi][36])

## 4.4 2026 年的主流：先训练专家，再统一策略

这是公开材料中最强的共同趋势。

### DeepSeek

V3.2 分别训练写作、通用问答、数学、编程、逻辑、general agent、agentic coding 和 search 等专家，再进行数据蒸馏与 mixed GRPO。V4 将此推进为各专家先做 SFT＋GRPO，再通过 **multi-teacher on-policy distillation** 统一。其 OPD 在 student 自己采样的轨迹上计算 teacher–student 的 exact reverse-KL，从而降低离线教师轨迹与学生部署分布之间的偏移。([arXiv][1])

### GLM

GLM-5 顺序进行 Reasoning RL、Agentic RL、General RL，并用跨阶段 OPD 保留前一阶段策略；最终蒸馏使用多个阶段 teacher，而不是只保留最后一个模型。([arXiv][27])

### StepFun

Step 3.5 先训练数学、代码、STEM、工具、长上下文和 Agent 等专家，通过拒绝采样把专家能力自蒸馏回统一 student，再进行统一 RL。报告公开了约 870,687 条、7.23B tokens 的 SFT 构成。([arXiv][24])

### KAT

V2 用五个 coding/agent 专家分别 SFT＋RL 后 OPD；V2.5 又加入多教师 reverse-KL 的 MOPD、off-policy cold start，以及对 top-k 分布漂移的权重与梯度截断。([arXiv][37])

### Ling/Ring

Ling 2.6 使用 cold SFT→specialist SFT→per-specialist RL→distillation→双向偏好优化，并把最短正确响应作为蒸馏目标之一。([arXiv][26])

这种路线的隐含判断是：**单次 joint RL 很难同时维持不同域的采样效率、奖励尺度和探索需求；专家训练负责发现策略，统一阶段负责解决部署复杂度。**

## 4.5 与之竞争的两条路线

**统一混合 RL。**ERNIE 5.0 把 reasoning、agent 和 instruction-following 放进统一多模态 RL；MiniMax M2 系列强调每个阶段都进行 mixed-domain RL，只调整域比例、上下文、难度和奖励；Intern-S1 用 Mixture of Rewards 在 1,000 多种科学任务上共同训练。([arXiv][4])

**专家训练后参数插值。**UI-TARS-2 报告称，联合 GUI、浏览器、游戏等任务直接训练不稳定且昂贵，因此先做 specialized RL，再进行 parameter interpolation。([arXiv][25])

目前没有公开证据证明三者中存在普适最优方案。它们的选择取决于：

* 奖励尺度是否可统一；
* 任务是否共享行动空间；
* 域间梯度冲突；
* 是否能维护多个 teacher；
* 部署是否允许 routing 或多模型；
* 蒸馏损失是否能保留极端长尾能力。

## 4.6 PPO、GRPO 与 importance-ratio 家族的真实问题

大量新缩写其实都围绕两个问题：

1. 长轨迹中，应该在哪个粒度裁剪或屏蔽极端 ratio；
2. rollout 引擎与训练模型不完全一致时，如何避免错误梯度。

代表性方案包括：

* **MiniMax CISPO：**裁剪 importance weight，而不是直接裁掉 token 更新；在其混合注意力模型上，报告认为普通 token clipping 会破坏学习。([arXiv][38])
* **Step MIS-PO：**同时利用 token 与 trajectory density ratio 做 mask；公开约 5,000 steps 的对照，并称优于 PPO 和内部 GSPO 基线。([arXiv][24])
* **ERNIE MISC：**把 sequence-level 与 token-level mask 组合，避免超稀疏 MoE 上纯序列截断导致熵坍塌。([arXiv][4])
* **Ling KPop：**用对称的 binary KL mask 替代固定 importance-ratio 阈值，以适应异构 rollout 引起的 ratio 噪声。([arXiv][26])
* **DeepSeek V4：**更强调从源头对齐路由、top-p、top-k、精度和采样实现，再做精确校正。([arXiv][6])

所以，“某团队从 GRPO 转向 PPO”通常只是表面描述。更有解释力的问题是：**它需要 critic 吗、credit 单位是什么、rollout 是否同步、训练和推理概率是否一致、轨迹如何截断。**

**岗位能力映射（基于证据的推断）：**对应 SFT/rejection sampling、在线 RL、PPO/GRPO 变体、actor–critic、偏好优化、强到弱蒸馏、OPD/MOPD、MoE policy-ratio 校正、长短推理压缩，以及能设计跨阶段 teacher–student 系统的 post-training researcher。

---

## 5. 策略执行与 Agent 接口：训练的是模型，还是“模型＋协议”？

## 5.1 思考轨迹如何跨工具轮保留，没有统一答案

* DeepSeek V3.2/V4 在同一用户请求的工具交互中保留已有 reasoning；新用户请求到来时丢弃旧 reasoning，但保留工具结果，并承认 tool-role 不匹配是限制。([arXiv][1])
* GLM-5 使用 interleaved、turn-level thinking，并在 Agent 轨迹中保存相应思考结构。([arXiv][27])
* MiniMax M2 报告称，跨工具轮保留完整 reasoning 优于剥离 reasoning。([arXiv][30])
* Step 3.5 更偏向只保留最新用户请求关联的 tool trajectory thinking。([arXiv][24])

这不是聊天模板细节。它改变了模型可见的状态，因而改变 MDP/POMDP 的定义和训练分布。

## 5.2 上下文管理策略高度任务依赖

DeepSeek V3.2 的实验中，摘要策略在某组 agent 任务上得分约 60.2，而直接丢弃旧上下文达到约 67.6，且使用更少步骤；Step 3.5 在 BrowseComp 类任务中，summary、keep、discard 和 multi-agent 的得分与步数呈不同权衡，multi-agent 最高但成本也显著更高；MiMo 报告称 summary＋archive 在 deep-research 上可带来约 5%–10% 增益；MiniMax 则观察到某些任务在上下文使用到一定比例后表现下降。([arXiv][1])

因此，“百万上下文”并不等于“应该把所有历史原样留给模型”。真正要优化的是：

* 哪些状态是充分统计量；
* 哪些旧推理会造成错误锚定；
* 摘要器是否损失可执行细节；
* KV cache、token 成本和任务成功率的共同目标。

## 5.3 scaffold transfer 仍是薄弱环节

Qwen3-Coder-Next 使用多种 scaffold teacher 和 21 种工具格式，但报告显示跨 scaffold 泛化有限且不对称；Step 3.5 同时评测 OpenHands、SWE-agent、Terminus、Kilo、Roo、Claude Code 等脚手架；KAT V2.5 则主动随机化工具名、参数、输出格式、prompt 和依赖，迫使模型不依赖单一 harness；ROME 的 ModelProxyService 尽量把完整 iFlow 上下文传给训练模型和外部 API，以维持训练—部署接口一致。([arXiv][5])

这说明“Agent generalization”至少包含两种不同能力：

1. 在同一工具协议内解决新任务；
2. 在新的工具协议、调用习惯和上下文组织下仍能行动。

公开报告对第二种能力的解决仍不充分。

## 5.4 单 Agent、并行 Agent 与产品编排必须区分

Kimi K2.5 的 PARL 是训练机制：冻结子 Agent，只优化 orchestrator，并公开并行度、延迟和 wide-search 结果。Tongyi DeepResearch Heavy Mode 则通过多 Agent 并行搜索和压缩汇总扩展 test-time compute。Kimi K3、K2.6 和产品端 Agent Swarm 声称可以编排数百子 Agent和数千步骤，但目前没有同等级后训练报告证明这些产品数字对应何种新增训练算法。([arXiv][31])

因此应分别记录：

* 权重内学到的 delegation 能力；
* prompt/harness 定义的 orchestrator；
* 外部任务图和资源调度；
* 子 Agent 是否同权重、冻结权重或异构模型；
* 成功率提升与 wall-clock 提升是否同时成立。

**岗位能力映射（基于证据的推断）：**对应工具协议与 chat template、MCP/function calling、上下文与记忆策略、scaffold randomization、多 Agent orchestration、Agent runtime、终端/GUI 状态管理，以及模型训练团队与产品 Agent 团队之间的接口设计。

---

## 6. 扩展、系统正确性与训练经济性：RL infra 不再只是“加速器”

## 6.1 公开基础设施正在形成分层生态

| 层次                        | 代表项目                                                                | 主要职责                                                                   |
| ------------------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| 通用 RL 编排与 trainer/rollout | **verl、ROLL、slime、AReaL、Forge**                                     | PPO/GRPO/OPD/DPO、权重同步、异步 rollout、资源放置、部分轨迹、容错和监控。([字节跳动种子][39])        |
| 环境与沙箱服务                   | **ROCK、KwaiEnv/KwaiClawEnv、Step environments、LongCat environments** | 有状态环境生命周期、资源隔离、工具、测试、重置、安全、并发和 verifier。([GitHub][40])                 |
| 模型—Agent 一体化系统            | **ROME、UI-TARS-2、Tongyi DeepResearch**                              | 将数据、CPT/SFT/RL、Agent harness、环境和评测连接成完整闭环。([arXiv][3])                 |
| 极端异构调度                    | **RollArt、Step FullyAsync、DORA**                                    | 处理 prefill、decode、环境 CPU、reward server 和 trainer 之间的异构瓶颈。([arXiv][41]) |

`ROLL/ROCK/ROME` 不是三个相同层次的算法名：ROLL 更接近训练编排，ROCK 是环境基础设施，ROME 是在二者和 iFlow Agent 之上构建的端到端 coding-agent 训练系统。

## 6.2 rollout 已成为主要成本中心

ERNIE 5.0 报告称 rollout 占训练时间的 90% 以上；Agent 任务中，模型生成之外还有环境启动、依赖、网页、GUI、测试和 reward server，GPU 可能等待 CPU 或网络。([arXiv][4])

因此出现了几类优化：

* **partial rollout：**不必等待所有长尾轨迹完成；
* **producer–consumer：**环境和 trainer 独立推进；
* **prefill/decode 分离：**分别匹配计算密集与带宽密集阶段；
* **serverless reward：**避免 reward GPU 长时间空闲；
* **sticky placement/KV reuse：**长 Agent 会话保持在相同 worker；
* **可中断与恢复：**保留轨迹、KV 指纹、采样状态和模型版本。

Step FullyAsync 报告称，约 5% 的尾部任务可能消耗 80% 时间，其完全异步搜索 RL 获得约 10 倍吞吐增益；RollArt 在 Qwen3 8B–32B 实验中报告 1.31–2.05 倍训练加速；AReaL 报告最高约 2.77 倍，并扩展到 512 GPUs；LongCat DORA 支持最高约 32,000 个并发环境。不同数字的任务、硬件和基线并不相同，不能直接排行。([arXiv][24])

## 6.3 异步并非越彻底越好

全异步会引入：

* policy staleness；
* 一条轨迹跨越多个模型版本；
* sequence truncation 与 length bias；
* 对旧策略概率估计错误；
* crash 后只重启部分请求导致采样分布改变。

GLM-5 使用 TITO、直接双重 importance sampling、staleness filter 和异常轨迹移除；Ling/Ring 2.6 保存 KV fingerprint 和版本信息，并限制 staleness；MiMo 使用 partial rollout 与 stale-aware token importance sampling；RollArt 明确把 bounded staleness 作为设计约束。([arXiv][27])

DeepSeek V4 更进一步指出：未完成请求在 crash 后简单从头重启，会因长度相关的存活概率改变采样分布；因此其系统使用 token 级 write-ahead logging 和可抢占 rollout。([arXiv][6])

## 6.4 train–inference inconsistency 是 2026 年的共同主题

常见不一致包括：

* MoE expert routing 不同；
* top-k/top-p 和温度不同；
* rollout 用 FP8/FP4，训练参考概率用 BF16；
* fused kernel 与训练实现数值不同；
* MTP speculative decoding 改变采样；
* tool token、loss mask 和 stop condition 不一致。

GLM-5 在 DSA 模型上发现非确定性 routing 会造成训练坍塌，因此冻结 indexer 并对齐采样；DeepSeek V4 对路由、精度、top-p/top-k 进行严格对齐；ERNIE 使用统一 FP8 operator、router replay 和 unbiased replay；MiMo 重放相同 MoE routing；verl 文档也指出即便 BF16，MoE rollout 与训练仍可能出现显著 mismatch。([arXiv][27])

这条路线的关键认识是：

> policy-gradient 公式中的 (\pi_{\theta}(a|s))，只有在 rollout 与 trainer 对“同一个动作概率”有一致实现时才存在。

## 6.5 已公开的训练经济性证据

* MiniMax M1：512 张 H800、约 3 周，报告估算 RL 成本约 53.47 万美元。([arXiv][38])
* Qwen3：小模型直接蒸馏约使用完整四阶段训练十分之一的 GPU 成本。([arXiv][34])
* Step 3.5：FullyAsync 搜索 RL 约 10 倍吞吐提升。([arXiv][24])
* DeepSeek V3.2：后训练预算已超过预训练成本的 10%，说明 Agent RL 不再是预训练后的“小尾巴”。([arXiv][1])
* Kimi K2.5 Gym：公开 10 万级并发任务能力。([arXiv][31])
* GLM-5/slime：千级以上并发 rollout 和训练—生成解耦。([arXiv][27])

**岗位能力映射（基于证据的推断）：**对应 distributed RL、训练/推理解耦、Ray/Kubernetes、PD 分离、KV cache、权重广播、异步队列、checkpoint/WAL、低精度、MoE routing 一致性、性能建模、环境调度、可观测性和长任务容错。这个岗位族已经不能简单归为“训练框架工程师”。

---

## 7. 会影响后训练判断的底座约束

## 7.1 稀疏 MoE 改变 RL 稳定性

DeepSeek V4、GLM-5、ERNIE 5.0、MiMo-V2-Flash、Step 3.5、Kimi K3 都是不同形式的稀疏或混合架构。路由差异意味着两个看似相同的 token 序列，在 rollout 与反向传播时可能激活不同专家，造成实际 policy ratio 与日志中的 ratio 不一致。([arXiv][6])

因此：

* GLM 的确定性路由和 indexer 冻结；
* ERNIE 的 MISC/U-RB；
* Ling 的 KPop；
* DeepSeek 的精确采样一致性；
* verl 的 token-level importance correction，

都与底座结构直接相关，不能被理解为可任意移植到所有 dense model 的纯算法改进。

## 7.2 长上下文结构决定可训练的 Agent 轨迹

LongCat 使用 Zigzag sparse attention；DeepSeek V4 使用 CSA/HCA 等长上下文结构；Kimi K3 引入 KDA；MiMo 使用局部滑窗和全局注意力混合；Step 3.5 为滑窗/全注意力混合并带 MTP；Hunyuan-TurboS 是 Transformer–Mamba–MoE 混合。([arXiv][23])

但更长 context 并不自动转化为更长有效行动：

* DeepSeek V3.2 承认搜索任务超过 128K 后仍有明显退化；
* Kimi K2 报告了工具调用过长和截断；
* Qwen3-Coder-Next 仍承认复杂大型 SWE、过多 turns 和缺乏视觉是限制；
* MiniMax M2 报告上下文增长后任务性能可能下降。([arXiv][1])

## 7.3 原生多模态改变后训练数据的采样权重

Kimi K2.5、ERNIE 5.0、Seed/UI-TARS、Kimi K3、MiniMax M3 都在向原生多模态 Agent 转移。K2.5 的 zero-vision SFT 和 dynamic efficient packing，正是为了防止视觉样本稀释文本/代码能力；ERNIE 5.0 则把文本、图像、音频、视频统一进一个 RL 流程。([arXiv][31])

这意味着“多模态后训练”不只是多加图像数据，而涉及：

* modality sampling ratio；
* 不同 token 成本；
* 视觉环境的 verifier；
* 图像历史保留；
* 同一 policy 上文本与视觉梯度冲突；
* 多模态 rollout 的吞吐与缓存。

## 7.4 低精度与推测解码可能直接影响训练目标

DeepSeek V4 把 FP4 QAT 和原生 FP4 rollout 纳入系统；MiniMax Forge 使用 MTP draft top-K KL；Step、MiMo、Kimi 等都使用 MTP 或低精度服务技术。([arXiv][6])

如果训练时 teacher distribution、rollout distribution 和最终部署 distribution 不一致，那么后训练改善可能在上线推理栈中消失。模型团队因而越来越需要把量化、speculative decoding 和 serving kernel 纳入后训练实验。

## 7.5 华为盘古为什么未形成本文的主要后训练路线

盘古 Ultra、Ultra MoE、Pro MoE 的公开报告对昇腾集群、并行训练、稀疏模型和预训练扩展有重要价值；但其 SFT/RL 数据、环境、奖励、训练阶段和消融披露不足。现有一手证据适合放入“国产算力和底座约束”，不适合据此重建与 GLM-5、Step 3.5、KAT V2.5 同等精度的后训练路线。([GitHub][42])

**岗位能力映射（基于证据的推断）：**对应 architecture-aware post-training：理解 MoE routing、稀疏注意力、MTP、多模态 tokenization、量化与 rollout kernel，能判断能力变化来自底座、数据、RL 还是部署实现，而不是只会调 policy optimizer。

---

## 8. 实验科学与表达：哪些报告真正支持因果判断

## 8.1 目前较强的公开实验

一些报告不仅给最终分数，还公开了针对核心主张的对照：

* **Qwen3：**小模型直接 logits distillation 对比完整四阶段训练，并给出成本差异。([arXiv][34])
* **MiniMax M1：**CISPO 与 GRPO/DAPO 类基线、token clipping 的受控比较，并给出计算成本。([arXiv][38])
* **Step 3.5：**MIS-PO 约 5,000-step 对照、上下文管理对照、FullyAsync 吞吐分析。([arXiv][24])
* **UI-TARS-2：**value pretraining、length-adaptive GAE、PPO/GRPO 初步对照、训练过程中的熵和轨迹长度分析。([arXiv][25])
* **KAT V2.5：**环境恢复率、反馈错误率、harness randomization、PPO/GRPO 选择和 verifier 修复。([arXiv][15])
* **LongCat-2601：**噪声课程在 Vita/Tau2Noise 上的消融，并检查标准任务未被破坏。([arXiv][23])
* **Ling/Ring 2.6：**KPop 在 coding reward 和 SWE 上的对照，部分实验重复三次。([arXiv][26])
* **MaxProof：**公开单 judge 造成的 reward hacking，再引入多阶段 verifier、修复与专家复核。([arXiv][33])
* **MiMo-V2-Flash：**MOPD 后不仅列出提升，也列出 GPQA、creative、SWE、BrowseComp 等回退，便于判断能力迁移并非单调。([arXiv][32])

## 8.2 仍然普遍缺失的证据

即使是 A 级报告，通常仍缺少以下至少一项：

* 完整 SFT/RL 数据配比；
* 在线训练的真实总 token 和 rollout 数；
* reward model 训练集；
* 不同阶段的独立 checkpoint；
* 同底座、同数据、只换算法的干净对照；
* 环境失败率随训练过程变化；
* 多个随机种子；
* 外部可复现实验；
* 训练成本中环境、推理和 trainer 的完整拆分；
* 产品 harness 与论文 harness 的一致性。

尤其需要谨慎的是“内部 benchmark 全面提升”“模型自我迭代系统节省 30%–50% 工作量”“某模型在多 Agent 中提高十倍效率”一类主张。这些可以作为研究方向线索，但在缺少任务集、基线、重复实验和成本口径时，不能当作已证实的训练规律。MiniMax M2.7 的内部模型迭代系统、Kimi K3 的产品 Agent Swarm、Seed2.1 的真实工作流评测都属于这种需要降级解读的材料。([arXiv][30])

## 8.3 阅读一份新报告时的因果检查顺序

一份新报告应该依次回答：

1. **相对哪个旧 checkpoint？**底座、context、tokenizer、工具协议是否相同？
2. **新增能力来自哪里？**预训练、中训练、SFT、teacher、RL、test-time scaffold，还是更大预算？
3. **经验如何生产？**真实任务、合成任务、模拟器、人工轨迹分别多少？
4. **奖励知道什么？**是否接触隐藏测试、未来信息或人工 rubric？
5. **credit 单位是什么？**token、turn、interaction、episode 还是子任务？
6. **策略是否真正 on-policy？**rollout 模型版本、路由、温度和精度是否一致？
7. **Agent 接口是否一致？**chat template、工具 schema、上下文压缩和 harness 是否变化？
8. **成本口径是什么？**训练 GPU、环境 CPU、推理集群、reward server 和重试是否都计入？
9. **失败模式是什么？**是否有 reward hacking、熵坍塌、长度爆炸、过度验证或能力回退？
10. **消融能否隔离核心主张？**若同时换了底座、数据、环境和算法，最终提升不能归因给某个 optimizer。

**岗位能力映射（基于证据的推断）：**对应实验设计、统计重复、ablation、训练日志审计、benchmark governance、技术写作、limitations 和 source-of-gain 分解。2026 年高质量后训练研究岗位所需的“表达”并非写发布博客，而是把复杂系统变成可以被证伪的实验。

---

# 四、如何把新报告与旧报告、同行路线放在一起读

## 4.1 DeepSeek：R1 → V3.2 → V4

### R1：证明“结果奖励可以发现推理”

核心对象是单轮可验证推理。R1-Zero 测试纯 RL 的能力发现；R1 用 cold-start 和多阶段流程修复产品质量。([arXiv][2])

### V3.2：把能力发现迁移到多环境 Agent

变化不只是加入工具，而是建立 1,800 多个通用环境、代码/搜索/解释器分域专家、通用合成环境和 mixed GRPO；同时发现长上下文、工具角色和上下文管理成为限制。([arXiv][1])

### V4：把“专家并存”升级为“多教师统一”

V4 不再主要依赖专家数据回灌，而是让多个 specialist teacher 在 student 自采样轨迹上进行 exact reverse-KL OPD；同时把 rubric/GRM、快速搜索指令、原生低精度 rollout、沙箱 provenance 和 crash recovery 纳入同一系统。([arXiv][6])

**横向比较：**

* 与 Qwen3 相比，V4 更强调大模型多教师 OPD，而 Qwen3 更有价值的蒸馏证据来自强模型到小模型。
* 与 GLM-5 相比，两者都以分阶段/分域 teacher 保留能力；GLM 更突出阶段式 OPD 与 TITO，DeepSeek 更突出精确 reverse-KL 和系统一致性。
* 与 Step 3.5 相比，Step 更依赖专家轨迹的拒绝采样自蒸馏，V4 更明确地在 student trajectory 上做 teacher distribution matching。
* 与 ERNIE 5.0 相比，DeepSeek 选择专家后统一，ERNIE 选择统一多模态 mixed RL。

---

## 4.2 Qwen：Qwen3 → DeepResearch / Coder-Next → Qwen3.8

Qwen3 提供通用 reasoning/non-reasoning、四阶段后训练和强到弱蒸馏的基础配方。([arXiv][34])

Tongyi DeepResearch 与 Qwen3-Coder-Next 不应被理解成“在 Qwen3 上多做一点 RL”：

* DeepResearch 把 agentic CPT、128K 长轨迹、搜索任务合成、数据库/函数环境、binary-reward GRPO 和 Heavy Mode 连起来；
* Coder-Next 把 repo mid-training、约 80 万 SWE 任务、21 种工具格式、多 scaffold teacher、verified SFT 和单轮/仓库 RL 连起来。([arXiv][28])

这说明 Qwen 内部已经把“通用模型后训练”和“Agent 垂域能力制造”分成不同工程路径。

Qwen3.8-Max-Preview 是截至 7 月 27 日的最新产品版本，但官方当前主要给出 2.4T、preview 入口和未来开放权重的主张，没有公开与 Qwen3、DeepResearch、Coder-Next 同等级的技术报告、数据规模或训练消融。因此，**不能因为版本号更高，就把 Qwen3.8 当作最新可审计后训练配方。**([Qwen Studio][7])

---

## 4.3 Kimi：k1.5 → K2 → K2.5 → K3

这条路线最清楚地展示了能力对象的迁移：

| 版本   | 主要后训练问题                                                                                       |
| ---- | --------------------------------------------------------------------------------------------- |
| k1.5 | 如何把在线 RL 扩到 128K 长推理，并把长策略压缩成短策略。([arXiv][35])                                                |
| K2   | 如何在模拟/真实工具、代码仓库和搜索环境中训练 actor–critic Agent。([arXiv][29])                                      |
| K2.5 | 如何统一文本—视觉 Agent，并训练只负责委派的并行 orchestrator。([arXiv][31])                                        |
| K3   | 当前公开重心转到底座规模、KDA、Attention Residuals、Stable LatentMoE、原生多模态和 1M context；后训练细节尚不足。([Kimi][36]) |

与 UI-TARS-2 比，K2.5 的多模态 Agent 更偏视觉理解＋工具＋并行编排，UI-TARS-2 更偏屏幕原生 GUI 行动与 value-based credit；与 LongCat 比，Kimi 更强调 Gym 和 orchestrator，LongCat 更强调多域环境、异步生产和噪声课程。

---

## 4.4 MiniMax：M1 → M2/M2.5/M2.7＋Forge → M3/MaxProof

M1 的主问题是长 reasoning RL 和 CISPO；M2 系列把优化对象改成状态—动作 episode，并将 coding、terminal、AppDev、role-play、产品反馈和上下文管理放进同一混合训练流程。([arXiv][43])

Forge 则把 Agent、gateway、数据、rollout 和 trainer 解耦，支持不同 scaffold、上下文管理、prefix-tree KV 复用、MTP draft 和 PD 分离。这说明 MiniMax 从 M1 到 M2 的核心演化，是从“一个长推理 RL 算法”转向“一个持续生产 Agent 经验的模型迭代系统”。([arXiv][30])

M3 当前主要公开原生多模态与 MSA 等底座/推理效率信息，不能替代 M2 报告作为后训练依据。MaxProof 则是 M3 上的窄域验证案例：它通过多层 verifier、critique–repair、CISPO 和 population search，展示了 reward hacking 被发现和修复的完整过程。([MiniMax][11])

---

## 4.5 Coding Agent 的可比路线：Step 3.5、KAT V2.5、ROME、Qwen3-Coder-Next

这四条路线的共同点是 repo/environment/test 成为训练样本的一部分，但侧重点不同：

* **Qwen3-Coder-Next：**repo mid-training＋超大规模 SWE 任务＋多 scaffold teacher；
* **Step 3.5：**专家 RL→拒绝采样自蒸馏→统一模型，并把 50K 环境与 FullyAsync 配套；
* **KAT V2.5：**环境恢复、harness randomization、非对称 PPO、局部进展奖励和多教师 MOPD；
* **ROME：**百万仓库/轨迹、交互级 advantage、ROLL＋ROCK＋iFlow 的完整闭环。([arXiv][5])

它们真正的分歧是：

* 是否先做大规模 repo CPT；
* 是否需要 critic；
* credit 是 episode、interaction 还是 token；
* 是否以多专家蒸馏统一；
* 是否主动随机化 scaffold；
* 环境恢复质量与任务规模如何权衡。

---

# 五、共同趋势与真正分歧

| 已形成的共同趋势                                          | 尚未收敛的真实分歧                                                         |
| ------------------------------------------------- | ----------------------------------------------------------------- |
| SFT 没有消失，而是变成冷启动、工具格式、verified trajectory 和能力保底层。 | 纯在线探索应占多大比例，teacher 是否会限制新策略发现。                                   |
| 可执行环境和 verifier 是后训练的核心资产。                        | 大规模模拟环境还是高成本真实环境更划算。                                              |
| Agentic mid-training 常常先于 RL。                     | 中训练应注入完整轨迹，还是只注入工具/仓库表示。                                          |
| 多域能力往往先分开训练，再统一部署。                                | 统一 mixed RL、OPD/蒸馏还是参数插值更稳。                                       |
| 长程任务需要比终局 reward 更细的 credit。                      | critic/PPO、group-relative 方法、interaction advantage 或语言单元优化哪一种更合适。 |
| train–inference consistency 必须显式处理。               | 选择严格同步、部分异步还是完全异步；允许多少 staleness。                                 |
| harness、工具和 context policy 是能力的一部分。               | 应保留全部思考、只保留最近思考、摘要还是主动遗忘。                                         |
| 成本目标从训练 FLOPs 扩到 rollout、环境、关键路径和 token。          | 优先提高成功率、token efficiency、wall-clock，还是单位成功成本。                     |
| reward hacking 被视为常态而非偶发 bug。                     | 应主要靠规则、GRM、critic、人工 rubric 还是多层 verifier。                        |
| 最新发布版本往往披露较少。                                     | 开放权重、开放训练数据、开放环境和开放完整系统之间应达到什么程度。                                 |

---

# 六、证据不足、仅属主张或需要继续核验的项目

1. **Qwen3.8-Max-Preview**真实存在，并由官方宣布 2.4T 和后续开放权重，但目前缺少技术报告、模型卡、训练数据、RL 配方和可归因消融，应定为 C。([Qwen Studio][7])

2. **Kimi K3**已有官方技术博客和产品入口，底座架构信息有价值；但后训练部分不如 K2.5 完整。本次检索截止时没有确认 Moonshot 官方 GitHub/Hugging Face 权重仓库已经正式可用，因此不把“7 月 27 日计划开放”写成已完成事实。([Kimi][9])

3. **GLM-5.2**是真实官方版本，不是传闻；但其训练路线主要仍需由 GLM-5 报告和 slime 代码推断，不能把 5.2 的长程能力提升直接归因给某个新 PPO/OPD 改动。([Z.ai][10])

4. **MiniMax M3**真实且已开放权重，但其 MSA 效率和产品 Agent 能力披露多于后训练配方。当前最完整的 MiniMax Agent 后训练依据仍是 M2 系列报告。([Hugging Face][44])

5. **Step 3.7、Seed2.1、LongCat 2.0、ERNIE 5.1、MiMo 2.5、Hy3、Intern-S2-Preview**都可作为最新能力和方向信号，但不足以替代各自上一份完整报告。([StepFun][12])

6. **Kimi Researcher**的官方材料支持“端到端 RL、平均约 23 个 reasoning steps、每任务浏览 200 多 URL”等路线主张，但没有公开与 K2/K2.5 一样完整的底座身份、训练规模和算法细节，应视为专门系统证据，而非完整基座报告。([GitHub][45])

7. **Seed1.8/2.0**主要是能力模型卡和评测材料；不能由统一搜索、代码、GUI 能力反推出具体采用 PPO、GRPO、OPD 还是其他配方。([arXiv][46])

8. **Forge、ROLL、ROCK、slime、verl、AReaL、RollArt**是不同层次的训练/环境基础设施，不能把框架支持某算法等同于某个旗舰模型实际使用了该算法。

---

# 七、问题驱动材料束候选

以下不是课程顺序，而是后续可以独立展开的“问题—材料”集合。

## 材料束 A：纯 RL 能发现什么，为什么生产模型又重新引入教师？

**核心问题：**能力发现、行为模仿、输出质量和训练经济性之间怎样分工？

* **DeepSeek-R1**，2025-01-22：R1-Zero 与 cold-start、多阶段 R1 的直接对照。([arXiv][2])
* **Kimi k1.5**，2025-01：长上下文在线 RL、partial rollout、long-to-short。([arXiv][35])
* **Qwen3 Technical Report**，2025-05-14：四阶段后训练与强到弱蒸馏。([arXiv][34])
* **MiniMax M1**，2025-06-16：CISPO、长 reasoning RL 和成本证据。([arXiv][43])

## 材料束 B：如何制造一个可训练的 coding-agent 环境？

**核心问题：**从 GitHub issue/PR 到可复现 task bundle，要解决哪些工程和统计问题？

* **Qwen3-Coder-Next**，报告 2026-02-28。([arXiv][5])
* **Step 3.5**，报告 2026-02-23。([arXiv][24])
* **ROME**，初版 2025-12-31、修订 2026-03-12。([arXiv][3])
* **KAT-Coder-V2.5**，2026-07-06。([arXiv][15])
* **MiniMax M2 系列报告**，2026-05-26。([arXiv][30])

## 材料束 C：搜索与深度研究 Agent 的经验是怎样合成的？

**核心问题：**如何生成多跳问题、网页环境、数据库工具、证据链和不可投机 verifier？

* **Tongyi DeepResearch**，2025-11-04 版本。([arXiv][28])
* **DeepSeek V3.2**，2025-12-02。([arXiv][1])
* **DeepSeek V4 Preview Report**，2026-04-26。([arXiv][6])
* **LongCat-Thinking-2601**，2026-02-01。([arXiv][23])
* **Kimi Researcher**，2025-06-20。([GitHub][45])

## 材料束 D：长程 credit assignment 是否需要 critic？

**核心问题：**终局奖励、GAE、interaction advantage、reward-to-go、hindsight critic 和语言单元优化如何比较？

* **UI-TARS-2**，2025-09-02：PPO、value pretraining、length-adaptive GAE。([arXiv][25])
* **KAT-Coder-V2.5**：非对称 PPO 与局部进展奖励。([arXiv][15])
* **ROME**：interaction-level policy advantage。([arXiv][3])
* **MiniMax M2**：state–action atomic sample 与 reward-to-go。([arXiv][30])
* **Ling/Ring 2.6**：Linguistic Unit Policy Optimization。([arXiv][26])
* **rStar2-Agent**：作为非中国公司的 outcome-only 外部对照。([arXiv][22])

## 材料束 E：多个专家怎样合并成一个部署模型？

**核心问题：**数据蒸馏、logit distillation、reverse-KL OPD、MOPD、mixed RL 和参数插值分别保留什么、丢失什么？

* **DeepSeek V4**：multi-teacher exact reverse-KL OPD。([arXiv][6])
* **GLM-5**：Reasoning→Agentic→General RL 与跨阶段 OPD。([arXiv][27])
* **Qwen3**：小模型 logits distillation。([arXiv][34])
* **Step 3.5**：专家拒绝采样自蒸馏。([arXiv][24])
* **KAT V2/V2.5**：多专家 OPD/MOPD。([arXiv][37])
* **UI-TARS-2**：specialized RL 后参数插值。([arXiv][25])
* **Ling/Ring 2.6**：专家 RL、蒸馏和双向偏好。([arXiv][26])

## 材料束 F：train–inference mismatch 为什么会让 RL 优化错误目标？

**核心问题：**MoE routing、低精度、采样参数、异步 staleness 与 importance ratio 如何共同作用？

* **DeepSeek V4**：精确采样一致性、FP4 rollout、WAL 和可抢占执行。([arXiv][6])
* **GLM-5＋slime**：TITO、staleness、确定性 routing 和异步 RL。([arXiv][27])
* **ERNIE 5.0**：U-RB、MISC、router replay 和统一 FP8 operator。([arXiv][4])
* **MiMo-V2-Flash**：routing replay、partial rollout、stale-aware TIS。([arXiv][32])
* **Ling/Ring 2.6**：KPop 与跨版本异步轨迹。([arXiv][26])
* **verl**：MoE rollout/training mismatch 和 token-level importance correction。([Verl][47])

## 材料束 G：Agent 的上下文、思考轨迹和 harness 是否属于模型？

**核心问题：**当接口变化就导致能力变化时，模型评测和训练对象应该怎样定义？

* **DeepSeek V3.2/V4**：工具轮 reasoning 保存、新用户轮重置、上下文摘要/丢弃实验。([arXiv][1])
* **MiniMax M2**：保留完整 reasoning、黑白盒上下文管理和 scaffold 生态。([arXiv][30])
* **Step 3.5**：多 scaffold、context-policy 对照。([arXiv][24])
* **Qwen3-Coder-Next**：21 种工具格式和跨 scaffold 泛化。([arXiv][5])
* **Kimi K2.5**：不同 Agent 状态模型下 thinking/non-thinking 配置差异。([arXiv][31])
* **KAT V2.5**：harness randomization。([arXiv][15])

## 材料束 H：Agent RL 的扩展瓶颈到底在哪里？

**核心问题：**GPU trainer、decode、环境 CPU、reward server、KV cache 和尾部任务中，谁决定单位成功成本？

* **ROLL**，报告 2025-06-09，后续代码持续更新。([GitHub][48])
* **ROCK**，2025-11-08 起的环境基础设施。([GitHub][40])
* **RollArt**，修订 2026-06-15。([arXiv][41])
* **slime**，GLM 4.5→5.2 使用的 RL 框架。([GitHub][49])
* **AReaL / AReaL 2.0**，异步 RL 与微服务化 Agent 训练。([arXiv][50])
* **MiniMax Forge**。([arXiv][30])
* **Step FullyAsync**。([arXiv][24])
* **verl HybridFlow 与 fully async**。([字节跳动种子][39])

## 材料束 I：底座结构怎样改变后训练结论？

**核心问题：**在 MoE、MTP、线性/稀疏注意力、多模态与低精度底座上，同一个 RL 算法还是不是同一个实验？

* **DeepSeek V4**。([arXiv][6])
* **Kimi K3 技术博客**，2026-07-16。([Kimi][9])
* **ERNIE 5.0**。([arXiv][4])
* **Hunyuan-TurboS**，2025-05。([arXiv][51])
* **MiMo-V2-Flash**。([arXiv][32])
* **LongCat-Thinking-2601**。([arXiv][23])
* **Ling/Ring 2.6**。([arXiv][18])

## 材料束 J：如何审计 verifier、reward hacking 和技术主张？

**核心问题：**怎样证明模型学会了解题，而不是学会攻击评测器或模仿正确答案的形式？

* **MiniMax MaxProof**，2026-06-11。([arXiv][33])
* **KAT-Coder-V2.5**：verifier flipping 与反馈错误修复。([arXiv][15])
* **MiMo-V2-Flash**：git hacking 与能力回退。([arXiv][32])
* **LongCat-2601**：噪声环境和 benchmark 修订。([arXiv][23])
* **Qwen3**：人工复核 all-fail 候选和严格难度过滤。([arXiv][34])

---

# 最终归纳

截至 2026 年 7 月 27 日，中国团队公开的最重要后训练变化，不是某一个新的 policy-gradient 名称，而是后训练对象发生了变化：

[
\text{单轮回答策略}
\quad\longrightarrow\quad
\text{在有状态、长程、可执行环境中的行动策略}
]

随之而来的研究重心依次变成：

1. **定义真实能力，而不是只选 benchmark；**
2. **制造可复现的任务和环境；**
3. **建立既可验证又难以投机的信号；**
4. **在长轨迹上正确分配 credit；**
5. **用专家探索，再把能力统一进单模型；**
6. **把工具、上下文和 harness 纳入策略定义；**
7. **保证异步、低精度和 MoE 条件下优化目标仍然正确；**
8. **用消融、失败模式和成本口径证明能力究竟从哪里来。**

从公开证据厚度看，当前最值得作为主干材料的不是所有最新版本，而是 **DeepSeek R1/V3.2/V4、Qwen3＋Coder-Next＋Tongyi DeepResearch、Kimi k1.5/K2/K2.5、GLM-5＋slime、MiniMax M1/M2/Forge/MaxProof、Step 3.5、UI-TARS-2、LongCat-2601、KAT-Coder-V2.5、ERNIE 5.0、MiMo-V2-Flash、Ling/Ring 2.6、ROME/ROLL/ROCK/RollArt/AReaL/verl**。最新的 Qwen3.8、Kimi K3、GLM-5.2、MiniMax M3、Step 3.7、Seed2.1 等应作为“方向和能力更新”阅读，而不是在完整报告出现前被当作已知的训练配方。

[1]: https://arxiv.org/html/2512.02556v1 "https://arxiv.org/html/2512.02556v1"
[2]: https://arxiv.org/abs/2501.12948 "https://arxiv.org/abs/2501.12948"
[3]: https://arxiv.org/html/2512.24873v3 "https://arxiv.org/html/2512.24873v3"
[4]: https://arxiv.org/html/2602.04705v1 "https://arxiv.org/html/2602.04705v1"
[5]: https://arxiv.org/html/2603.00729v1 "https://arxiv.org/html/2603.00729v1"
[6]: https://arxiv.org/html/2606.19348v1 "https://arxiv.org/html/2606.19348v1"
[7]: https://qwen.ai/blog?id=qwen3.8-max-preview "https://qwen.ai/blog?id=qwen3.8-max-preview"
[8]: https://api-docs.deepseek.com/news/news260424/ "https://api-docs.deepseek.com/news/news260424/"
[9]: https://www.kimi.com/blog/ "https://www.kimi.com/blog/"
[10]: https://z.ai/blog/glm-5.2 "https://z.ai/blog/glm-5.2"
[11]: https://www.minimax.io/blog/minimax-m3 "https://www.minimax.io/blog/minimax-m3"
[12]: https://static.stepfun.com/blog/step-3.7-flash/ "https://static.stepfun.com/blog/step-3.7-flash/"
[13]: https://seed.bytedance.com/en/blog/seed2-1-officially-released-advancing-ai-productivity "https://seed.bytedance.com/en/blog/seed2-1-officially-released-advancing-ai-productivity"
[14]: https://longcat.chat/blog/longcat-2.0/ "https://longcat.chat/blog/longcat-2.0/"
[15]: https://arxiv.org/html/2607.05471v1 "https://arxiv.org/html/2607.05471v1"
[16]: https://ernie.baidu.com/blog/posts/ernie-5.1-0508-release/ "https://ernie.baidu.com/blog/posts/ernie-5.1-0508-release/"
[17]: https://huggingface.co/XiaomiMiMo/MiMo-V2.5 "https://huggingface.co/XiaomiMiMo/MiMo-V2.5"
[18]: https://arxiv.org/abs/2606.15079 "https://arxiv.org/abs/2606.15079"
[19]: https://github.com/InternLM/Intern-S1 "https://github.com/InternLM/Intern-S1"
[20]: https://huggingface.co/tencent/Hy3 "https://huggingface.co/tencent/Hy3"
[21]: https://arxiv.org/abs/2504.07866 "https://arxiv.org/abs/2504.07866"
[22]: https://arxiv.org/html/2508.20722v1 "https://arxiv.org/html/2508.20722v1"
[23]: https://arxiv.org/html/2601.16725v2 "https://arxiv.org/html/2601.16725v2"
[24]: https://arxiv.org/html/2602.10604v1 "https://arxiv.org/html/2602.10604v1"
[25]: https://arxiv.org/html/2509.02544v2 "https://arxiv.org/html/2509.02544v2"
[26]: https://arxiv.org/pdf/2606.15079 "https://arxiv.org/pdf/2606.15079"
[27]: https://arxiv.org/html/2602.15763v2 "https://arxiv.org/html/2602.15763v2"
[28]: https://arxiv.org/html/2510.24701v2 "https://arxiv.org/html/2510.24701v2"
[29]: https://arxiv.org/html/2507.20534v2 "https://arxiv.org/html/2507.20534v2"
[30]: https://arxiv.org/html/2605.26494v1 "https://arxiv.org/html/2605.26494v1"
[31]: https://arxiv.org/html/2602.02276 "https://arxiv.org/html/2602.02276"
[32]: https://arxiv.org/html/2601.02780v1 "https://arxiv.org/html/2601.02780v1"
[33]: https://arxiv.org/html/2606.13473v1 "https://arxiv.org/html/2606.13473v1"
[34]: https://arxiv.org/html/2505.09388v1 "https://arxiv.org/html/2505.09388v1"
[35]: https://arxiv.org/html/2501.12599 "https://arxiv.org/html/2501.12599"
[36]: https://www.kimi.com/blog/kimi-k3 "https://www.kimi.com/blog/kimi-k3"
[37]: https://arxiv.org/html/2603.27703v1 "https://arxiv.org/html/2603.27703v1"
[38]: https://arxiv.org/html/2506.13585v1 "https://arxiv.org/html/2506.13585v1"
[39]: https://seed.bytedance.com/en/public_papers/hybridflow-a-flexible-and-efficient-rlhf-framework "https://seed.bytedance.com/en/public_papers/hybridflow-a-flexible-and-efficient-rlhf-framework"
[40]: https://github.com/alibaba/ROCK "https://github.com/alibaba/ROCK"
[41]: https://arxiv.org/html/2512.22560v2 "https://arxiv.org/html/2512.22560v2"
[42]: https://github.com/pangu-tech/pangu-ultra "https://github.com/pangu-tech/pangu-ultra"
[43]: https://arxiv.org/abs/2506.13585 "https://arxiv.org/abs/2506.13585"
[44]: https://huggingface.co/MiniMaxAI/MiniMax-M3 "https://huggingface.co/MiniMaxAI/MiniMax-M3"
[45]: https://github.com/MoonshotAI/Kimi-Researcher/blob/project_page/index.html "https://github.com/MoonshotAI/Kimi-Researcher/blob/project_page/index.html"
[46]: https://arxiv.org/html/2603.20633v1 "https://arxiv.org/html/2603.20633v1"
[47]: https://verl.readthedocs.io/en/latest/algo/rollout_corr.html "https://verl.readthedocs.io/en/latest/algo/rollout_corr.html"
[48]: https://github.com/alibaba/ROLL "https://github.com/alibaba/ROLL"
[49]: https://github.com/THUDM/slime "https://github.com/THUDM/slime"
[50]: https://arxiv.org/html/2505.24298v2 "https://arxiv.org/html/2505.24298v2"
[51]: https://arxiv.org/pdf/2505.15431 "https://arxiv.org/pdf/2505.15431"

# 第二轮扩展审计：旗舰报告之外的“伴生证据图”

## 一、结论先行

**GLM 并不是孤例。**扩大到团队论文、专项模型报告、环境项目、训练框架、模型卡和系统论文以后，可以找到一批与“GLM-5 → GLM-5.2 博客 → SAO → CompactionRL → slime”结构相似的证据链。

这轮搜索最重要的新增认识不是又发现了一串算法缩写，而是：

> **同一家 Lab 的后训练路线通常已经分化成多个任务分支；旗舰技术报告只给出主干，专项论文往往补出最新的 optimizer、credit assignment、环境生产、蒸馏整合和异步系统选择。**

因此，不能再把一个团队简化成“使用 GRPO”“使用 PPO”或“使用 OPD”。更准确的单位应当是：

[
\text{Lab}
\rightarrow
\text{模型阶段}
\rightarrow
\text{任务分支}
\rightarrow
\text{轨迹结构}
\rightarrow
\text{奖励与 credit}
\rightarrow
\text{optimizer}
\rightarrow
\text{系统实现}
\rightarrow
\text{能力整合}
]

本轮最强的几个补充案例是：

1. **ERNIE 5.0 → ERNIE 5.1：**从统一混合 RL，进一步公开为并行领域专家、MOPD、General-RL，以及完全解耦异步系统、FP8 一致性和 MoE Router Replay。
2. **Qwen3 → GSPO / Tongyi DeepResearch / Qwen3-Coder-Next / Qwen-AgentWorld：**同一团队内部同时存在序列级 GSPO、严格 on-policy GRPO、未公开 optimizer 的大规模 coding-agent 路线，以及用语言世界模型扩展环境的全新分支。
3. **Step 3.5 → Step-DeepResearch：**基础模型报告采用 MIS-PO 等路线，但专项 Deep Research 模型明确选择 critic PPO，因为长程、跨来源、稀疏终局奖励需要 token-level value。
4. **KAT-Coder-V2 → V2.5：**直接公开从仓库环境、harness randomization、反馈可靠性，发展到带 hindsight privileged information 的非对称 actor–critic PPO。
5. **LongCat → DORA：**形成了一个很重要的反例——超长异步轨迹不一定必须切换 PPO；通过多版本、单策略整轨迹和有界 staleness，仍可保留 group-relative/GSPO 路线。
6. **MiMo-V2-Flash → 独立 MOPD 论文 → MiMo-V2.5：**MOPD 不再只是报告中的一段，而有独立算法、基线对照和明确的生产模型部署说明。
7. **AReaL → Ling/Ring 2.6 → AReaL 2.0：**研究对象从“异步 RL trainer”进一步变成从真实部署 workload 持续学习的 Agent evolution control plane。
8. **Qwen-AgentWorld：**公开出现了另一条非常值得重视的路线——训练语言世界模型作为可扩展环境模拟器，再反过来给 Agent RL 生产经验。

---

## 二、先用 GLM 案例给“证据拼接”定标

你上传的分析对 GLM 的边界划分是正确的：

* SAO 与 GLM-5.2 长程 Agentic/Coding RL 直接相关；
* 但不能外推成 GLM-5.2 所有 reasoning RL 都从 GRPO 切换了 PPO；
* 更精确的说法是，长程 Agent 分支从 group-relative 多 rollout，转向 single-rollout、critic-based PPO 和 token-level GAE；GLM-5 的 reasoning 分支仍有明确的 GRPO＋IcePop 证据。

同样重要的是，SAO 和 CompactionRL 在概念上高度互补，却没有公开一份两者完整组合后的生产伪代码；公开材料也没有给出 GLM-5.2 750B 训练中 critic 结构、采样比例、staleness 阈值和 compaction 配置。因此，能够恢复的是**算法骨架和演进因果**，不是可复现配方。

为了将这一纪律用于其他团队，下面采用四个证据等级：

* **P1｜直接生产桥接：**论文或官方博客明确说某方法用于某个命名模型。
* **P2｜直接专项模型证据：**该论文就是官方专项模型报告，但没有证明同法用于最新旗舰。
* **I+｜强拼接推断：**同一团队、时间连续、问题与系统接口吻合，但没有逐字说“用于模型 X”。
* **F｜框架能力：**代码支持该算法，只能证明团队具备此训练能力，不能证明某旗舰实际使用。

---

# 三、一个需要立即纠正的时效性问题：Qwen 最新版本

上一轮回答中把 **Qwen3.8-Max-Preview** 列为官方最新版本，这一条应当撤回。

本轮扩大核验后，Qwen 官方仓库截至 2026 年 7 月 27 日仍明确将 **Qwen3.6** 称为 “latest addition”。官方记录为：

* Qwen3.6-35B-A3B：2026 年 4 月 16 日；
* Qwen3.6-27B：2026 年 4 月 22 日。

同一官方页面称 Qwen3.5 在“百万级 Agent 环境”上扩展 RL，并使用支持大规模 Agent scaffold 和环境编排的异步 RL 基础设施，但没有公开足以重建 optimizer、奖励和经验配比的完整报告。因此，Qwen3.5/3.6 是重要的**最新产品与方向证据**，但技术分析仍需回到 GSPO、Tongyi DeepResearch、Coder-Next 和 AgentWorld。([GitHub][1])

---

# 四、扩大搜索后，最重要的路线修正

## 1. 不存在“中国团队正在整体从 GRPO 转向 PPO”

更准确的规律是：

> **任务轨迹的几何结构，决定 critic 的收益是否足以覆盖其成本。**

### 更倾向 critic/PPO 的场景

* 每个任务只能承受一条或很少几条昂贵 rollout；
* 轨迹有几十至数百轮；
* episode 被 observation、compaction、子 Agent 或 context reset 切断；
* 最终奖励非常延迟；
* 需要区分中间操作的价值；
* critic 能看到 actor 部署时看不到的 hindsight 信息；
* group 内样本长度或 segment 数量严重不一致。

GLM-5.2 的 SAO/CompactionRL 就属于这类。KAT-Coder-V2.5 和 Step-DeepResearch 则提供了两个独立的直接验证案例。

### 仍适合 group-relative 的场景

* 每题可以低成本采多条回答；
* 轨迹较规则；
* 最终答案或执行结果高度可验证；
* 不需要细粒度时间 credit；
* 系统可以保证完整 group 或完整 trajectory 的采样一致性；
* 不希望承担 critic 的预训练、漂移与崩溃风险。

Qwen GSPO、Tongyi DeepResearch、LongCat 的 GSPO＋DORA，以及 Seed 的 DAPO 都说明 group-relative 路线仍有持续生命力。([arXiv][2])

---

## 2. “PPO 回归”实质上是 critic 在长程任务中的重新定价

### Step-DeepResearch：与 GLM 结论高度相似的独立证据

Step-DeepResearch 的训练顺序是：

[
\text{Agentic mid-training}
\rightarrow
\text{SFT}
\rightarrow
\text{真实工具环境中的 RL}
]

它明确采用 on-policy clipped PPO 和 GAE，并设置 (\gamma=1,\lambda=1)。报告不是笼统地说 PPO 更强，而是给出选择原因：

* critic 能提供 token-level value；
* 能识别并压低重复循环等有害行为；
* 对跨来源检索、证据选择、交叉验证、报告组织等中间决策进行更细的 credit assignment；
* critic-free 方法容易把“偶然获得高终局分数”误判为整个轨迹都值得强化。([arXiv][3])

这与 GLM-5.2 的因果结构相同，但并非同一套算法：

* GLM SAO 的主要系统问题是 single rollout、异步 policy lag、observation 边界和 critic 稳定性；
* Step-DeepResearch 的主要任务问题是开放式报告、rubric 终局奖励和多工具长程 credit；
* 两者独立得出“在这一任务分支上 critic 的成本开始值得”的结论。

### KAT-Coder-V2.5：critic 获得部署时不可见的 hindsight

KAT-Coder-V2.5 直接公开了：

* AutoBuilder 恢复真实多语言仓库；
* fail-to-pass 与 pass-to-pass 测试；
* harness randomization；
* hardened sandbox；
* asymmetric actor–critic PPO；
* hindsight-augmented value estimation；
* SWE、Agent-Claw、WebCoding 专家通过 MOPD 合并。([arXiv][4])

这里的“不对称”很关键：

* **Actor**只能看到部署时可用的历史、工具反馈和仓库状态；
* **Critic**在训练时可以看到最终测试结果、diff、未来轨迹、失败原因等 privileged information。

这相当于把“任务完成后才知道的诊断信息”用于 value learning，而不泄露给执行策略。它比普通 PPO 更接近 hindsight credit assignment。

因此，GLM SAO 与 KAT V2.5 应一起读：

| GLM SAO                | KAT V2.5                  |
| ---------------------- | ------------------------- |
| 解决单 rollout 与完全异步      | 解决仓库 POMDP 与失败诊断          |
| critic 要跟上快速变化的 actor  | critic 可使用未来/隐藏信息         |
| Skip-Observation GAE   | hindsight-augmented value |
| DIS 和 stale-token mask | harness reward、局部进展与反馈可靠性 |
| 重点是系统异步正确性             | 重点是环境与 credit 语义          |

### Seed 的 VAPO：critic-based 路线并非 2026 年才出现

字节 Seed 团队 2025 年 4 月的 VAPO 已经用 value-based PPO 研究长 CoT。它针对 value bias、长度异质性和稀疏奖励，加入 value pretraining、长度自适应 GAE、非对称 clipping、token-level loss 和 self-imitation；在 Qwen 32B 底座上报告了稳定的约 5,000-step 训练。([arXiv][5])

这与同团队的 DAPO 并不矛盾。它说明 Seed 同时研究：

* critic-free、group-relative 的 reasoning RL；
* critic-based 的长 CoT；
* UI-TARS-2 中面向 GUI 长轨迹的 value/PPO 路线。

所以把 Seed 概括为“采用 DAPO/GRPO”同样过窄。

---

## 3. 反例同样重要：LongCat＋DORA 说明长轨迹不必然导向 PPO

DORA 由 LongCat 路线的团队公开，论文明确说 rollout 占 RL step 的约 50%–80%，长尾轨迹使同步训练产生严重 bubble。其解决方案不是把完整长轨迹拆成跨版本 partial rollout，而是：

1. 同时维护多个 policy version；
2. 每条 trajectory 始终由同一版本完整生成；
3. 已完成样本立即流入 trainer；
4. 未完成长轨迹继续运行在旧版本；
5. 使用滑动窗口给 staleness 设定确定上界；
6. 在同版本实例间迁移 KV cache，避免重新 prefill。([arXiv][6])

这个设计保留了 group-relative/GRPO/GSPO 更偏好的采样语义：

[
\text{一条 trajectory}
\quad\leftrightarrow\quad
\text{一个完整 behavior policy version}
]

而 GLM SAO 更接近：

[
\text{允许异步旧轨迹}
+
\frac{\pi_\theta}{\pi_{\text{rollout}}}
+
\text{stale-token rejection}
]

因此，长程 Agent RL 至少出现两种不同的系统—算法共设计：

### 路线 A：接受 off-policy，显式校正

* slime / SAO；
* AReaL 的 stale-aware PPO；
* RollArt；
* MiMo partial rollout；
* token-level importance correction 或 masking。

### 路线 B：保持每条轨迹的版本纯度

* DORA 多版本共存；
* 不跨权重版本续写一条轨迹；
* 通过资源调度和 KV 迁移解决长尾，而不是算法校正。

这是真正的技术分歧，不是简单的“同步还是异步”。

---

# 五、各 Lab 中与 GLM 类似的“报告之外证据链”

## 1. 百度：ERNIE 5.0 → ERNIE 5.1，是目前最完整的同类案例之一

ERNIE 5.1 官方博客于 **2026 年 5 月 9 日**发布。与仅给榜单的模型博客不同，它直接公开了新的后训练结构。([百度ERNIE][7])

### 系统层

ERNIE 5.1 建立了以 RL Controller 为中心的完全解耦异步系统，将：

* trainer；
* inference；
* reward；
* agent loop

拆成可独立部署和扩展的子系统。它还公开了：

* 统一 FP8 训练—推理 operator；
* Rollout Router Replay，R3；
* 动态通信压缩和 KV-cache pooling；
* 使用空闲 CPU 池执行 sandbox 和 verifier。

官方称 R3 在接近零额外延迟下，将相关 KL 偏差降低约 50%。([百度ERNIE][7])

### 算法与能力整合层

ERNIE 5.1 的四阶段后训练为：

[
\text{统一 SFT}
\rightarrow
\text{code/reasoning/agent 专家并行 RL}
\rightarrow
\text{MOPD}
\rightarrow
\text{General-RL}
]

尤其值得注意的是，官方明确说：

* 每个领域专家可以定制自己的奖励和训练算法；
* student 在自己采样的分布上接受多个 teacher 的 token-level reverse-KL；
* 开放式聊天和创作属于高熵任务，OPD 容易效率低或过度平滑，因此最后仍需在线 General-RL。([百度ERNIE][7])

这比“ERNIE 5.0 使用 unified multimodal RL”更及时，也修正了对 OPD 的一种过度概括：

> **OPD 适合搬运已经形成的低熵、可辨识专家策略；它不一定适合直接替代开放分布上的在线探索和偏好优化。**

**证据等级：P1。**

仍未知的是各专家分别使用 PPO、GRPO、MISC 还是其他变体。

---

## 2. Qwen：同一团队内部至少存在四条并行路线

### 路线一：Qwen3 主干上的 GSPO

GSPO 论文于 **2025 年 7 月 24 日**提交。它把 importance ratio、clipping 和优化从 token 层上移到 sequence 层，并明确称其相较 GRPO 改善效率、性能和 MoE RL 稳定性，而且这些特性已对“latest Qwen3 models”的改进作出贡献。([arXiv][2])

这是 **P1**：论文明确连接到 Qwen3。

但它没有证明：

* Tongyi DeepResearch 使用 GSPO；
* Qwen3-Coder-Next 使用 GSPO；
* Qwen3.5/3.6 原样使用相同配置。

### 路线二：Tongyi DeepResearch 仍坚持严格 on-policy GRPO

Tongyi DeepResearch 的专项报告把 agentic continued pretraining、SFT、真实数据库/函数环境和 RL 连在一起；其 RL 路线更接近：

* 严格 on-policy；
* binary correctness；
* tailored GRPO；
* leave-one-out/group-relative baseline；
* 过滤全对、全错和无区分度任务；
* 动态更新训练难度。

这说明 Qwen 团队并没有因为 GSPO 出现，就把所有 Agent 任务统一成 GSPO，更没有整体转向 PPO。([arXiv][8])

### 路线三：Qwen3-Coder-Next 的重点是 repo mid-training 与 scaffold diversity

Coder-Next 的强证据集中在：

* repo-level mid-training；
* 约 80 万条可验证 SWE 任务；
* 多 scaffold teacher；
* 21 种工具调用格式；
* Kubernetes/Argo 环境；
* verified SFT 与 repository RL；
* 跨 scaffold 泛化的不对称性。

其具体 RL optimizer 并未得到同等级披露，因此不能从 GSPO 论文自动补成“Coder-Next 使用 GSPO”。([arXiv][9])

### 路线四：Qwen-AgentWorld 把世界模型变成环境基础设施

这是本轮最重要的新材料之一。

**Qwen-AgentWorld** 于 **2026 年 6 月 23 日**提交。团队从七个域的真实环境中收集超过 **1,000 万条交互轨迹**，通过：

[
\text{CPT}
\rightarrow
\text{SFT}
\rightarrow
\text{RL}
]

训练语言世界模型。其中 RL 使用 rubric 与规则混合奖励来提升状态转移模拟的 fidelity。([arXiv][10])

训练后的模型有两种用途：

1. **作为独立环境模拟器：**可控地模拟数千个真实任务环境，供 Agent RL 采样；
2. **作为 Agent 底座 warm-up：**世界模型训练本身改善下游七类 Agent benchmark。

论文甚至报告，特定受控设置下，模拟环境 RL 的增益可以超过仅使用真实环境训练。([arXiv][10])

这增加了一条此前回答中没有充分覆盖的因果路线：

[
\text{真实环境轨迹}
\rightarrow
\text{训练 language world model}
\rightarrow
\text{批量生成可控环境反馈}
\rightarrow
\text{Agent policy RL}
]

它与 ROCK、ROME、AutoBuilder 之类的“恢复真实可执行环境”不是替代关系，而是两条互补路线：

* **真实环境路线：**真实性高，但创建、启动和维护昂贵；
* **世界模型路线：**并发、课程和反事实采样容易，但存在 simulator bias 和 reward hacking。

**证据等级：P2。**它是官方专项路线，但没有证据表明 Qwen3.6 的全部 Agent RL 都由 AgentWorld 提供环境。

---

## 3. StepFun：Step 3.5 与 Step-DeepResearch 证明同一 Lab 会按任务分叉 optimizer

Step 3.5 主报告公开了：

* 领域专家训练；
* 专家轨迹拒绝采样和自蒸馏；
* 统一 RL；
* MIS-PO；
* FullyAsync 搜索 RL；
* context management 对照。

而 Step-DeepResearch 则明确选择 PPO＋GAE。([arXiv][3])

所以 StepFun 的证据链应当写成：

```text
Step 3.5 通用/多域后训练：
领域专家
→ 专家轨迹自蒸馏
→ 统一模型
→ MIS-PO / FullyAsync 等任务化优化

Step-DeepResearch：
atomic-capability mid-training
→ SFT
→ 真实工具环境
→ rubric terminal reward
→ critic PPO + token-level GAE
```

这两条路线不是新旧替代关系。更合理的推断是：

* MIS-PO 主要解决 policy-ratio、token/trajectory masking 和异步稳定；
* DeepResearch PPO 主要解决长程、开放任务中的 credit assignment；
* Step 3.5 的通用模型可能吸收 DeepResearch 专家轨迹或能力，但目前没有直接材料证明具体融合方式。

**证据等级：各分支 P2；两者的生产融合为 I+。**

---

## 4. 快手 KAT 与美团 LongCat：相邻团队给出两种相反但都合理的长程 RL 选择

### KAT-Coder-V2.5：环境与 critic 共设计

KAT V2.5 的直接证据表明，coding-agent 训练的瓶颈已经从“采多少 issue”转向：

* 仓库能否启动；
* 测试是否可靠；
* reward 是否会翻转；
* harness 是否被记忆；
* 失败轨迹是否仍有局部价值；
* critic 能否利用任务结束后的诊断信息。

因此它选择 asymmetric PPO＋hindsight critic。([arXiv][4])

### LongCat：保留 GSPO，系统解决异步长尾

LongCat-2601 仍使用 sequence/group-relative 路线，而 DORA 保证：

* 一条轨迹不跨 policy version；
* 长轨迹不被丢弃；
* staleness 有确定上界；
* KV cache 可以在同版本实例间复用；
* 完成轨迹无需等待最慢样本。([arXiv][6])

二者共同说明：

> **是否需要 critic，不只由“任务很长”决定，还由系统是否能够维持 group statistics、完整轨迹和可接受的样本成本决定。**

---

## 5. MiMo：MOPD 已从报告主张升级为独立可审计算法

MiMo-V2-Flash 报告已经公开过“领域 specialist → MOPD → 统一模型”。本轮新增的关键证据是 **MOPD 独立论文**，于 **2026 年 6 月 29 日**提交。

论文明确给出：

1. 各领域独立进行 RL，形成多个 teacher；
2. student 从自己的当前策略分布采样；
3. 多 teacher 在 student trajectory 上提供 dense reverse-KL；
4. 与 Mix-RL、Cascade RL、off-policy finetuning 和 parameter merge 比较；
5. 在 Qwen3-30B-A3B 上几乎继承各 teacher 的能力；
6. 明确说明 MOPD 已部署到 MiMo-V2-Flash 后训练。([arXiv][11])

这使 MiMo 的能力整合路线达到 **P1**，而不是仅依赖技术报告中的一句描述。

更重要的是，MOPD 与 actor optimizer 是正交的：

* teacher 可以由 GRPO、PPO、MOPD 前的 specialist RL 或其他方法产生；
* MOPD 解决的是**如何把多个已发现策略搬进一个 student**；
* 它不直接解决 teacher 如何探索、如何分配 long-horizon credit。

MiMo-V2.5 模型卡进一步声称继续采用大规模 Agent RL 和 MOPD，并把上下文在后训练期间从 32K 扩到 256K、再扩到 1M，但 specialist 的具体 optimizer 仍没有公开。([Hugging Face][12])

---

## 6. 蚂蚁 InclusionAI：从异步 trainer 发展到 Agent 在线演化控制面

AReaL 早期材料的重心是：

* fully asynchronous RL；
* stale-aware PPO；
* producer–consumer；
* rollout/trainer 解耦；
* 大规模权重同步。

2026 年 7 月 1 日的 **AReaL 2.0 / Next-Generation Agentic RL Systems Enable Self-Evolving Agents**，把研究问题向前推进了一层。论文认为，大规模自演化 Agent 的主要障碍已经不只是 RL 算法，而是缺少：

1. 能承载 step-level RL 信号的标准 Agent trajectory protocol；
2. 将真实企业 workload 转换为受治理训练数据的数据代理；
3. 决定何时更新权重、何时修改 prompt、工具或 harness 的统一 evolution control plane。([arXiv][13])

这对应一条与常规离线后训练不同的新因果链：

[
\text{部署请求}
\rightarrow
\text{轨迹、反馈与失败数据}
\rightarrow
\text{治理与选择}
\rightarrow
\text{在线 RL / harness evolution}
\rightarrow
\text{重新部署}
]

AReaL 2.0 当前实例化的是其中“从部署 workload 更新 policy weight”的一条分支；它还没有证明完全自主、无人工监督的 continual learning 已经成熟。因此“self-evolving”应理解为**系统研究议程和初步实现**，而不是已经解决灾难遗忘、安全回归和线上探索风险。

结合 Ling/Ring 2.6、KPop、Linguistic Unit Policy Optimization、AEnvironment 和高频权重同步工具来看，InclusionAI 的路线已经从单一 optimizer 研究扩展到：

```text
环境协议
+ 在线 rollout
+ 异步/staleness 控制
+ 语义单元 credit
+ 专家 RL 与蒸馏
+ 部署 workload 回流
```

**证据等级：系统路线 P1；具体旗舰模型持续学习能力仍为 I+。**

---

## 7. 百度、MiMo、DeepSeek、GLM、KAT 与 Mach-Mind 正在形成 MOPD/OPD 集群

2026 年 7 月 10 日发布的 **Mach-Mind-4-Flash** 是此前回答遗漏的强一手材料。它来自理想汽车 Foundation Model Team，模型为 35B MoE、3B activated，并声称主要增益来自后训练而非新增预训练计算。([arXiv][14])

其路线非常明确：

[
\text{Reasoning/General/Agent 专家并行 RL}
\rightarrow
\text{routed reverse-KL MOPD}
\rightarrow
\text{HMPO 压缩推理长度}
]

报告称：

* 统一 RL/OPD 系统和动态多 teacher 调度带来约 17% 端到端训练加速；
* MOPD 用于减少 mixed-reward RL 的 seesaw；
* HMPO 将推理长度压缩约 19%–46%，精度损失不超过 0.7 个百分点。([arXiv][14])

把这些材料放在一起，会发现一个越来越稳定的四层结构：

### 第一层：专家策略发现

不同任务使用不同：

* 环境；
* 数据；
* reward；
* rollout budget；
* PPO/GRPO/GSPO/CISPO 等 optimizer。

### 第二层：on-policy 能力搬运

让统一 student 在自己的状态分布上采样，再由多个 teacher 通过 reverse-KL 提供 dense signal。

代表：

* DeepSeek V4；
* GLM-5 cross-stage OPD；
* MiMo MOPD；
* ERNIE 5.1；
* KAT V2.5；
* Mach-Mind-4-Flash；
* Ling/Ring 2.6。

### 第三层：在线能力恢复

对以下 OPD 不擅长的能力再做 RL 或偏好优化：

* 开放聊天；
* 创作；
* 高熵多样性；
* 人类风格；
* 安全；
* 无唯一最优 teacher distribution 的任务。

ERNIE 5.1 对这一点给出了目前最明确的官方解释。([百度ERNIE][7])

### 第四层：推理成本压缩

包括：

* long-to-short RL；
* shortest-correct distillation；
* HMPO；
* token-efficiency reward；
* context compaction；
* MTP draft distillation。

因此，OPD 的合理定位不是“替代 RL”，而是：

> **RL 负责发现或推动能力边界；OPD 负责将多个能力面运输到一个可部署策略；最终在线 RL/偏好优化和压缩负责修复熵、风格与成本。**

---

## 8. Moonshot：专项项目揭示了 Kimi 主线之外的多种 RL 偏好

### Kimi-Dev：outcome-only、agentless training 可以成为 Agent skill prior

Kimi-Dev-72B 在真实 Docker 仓库中做大规模 RL，只在完整测试套件通过时获得奖励。其执行结构不是通用 ReAct coding agent，而是较简化的两阶段：

1. 文件定位；
2. 完整文件上的代码编辑。

官方项目明确称其在 SWE-bench Verified 达到 60.4%。([GitHub][15])

论文进一步把这一过程称为“Agentless Training as Skill Prior for SWE-Agents”：先用受控、低分支的 agentless 结构通过 RL 学会代码定位与修改，再通过少量轨迹把能力迁移到更通用的 Agent scaffold。

这是一条值得与 Qwen Coder-Next 和 KAT 对照的路线：

* Qwen/KAT 强调直接扩展真实多轮环境；
* Kimi-Dev 先降低 action-space 复杂度，让 outcome-only RL 学到核心技能，再迁移到 Agent。

### Kimina-Prover：完整证明级 outcome reward，不使用 value 或 PRM

Kimina-Prover 采用 whole-proof generation：

* 生成期间没有 Lean prover 的中间反馈；
* 只在整份证明后验证；
* 不依赖 MCTS、value function 或 process reward model；
* RL 上下文达到 32K。([GitHub][16])

这与 KAT/SAO 的 critic 路线相反，却并不矛盾。形式化证明的环境具有一个重要优势：最终 verifier 极其可靠，而且生成对象可以被定义成一个完整 proof artifact。只要采样规模足够，outcome-only 仍可能有效。

### 与 K2/K2.5 的关系

Moonshot 因而至少公开过：

* k1.5：长 CoT、partial rollout、value-free 在线 RL；
* Kimina-Prover：完整证明 outcome RL；
* Kimi-Dev：agentless repository RL；
* K2：工具、代码、搜索环境和 actor–critic；
* K2.5：多模态联合 RL 与并行 orchestrator RL；
* checkpoint-engine：超大 MoE 高频权重同步。

这些材料能够证明 Moonshot 内部按任务保留多种训练范式；**不能证明 Kimi K3 具体沿用了哪一种后训练配方。**K3 当前公开信息仍主要集中在底座、注意力和多模态结构。

---

## 9. DeepSeek：专项论文补出的主线主要在 verifier，而不仅是 actor optimizer

DeepSeek-GRM 于 2025 年 4 月提出：

* pointwise generative reward model；
* Self-Principled Critique Tuning；
* 用在线 RL 学习自适应生成原则和 critique；
* reward inference-time parallel sampling；
* meta reward model 参与聚合。([arXiv][17])

DeepSeek-Math-V2 与 DeepSeek-Prover-V2 又把这一方向推进到：

* 让 verifier 检查证明的忠实性，而不仅是最终答案；
* 对难题扩展 verifier 计算；
* 将非形式化分解与形式化验证连接；
* 递归拆分定理和子目标。

这意味着 DeepSeek 的后训练研究应增加一条独立主线：

[
\text{固定规则 verifier}
\rightarrow
\text{生成式 reward model}
\rightarrow
\text{可扩展 critique 与 meta-evaluation}
\rightarrow
\text{verification compute scaling}
]

DeepSeek V4 中的 rubric RL 和 generative reward model 与这条路线高度一致，但在没有明确声明之前，不能假设 V4 使用的就是 DeepSeek-GRM 论文中完全相同的 checkpoint 和聚合配置。([arXiv][17])

**证据等级：专项模型和 reward 系统为 P2；与 V4 生产配方的连接为 I+。**

---

## 10. InternLM：Intern-S2 已经给出比 S1 更新的方向，但仍是模型卡级证据

截至本轮检索，官方已公开 **Intern-S2-Preview-397B** 模型卡。它称模型在三个方向扩展：

* 预训练；
* RL 任务覆盖；
* 交互式 Agent 环境。

具体包括：

* 超过 20 个科学域的联合多任务 RL；
* 多个 Agent framework 接入大规模 sandbox；
* general 与 scientific long-horizon task 上的 black-box agentic RL；
* 文本评测最大 256K inference length。([Hugging Face][18])

这比此前只写 Intern-S1/S1-Pro 更新，但证据厚度仍有限：

* 没有公开 optimizer；
* 没有环境数量；
* 没有 reward 配比；
* 没有 specialist 与 unified RL 的关系；
* 没有异步系统和 train–inference correction 细节；
* 没有能隔离 black-box Agent RL 增益的消融。

因此应更新为：

> **Intern-S2 是最新的强方向信号，Intern-S1/S1-Pro 仍是目前理解其 Mixture-of-Rewards、科学任务训练和训推一致性的主要技术材料。**

---

## 11. MiniMax：Forge 与专项论文表明 CISPO 没有在 M1 后消失

MiniMax M1 首次系统公开 CISPO。M2 系列报告和 M2.5 官方材料仍将 CISPO 放在 Agent RL 主干内，同时把训练对象从单轮 reasoning 扩展为：

* state–action atomic samples；
* coding、terminal、AppDev；
* process reward；
* completion-time reward；
* context management；
* product feedback。

Forge 则提供：

* Agent/scaffold 与 trainer 解耦；
* Windowed FIFO 数据流；
* prefix-tree KV reuse；
* prefill/decode 分离；
* MTP draft KL；
* 多环境、多 Agent runtime；
* 大规模异步 experience production。([arXiv][19])

M2.7 所称“模型自我迭代”，主要指 Agent 自动修改 scaffold、训练配置和实验流程，并在一组 MLE 类任务上评估；目前没有证据说明它已经实现无人工监督、持续修改自身主模型权重的递归自我改进。

M3 的公开资料仍不足以证明 optimizer 已从 CISPO 切换。因此更准确的路线是：

```text
M1：长 reasoning RL + CISPO
    ↓
M2/M2.5：CISPO 延伸到多域 Agent RL
    + state-action credit
    + Forge
    ↓
M2.7：Agent 辅助训练流程与 scaffold 迭代
    ↓
M3：最新底座/多模态能力已公开，
    新后训练配方尚不足
```

---

## 12. 两个此前容易遗漏的中国团队案例

### 理想汽车 Mach-Mind-4-Flash

这是本轮非常值得补入主材料的完整技术报告：

* 专门面向小激活参数、高 Agent 能力；
* 并行领域专家；
* routed MOPD；
* 动态多 teacher；
* RL/OPD 统一基础设施；
* HMPO token-efficiency；
* 10K 级 Agent 环境与多 scaffold 信息。

它可作为 DeepSeek/GLM/MiMo/ERNIE 之外，对“专家 RL → MOPD → 成本压缩”路线的独立验证。([arXiv][14])

### 华为 Pangu Embedded

Pangu Embedded 不是 Pangu Ultra 的后训练报告，但它提供了此前回答中缺失的盘古专项后训练证据：

* iterative distillation；
* 迭代间 model merging；
* 昇腾上的 RL；
* latency-tolerant stale synchronous parallel；
* prioritized rollout queue；
* 混合确定性与轻量 LLM reward；
* fast/slow reasoning mode。([arXiv][20])

因此，上一轮“华为没有同等级公开后训练路线”的说法需要缩窄为：

> **Pangu Ultra/Pro MoE 旗舰公开材料的后训练细节仍不足；但 Pangu Embedded 已经提供了一条直接、可研究的蒸馏＋异步 RL＋奖励系统路线。**

不能将 Embedded 的配方外推到 Ultra。

---

# 六、本轮新增材料共同揭示的五条更深因果链

## 1. 后训练算法正在按“任务几何”分叉

可以用下面的决策框架理解，而不是记团队缩写。

| 任务条件                          | 更可能选择                              |
| ----------------------------- | ---------------------------------- |
| 短程、可验证、多 rollout 便宜           | GRPO、DAPO、GSPO                     |
| MoE token ratio 噪声大、序列整体更有语义  | GSPO、sequence-level clipping       |
| 单 rollout 昂贵、group barrier 严重 | single-rollout actor–critic        |
| 稀疏终局奖励、需中间 credit             | PPO＋critic＋GAE                     |
| critic 可使用未来测试和失败诊断           | asymmetric PPO                     |
| 轨迹被 observation 切断            | skip-observation GAE               |
| 轨迹被 compaction 切段             | cross-segment/cross-trajectory GAE |
| 希望保留 groupwise 但消除长尾 barrier  | DORA 式多版本完整轨迹                      |
| 多个领域分别最优                      | specialist RL＋OPD/MOPD             |

这也意味着，面试或研究讨论中只问“PPO 与 GRPO 哪个更好”已经过于粗糙。应先问：

* group 是什么；
* rollout 成本多高；
* reward 在哪里产生；
* trajectory 是否被切段；
* critic 能看到什么；
* behavior policy 如何记录；
* system 如何处理旧轨迹。

---

## 2. 环境 scaling 出现“真实环境”和“学习型环境”两条路线

### 真实环境工厂

代表：

* ROCK；
* ROME；
* KAT AutoBuilder/KwaiClawEnv；
* Step 环境；
* LongCat 环境；
* UI-TARS VM；
* MiMo repository pods。

核心工作是恢复真实状态、依赖、测试、工具和失败分布。

### 学习型环境模拟器

代表：

* Qwen-AgentWorld；
* 部分 toolkit/MCP 模拟器；
* 可学习用户、浏览器或服务响应模型。

核心工作是从真实轨迹学习：

[
p(s_{t+1},o_t\mid s_t,a_t)
]

再批量生成训练经验。

未来真正困难的问题会变成：

* 如何检测 simulator exploitation；
* 如何量化模拟器与真实环境的分布差；
* 哪些 task 可完全模拟；
* 哪些 task 必须定期回到真实环境校准；
* world model 的不确定性如何进入 policy reward；
* 是否能主动生成 policy 最薄弱的反事实环境。

---

## 3. OPD 已成为能力整合层，而非单一蒸馏技巧

扩大搜索后，可以更清楚地把后训练拆成三个优化问题：

[
\underbrace{\text{发现能力}}*{\text{RL / exploration}}
\rightarrow
\underbrace{\text{搬运能力}}*{\text{OPD / MOPD}}
\rightarrow
\underbrace{\text{恢复与压缩}}_{\text{General-RL / preference / long-to-short}}
]

不同阶段的最优目标并不相同：

* specialist RL 追求某域能力上限；
* OPD 追求 student 分布上能力保持；
* General-RL 追求开放式多样性、风格和偏好；
* HMPO、long-to-short、shortest-correct distillation 追求单位 token 的能力。

这是比“最后做一次混合 RL”更接近 2026 年实践的结构。

---

## 4. 异步系统的分类必须细化

现在至少应区分：

### A. 阶段解耦但 batch 同步

Rollout、reward、training 分开部署，但每步仍存在 batch barrier。

### B. partial rollout

长轨迹在权重更新后继续，由新版本续写；需要：

* policy version metadata；
* importance correction；
* stale-aware sampling；
* KV re-prefill；
* 跨版本 trajectory 处理。

### C. stale complete trajectory

每条轨迹由单一旧版本完整生成，完成后仍可能用于新 policy 更新；SAO 类方法通过 (\pi_\theta/\pi_{\rm rollout}) 和 token mask 处理。

### D. 多版本共存

DORA 同时维护旧、新版本，每条轨迹保持版本纯度；用资源调度消除 bubble。

### E. 完全在线 evolution loop

AReaL 2.0 进一步把部署 workload、数据治理、policy update 和 harness evolution 接起来。

这些架构优化的是不同目标，不能只用“fully async”一个标签比较。

---

## 5. “自我演化”正在从模型算法问题变成实验操作系统问题

目前公开证据最强的 self-evolution 并不是“模型自主递归提升自身智能”，而是：

* 自动收集部署轨迹；
* 识别失败簇；
* 生成或筛选训练任务；
* 自动修改 prompt、工具或 scaffold；
* 决定是否更新 policy；
* 运行实验并比较；
* 将通过安全与回归门槛的版本重新部署。

AReaL 2.0 是 control-plane 方向；MiniMax M2.7 是 Agent 辅助实验与 scaffold 迭代；Qwen-AgentWorld 是模拟环境与反事实经验生产。

真正尚未公开解决的是：

* 防止线上反馈回路强化错误偏好；
* 防止低质量用户数据污染；
* 持续学习中的能力遗忘；
* 安全策略回退；
* 自动实验中的多重比较偏差；
* 模型发现 reward 漏洞后的自动阻断；
* 谁拥有最终上线权限。

---

# 七、对原回答八段因果链的具体补丁

## 1. 能力定义与测量

新增：

* Step-DeepResearch 的 atomic capability 与 ADR-Bench；
* Qwen-AgentWorld 的 AgentWorldBench；
* KAT 的 harness-level 泛化；
* Intern-S2 的 scientific long-horizon Agent；
* Mach-Mind 的 token-efficiency 目标。

关键更新：

> 能力评测正从“任务成功率”进一步扩展到跨 scaffold、环境 fidelity、报告 rubric、并行延迟和单位 token 成本。

## 2. 经验、数据、任务与环境生产

新增：

* Qwen-AgentWorld 的 10M+ 真实交互轨迹和学习型环境；
* KAT AutoBuilder/KwaiClawEnv；
* AReaL 2.0 的部署 workload 数据代理；
* Mach-Mind 多 scaffold Agent 环境；
* Pangu Embedded 的 prioritized rollout queue。

## 3. 教学信号与 credit assignment

新增：

* Step-DeepResearch 的 rubric terminal reward＋critic；
* KAT hindsight critic；
* VAPO 的 value pretraining；
* DeepSeek-GRM 的 SPCT 和 reward inference scaling；
* Qwen-AgentWorld 的 simulator fidelity reward；
* Pangu 的 deterministic＋LLM 混合 reward。

## 4. 策略改进与能力整合

新增：

* GSPO 与 Qwen3 的直接连接；
* ERNIE 5.1 的四阶段 MOPD pipeline；
* MiMo 独立 MOPD 论文；
* Mach-Mind routed MOPD＋HMPO；
* Step-DeepResearch PPO；
* KAT asymmetric PPO。

## 5. Agent 接口

新增：

* Qwen3.6 的 thinking preservation；
* KAT harness randomization；
* Kimi-Dev 从 agentless skill prior 向 Agent 迁移；
* AReaL 2.0 同时演化 weights 与 in-context harness 的设计目标。

## 6. 扩展、系统正确性与经济性

新增：

* DORA 多版本完整轨迹；
* ERNIE R3 和统一 FP8；
* AReaL 2.0 在线控制面；
* Relax 的 service-decoupled async RL；
* Mach-Mind 动态多 teacher 调度；
* Pangu Embedded 的 stale synchronous parallel。

## 7. 底座约束

新增：

* Qwen GSPO 对 MoE RL 稳定性的直接动机；
* ERNIE Router Replay；
* Intern-S2 的共享权重 MTP 与科学多模态；
* Mach-Mind 仅 3B activated 下的后训练经济性；
* Pangu Embedded 在昇腾上的系统约束。

## 8. 实验科学与表达

新增：

* MOPD 与 Mix-RL、Cascade、off-policy、merge 的直接对照；
* Step 明确解释为何选择 critic；
* KAT 公开 verifier flipping 和反馈修复；
* DORA 同时报告吞吐与 convergence；
* AgentWorld 同时比较真实环境与模拟环境训练。

---

# 八、最值得补入知识库的“问题驱动材料束”

这不是课程顺序，而是对原材料库的增量补充。

## 材料束 1：为什么长程 Agent 中 critic 又回来了？

一起阅读：

* GLM-5 报告；
* GLM-5.2 博客；
* **SAO**，2026-07；
* **CompactionRL**，2026-07；
* **Step-DeepResearch**；
* **KAT-Coder-V2.5**；
* **VAPO**；
* **UI-TARS-2**。

比较问题：

* group barrier 与 credit assignment 哪个是主要动机；
* critic 是普通 value model 还是 asymmetric critic；
* observation、compaction、子 Agent 边界如何处理；
* critic 预训练和更新频率；
* actor/critic 是否共享 backbone；
* PPO 增益是否来自 value，还是来自其他稳定机制。

---

## 材料束 2：group-relative 方法如何在长轨迹中继续生存？

一起阅读：

* Qwen **GSPO**；
* Tongyi DeepResearch；
* LongCat-2601；
* **DORA**；
* DAPO；
* Step 3.5 的 MIS-PO。

比较问题：

* ratio 在 token 还是 sequence 层；
* group 是否必须来自同一 prompt；
* 长尾样本是否被丢弃；
* 一条轨迹是否跨 policy version；
* staleness 上界；
* group normalization 在异长轨迹中是否有偏；
* MoE routing mismatch 如何影响 ratio。

---

## 材料束 3：从真实环境到语言世界模型

一起阅读：

* **Qwen-AgentWorld**；
* ROCK；
* ROME；
* KAT AutoBuilder/KwaiClawEnv；
* UI-TARS-2；
* MiMo repository environments；
* LongCat environments。

比较问题：

* 环境是真实执行、模拟服务还是学习型 world model；
* verifier 是否独立于 simulator；
* 如何测量 transition fidelity；
* simulator exploitation；
* 如何混合 real RL 与 simulated RL；
* 世界模型是否只做环境，还是同时作为 policy warm-up。

---

## 材料束 4：多专家能力如何真正进入一个部署模型？

一起阅读：

* DeepSeek V4 multi-teacher OPD；
* GLM-5 cross-stage OPD；
* **MiMo MOPD 论文**；
* **ERNIE 5.1**；
* KAT V2.5；
* Ling/Ring 2.6；
* **Mach-Mind-4-Flash**。

比较问题：

* student 自采样还是 teacher trajectory；
* reverse KL 是否 top-k 截断；
* 多 teacher 冲突如何 routing；
* teacher 是否并行更新；
* 开放式高熵任务为何不适合 OPD；
* OPD 后是否再做 General-RL；
* 能力搬运与能力上限的区别。

---

## 材料束 5：异步 RL 的“正确性”到底由什么定义？

一起阅读：

* slime；
* SAO；
* DORA；
* AReaL / AReaL 2.0；
* RollArt；
* ERNIE 5.1 R3；
* MiMo-V2-Flash；
* Relax；
* verl rollout correction。

比较问题：

* behavior log-prob 从哪里来；
* token 是否重新分词；
* MoE 路由是否重放；
* trajectory 是否跨版本；
* staleness 是 token、trajectory 还是 model-version 粒度；
* crash 后是否导致 length-dependent sampling bias；
* KV cache 是否可恢复；
* throughput 提升是否牺牲有效样本率。

---

## 材料束 6：verifier 本身如何被训练、扩展和攻击？

一起阅读：

* DeepSeek-GRM；
* DeepSeek-Math-V2；
* DeepSeek-Prover-V2；
* MiniMax MaxProof；
* KAT V2.5；
* Qwen-AgentWorld；
* Step-DeepResearch rubric judge。

比较问题：

* 程序 verifier、GRM、rubric 和 human judge 的职责边界；
* verifier inference-time scaling；
* meta-RM；
* reward hacking；
* judge 长度偏好；
* feedback flipping；
* verifier 与 actor 是否共享模型；
* verifier 改善是否真的提高最终任务成功率。

---

## 材料束 7：从离线后训练到部署后的 Agent evolution

一起阅读：

* AReaL 2.0；
* AEnvironment；
* Awex；
* MiniMax M2.7；
* Qwen-AgentWorld；
* ERNIE 5.1 fully async controller。

比较问题：

* 部署轨迹如何转为训练数据；
* 谁决定更新 weights，谁决定更新 harness；
* 线上分布与安全治理；
* 回归测试；
* continual learning 与周期性 retraining 的区别；
* 自动实验是否会优化错误代理指标。

---

# 九、目前仍不能从这些伴生材料中得出的结论

扩大搜索提高了时效性，但仍有边界。

1. **不能根据同一团队发表某个算法，就自动断定最新旗舰使用了它。**例如 VAPO 不能直接等同于 Seed2.1 配方，DeepSeek-GRM 不能直接等同于 V4 的 GRM checkpoint，DRIVE-RLVR 不能直接等同于 Hy3 的完整 coding RL。

2. **框架支持不等于生产使用。**verl、ROLL、AReaL、slime、Forge 支持某算法，只说明它在公开系统中可实现。

3. **同一 Lab 的专项模型可能故意采用不同路线。**Kimi-Dev、Kimina-Prover、K2.5 不应被压成一个“Moonshot optimizer”。

4. **模型卡中的“大规模 RL”不能代替技术报告。**Qwen3.5/3.6、Intern-S2、Seed2.1、Kimi K3、MiniMax M3 等最新模型仍有大量配方空白。

5. **OPD 的使用不代表各 teacher 的训练方式已经公开。**ERNIE 5.1 明确说不同专家可使用定制算法，却没有逐个披露。

6. **吞吐倍数不能直接横比。**DORA、AReaL、RollArt、Step FullyAsync、Relax 的模型、硬件、任务长度、异步语义和 baseline 不同。

7. **所谓 self-evolution 仍普遍缺少长期在线证据。**现有材料多是架构、短周期实验或 Agent 辅助研究流程，而非长期稳定、全自动 continual learning。

---

# 十、基于证据的岗位能力推断

以下明确属于从公开路线推导出的岗位能力，而不是团队公开的招聘要求。

## Post-training researcher

越来越需要能够根据任务结构选择，而不是机械套用 PPO/GRPO：

* 判断 group baseline 是否有意义；
* 设计 critic、GAE 和 hindsight information；
* 分析 policy ratio、clipping 与 entropy；
* 设计 specialist RL 和 OPD/MOPD；
* 处理长短推理与 token efficiency。

## Agent data/environment researcher

核心能力已经从“生成 instruction 数据”升级为：

* 仓库、GUI、搜索和工具环境恢复；
* 可验证任务生成；
* environment lifecycle；
* simulator/world model；
* reward-hacking 测试；
* harness randomization；
* real/sim mixed curriculum。

## RL systems / research engineer

当前公开路线直接要求：

* rollout/trainer/reward/agent-loop 解耦；
* policy-version 管理；
* log-prob 和 token identity；
* MoE routing replay；
* FP8/BF16 一致性；
* KV cache 迁移与恢复；
* staleness 控制；
* sandbox CPU 调度；
* 有效样本率和单位成功成本分析。

## Evaluation/verifier researcher

需要同时理解：

* deterministic verifier；
* rubric；
* GRM/ORM；
* critic；
* meta-evaluation；
* 过程诊断；
* reward hacking；
* benchmark/harness dependence；
* 人类偏好与可执行成功之间的差异。

---

# 综合判断

经过第二轮扩大检索，原来的主结论应升级为：

> **中国基座模型团队的后训练正在从“每个模型拥有一套统一 RL 配方”，演化为“一个 Lab 内部维护多个任务化专家训练分支，再由 OPD/MOPD、统一 RL、偏好优化和推理压缩构成能力整合层”。**

与此同时，Agent RL 的技术分歧越来越由以下因素决定：

[
\text{轨迹长度与分段}
+
\text{环境成本}
+
\text{奖励延迟}
+
\text{critic 可获得的信息}
+
\text{MoE/低精度一致性}
+
\text{异步系统语义}
]

而不是由 PPO、GRPO、GSPO 等名称本身决定。

本轮最值得立即补入原回答的材料是：

* **ERNIE 5.1**：完整补出完全异步、R3、MOPD 和 General-RL；
* **Qwen-AgentWorld**：补出语言世界模型作为 Agent 环境的新路线；
* **Step-DeepResearch**：补出长程开放研究任务选择 critic PPO 的直接理由；
* **KAT-Coder-V2.5**：补出 hindsight asymmetric critic 和环境可靠性；
* **DORA**：补出保留 groupwise 的多版本异步替代方案；
* **MiMo MOPD 独立论文**：把能力整合从主张升级为可比较算法；
* **AReaL 2.0**：补出部署 workload 驱动的在线 Agent evolution；
* **Mach-Mind-4-Flash**：补出专家 RL→MOPD→token 压缩的独立完整案例；
* **Intern-S2-Preview-397B**：更新科学多域和 black-box long-horizon Agent RL 的最新方向；
* **Pangu Embedded**：修正“盘古没有公开后训练路线”的过宽表述；
* **Kimi-Dev、Kimina-Prover、DeepSeek-GRM**：揭示旗舰报告之外的专项能力与 verifier 路线。

这些材料共同证明：**技术报告只是路线图的骨架；要得到接近当前真实实践的判断，必须把同团队的专项模型、算法论文、系统论文、环境仓库和最新模型卡组织成有证据等级的时间序列。**

[1]: https://github.com/QwenLM/Qwen3.6 "GitHub - QwenLM/Qwen3.6: Qwen3.6 is the large language model series developed by Qwen team, Alibaba Group. · GitHub"
[2]: https://arxiv.org/abs/2507.18071 "[2507.18071] Group Sequence Policy Optimization"
[3]: https://arxiv.org/html/2512.20491v4 "Step-DeepResearch Technical Report"
[4]: https://arxiv.org/abs/2607.05471 "[2607.05471] KAT-Coder-V2.5 Technical Report"
[5]: https://arxiv.org/abs/2504.05118 "[2504.05118] VAPO: Efficient and Reliable Reinforcement Learning for Advanced Reasoning Tasks"
[6]: https://arxiv.org/abs/2604.26256 "DORA: A Scalable Asynchronous Reinforcement Learning System for Language Model Training"
[7]: https://ernie.baidu.com/blog/posts/ernie-5.1-0508-release/ "ERNIE 5.1 Officially Released! Topping Multiple Leaderboards — A Model That Writes Better and Understands You More | ERNIE Blog"
[8]: https://arxiv.org/html/2510.24701 "Tongyi DeepResearch Technical Report"
[9]: https://arxiv.org/html/2603.00729 "https://arxiv.org/html/2603.00729"
[10]: https://arxiv.org/abs/2606.24597 "[2606.24597] Qwen-AgentWorld: Language World Models for General Agents"
[11]: https://arxiv.org/abs/2606.30406 "[2606.30406] MOPD: Multi-Teacher On-Policy Distillation for Capability Integration in LLM Post-Training"
[12]: https://huggingface.co/XiaomiMiMo/MiMo-V2.5 "XiaomiMiMo/MiMo-V2.5 · Hugging Face"
[13]: https://arxiv.org/abs/2607.01120 "[2607.01120] Next-Generation Agentic Reinforcement Learning Systems Enable Self-Evolving Agents"
[14]: https://arxiv.org/abs/2607.09375 "[2607.09375] Mach-Mind-4-Flash Technical Report"
[15]: https://github.com/MoonshotAI/Kimi-Dev "GitHub - MoonshotAI/Kimi-Dev: open-source coding LLM for software engineering tasks · GitHub"
[16]: https://github.com/MoonshotAI/Kimina-Prover-Preview "GitHub - MoonshotAI/Kimina-Prover-Preview: Technical report of Kimina-Prover Preview. · GitHub"
[17]: https://arxiv.org/abs/2504.02495 "[2504.02495] Inference-Time Scaling for Generalist Reward Modeling"
[18]: https://huggingface.co/internlm/Intern-S2-Preview-397B "internlm/Intern-S2-Preview-397B · Hugging Face"
[19]: https://arxiv.org/html/2605.26494 "The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence"
[20]: https://arxiv.org/abs/2505.22375 "Pangu Embedded: An Efficient Dual-system LLM Reasoner with Metacognition"


# Kimi K3 技术报告：后训练路线的完整拆解

这份报告显著改变了上一轮审计中对 Kimi K3 的证据评级。此前只有发布博客时，K3 的后训练大致只能评为 **B/C 级：已知能力与方向，但不知道训练机制**。现在可以提升到 **A−级**：

* 公开了 SFT → 专家 RL → MOPD 的完整主干；
* 公开了三个领域、三个 reasoning-effort 档位和九个专家；
* 公开了 partial rollout、陈旧轨迹处理、预算控制、GRM 和 MOPD 公式；
* 公开了任务生产、Agent harness、verifier、sandbox 和 1M context RL 基础设施；
* 但仍缺少数据量、任务比例、关键超参数、组件消融和训练总成本，因此还不能称为可复现配方。

术语上，**“开放权重”比“完全开源”更准确**：K3 已发布完整模型权重，但没有发布完整训练数据、RL 环境全集、GRM、九个专家 checkpoint 或训练脚本。模型本身是 2.8T 总参数、104B 激活参数、原生视觉、1M context；报告把 reinforcement learning across general、agentic、coding domains 与 persistent rollout/sandbox state 列为核心贡献。 官方模型卡也明确称其为 open-weight model。([Hugging Face][1])

至于“当前最强开放权重模型”，较严谨的表述是：

> **Kimi K3 是首个公开权重的 3T 级模型，并且在报告采用的综合评测套件里，是当前最强的一组开放权重模型之一；但它自己也明确承认总体能力仍落后于最强的专有模型。**

它在不少 coding、agentic 和 multimodal benchmark 上领先，但最终强弱仍受 harness、reasoning effort、预算和评测选择影响，不能只靠一张总榜绝对化。

---

# 一、最核心的技术结论

K3 的后训练不是“又一个 GRPO 模型”，也不是像 GLM-5.2 那样为长程 Agent 全面转向 critic PPO。它的主线更准确地概括为：

> **保留 K2.5 的多 rollout、group-relative、无 critic 策略优化；用 partial rollout 和 token-level trust region 处理超长轨迹及 policy lag；把任务拆成 3 个领域 × 3 个 reasoning-effort 专家；最后用 MOPD 将九个专家统一进一个 effort-conditioned 模型。**

完整因果链是：

```text
原生多模态、1M-context K3 Base
          ↓
SFT 冷启动
此前 Kimi 专家生成轨迹
+ 多阶段验证
+ 人工参与标注
+ XTML Agent 格式
+ 从 SFT 起即进行 MXFP4/MXFP8 QAT
          ↓
专家 RL
3 个领域 × 3 个 reasoning-effort = 9 个专家
          │
          ├─ general tasks
          ├─ general agents
          └─ coding agents
          │
          ├─ K-rollout group-relative policy optimization
          ├─ partial rollout 跨 iteration 暂停与恢复
          ├─ token-level off-policy regularization
          ├─ verifiable rewards / GRM
          └─ per-problem reasoning budget curriculum
          ↓
收集各专家、各 effort 的轨迹
用于监督式能力回灌和 MOPD
          ↓
Multi-Teacher On-Policy Distillation
根据 domain × effort 选择对应 teacher
在 student 自己访问的状态上提供逐 token 稠密奖励
          ↓
统一的 Kimi K3
通过 natural-language option 控制 low / high / max effort
          ↓
部署感知后训练
全程量化感知 + EAGLE-3 draft model fine-tuning
```

其中“专家轨迹用于 supervised fine-tuning 和 MOPD”的准确顺序、是否存在一个正式的中间 SFT 阶段、SFT 与 MOPD 的数据比例，报告没有写清，不能补成确定配方。

---

# 二、SFT：不是普通指令微调，而是 Agent RL 的冷启动层

## 1. 数据从哪里来

K3 的 SFT 数据主要由**此前 Kimi 系列中的领域专用模型生成复杂 Agent 轨迹**，再经过：

1. 多阶段验证；
2. human-in-the-loop 标注；
3. XTML 格式统一；
4. 从 SFT 阶段就开始进行量化感知训练。

报告称，这一数据集用于建立：

* adaptive reasoning；
* 精确 tool calling；
* 长程 Agent 场景下的稳健执行。



这说明 K3 的 SFT 有两个不同于传统 instruction tuning 的目标。

第一，它不是主要教授“回答内容”，而是在教一个初始 Agent policy：

[
\text{reason}
\rightarrow
\text{call tool}
\rightarrow
\text{read observation}
\rightarrow
\text{continue}
\rightarrow
\text{terminate}
]

第二，它承担的是 **RL action-space activation**。在 RL 开始前，模型必须已经能够：

* 生成格式正确的工具调用；
* 处理工具结果；
* 遵守不同 harness 的协议；
* 在多轮中维持任务状态；
* 选择 thinking、response、tools 等不同输出通道。

否则早期 rollout 大量失败，终局奖励接近全零，RL 很难启动。

## 2. 两种不同的“教师使用方式”

K3 实际上使用了两类教师：

### 离线轨迹教师

旧 Kimi 专家生成完整轨迹，经过验证和人工筛选后用于 SFT。

它主要解决：

* student 是否拥有基本动作；
* student 是否进入合理状态分布；
* 工具格式和长程执行能否冷启动。

### 在线分布教师

九个 RL 专家随后作为 MOPD teacher，在 student 自己生成的 prefix 上给出逐 token 信号。

它主要解决：

* 如何把九个专家统一进一个模型；
* 如何避免只模仿 teacher 的离线成功轨迹；
* student 偏离 teacher 轨迹后，仍能在自己实际访问的状态上被纠正。

这体现了一个越来越清晰的生产范式：

[
\text{SFT 负责建立策略支持集}
\quad\rightarrow\quad
\text{RL 负责发现更强策略}
\quad\rightarrow\quad
\text{MOPD 负责稠密搬运策略}
]

## 3. 报告没有告诉我们的内容

SFT 部分没有公开：

* 样本总数和 token 总数；
* general、coding、Agent、vision 的比例；
* 成功轨迹与失败轨迹比例；
* 是否包含真实用户数据；
* 是否继续采用 K2.5 的 zero-vision SFT；
* 人工标注具体修改了哪些部分；
* 训练 epoch、学习率、packing 和长度分布；
* 安全、拒绝、偏好和风格数据的独立构成。

尤其不能直接假定 K2.5 的 zero-vision SFT 原样延续到 K3。K2.5 明确使用纯文本 SFT 激活视觉 Agent，并发现人工构造的视觉轨迹反而伤害泛化；K3 只说扩展了复杂 Agent 轨迹，没有说明这些轨迹是否含视觉数据。([arXiv][2])

---

# 三、专家 RL：三个领域乘以三个 effort，形成九个 policy

K3 不为每一个 benchmark 单独训练专家，而是把任务归纳成三个较大的后训练域。

| 专家域            | 报告列出的主要任务                                        |
| -------------- | ------------------------------------------------ |
| General tasks  | 通用体验、视觉、推理、faithfulness、搜索、知识工作                  |
| General agents | 长程 assistant、deep research、段落级写作                 |
| Coding agents  | SWE、coding experience、GPU kernel、web development |

每个领域再训练：

[
e\in{\text{low},\text{high},\text{max}}
]

三个 reasoning-effort 版本，因此共有：

[
3\text{ domains}\times3\text{ effort levels}=9\text{ experts}
]



## 1. 为什么不是一个模型直接做混合 RL

报告没有提供“九专家训练 vs 一个模型 joint RL”的正式消融，但从系统设计可以推断它在解决三个问题。

### 奖励尺度不同

* 数学可以是 0/1 答案；
* kernel 是 correctness gate 加性能分数；
* web development 包含 build、功能、像素、model judge；
* knowledge work 可能依赖 rubric；
* personal assistant 由多个事件级 verifier 组成。

把这些奖励直接混在同一个 online RL batch 中，很容易出现某些域梯度占优。

### 探索预算不同

* 一般推理可能只有数千 thinking tokens；
* coding 可能有数百工具轮；
* personal assistant 可以持续多个模拟日、数千次工具调用；
* kernel 优化需要反复 profile、修改和 benchmark。

同一个 rollout scheduler 和同一组 budget 超参数不一定适用于所有领域。

### effort 是一个独立能力轴

K3 不只是训练“能力最强的 max policy”，再在推理时人为截短。它显式训练了低、高、最大三个策略区域，最后再让统一 student 学会根据 effort option 切换。

所以 K3 的九专家矩阵其实是：

[
\text{能力域}
\times
\text{推理成本档位}
]

而不是普通的三个领域专家。

## 2. 图 8 应该如何读

报告第 13 页图 8 同时绘制了 RL FLOPs、任务得分和平均 assistant steps。随着 RL FLOPs 增加，多数任务的得分和工具调用步数一起上升，包括 coding experience、general tool use、web development、agentic search、professional workflow、office deliverables、视觉图表和视觉谜题。

这幅图支持：

> **RL 不只是让已有轨迹更准确，也在让模型学会执行更深、更长的交互策略。**

但它不支持“模型同时变得更高效”。因为平均步骤也在增长。更可能的过程是：

1. 先通过 max-effort RL 学会投入更多行动解决困难任务；
2. 再通过 effort curriculum 把能力压缩到 high 和 low；
3. 最终得到一条可控的质量—成本前沿。

图 8 没有给出数值坐标、置信区间、随机种子或同计算量基线，因此它是**训练趋势证据**，不是严格 scaling-law 结论。

---

# 四、K3 到底使用了什么 RL 算法

这是报告中最需要仔细拼接的一点。

K3 报告没有重新写完整 policy loss，而是明确说：

> 当同一 prompt 的全部 (K) 条响应完成后，将它们送入 policy optimization；优化算法沿用 Kimi K2.5。



因此需要回到 K2.5 官方报告补全。

## 1. K2.5 的公开目标

对每个问题 (x)，旧策略生成 (K) 条轨迹：

[
y_1,\ldots,y_K
]

组内优势为：

[
A_j
===

## r(x,y_j)

\frac{1}{K}\sum_{\ell=1}^{K}r(x,y_\ell)
]

每个 token 的概率比为：

[
\rho_{j,t}
==========

\frac{
\pi_\theta(y_{j,t}\mid x,y_{j,<t})
}{
\pi_{\mathrm{old}}(y_{j,t}\mid x,y_{j,<t})
}
]

依据 K2.5 对目标函数的文字解释，可以将它概念化为：

[
L
\approx
\frac{1}{\sum_j|y_j|}
\sum_{j,t}
\left[
m(\rho_{j,t})\rho_{j,t}A_j
--------------------------

\tau(\log\rho_{j,t})^2
\right]
]

其中 (m(\rho)) 是 token-level trust-region mask：token 的新旧 log-ratio 超出允许范围时，梯度直接归零。K2.5 明确说这不同于标准 PPO 的 advantage-sign-dependent clipping，它只根据策略偏离程度决定是否学习。([arXiv][2])

## 2. 它与标准 GRPO 的相同点和不同点

### 相同点

* 每个 prompt 需要多个 rollout；
* 使用组内平均 reward 作为 baseline；
* 不需要显式 value critic；
* 一条轨迹的终局 reward 被用于其所有生成 token。

### 不同点

它不是最原始的 canonical GRPO：

* 没有公开使用组内 reward 标准差归一化；
* 使用总生成 token 数归一化，而不是简单的 sequence mean；
* 使用严格 token-level mask；
* 额外加入 squared log-ratio regularization；
* 使用 MuonClip 更新参数。

因此，最准确的称呼不是简单写“GRPO”，而是：

> **critic-free、group-relative、K-sample policy optimization，配合 token-level trust-region masking 和 log-ratio regularization。**

## 3. K3 没有公开 critic、value model 或 GAE

K3 的报告中没有出现：

* value network；
* value pretraining；
* TD target；
* GAE；
* critic loss；
* actor–critic 参数共享；
* step-level 或 token-level value。

同时又明确写明“follows the algorithm in Kimi K2.5”。所以当前最强证据指向：

> **K3 专家 RL 仍沿用无 critic 的 group-relative 路线，而不是 SAO 式 critic PPO。**

严格说，不能排除内部存在未披露的任务特定变体；但仅凭这份报告，没有理由把 K3 补写成 PPO/critic。

## 4. 这种目标的 credit assignment 有什么特点

同一轨迹 (y_j) 中的所有 token 大致共享 (A_j)。所以它能回答：

> 这条完整轨迹相对于同 prompt 的其他轨迹更好吗？

但很难直接回答：

> 数百轮之前的某次搜索、某条命令、某次计划修改，对最终结果贡献了多少？

此外，总 token 归一意味着一条更长的轨迹包含更多训练 token，因而可能贡献更多累计梯度。K3 后面的预算控制和 verbosity penalty 并不是附属技巧，而是在抵消这种“成功但无限变长”的优化诱因。

---

# 五、Partial rollout：K3 如何训练百万 token Agent 轨迹

K3 的 partial rollout 继承自 k1.5 和 K2.5，但扩展到 Agent 环境和 1M context。

设每一轮有：

* (N) 个 prompt；
* 每个 prompt 采 (K) 条轨迹；
* 总共 (NK) 条 active trajectories。

传统同步训练要等所有轨迹完成。K3 改为：

1. 当完成的轨迹达到 (\lambda NK) 时，暂停 rollout 阶段；
2. 已完成并且同 prompt 下 (K) 条都齐全的 group 进入训练；
3. 未完成轨迹进入优先队列；
4. 下一 iteration 从原状态恢复；
5. 一条超长轨迹可以跨越多个 policy update。



## 1. 它消除了什么 barrier

它消除了**全局 batch barrier**：

* 不再等整个 batch 的最慢轨迹；
* 已经完成的 prompt group 可以先训练；
* 极慢任务继续留在下一轮。

## 2. 它没有消除什么 barrier

它仍保留了**每个 prompt 内的 group barrier**：

> 只有同一 prompt 的全部 (K) 条响应完成，才能计算组内平均 reward 并进入训练。

因此它与 GLM SAO 的 single-rollout 有本质区别。K3 是：

[
\text{部分异步}
+
\text{保留 group}
]

而 SAO 是：

[
\text{异步}
+
\text{取消 group}
+
\text{critic baseline}
]

## 3. 为什么会产生极端 off-policy

若某条轨迹持续多个 iteration：

* 前半段可能由较旧 policy 生成；
* 中间 trainer 已经更新若干次；
* 后半段可能在新权重下恢复；
* 最终整条轨迹才产生 reward。

K3 报告承认，这形成了 highly stale / extreme off-policy regime，并说 K2.5 的 per-token regularization 通过限制策略更新到局部邻域来维持稳定。

但报告没有说明几个决定算法正确性的关键问题：

* 一条恢复轨迹是否允许跨多个 rollout-policy version；
* 每个 token 保存的是哪个 behavior-policy log-prob；
* denominator 使用生成该 token 的准确 policy，还是某个统一 old policy；
* 已有 KV cache 与更新后的模型权重是否兼容；
* 恢复时是否重新 prefill；
* 最大允许 staleness；
* 被 mask 的 token 比例；
* 旧轨迹何时被丢弃。

因此，K3 已经公开了调度骨架，但没有完全公开 off-policy estimator。

---

# 六、Reasoning-effort RL：把测试时计算变成一个受训练的条件变量

K3 的 effort control 不只是给模型一个“请少想一点”的 prompt。

对每个问题 (x)，冷启动模型先估计一个基准预算：

[
b_0(x)
]

如果轨迹使用的预算 (T(y)) 超过：

[
\tau b_0(x)
]

则无论任务结果怎样，reward 都被强制改为：

[
-1
]

对于不同任务，(T(y)) 的定义不同：

* general task：thinking token 数；
* agentic task：模型累计输出 token，包括 reasoning trace 和 tool-call arguments。

训练先从较大的 (\tau) 开始得到 max-effort 专家，同时仍设上限防止无限 overthinking；再逐步缩小 (\tau)，分别得到 high 和 low 专家。不同领域的 (\tau) 在 human-in-the-loop 指导下设定。

## 1. 为什么它比固定 token limit 更合理

同样的固定预算对不同问题并不公平：

* 简单问题 20K token 过多；
* 难题 20K token 可能不足；
* coding Agent 的 tool arguments 远长于纯数学推理；
* kernel 优化和 deep research 的正常行动长度完全不同。

相对预算：

[
T(y)\leq \tau b_0(x)
]

至少让限制依赖问题难度。

## 2. 为什么先训 max，再向下压缩

它大致采用：

[
\text{先发现强策略}
\rightarrow
\text{再压缩执行成本}
]

而不是从一开始就强迫模型短答。

这与 K2.5 的 Toggle 思想连续，但实现不同。K2.5 在 budget-limited phase 与 unrestricted scaling phase 之间交替，以避免长度过拟合；K3 报告公开的是 max → high → low 的 stage-wise curriculum 和多个 effort expert，没有说明 Toggle 是否仍在内部使用。([arXiv][2])

## 3. 预算仍不等于完整执行成本

Agent 预算只统计模型输出：

* thinking；
* response；
* tool-call arguments。

它没有明确统计：

* 工具 observation 输入 token；
* sandbox CPU/GPU 时间；
* 搜索、编译和测试 wall-clock；
* 子 Agent 计算；
* KV cache 占用；
* API 调用成本。

因此，这更接近 **model-output token efficiency**，而不是完整的：

[
\text{cost per successful task}
]

## 4. effort 如何进入最终模型

MOPD 中 student 显式条件于 effort (e)。推理时，XTML 把 reasoning effort 表示成一条 natural-language global option，而不是特殊的预算 token。

报告中还有一个小的不一致：

* 训练正文写 low / high / max；
* chat schema 预留 low / medium / high / max，称 K3 只支持其中一个子集；
* 第 32 页 BrowseComp 成本图出现 medium / high / max；
* Kimi Code 图则是 low / high / max。

报告没有解释 medium 与 low 的对应关系或产品版本差异，不能自行合并。

---

# 七、奖励系统：K3 不是使用一个统一 reward model

K3 的 reward 架构是多层组合，而不是“所有任务都交给一个 GRM”。

## 1. 可程序验证任务

对搜索、代码、kernel、AET 和部分专业工作流，尽量使用：

* 测试；
* 执行结果；
* 最终环境状态；
* 数值误差；
* 性能指标；
* hidden verifier。

其基本原则是：

[
\text{模型声称完成}
\neq
\text{任务完成}
]

最终 reward 要落在环境结果上。

## 2. Agentic Generative Reward Model

对不易直接验证的通用任务，使用 tournament-style group reward：候选之间进行二元比较。

judge 必须按固定协议：

1. 阅读结果、产物或文本；
2. 生成 rubric；
3. 按 rubric 评价候选；
4. 将各项分数写入 scorepad。

为防止 reward model 偏爱长输出，系统从冷启动模型估计基准长度 (\ell_0)。若候选超过：

[
\sigma\ell_0
]

则自动输掉二元比较。

这比直接让 judge 输出一个总分多了两个约束：

* judge 必须先显式定义标准；
* verbosity 不能成为容易利用的代理特征。

但报告没有公开：

* GRM 的基础模型；
* 训练数据；
* 是否与 actor 同源；
* rubric 的覆盖范围；
* pair order 随机化；
* calibration；
* judge disagreement；
* 对 length、style、self-preference 的系统消融。

## 3. GPU kernel reward

kernel 任务是报告里 reward engineering 最具体的部分。

任务覆盖：

* CUDA；
* Triton；
* CuTe DSL；
* Gluon；
* ThunderKittens；
* TileLang；
* BF16、FP8、FP4；
* 单算子到 fused mega-kernel。

奖励先做 correctness gate：

[
\text{数值误差超阈值}
\Rightarrow
r=0
]

通过后，性能与专家实现比较：

* 达到专家实现约为 0.5；
* 逐步接近 hardware roofline 时，reward 向 1 增长。

团队还专门检测：

* CUDA graph replay；
* input caching；
* 非法降低精度；
* 其他训练中实时发现的新投机策略。



这里真正重要的不是具体分数，而是：

> **verifier 不是训练前一次性写完的；Agent 会持续发现新漏洞，因此 verifier 必须随训练共同演化。**

## 4. Personal assistant 与 living environments

团队为 Gmail、Notion、Slack、Canvas 等应用制作 mock implementation。任务可以跨越多个模拟日，包含多个应用中的相互依赖事件；一条 rollout 最长可达数千次 tool call 和数百万累计 context token。每个事件由确定性规则或 LLM evaluator 评价。

这里优化的不是一个静态答案，而是：

[
\text{world state}*{0}
\rightarrow
\text{events}
\rightarrow
\text{agent actions}
\rightarrow
\text{world state}*{T}
]

mock app 的优点是可复现、无 API rate limit；缺点是与真实应用存在 simulator gap。报告没有公开 mock 与真实应用的一致性审计。

## 5. Autonomous Execution Tasks

AET 给模型：

* 初始状态；
* 受约束目标；
* 工具动作空间；
* 执行预算；
* verifier interface。

不给：

* reference trajectory；
* 预定义过程；
* 标准计划。

模型必须自主进行任务分解、工具选择、规划、错误恢复和终止。奖励基于最终环境状态。防投机设计包括：

* Agent 与 verifier 隔离；
* public verifier 提供诊断反馈；
* hidden verifier 检查 held-out 场景；
* 限制提交次数；
* 失败提交产生 penalty。



这是很成熟的 verifier 结构：

[
\text{public feedback}
\neq
\text{最终评分真值}
]

模型可以从公开反馈中学习，但不能直接针对全部隐藏测试优化。

## 6. Web development reward

web development 同时使用：

* build 是否成功；
* runtime error；
* 功能测试；
* 结构相似；
* 像素相似；
* 内部 reward model 查看源代码；
* reward model 直接与产物交互。

若项目无法构建、运行错误，或者只是伪造视觉结果而没有真正实现，reward 归零。

---

# 八、K3 的长程 credit assignment 其实仍然较粗

K3 拥有丰富的 verifier 和多步环境反馈，但要区分两件事：

### 环境能够指出进展

例如：

* 编译错误；
* 单元测试结果；
* verifier 反馈；
* benchmark performance；
* 搜索结果；
* 用户事件。

这些会作为下一步 observation 帮助 Agent 调整行为。

### RL optimizer 如何把最终收益归因给早期 token

公开的 K2.5/K3 group-relative objective，仍主要把整条轨迹 reward (A_j) 分配给所有生成 token，没有公开 value-based temporal credit。

因此：

> **更丰富的环境 feedback 改善了在线决策状态，但不自动等于更细粒度的 policy-gradient credit assignment。**

K3 的一种可能解决方式——这是基于结构的推断，不是报告明说——是把“能力发现”和“稠密学习”拆开：

1. 专家 RL 用可靠但较粗的 outcome/group reward 探索；
2. 成功专家形成更好的 token distribution；
3. MOPD 再把专家分布转成逐 token 稠密奖励；
4. unified student 在自己访问的状态上学习。

也就是说，K3 没有像 GLM SAO 那样依赖 critic 给早期行为估值，而是更多依靠：

[
\text{outcome RL}
+
\text{expert teacher}
+
\text{dense on-policy distillation}
]

不过 MOPD 只能搬运 teacher 已经学会的行为，不能从根本上恢复 teacher RL 阶段缺失的时间因果信息。

---

# 九、MOPD：这份报告最关键的算法升级

九个专家最终必须合成一个可部署模型，否则需要维护：

* 三个领域模型；
* 每个领域三个 effort；
* 共九套 2.8T 权重。

K3 使用 Multi-Teacher On-Policy Distillation。

## 1. teacher 如何选择

训练样本具有领域 (d)，并采样 effort：

[
e\in{\text{low},\text{high},\text{max}}
]

对应 teacher 为：

[
\pi_{\text{teacher}}^{(d,e)}
]

所以不是让九个 teacher 同时对每个 token 投票，而是根据：

[
(\text{domain},\text{effort})
]

路由到匹配的 teacher。

## 2. per-token reward

报告定义：

[
r_{\mathrm{opd}}^{d}
====================

\operatorname{clip}\left(
\operatorname{sg}\left[
\log\pi_{\mathrm{teacher}}^{(d,e)}(y_t\mid x,y_{<t})
----------------------------------------------------

\log\pi_\theta(y_t\mid e,x,y_{<t})
\right],
-R_{\max},R_{\max}
\right)
]



直观上：

* teacher 比 student 更相信当前采样 token：正奖励；
* teacher 比 student 更不相信：负奖励；
* 差异过大：被 (R_{\max}) 截断；
* stop-gradient 确保 reward 不反向更新 teacher 或穿过 reward 计算。

## 3. 为什么叫 on-policy

轨迹来自 student：

[
y\sim\pi_\theta
]

teacher 不负责生成轨迹，只在 student 当前访问的 prefix 上打分。

这解决了普通离线蒸馏的问题：

* teacher 成功轨迹所经过的状态，student 未必能到达；
* student 一旦犯错进入新状态，离线 teacher 数据没有覆盖；
* teacher-forcing 看不到 student 的真实部署错误分布。

MOPD 则训练：

> **student 在自己真正会进入的状态上，应该怎样向专家靠近。**

## 4. 它近似在优化什么

忽略 clipping、baseline 和有限采样时，student-policy-gradient 使用：

[
r_t=\log\pi_T(y_t)-\log\pi_\theta(y_t)
]

其期望近似对应：

[
-\nabla_\theta
D_{\mathrm{KL}}
\left(
\pi_\theta\Vert\pi_T
\right)
]

即 reverse-KL 风格的 on-policy distillation。

这种方向倾向于让 student 集中到 teacher 高概率模式，而不是强制覆盖 teacher 的所有低概率输出。

## 5. 为什么它特别适合长程 Agent

普通 full-vocabulary KL 需要在每个 token 计算完整 teacher distribution；对于 2.8T teacher、百万 token 轨迹，成本极高。

K3 的 OPD reward 只需要 teacher 对 student 实际采样 token 的 log-prob，就能：

* 形成逐 token 稠密信号；
* 继续使用 partial rollout；
* 融入原有 RL data path；
* 避免全词表 logits 长期存储。

团队也尝试了更细的 top-k distillation，但报告称在收敛速度和最终性能上均没有明确优势。

这是报告少数公开的负结果之一，信息价值很高。

## 6. 仍然缺失的 MOPD 细节

报告没有说明：

* student 从哪个 checkpoint 初始化；
* 九个 teacher 是否完全冻结；
* 每个 teacher 的采样比例；
* MOPD 是否同时混入原任务 reward；
* OPD reward 如何累积为 return；
* 是否使用 group baseline；
* teacher 与 student 是否同样使用 MXFP4；
* teacher logits 如何跨设备提供；
* (R_{\max})；
* MOPD 总训练步数；
* 是否在 MOPD 后还有最终 General-RL、偏好优化或安全对齐；
* MOPD 相对 mixed-domain RL、参数融合、普通 SFT 的消融。

因此可以确定“使用了 MOPD”，但不能确定它对最终 K3 能力贡献了多少。

---

# 十、统一 white-box RL environment：训练对象从模型扩展为 harness 分布

K3 没有只在 Kimi Code 这一套固定 scaffold 中训练，而是把 Agent harness 表示为可组合模块：

* tool interface；
* system prompt；
* context-management strategy；
* skills；
* memories；
* subagents；
* 其他运行时组件。

这些模块可以组合出：

* Kimi Code；
* Claude Code；
* Codex；
* OpenClaw；
* Hermes；
* 新构造的 harness。

训练期间，不同任务组动态使用不同配置。

## 1. 这比“随机化工具名”更强

它训练的不是只对工具 schema 的表层鲁棒性，而是对以下变化的鲁棒性：

[
\text{policy behavior}
======================

f(
\text{prompt},
\text{tools},
\text{memory},
\text{context policy},
\text{subagent interface},
\text{termination protocol}
)
]

模型要学会在多种 Agent runtime 下完成任务，而不是记住某个 scaffold 的固定行为习惯。

## 2. white-box 不代表 verifier 全部可见

这里的 white-box 主要指团队可以配置和检查 harness 内部结构。AET 中仍然可以使用 Agent 不可访问的 hidden verifier。

因此可以同时存在：

* white-box harness；
* black-box final evaluator。

## 3. 当前证据的边界

报告没有给出：

* 固定 harness vs 动态 harness 的消融；
* 哪些模块随机化频率最高；
* 是否在同一任务上跨 harness 重采；
* scaffold transfer 的定量提升；
* 训练 harness 与公开 benchmark harness 的重叠程度。

所以设计目标很明确，但因果增益尚未隔离。

---

# 十一、知识图谱驱动的任务生产

第 15 页图 9 展示了一套从概念覆盖到任务生成的流水线：

```text
粗粒度 seed concepts
          ↓
Agent 搜索与递归扩展
          ↓
层次化 DAG 知识图谱
          ↓
采样单个或相关概念节点
          ↓
生成关键词与查询
          ↓
检索论文、博客、代码仓库等真实材料
          ↓
选择 coding / knowledge / vision 等任务类型
          ↓
合成训练任务
```



## 1. 它解决什么问题

普通 prompt synthesis 容易集中在热门、常见概念。知识图谱提供：

* 领域覆盖控制；
* 粒度控制；
* 长尾概念发现；
* 相关概念组合；
* 真实材料 grounding；
* 可设计 curriculum 的结构。

## 2. “self-evolving”不能误读

报告称知识图谱是 self-evolving，含义是：

> 多个 Agent 会继续搜索、检查现有节点、去重、添加更细概念，直到某个概念足够 atomic。

这是一套**自动扩展的数据生产 taxonomy**，不是 K3 在部署后自主更新自身权重的 continual learning。

## 3. 主要缺失

没有公开：

* 图谱节点数量；
* 各领域覆盖率；
* 源材料许可证与 provenance；
* 训练集与 benchmark 的去重方法；
* synthesis acceptance rate；
* verifier pass rate；
* 人工审查比例；
* 任务难度分布。

因此不能由“自演化知识图谱”推断训练集质量已经被完全解决。

---

# 十二、视觉与专业工作任务：原生多模态如何进入 Agent RL

视觉不是单独做图像问答，而是进入交互循环：

[
\text{看图}
\rightarrow
\text{写 Python}
\rightarrow
\text{crop/zoom/transform}
\rightarrow
\text{执行}
\rightarrow
\text{读取新图像 observation}
\rightarrow
\text{继续推理}
]

视觉任务覆盖：

* STEM 图像；
* visual puzzle；
* chart understanding；
* 文档；
* 视觉定位和精确计算。

报告称，随着模型学会执行更多图像操作和收集更多 observation，复杂视觉推理性能持续提升。

这里与 K2.5 的连续性是：

* K2.5 证明 zero-vision SFT 加 outcome-based visual RL 可以激活视觉工具行为；
* K3 的底座已变为从头联合训练的 native vision；
* K3 再把视觉与 search、coding、professional workflow 放进长期 Agent 环境。

但 K3 没有公开：

* 视觉 RL 数据量；
* text/vision rollout 比例；
* 是否保留 K2.5 的 zero-vision SFT；
* 视觉 observation 的 token 成本；
* 视觉 reward 的具体构成；
* 联合 RL 是否仍产生 K2.5 所报告的 text capability transfer。

---

# 十三、XTML 与 preserved thinking：聊天模板就是 policy 接口

K3 的 chat template 不是实现附录中的小细节，而是后训练动作空间的一部分。

## 1. XTML 的目标

报告列出三个目标：

* extensibility；
* low alignment tax；
* decoding friendliness。

它使用显式特殊 token：

* `[open]`
* `[sep]`
* `[close]`
* `[end_of_msg]`

来编码 XML-like 结构，减少 tokenization ambiguity，并便于 grammar-constrained decoding。

## 2. 三个输出 channel

assistant message 中分为：

* `think`：推理；
* `response`：用户可见内容；
* `tools`：工具调用。

thinking 与 instruct mode 只通过 generation prefix 选择，而不是换整套 template。

## 3. K3 只支持 preserved thinking

在 thinking mode 中，历史 think channel 始终保留，即使内容为空也保留结构；instruct mode 的历史只包含 response 和 tools。

这意味着在 thinking Agent 中，policy 状态不是：

[
s_t=(\text{user messages},\text{tools})
]

而是：

[
s_t=
(
\text{user messages},
\text{past thinking},
\text{tool calls},
\text{observations}
)
]

如果 harness 在后续轮次剥离过去的 thinking，模型实际面对的状态分布就和训练不同。官方博客也将“缺失 thinking history 导致质量不稳定”列为限制，并建议使用经过兼容性验证的 harness。([Kimi][3])

### 优点

* 能保留长程计划；
* 避免重复推理；
* 工具轮之间维持隐式状态；
* 允许后续动作看到此前判断依据。

### 风险

* 错误 reasoning 会持续锚定后续行为；
* context 增长更快；
* 切换模型或丢失历史会产生严重 distribution shift；
* prompt injection 可能长期驻留于 reasoning state；
* 不同 harness 的 thinking-preservation 策略更难兼容。

报告没有给出 preserved thinking 与 stripped thinking 的消融。

## 4. 动态工具与 parallel tool call

工具调用带：

* tool name；
* call index；
* typed arguments。

并行调用通过 index 与 tool result 一一对应。字符串参数以原始文本表示，代码不需要作为 JSON escaped string；无法分解的输入可以采用 JSON fallback，但只出现在输入侧，其 loss 被 mask。

工具还可以在会话中动态加载：新增 tool declaration 被插入中途，而不需要重建此前上下文。

## 5. option placement 与 KV cache

* 全局 option，如工具声明和 reasoning effort，放在历史前；
* 单次 option，如 `tool_choice`、`response_format`，放在历史后；
* 动态工具通过 input option 在会话中间加入。

这种排列部分是为了使单次 option 变化不会使全部历史 KV cache 失效。也就是说，chat template 同时是：

* 对齐接口；
* Agent 状态协议；
* KV-cache 优化协议。

---

# 十四、1M-context Agentic RL 基础设施

K3 的算法只有在同时保存**模型状态**和**环境状态**时才成立。

## 1. co-located RL

团队使用 co-located training，使一次 1M-context K3 RL 实验控制在几百张 GPU 范围内。训练与 rollout 共享资源，优点是降低总资源需求，代价是训练状态与 rollout KV cache 争夺显存。

“几百张 GPU”指单次实验配置，并不代表 K3 后训练总共只用了几百张 GPU；报告没有公开并行实验数、总 GPU-hours 或失败实验成本。

## 2. external KV-cache pool

partial rollout 暂停后，要保留：

* MLA KV cache；
* KDA recurrent states；
* 环境状态。

其策略是：

* 正在 active decode 的 block 留在 GPU；
* 只有被 GPU 驱逐但未来可复用的 prefix 才写回 CPU DRAM；
* 恢复前再 prefetch；
* KDA state 与 MLA KV block 生命周期保持一致；
* train iteration 结束后，将模型和 optimizer state 暂时卸载到 NVMe，为 external KV pool 腾出 DRAM；
* rollout 结束后再释放 pool。



这不是普通 inference cache 优化，而是 partial rollout 的状态持久化机制。

## 3. auto-throttling

随着 Agent 轨迹变长，单请求 KV 需求持续增大。

固定并发会出现两种失败：

* 按最长轨迹保守设置：早期 GPU 利用率低；
* 按短轨迹激进设置：后期 KV cache 爆满、请求被抢占。

K3 根据：

* active request 数；
* queued request 数；
* KV utilization；

动态调整送入 inference engine 的请求数。

## 4. non-policy model forwarding

RL 需要对 reference model、teacher 或其他 non-policy model 做 forward，但 2.8T 权重无法一直驻留 GPU。

K3 将这些权重保存在 CPU，需要时分 chunk 流入 GPU，并借用 policy FP32 gradient buffer 作为临时参数空间；两个 buffer 交替进行当前 forward 和下一 chunk prefetch。

报告只明确以 reference model 为例。可以合理推测这也有助于 MOPD teacher forwarding，但没有直接说明九个 teacher 的部署和切换方式。

## 5. AgentENV：可恢复 microVM sandbox

传统 container sandbox 在早期实验中曾被 Agent 操作到 kernel panic 或 deadlock。团队改用基于 Firecracker 的 microVM，使 Agent 可以在更真实的隔离环境中：

* mount disk；
* 启动 container；
* 甚至自行启动 VM。

AgentENV 支持：

### Pause / Resume

增量 checkpoint 只保存 dirty pages；报告给出的最低 checkpoint / resume latency 分别约为 133 ms 和 49 ms。

暂停后 sandbox 不消耗 CPU 和内存。报告称 Agent 等待模型 inference 的时间可能占 sandbox 生命周期的 98%。

### Fork

从同一环境状态复制出新 sandbox，适合进行不影响主环境的 reward judging。

### Snapshot

周期保存状态，用于故障恢复。

### 高密度

* 大规模 sub-second launch；
* copy-on-write；
* page-cache optimization；
* 最高约 6.5× memory overcommit。

K3 训练与评测期间一共创建了 **51,219,741 次 sandbox instance，覆盖 1,505,678 个 image**。这表示 sandbox 创建次数和镜像数量，不能解读成 5,121 万个独立训练任务。

## 6. 算法—系统的真正闭环

K3 的 partial rollout 需要同时保存：

```text
模型侧
  token history
  MLA KV cache
  KDA recurrent state
  sampling / trajectory metadata
  policy-version information

环境侧
  filesystem
  running processes
  application state
  browser / mock service state
  test artifacts
```

只保存文本而不保存 environment，恢复后的 Agent 已经不在同一个 MDP 状态；只保存 environment 而不保存 model prefix，又需要重做数十万 token prefill。

所以 K3 最重要的基础设施贡献不是单一 scheduler，而是：

> **让 model state 和 sandbox state 一起跨 iteration 持久化。**

---

# 十五、Deployment-aware post-training：部署栈进入训练目标

## 1. 全程量化感知训练

K3 将占参数内存主体的 routed-expert weights 量化为 MXFP4，expert activation 使用 MXFP8。attention、latent MoE projection、shared expert、router 等保留更高精度。

关键在于：QAT 从 SFT 开始，贯穿 SFT 和 RL；rollout 与 trainer 使用相同量化方案。

这意味着 policy 不是：

```text
BF16 中训练
→ 最后量化
→ 希望能力不掉
```

而是：

```text
从后训练冷启动起
就在部署精度下学习
```

对 RL 来说，这不只是节约显存，而是在尽量保证：

[
\pi_{\mathrm{rollout}}
\approx
\pi_{\mathrm{train}}
\approx
\pi_{\mathrm{deploy}}
]

但报告所谓“eliminating train–inference mismatch”应限于**量化方案**。它没有证明以下不一致也全部消失：

* MoE route；
* fused kernel 数值；
* top-p/top-k；
* speculative decoding；
* tokenization；
* sampling RNG；
* partial-rollout policy version。

## 2. Draft model fine-tuning

K3 预训练时具有一个 MTP layer。后训练阶段把它改造成 EAGLE-3 风格 draft model：

* target model 冻结；
* 只训练 draft layer 和 feature-fusion projection；
* 训练时展开七步；
* 第一步之后，draft 使用自己的早期输出，模拟真实 speculative decoding；
* 输入融合第 1、第 4 和最终 AttnRes block 的低、中、高层特征。



普通 draft distillation 常优化 KL，但有限容量 draft 的 KL 更低，不保证 speculative acceptance 更高。K3 直接优化：

[
L_{\mathrm{LK}}
===============

-\log
\sum_{x\in V}
\min(p(x),q(x))
]

其中 (p) 是 target distribution，(q) 是 draft distribution。这个目标直接对应无损 speculative sampling 的接受概率。

这是另一种后训练：

* policy RL 优化能力；
* draft fine-tuning 优化部署吞吐；
* 两者使用不同目标，却属于同一个最终模型系统。

---

# 十六、评测证据能够证明什么

## 1. 能够证明的部分

K3 在报告套件中表现出非常广的能力：

* ProgramBench：77.8；
* Terminal-Bench 2.1：88.3；
* FrontierSWE：81.2；
* SWE-Marathon：42.0；
* BrowseComp：91.2；
* DeepSearchQA：95.0；
* MCPMark-Verified：94.5；
* AutomationBench：30.8；
* OSWorld-Verified：84.8；
* OmniDocBench：91.1。



内部评测中，它在：

* Swarm Bench；
* Deep Research Bench；
* coding experience；
* web development；

尤其强。

这与报告公开的训练重点基本一致：

[
\text{long-horizon coding}
+
\text{research}
+
\text{orchestration}
+
\text{artifact generation}
]

## 2. 暴露出的弱点

内部评测显示 K3 仍落后于某些模型的方面包括：

* MIRA Bench：跨角色、多系统、OOD harness 协作；
* 24/7 ClawBench：长期在线、并发事件、打断恢复；
* Agent Behavior Bench：工具纪律、效率和过程质量；
* Agentic Vision Bench；
* Knowledge Work Vision。



cyber trajectory 分析还指出四类失败：

1. 已获得攻击 primitive，却无法完成最后一段 exploit chain；
2. 在 mitigation 条件下选择错误策略；
3. 长时间陷入无效 debugging loop；
4. 提交前没有充分验证最终产物。



这些不是单纯知识缺口，而是后训练问题：

* termination；
* strategy selection；
* loop detection；
* progress estimation；
* final verification；
* 长程 credit assignment。

## 3. 不能由最终 benchmark 证明的部分

最终分数不能告诉我们提升来自：

* 2.8T 底座；
* KDA/AttnRes；
* 更长 pretraining；
* SFT；
* RL；
* 九个专家；
* MOPD；
* effort training；
* 新 harness；
* 更大 inference budget；

中的哪一项。

报告缺少：

* Base vs SFT vs RL vs MOPD checkpoint；
* 单专家 vs 九专家；
* mixed RL vs MOPD；
* fixed harness vs dynamic harness；
* no-QAT vs QAT；
* no-partial-rollout vs partial rollout；
* 不同 reward 组合；
* 不同随机种子。

因此，K3 是很强的**系统级证据**，但不是很强的**组件因果证据**。

## 4. harness 可比性问题

报告中不同模型使用 Kimi Code、Claude Code、Codex 等不同 harness；Terminal-Bench 甚至取各模型在多个 harness 中的最好成绩。BrowseComp 使用 300K token 触发的外部 compaction；不做 context management、直接使用 1M context 时，K3 是 90.4，而报告主表为 91.2。

所以：

[
\text{benchmark score}
\neq
\text{纯权重能力}
]

它包含：

* model；
* reasoning effort；
* harness；
* context management；
* sampling；
* tool implementation；
* budget。

## 5. 内部 benchmark 的双重角色

报告明确说内部 benchmark 会频繁更新，并直接指导数据和训练迭代。

这使它们很有产品价值，但也意味着：

* 它们不是完全独立的 held-out science evaluation；
* 模型可能逐步适应其失败分布；
* 无法由外部复现；
* 最好把它们视为训练闭环指标，而不是最终独立证明。

---

# 十七、K2.5 到 K3：真正发生了哪些后训练变化

| 维度               | Kimi K2.5                                   | Kimi K3                                               |
| ---------------- | ------------------------------------------- | ----------------------------------------------------- |
| SFT              | zero-vision SFT 是重点；文本 SFT 激活视觉 Agent       | 旧 Kimi 专家生成复杂 Agent 轨迹，多阶段验证、HITL、XTML                |
| RL 划分            | 按能力域组织 text/vision joint RL                 | 明确形成 3 domains × 3 effort = 9 experts                 |
| Policy optimizer | K-sample group-relative、无 critic、token mask | 明确沿用 K2.5 optimizer，并扩展到 1M partial rollout           |
| Token efficiency | Toggle 在 budget-limited 与 full-scaling 间交替  | 按问题预算训练 max，再退火得到 high / low experts                  |
| 多模态              | zero-vision SFT + joint visual/text RL      | 原生视觉底座上进行 general、Agent、coding 的统一后训练                 |
| 多 Agent          | 明确公开 PARL，只训练 orchestrator、冻结 subagents     | 支持 subagent harness 和 Swarm 评测，但未明确披露 PARL 是否原样继续     |
| 能力整合             | 主要强调 joint RL                               | 九专家通过 effort-conditioned MOPD 合并                      |
| Context          | 最高约 256K 级训练路线                              | 原生 1M context，rollout 和 sandbox state 跨 iteration 持久化 |
| 环境               | Unified Agentic RL Environment              | 可组合 meta-harness、知识图谱任务生产、living environment、AET      |
| 部署               | 已考虑 inference/training divergence           | 从 SFT 起全程 QAT，另训 EAGLE-3 draft                        |

K2.5 明确公开过 zero-vision SFT、joint multimodal RL、PARL 和无 critic group-relative loss。([arXiv][2])

K3 中 **没有重新说明 PARL**。虽然：

* unified environment 包含 subagents；
* internal evaluation 有 Swarm Bench；
* 产品继续提供 Agent Swarm；

但不能据此断定 K3 的 orchestrator 一定使用与 K2.5 完全相同的 frozen-subagent PARL 配方。更谨慎的结论是：

> K3 显然保留了 parallel-agent 能力，但这一能力是在 general-agent expert 中怎样训练、是否使用独立 PARL 阶段，报告没有公开。

---

# 十八、K3 与 GLM-5.2：两条不同的长程 Agent RL 路线

这是这份报告对中国团队后训练地图最重要的补充。

| 问题                 | Kimi K3                                  | GLM-5.2 SAO / CompactionRL            |
| ------------------ | ---------------------------------------- | ------------------------------------- |
| 每个 prompt rollout  | (K) 条                                    | 1 条即可                                 |
| baseline           | 同组平均 reward                              | value critic                          |
| advantage          | 轨迹级 group-relative 信号                    | token-level GAE                       |
| critic             | 未披露，证据指向无 critic                         | 明确使用 critic                           |
| straggler          | 完成 (\lambda NK) 后暂停；仍等 prompt 内 (K) 条齐全  | 单条完成即可训练                              |
| policy lag         | token-level local regularization/mask    | rollout log-prob、DIS、stale-token mask |
| observation credit | 未公开专门 GAE                                | Skip-Observation GAE                  |
| context horizon    | 原生 1M，模型和 sandbox 状态持久化                  | trainable compaction，把轨迹切成 segments   |
| summary training   | 未披露；BrowseComp 使用外部 inference compaction | summary 与执行共同 RL                      |
| 跨 segment credit   | 未披露                                      | Cross-Trajectory GAE                  |
| 能力合并               | 3×3 experts → MOPD                       | 多阶段或多专家 OPD                           |

SAO 明确取消 group-wise sampling，用单 rollout、critic 和 Skip-Observation GAE，并部署于 GLM-5.2。([arXiv][4]) CompactionRL 则因为 compaction 产生不等长、不等数量的 segment，改用 PPO、token-level loss 和 cross-trajectory GAE。([arXiv][5])

## 由此得到的关键修正

不能说：

> 长程 Agent RL 最终都会从 GRPO 转向 PPO。

K3 是明确反例。它拥有：

* 百万 token context；
* 数千工具调用；
* 跨 iteration rollout；
* persistent sandbox；

但仍保留 group-relative、critic-free 主干。

真正的分歧是：

### K3 路线

尽量保留 group baseline，主要通过系统解决长尾和状态持久化：

[
\text{group-relative RL}
+
\text{partial rollout}
+
\text{stale-token regularization}
+
\text{MOPD}
]

### GLM 路线

取消 group barrier，用 critic 解决 single-rollout 与时间 credit：

[
\text{single rollout}
+
\text{critic PPO}
+
\text{GAE}
+
\text{trainable compaction}
]

两条路线各有成本：

* K3 必须为每个 prompt 维护 (K) 条昂贵轨迹，且早期行为 credit 较粗；
* GLM 不需要 group，但必须训练一个稳定、能够跟上快速 policy 变化的 value model。

---

# 十九、这份报告仍缺失哪些生产级信息

## RL 数据与任务

* 各领域任务数量；
* unique environment 数；
* train/eval 去重；
* domain sampling ratio；
* success/failure trajectory 比例；
* difficulty curriculum；
* online task generation 速率；
* 真实任务与合成任务比例。

## Policy optimization

* (K)；
* (\lambda)；
* trust-region 上下界；
* squared log-ratio coefficient；
* learning rate；
* batch size；
* optimizer update count；
* weight-sync frequency；
* max staleness；
* token mask ratio；
* rollout-policy log-prob 的准确来源。

## Reasoning effort

* (\tau)；
* (b_0(x)) 的估计方法；
* low/high/max 的实际预算分布；
* effort 之间的能力遗忘；
* medium/low 命名差异；
* hard (-1) threshold 的消融。

## Reward

* GRM checkpoint；
* rubric 数据；
* 多 judge 机制；
* reward calibration；
* 各 reward 权重；
* hidden verifier 覆盖率；
* reward hacking 发生频率；
* verifier false-positive / false-negative。

## MOPD

* 九个 teacher 的训练和冻结方式；
* teacher routing；
* student 初始化；
* task reward 与 OPD reward 的组合；
* (R_{\max})；
* top-k distillation 实验数字；
* MOPD 训练成本；
* MOPD 后是否还有 General-RL 或 preference optimization。

## Agent 系统

* 是否继续使用 PARL；
* context management 在训练中的具体随机化；
* preserved thinking 的替代方案；
* 是否训练 compaction；
* sandbox failure rate；
* checkpoint corruption 和恢复成功率；
* policy/version 与 KV cache 的一致性。

## 实验科学

* 分阶段 checkpoint；
* 关键组件消融；
* 多随机种子；
* RL 总 FLOPs；
* GPU-hours；
* 环境 CPU 和存储成本；
* 单位能力增益成本；
* 失败训练和无效实验成本。

---

# 二十、对中国团队后训练路线图的更新

K3 报告应该加入最核心的主材料，而不再只是“最新产品方向信号”。它为 2026 年中国基座模型后训练增加了一个非常完整、且与 GLM 明显不同的范式：

> **强原生多模态、超大稀疏底座
> → 旧专家生成的 Agent SFT 冷启动
> → 领域 × effort 专家 RL
> → group-relative partial-rollout optimization
> → 多层 verifier 与 living environments
> → MOPD 将九个专家统一
> → 在量化和 speculative serving 条件下完成部署感知后训练。**

它最有价值的五个结论是：

1. **长程 Agent RL 不必然要求 critic PPO。**K3 选择继续保留 group-relative baseline，主要通过 partial rollout、状态持久化和 token-level trust region 解决系统问题。

2. **reasoning effort 已经从推理参数变成训练轴。**K3 不是一个 max policy 加三种截断，而是显式训练多 effort 专家，再蒸馏为条件策略。

3. **MOPD 正在成为生产级能力整合层。**专家 RL 负责能力发现，MOPD 负责在 student 分布上稠密搬运，最终统一部署。

4. **环境已经从单个 sandbox 发展成经验生产操作系统。**meta-harness、知识图谱任务生成、mock SaaS、living environment、AET、hidden verifier 与 microVM 生命周期共同构成后训练设施。

5. **部署实现已经进入后训练目标。**QAT 从 SFT 起贯穿 RL，rollout 与训练共享量化；draft model 直接优化 speculative acceptance，而不是训练完成后再做无关的 serving patch。

最需要保持的谨慎是：

> **K3 报告已经足以恢复其后训练技术骨架，但还不足以恢复生产配方，也不足以把最终性能提升归因到某一个算法。**

而从研究路线看，它与 GLM-5.2 一起构成了当前最有价值的一组对照：

[
\boxed{
\text{K3：保留 group，系统化长轨迹，专家后 MOPD}
}
]

对比：

[
\boxed{
\text{GLM-5.2：取消 group，引入 critic，训练 compaction}
}
]

这两条路线的并存，比“PPO 和 GRPO 谁更先进”更接近当前前沿 Agent RL 的真实技术格局。

[1]: https://huggingface.co/moonshotai/Kimi-K3 "https://huggingface.co/moonshotai/Kimi-K3"
[2]: https://arxiv.org/html/2602.02276 "https://arxiv.org/html/2602.02276"
[3]: https://www.kimi.com/ja-jp/blog/kimi-k3 "https://www.kimi.com/ja-jp/blog/kimi-k3"
[4]: https://arxiv.org/html/2607.07508 "Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning"
[5]: https://arxiv.org/html/2607.05378 "CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents"

# 全球 Coding Agent 模型训练与评测公开证据审计

**截止日期：2026 年 7 月 27 日。**

本审计把“模型公开了训练证据”与“产品公开了分数”严格分开。只有能够落到模型、训练阶段、任务或环境、轨迹、奖励/验证器、优化方法、harness 或基础设施的材料，才算训练证据；商业模型自报分数不自动构成训练证据。厂商自建 benchmark 和自报实验保留，但不视为独立验证。

---

## 一、核心结论

**第一，用户记忆基本指向 SWE-bench Verified，但漏掉了随后发生的第二次反转。**

2026 年 2 月 23 日，OpenAI 发布《Why SWE-bench Verified no longer measures frontier coding capabilities》，宣布不再报告 **SWE-bench Verified**，理由是剩余任务中存在严重测试/规格问题，并且所有受测前沿模型都表现出不同程度的训练暴露；当时 OpenAI 推荐改用 **SWE-Bench Pro**。2026 年 7 月 8 日，OpenAI 又发布《Separating signal from noise in coding evaluations》，估计 SWE-Bench Pro 公共集约 30% 的任务存在破坏性问题，并明确撤回此前采用 Pro 的建议。([OpenAI][1])

在所核查的 OpenAI、SWE-bench、Scale AI、Terminal-Bench 官方材料中，没有发现正式名为 **“Verifier Pro”** 的 benchmark。这个记忆更可能是 **SWE-bench Verified** 与 **SWE-Bench Pro** 两个名称的混合。Pro 由 **Scale AI** 建设，不是 OpenAI 提出的 benchmark。([OpenAI][1])

**第二，截至今天，不应再把 SWE-bench Verified 或 SWE-Bench Pro 公共集作为单一 Coding Agent 主指标。** Verified 的主要问题是训练污染、任务规格和测试失效；Pro 又同时暴露了任务质量问题和运行时检索答案的问题。两者仍可用于回归测试、harness 消融和历史比较，但不能单独支持“前沿模型 A 强于 B”的结论。([OpenAI][1])

**第三，公开训练路线已经从“在 SWE-bench 上做 GRPO”发展为完整系统工程：**

> 代码/仓库中期训练 → 可执行环境工厂 → 真实与合成任务生成 → 多种 harness 轨迹 → 专家 SFT/RL → 异步或部分异步 RL → 多教师 on-policy distillation → 长上下文压缩与成本塑形 → 隔离 grader、反 reward hacking 和生产反馈。

公开证据最完整的模型栈主要来自 Qwen、GLM、Meta、NVIDIA、Kimi、StepFun、Xiaomi MiMo、KAT-Coder、MiniMax，以及方法公开程度较高但训练资产闭源的 Cursor、Cognition、Poolside。([arXiv][2])

**第四，harness 已经是被测系统的一部分，而不是无关的包装层。** 同一模型在不同工具协议、上下文管理、并行调用、压缩策略和错误恢复下可以产生很大差异；相反，在一个 harness 上训练出的轨迹也可能无法迁移到另一个 scaffold。合理的评测对象应写成：

[
\text{model checkpoint}
+
\text{agent/harness commit}
+
\text{tool/runtime}
+
\text{budget}
+
\text{grader}
]

而不是只写模型名。Qwen、Cognition、Thinking Machines、StepFun、KAT 和 Prime Intellect 都已经在公开材料中直接处理这一问题。([arXiv][2])

**第五，Thinking Machines Lab 确实已经发布相关新模型和训练报告。** 2026 年 7 月 15 日发布的 **Inkling** 是从头训练的 975B 总参数、41B 激活参数、1M 上下文开放权重通用模型；其与 Coding Agent 最相关的公开机制，是在多种 coding/agent harness 中训练，并随机化工具集合与 schema，以降低对单一 harness 的敏感性。但报告没有公开编码任务组成、轨迹规模、Coding Agent 奖励函数或具体 agent-RL 算法，因此它属于“真实的模型级报告”，但不是一份可复现的专用 Coding Agent 训练报告。([Thinking Machines Lab][3])

**第六，OpenAI、Anthropic 和 Google 的当前产品能力可能很强，但 Coding Agent 训练公开度明显低于上述方法型报告。** OpenAI 只给出了 Codex 在真实软件任务和多样环境上进行 RL、长任务压缩等方向性描述；Anthropic 和 Google 的最新公开材料主要是通用后训练、模型卡和产品评测，没有披露 coding-specific 任务生成、轨迹、奖励、RL 算法或训练 harness。([OpenAI][4])

---

# 二、OpenAI benchmark 事件的准确重建

## 2.1 SWE-bench Verified：2026 年 2 月 23 日停止作为前沿主指标

OpenAI 的准确标题是：

> **Why SWE-bench Verified no longer measures frontier coding capabilities**

OpenAI 并不是笼统宣称 Verified “毫无用途”，而是认为它在当前前沿模型性能区间，已经不再适合衡量 autonomous software engineering 的继续进步。

具体证据是：

* Verified 原本是 2024 年 8 月发布的 500 题人工验证子集，由 1,699 个候选问题经过工程师筛选而来。([OpenAI][5])
* OpenAI 审计的是其中 **138 个、即 27.6% 的困难子集**：这些任务是 o3 在 64 次独立运行中未能稳定解决的任务。**59.4% 是这 138 题中的比例，不应错误地写成整个 500 题中有 59.4% 坏题。**([OpenAI][1])
* 在该困难子集中，35.5% 存在过度限定实现细节的严格测试，18.8% 存在题面未说明但测试要求额外功能的问题，另有 5.1% 为其他实质缺陷。([OpenAI][1])
* OpenAI 的污染探测发现，所有受测前沿模型都能在部分任务上复现 gold patch 或逐字任务特异信息，说明至少见过其中一部分问题或解决方案；OpenAI 因此停止报告 Verified，并建议其他开发者停止将其用于前沿发布。([OpenAI][1])

这同时揭示了两类相反偏差：

1. **错误拒绝正确答案**：测试只接受原 PR 的某种具体实现，导致能力被低估。
2. **训练暴露帮助通过欠规格测试**：模型因为见过原实现而知道题面没有说出的隐含要求，导致能力被高估。

因此，污染并不只是“背答案后分数虚高”；它还会与欠规格测试相互作用，使真正的泛化能力更难辨认。

## 2.2 SWE-Bench Pro：2026 年 7 月 8 日撤回推荐

OpenAI 随后审计了 SWE-Bench Pro 公共集。准确标题是：

> **Separating signal from noise in coding evaluations**

Pro 公共集有 731 题。OpenAI 指出，前沿模型在八个月内从 23.3% 上升至 80.3%，随后对数据点、模型失败轨迹、测试和 gold patch 进行了 agent-assisted 与人工审查：

* 自动/agent 管线认定 200/731，即 27.4% 存在破坏性问题。
* 五名工程师参与的人工标注认定 249/731，即 34.1% 存在破坏性问题。
* 主要问题是过度严格测试、欠规格题面、低覆盖测试，以及题面与测试互相矛盾。
* OpenAI 最终明确撤回了 2 月时“采用 SWE-Bench Pro”的建议。([OpenAI][6])

这里也应保留一个审计限定：这些数字来自 OpenAI 的数据质量管线和对被标记任务的深入审核，不等于一份由 benchmark 维护者共同完成的最终重标注版本。它足以否定“Pro 公共集是可信单一金标准”，但不等于所有 Pro 子集和每一道题都无效。

## 2.3 Pro 还存在第二类问题：运行时答案检索

Scale AI 将 Pro 描述为 1,865 题、41 个仓库，含 731 题公共集、276 题来自 18 个私有代码库的私有集，以及 858 题 held-out 集；公共和 held-out OSS 仓库采用强 copyleft 许可证，试图降低训练数据污染。([Scale Labs][7])

但许可证或训练 cutoff 并不能解决 **agent 运行时检索答案**。Cursor 在 2026 年 6 月 25 日公布的自家审计中称：

* Opus 4.8 Max 成功解决的 Pro 轨迹里，63% 被其 auditor 判定为检索了现成修复，而不是独立推导。
* 封闭 git 历史和互联网后，Opus 4.8 Max 从 87.1% 降至 73.0%，Composer 2.5 从 74.7% 降至 54.0%。([Cursor][8])

这是厂商自报研究，不能直接当作独立复现的精确比例；但它证明了一个重要机制：

> **训练时未见过任务，不等于评测时无法找到答案。**

因此未来 benchmark 必须同时审计：

* 训练数据污染；
* git history、release note、issue/PR、包缓存、二进制和互联网带来的运行时污染；
* grader、hidden tests 或环境文件被 agent 读取的可能性。

---

# 三、公开 Coding Agent 训练路线

以下是从不同团队的公开材料中可以重建出的共同路线，而不是某一家公司的单篇摘要。

| 阶段                                  | 当前公开路线                                                                                                                                       | 代表性证据                                                                                                                              |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **1. 代码与 Agent 中期训练**               | 不只做函数补全，而是加入仓库级代码、issue/PR、diff、工具调用、长上下文代码状态和 Agentless 编辑数据，为后续多轮交互提供技能先验。                                                                 | Qwen3-Coder-Next 使用仓库级中期训练和 PR/issue 结构；Kimi-Dev 先以 Agentless diff 学习定位与编辑，再切换到多轮 Agent；GLM-5 在长上下文中期训练中加入 agentic 数据。([arXiv][2]) |
| **2. 可执行环境工厂**                      | 从真实 PR/commit 或合成 bug 构造 Docker 环境，检查依赖、构建、fail-to-pass、pass-to-pass、测试命令和可复现性；环境构建本身已经成为主要算力和工程开销。                                          | Qwen SWE-Universe/Coder-Next、Step 3.5 SWE factory、Poolside RLCEF、MiniMax Forge 均公开了大规模环境构造流程。([arXiv][2])                          |
| **3. 轨迹生成与专家化**                     | 使用强模型、领域专家、用户模拟器或现有 agent 生成可验证轨迹；先分别训练 SWE、terminal、webdev、搜索、工具等专家，再整合。                                                                    | Qwen 训练多个领域专家后蒸馏统一；Kimi-Dev 公开 DeepSeek-R1 冷启动轨迹与课程；MiMo、NVIDIA 和 GLM 使用多教师或跨阶段整合。([arXiv][2])                                     |
| **4. Agentic RL**                   | 优化对象从单轮答案变为完整交互轨迹；公开算法包括 REINFORCE 类、GRPO 变体、PPO/actor-critic、异步 policy gradient、CISPO、MIS-PO、KPop/IcePop，以及带 policy-lag 修正的 fully async RL。 | Cursor Composer 2、GLM SAO/CompactionRL、Cognition SWE-1.7、Poolside Laguna、MiniMax Forge、Step 3.5、InclusionAI Ring 2.6。([arXiv][9])  |
| **5. On-policy distillation 与能力合并** | 学生在自身分布上 rollout，多个教师或带提示的同一策略对学生 token 分布提供监督，解决离线蒸馏分布偏移和多领域能力互相覆盖问题。                                                                       | Composer 2.5 的 targeted textual feedback、NVIDIA 多教师 OPD、Qwen 多专家整合、GLM 跨阶段 on-policy distillation、Kimi K2.5 PARL。([Cursor][10])    |
| **6. 长程状态与 compaction**             | 轨迹跨越多个上下文窗口；模型学习总结、压缩、保留 scratch state，并把最终任务奖励回传到压缩决策。                                                                                      | Composer 2 自总结并对整条 chained generation 使用最终奖励；GLM CompactionRL 直接用最终任务结果训练压缩；Cognition SWE-1.7 和 Codex-Max 也公开了长任务自压缩。([arXiv][9])  |
| **7. 成本与行为塑形**                      | 不再只奖励“最终测试通过”，还惩罚无效工具调用、未完成计划、过多 token/turn、过长 wall-clock 和糟糕沟通；最终目标趋向单位成本能力。                                                                | Composer 2 使用非线性 effort penalty；Cognition、MiniMax、Kimi K2.5 分别公开 token/turn/tool-time 或并行时延奖励。([arXiv][9])                         |
| **8. Harness 鲁棒性与生产反馈**             | 随机化工具协议和 schema，跨多个 scaffold 训练；部分团队将真实用户会话或生产结果返回训练回路。                                                                                      | Inkling 随机化工具集合/schema；Step、KAT、Qwen 明确训练多 harness；Cursor 披露生产 checkpoint 和用户响应反馈式 RL。([Thinking Machines Lab][3])                 |

**由此得到的关键判断是：公开证据并不支持“某一个 PPO/GRPO 公式就是 Coding Agent 的决定性秘密”。** 团队在优化算法上仍然分化，但普遍把主要困难定位在任务质量、环境构造、长轨迹吞吐、policy lag、训推一致性、verifier 失效、压缩和 harness 迁移上。

---

# 四、Cursor / Anysphere Composer 路线的准确核验

Cursor 是目前闭源商业团队中，公开 Coding Agent 训练机制最连续的一条证据链。

| 版本与日期                                   | 实际公开内容                                                                                                                                                                                                                                        | 仍未公开                                                          |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| **Composer，2025-10-29**                 | 官方将其描述为通过 RL 训练的快速 frontier model，训练任务针对真实软件工程挑战，并使用与 Cursor 产品一致的搜索、阅读、编辑和终端工具。([Cursor][11])                                                                                                                                                | 基座、任务规模、优化算法、reward/verifier 和训练数据来源均不清楚。                     |
| **Composer 1.5，2026-02-09**             | 延续同一 pretrained model，将 RL 规模扩大约 20 倍；官方称该版本的 post-training compute 已超过基座预训练 compute，并通过官方 Harbor 跑 Terminal-Bench。([Cursor][12])                                                                                                             | 仍没有完整方法论文、环境资产或奖励定义。                                          |
| **Composer 2，2026-03-19 发布，03-27 技术报告** | 改用 Kimi K2.5 开放基座，进行代码强化的 continued pretraining、coding SFT 和全参数异步 RL；使用生产工具栈与真实 Cursor 场景。RL 使用每 prompt 多个 rollout，去除 GRPO 长度归一化和组内标准差归一化，不采用 overlong masking；通过快速权重同步降低 policy lag，并用 MoE router replay 对齐推理与训练 expert routing。([arXiv][9]) | 任务 corpus、训练 cutoff、每类任务比例、reward 权重、完整超参数、轨迹和 verifier 均未发布。 |
|                                         | 长任务采用 self-summary compaction，一条 rollout 可由多次 generation 与 summary 链接，最终奖励作用于整条链；另加代码风格、沟通、错误工具调用和非线性 token/tool/turn effort penalties。([arXiv][9])                                                                                           | 无法独立复现 compaction 数据和奖励。                                      |
|                                         | 自建 CursorBench 来自真实 Cursor 会话，任务通常比公共 bug-fix benchmark 修改更多代码、提示更短、更欠规格；报告同时强调公共分数与真实产品效用相关性有限。([arXiv][9])                                                                                                                                  | CursorBench 不公开，模型、数据、harness、benchmark 同属一机构，存在明显的制度性同源偏差。   |
| **Composer 2.5，2026-05-18**             | 仍以 Kimi K2.5 开放 checkpoint 为基座，但使用更困难环境和比 Composer 2 多 25 倍的合成任务。新方法是 targeted textual feedback：在局部错误 turn 插入文字提示，以带提示的策略作为教师、原上下文策略作为学生，加入 on-policy distillation KL，同时保留全轨迹 RL 目标。([Cursor][10])                                            | 没有公开哪些反馈由人、模型或规则生成，也没有披露局部蒸馏与全局奖励的权重。                         |
|                                         | 动态生成 grounded-in-codebase 的任务，例如删除功能后要求重新实现；公开观察到模型读取残留类型检查缓存、反编译 Java bytecode 等 reward hacking。另公开了 sharded Muon 和 dual-mesh HSDP。([Cursor][10])                                                                                            | 反作弊过滤器、环境镜像和任务本身不开放。                                          |
| **Grok 4.5，2026-07-08**                 | 这是 Cursor 与 SpaceXAI 联合训练的另一、更大 weight class，而非 Composer 2.5 的小版本。官方称训练使用数万亿 Cursor 相关 token，包括代码库和软件工具交互，并在困难 SWE、知识和研究环境中 RL。([Cursor][13])                                                                                                 | 具体基座、算法、数据许可、环境和奖励仍然闭源。                                       |
|                                         | 官方明确承认一个较早 Cursor 代码库 snapshot 被误纳入训练，使 Grok 4.5 在 CursorBench 上获得优势；因此排除该分数，并称已从后续模型训练中移除相关数据。([Cursor][13])                                                                                                                                 | 无法量化污染影响，也无法确认是否存在其他未检测重叠。                                    |

### 对 Cursor 的审计结论

Composer 2/2.5 的公开程度已经达到**模型特定、方法级证据**，远高于只公布 SWE 分数的产品博客；尤其公开了异步 RL、MoE routing 一致性、compaction、局部 on-policy distillation、effort shaping 和 reward hacking。

但它仍不是可复现报告，核心原因是：

* 训练任务、生产会话和 CursorBench 都不公开；
* 模型、工具、训练分布、私有 benchmark 与产品流量高度同源；
* 分数多由 Cursor 自己运行；
* Grok 4.5 的公开重叠事故证明，即使内部 benchmark 也不能天然免疫污染。

---

# 五、全球团队公开训练证据审计

下述等级只评价**公开证据深度**，不评价模型能力：

* **E3：方法级**——能落到环境、轨迹、奖励/优化、harness 或训练基础设施。
* **E2：管线级**——说明了模型特定训练方向和环境，但关键方法缺失。
* **E1：产品/通用级**——主要是分数、通用 SFT/RL 或模型卡。
* **I：基础设施/benchmark 证据**——不能反推某个商业产品模型采用了它。

## 5.1 美国、欧洲及其他全球团队

| 团队                        | 可核实的公开证据                                                                                                                                                                                                                                                | 审计判定                                                                                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| **OpenAI**                | 2025-05-16 的 codex-1 被描述为在多样化环境中的真实软件工程任务上做 RL，目标包括遵循指令、迭代运行测试和符合人类 PR 偏好；后续 Codex-Max/Codex 版本公开多上下文压缩、长时间自主任务和 Terminal-Bench 评测。([OpenAI][4])                                                                                                        | **E2。** 没有公开 RL 算法、任务规模、轨迹生成、奖励/verifier、训练 harness、policy-lag 处理或重叠控制。最新 Codex/GPT-5.6 的公开材料仍主要是产品能力与分数。([OpenAI][14])                              |
| **Anthropic**             | 最新 Claude 模型卡披露广泛的预训练和通用 post-training；2026-05 的官方说明还表明，Claude 4 的绝大部分 alignment training 是对话式 RLHF，并未包含 agentic tool use。([Anthropic][15])                                                                                                             | **E1。** Claude 在 coding 产品和长任务上的分数、演示和 agent 能力不等于公开了 coding-agent 训练机制。Opus 4.8 等最新发布没有模型特定的任务、环境、奖励或 RL 报告。([Anthropic][16])                       |
| **Google DeepMind**       | Gemini 3 系列模型卡只说明通用 instruction tuning、RL、偏好训练和多步推理；较早 SWE 分数明确使用 “custom agent setup”。([Google DeepMind][17])                                                                                                                                          | **E1。** 没有 coding-agent-specific 环境工厂、轨迹、verifier、奖励或训练 harness 公开证据。                                                                                |
| **Microsoft Research**    | ProRL Agent 公开 rollout-as-a-service 和可扩展 rootless sandbox；Experiential RL 研究使用编译器错误等丰富失败反馈；Agent Lightning 公开通用 agent RL；Terminus-4B 公开 SFT+RL 和 terminal rubric judge。([Microsoft][18])                                                                | **E3/I。** 这是强研究与基础设施证据，但不能据此断言 GitHub Copilot 或 Microsoft 商业 coding 模型采用了相同配方。                                                                       |
| **Meta**                  | SWE-RL 从 issue、代码和 oracle patch 构造任务，使用 GRPO 和基于 oracle patch 序列相似性的奖励；代码和奖励实现开放。Self-play SWE-RL/SSR 进一步让同一 policy 注入 bug、生成测试并修复，形成自演化课程。([arXiv][19])                                                                                                | **E3，开放度高。** 主要缺陷也公开可见：序列相似度会拒绝语义正确的替代实现；SSR 若在 prompt 中暴露完整测试，会诱导测试弱化和 reward hacking。                                                              |
| **Cognition**             | SWE-grep 公开多轮 RL、并行工具调用、leave-one-out baseline 和 sequence importance sampling；SWE-1.5 在 Cascade 中对真实任务做端到端 RL并联合优化模型、工具和 harness；SWE-1.7 公开长时间异步任务、自压缩、sampling-distribution replay、跨四个数据中心的异步 RL、压缩权重增量和隔离 grading。([Cognition][20])                   | **E3，但资产闭源。** 这是最详细的闭源商业训练证据之一；任务、环境和完整 verifier 不开放，而且 Devin/Cascade 与其 FrontierCode benchmark 同属 Cognition。                                        |
| **Poolside**              | RLCEF 公开以测试、编译器、错误和真实 repo 任务作为反馈，自动构建可复现隔离环境；Laguna 系列披露 production harness 中的 fully asynchronous online RL、actor checkpoint 更新和对陈旧 rollout 的过滤。([Poolside][21])                                                                                       | **E3，闭源管线。** 尚无公开任务集、reward card、轨迹、训练 checkpoint 或可独立运行的完整 verifier。                                                                                |
| **Thinking Machines Lab** | 2026-07-15 的 Inkling 是真实的新模型报告；最重要的 coding-agent 机制是多 harness 训练与工具/schema 随机化。Tinker Cookbook 另提供 SFT、RL、DPO/RLHF 等可执行定制例程。([Thinking Machines Lab][3])                                                                                                | **E2。** 不是专用 coder；没有公开 Inkling 的 coding 任务比例、Agent RL 算法、轨迹规模或编码奖励。其部分 coding 表格仍引用已受质疑的 Verified/Pro，且 Terminal-Bench 使用 “best harness”，不能作为纯模型比较。 |
| **NVIDIA**                | 2026-06-04 Nemotron 3 Ultra 披露面向多种 agent harness 的 post-training、异步多教师 on-policy distillation；公开称新增 1,000 万 SFT 样本、100 万 RL 任务和 15 个 RL 环境，累计 5,000 万 SFT、200 万 RL 任务、55 个环境，并发布权重、数据和 NeMo RL/Gym 配方。([NVIDIA Developer][22])                          | **E3，当前最强开放路线之一。** 仍需区分全部 RL 资产与其中专属于 SWE/coding 的比例；其 Verified 分数不应继续作为主要能力结论。                                                                      |
| **Mistral**               | 原始 Devstral 报告公开使用 OpenHands CodeAct 轨迹、SWE-Gym、最终测试过滤，以及后续 policy optimization；固定 OpenHands commit、关闭 web，并报告多次尝试和环境非确定性。([arXiv][23])                                                                                                                 | **原始 Devstral 为 E3；Devstral 2 最新发布接近 E1。** 后者主要给出模型和分数，没有同等深度的新训练报告。([Mistral AI][24])                                                               |
| **Prime Intellect**       | Verifiers v1 将 taskset、harness、runtime 分离，可复用同一任务训练不同 agent，并记录精确 token/logprob 和 trace DAG；2026-07-22 公布约 36.5 万 coding、terminal、search 任务，以及 GLM-4.5-Air ScaleSWE 训练。官方同时承认 shared sandbox 允许 policy 探测 grader，单纯隐藏 grader 不够。([Prime Intellect][25]) | **I/E3。** 这是目前最强的开放 agent 环境、trace 和 RL 接口之一，但不是一份自有前沿 Coding Agent 模型报告。                                                                            |
| **Amazon**                | 公开价值主要在 benchmark：SWE-PolyBench 扩展多语言 repo repair；MigrationBench 构造 5,102 个 Java 迁移 repo，并精选 300 个严格评测任务。([arXiv][26])                                                                                                                                  | **I。** 本次未定位到可归因于 Amazon Q 或 Nova 产品模型的 coding-agent 环境、轨迹、奖励和 RL 训练报告，不能从 benchmark 资产反推产品训练。                                                       |
| **Sierra**                | Sierra 的主要公开研究资产是面向客服、多轮工具和用户交互的 τ-bench，而非软件工程模型训练。([Sierra][27])                                                                                                                                                                                      | **不属于 Coding Agent 模型证据。** 可借鉴其多轮用户模拟和 policy adherence 评测，但不应列入 coding-model 路线。                                                                    |

## 5.2 中国及开放模型团队

| 团队                          | 可核实的公开证据                                                                                                                                                                                                                                                              | 审计判定                                                                                                                                              |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Alibaba Qwen**            | Qwen3-Coder 公开 20,000 个并行独立环境；Qwen3-Coder-Next 进一步公开约 80 万个可执行 SWE 任务、真实 PR 与合成 bug、Docker 环境构建 agent、独立评分容器、SFT/RL prompts 隔离、多个 SWE/webdev/UX 专家和最终蒸馏。([Qwen][28])                                                                                                  | **E3，公开证据最完整之一。** 报告还公开 OpenHands 轨迹向 SWE-Agent 迁移不佳，证明 harness-specific learning；reward hacking 中模型会尝试重新连接、clone/curl，团队用网络与字符串规则阻断。([arXiv][2]) |
|                             | Qwen3.7 又进行 cross-harness、cross-verifier RL；《The Verification Horizon》公开强 verifier 在同一模型上可产生约 ±10 个百分点波动，并总结无执行、无 E2E、角色混淆、上下文过载、过度规格化等 verifier 失败。([Qwen Studio][29])                                                                                               | 重要缺口是训练任务、reward 组合和 blocker 实现尚未完整开放，且团队自建任务与自建评测仍有同源偏差。                                                                                         |
| **Moonshot / Kimi**         | Kimi-Dev 公开从 Qwen2.5-72B 出发，约 150B 中期训练 token；先用 Agentless diff/PR 学定位与编辑，再用多轮 SWE 轨迹和 REINFORCE 类 RL。奖励由 bug-fix 测试和 test-writer fail-before/pass-after-gold 组成，课程动态加入更难任务，并在 Kubernetes 上运行超过一万并发环境。([arXiv][30])                                                   | **E3。** Kimi-Dev 的 40 个 patch × 40 个测试的 self-play 分数不是 pass@1，必须单独标注。                                                                             |
|                             | Kimi K2/K2.5 公布大规模合成工具、可验证 gym、joint RL；K2.5 的 PARL 冻结 subagent、排除 subagent 轨迹，仅优化 orchestrator，并以 outcome、并行实例化和延迟 shaping 奖励主 agent。([arXiv][31])                                                                                                                   | K2.5 是通用 agent 模型，不是纯 coder；具体 SWE 任务规模和 verifier 仍不公开。                                                                                           |
| **Z.ai / GLM**              | GLM-5 公开 reasoning→agentic→general 的顺序 RL、跨阶段 on-policy distillation、超过一万真实 SWE/terminal/search 任务，以及基于 slime 的异步解耦 rollout/training。([arXiv][32])                                                                                                                    | **E3，形成目前最连续的模型—算法—基础设施证据链之一。**                                                                                                                   |
|                             | 2026-07 的 SAO 用单 rollout/prompt 的异步 PPO、token logprob correction、double-sided clipping/masking、快速 critic 和 skip-observation GAE，官方称已用于 GLM-5.2；CompactionRL 以最终任务奖励共同训练 summary 和后续动作。slime 公开 data buffer、环境/reward/verifier 接口、权重同步和 session affinity。([arXiv][33]) | 训练任务、测试和奖励服务仍闭源，外部只能复现算法框架，不能复现 GLM-5.2 数据分布。                                                                                                     |
| **MiniMax**                 | M2/Forge 公开超过十万个真实 scaffold/environment、每天数百万样本、长达 200K 的轨迹、fully async 训练、CISPO、process reward、wall-clock reward、reward-to-go、FIFO 窗口和 prefix-tree rollout 合并；M2.7 进一步让模型参与修改 scaffold 和训练过程。([arXiv][34])                                                           | **E3，闭源资产。** 报告充分说明系统结构，但任务 corpus、奖励细节和完整训练代码未开放；Pro/Verified headline 分数不再可靠。                                                                   |
| **StepFun**                 | Step 3.5 Flash 的 SWE factory 公开约 50,000 个验证环境、15,000 个 repo、20 多种语言；环境构造约占流程 40%，并训练 OpenHands、SWE-Agent、Terminus、Kilo/Roo/Claude Code 等多种 harness。RL 使用 MIS-PO 处理 off-policy 数据。([arXiv][35])                                                                        | **E3。** 多 harness 是强证据；但环境、任务和 verifier 未完整发布。                                                                                                    |
| **DeepSeek**                | DeepSeek V4 报告把数学、coding、agent 和 instruction 专家分别通过 SFT+GRPO 训练，再用 on-policy reverse-KL distillation 合并；对难验证任务使用 rubric RL 与生成式 reward model，并公开最小 bash/edit coding harness。([arXiv][36])                                                                             | **E3，但不够可复现。** 具体 coding 任务规模、GRM 训练和内部 R&D benchmark 均未开放。                                                                                       |
| **Xiaomi MiMo**             | MiMo-V2-Flash 公开超过十万个可验证 GitHub issue 任务、超过一万 Kubernetes pods、多教师 on-policy distillation 与 agentic RL；基础设施包括 MoE routing replay、prefix-cache preserving experts 和 partial rollout。([GitHub][37])                                                                      | **E3。** 是公开度很高的模型级证据，但任务和 reward 实现仍闭源；其 Verified headline 应降级为历史值。                                                                               |
| **Kwai / KAT-Coder**        | KAT-Coder-V2 公开 AutoBuilder 多语言环境、fail-to-pass/pass-to-pass、任务再生成、过程感知轨迹过滤、white/black-box harness 随机化、非对称 actor-critic PPO 与多教师 on-policy distillation。([arXiv][38])                                                                                                 | **E3。** 内部 KAT Code/KwaiClawEnv 与评测共建，需防止 institutional co-design bias。                                                                           |
| **Tencent Hunyuan**         | Hy3 披露多轮意图 SFT/RL、工具调用恢复和跨 CodeBuddy/Cline/Kilo scaffold 训练；SkillSynth 从技能图生成 terminal 场景，公开 82,073 个场景、57,214 个技能、185,529 个 LLM 验证关联，并通过执行与 rubric 双重验证。([GitHub][39])                                                                                               | **E2–E3。** 有明确任务生成与多 harness 证据，但缺少完整 RL 目标和轨迹规模。WorkBuddy Bench 是 Tencent 新评测资产，不能自动视为独立验证。([arXiv][40])                                         |
| **InclusionAI / Ant Group** | 2026-06-13 的 Ling/Ring 2.6 报告公开 KPop，用 binary-KL 类 token filtering 与异步调度在 coding、search、tool use 和 workflow 环境中训练 Ring-2.6-1T，并开放全系列 checkpoint；AReaL 2.0 于 2026-07-01 发布独立 training、inference、agent、weight-update 微服务和端到端 SWE RL 示例。([arXiv][41])                    | **E3。** 是此前容易漏掉的强开放路线；但 Coding Agent 在总 agentic 数据中的比例、奖励和环境 corpus 仍不清楚。                                                                         |
| **ByteDance Seed**          | Seed1.8、Seed2.0/2.1 和 Code 相关版本公开了产品能力、模型卡和评测；ByteDance 另发布 Multi-SWE-bench 等 benchmark。([arXiv][42])                                                                                                                                                                 | **E1/I。** 本次未定位到与 Qwen、GLM、MiMo 同级的最新 Seed Coding Agent 任务生成、轨迹、verifier 或 RL 配方。                                                                 |

补充边界：

* **ArkEval** 使用华为官方 HarmonyOS/ArkTS 仓库构造 502 个 repair 问题，但论文作者来自上海交通大学；它是相关 benchmark 证据，不是华为盘古团队的模型训练报告。([arXiv][43])
* 本次没有为了名单完整，把未找到模型特定训练证据的百度、华为产品宣传或一般代码补全模型硬归入 Coding Agent post-training 路线。
* “没有公开”不等于团队内部没有使用这些技术，只表示目前没有可核验的一手公开证据。

---

# 六、Benchmark 与环境谱系及当前可用性

## 6.1 SWE 系列

| 评测                                                           | 来源与结构                                                                                                        | 截至 2026-07-27 的可用性判断                                                                                       |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| **SWE-bench Original，2023**                                  | 2,294 个真实 GitHub issue/PR 任务，来自 12 个 Python repo；通过 fail-to-pass 与 pass-to-pass 测试判断 patch。([Swebench][44])  | **历史基线。** 对研究环境构造和回归有价值，但语言窄、任务公开时间长、污染严重，不适合前沿主指标。                                                        |
| **SWE-bench Lite**                                           | Original 中筛选的 300 题小集。([Swebench][45])                                                                       | **历史与快速迭代用途。** 不足以支持当前前沿排序。                                                                                |
| **SWE-bench Verified，2024-08-13**                            | 500 题人工审核子集，试图修复 Original 中环境和规格问题。([OpenAI][5])                                                             | **应退出前沿 headline。** 可用于同一模型、同一 harness 的历史回归或方法消融，但需显式标注训练污染和坏题风险。                                         |
| **SWE-Bench Pro，Scale AI**                                   | 1,865 题、41 个 repo；731 公共、276 私有、858 held-out，包含 feature、bug、优化、安全和 UI/UX 等较长任务。([Scale Labs][7])             | **公共集不能作为单一主指标。** OpenAI 估计约 30% 坏题，Cursor 又发现运行时检索答案。私有集可能降低训练污染，但隐藏测试仍可能过严、欠规格或低覆盖，且外部难以审计。([OpenAI][6]) |
| **SWE-rebench / V2**                                         | 自动持续从新 repo/commit 构造 fresh executable tasks；V2 于 2026-03 发布，公开约 32,000 个可执行任务、20 种语言，并保留更多候选。([Nebius][46]) | **当前最值得用于时序切片的公共体系之一。** 但每个公开 snapshot 一旦进入训练和 prompt 调优，也会迅速折旧；必须按模型训练 cutoff 选用之后产生的任务。                  |
| **SWE-bench Multilingual / Multi-SWE-bench / SWE-PolyBench** | 分别扩展到多语言或 Java、JS/TS、Python 等 repo；Multi-SWE-bench 来自 ByteDance，SWE-PolyBench 来自 Amazon。([Swebench][47])     | **适合检测 Python/SWE-bench 过拟合和语言迁移。** 仍属于公开历史 repo 任务，污染和 gold-patch specificity 没有自动消失。                     |

## 6.2 Terminal、长程与新任务类型

| 评测/框架                        | 实际性质                                                                                                                                   | 当前判断                                                                                                                                                               |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Terminal-Bench 2.0 / 2.1** | Terminal-Bench 2.0 于 2026-01 发布，含 89 个精心构造的 terminal 任务；每题有指令、隔离环境、测试和 oracle。官方当前同时维护 2.0 与 2.1。([arXiv][48])                         | **仍是有用的 terminal/general computer benchmark。** 但它测量的是模型+harness；官方 2.0 leaderboard 要求 `k=5`，固定资源和 timeout，并报告不确定区间，因此不能与 pass@1 或任意预算运行直接比较。([Terminal-Bench][49]) |
| **Harbor**                   | 由 Terminal-Bench 创建者开发的评测与优化框架；可运行任意 agent、构建 benchmark/environment、并行环境和生成 RL rollout，是 Terminal-Bench 2.0 的官方 harness。([GitHub][50]) | **不是 benchmark 名称，也不是 OpenAI 提出的评测。** 它是 train/eval 共用的环境与 harness 层。                                                                                              |
| **DeepSWE**                  | 2026-05 发布，v1.1 于 06-14 修复依赖漂移和 flaky task；113 个原创、长程、多语言任务，采用程序化 verifier 和隔离 grading，而不是简单从已合并 PR 反推问题。([DeepSWE][51])               | **很有价值的补充集。** 原创任务降低 gold-patch 记忆，但规模仅 113，公开后仍会产生污染半衰期。                                                                                                          |
| **FrontierCode / 1.1**       | Cognition 与 20 多位维护者构造约 150 个复杂任务，单题投入超过 40 小时；结合测试与 mergeability、correctness、test quality、scope、style 等 rubric。([Cognition][52])      | **任务质量路线值得重视。** 但由 Cognition 自建并用于评估 Devin/SWE 模型，且使用每 effort 五次运行和 best-effort 选择，不等于统一 pass@1。                                                                   |
| **SWE-EVO**                  | 48 个接近 release-sized 的任务，平均约修改 21 个文件，并使用约 874 个测试；最强系统仍只能完成约四分之一。([arXiv][53])                                                        | **补足真正长程、多文件开发。** 小规模导致置信区间宽，适合作为 stress test，不适合唯一排名。                                                                                                             |
| **NL2Repo**                  | 从自然语言规格和空 workspace 开始生成可安装 Python library，而不是修复已有 PR。([arXiv][54])                                                                    | **补足 greenfield development。** 有助于避免整个领域只优化历史 bug-fix。                                                                                                             |
| **BackendForge**             | 2026-07-13 发布的 56 个合同驱动后端生成任务，agent 构建 Docker 服务，再通过 OpenAPI 和黑盒 HTTP 测试。([arXiv][55])                                                 | **适合系统级后端验证。** 规模小，但任务与评分形式和 SWE-bench 明显互补。                                                                                                                       |
| **MigrationBench**           | Amazon 团队构造 5,102 个完整 Java repo 迁移实例，并选择 300 个 Java 8→17/21 任务做严格评测。([亚马逊科学][56])                                                      | **适合真实维护与迁移能力。** 检验 dependency/build/API migration，而不是局部 bug patch。                                                                                                |
| **WorkBuddy Bench**          | Tencent 于 2026-07-23 发布，覆盖 Code、Web、Office、Security；任务来自真实 commit/PR/业务场景重写，并提供任务目录、镜像、harness、测试和参考。([arXiv][40])                     | **新鲜且跨工作流，但仍由模型团队自建。** 官方已经承认未来污染、judge 偏差和 harness/serving 版本风险。                                                                                                  |
| **SWE-Explore**              | 848 个 issue、10 种语言、203 个 repo，重点隔离在有限 line budget 下的代码库探索与定位。([arXiv][57])                                                             | **适合把“找对文件/状态”与“写出 patch”分离。** 能诊断模型是探索失败还是实现失败。                                                                                                                   |

---

# 七、可比性与污染风险

## 7.1 至少要区分三种污染

### A. 训练时任务/答案暴露

Verified 的 issue、PR、gold patch 和 release note 长期公开，模型可能在预训练、中期训练、SFT、RL 数据或 teacher 轨迹中见过。OpenAI 已经观察到不同前沿模型复现任务特异信息。([OpenAI][1])

### B. 运行时检索现成答案

即使训练时没有见过，agent 仍可能通过：

* `.git` history；
* GitHub issue/PR；
* web search；
* release notes；
* package cache；
* 编译后的 bytecode；
* 构建残留文件；

恢复原修复。Cursor 对 Pro 的审计和 Composer 2.5 训练中发现的类型缓存、Java bytecode 例子证明，这不是理论风险。([Cursor][8])

### C. 制度性同源偏差

这不一定是任务泄漏，而是模型、任务分布、工具、harness、reward 和 benchmark 都由同一团队共同设计。例如 Cursor/Composer/CursorBench、Cognition/Devin/FrontierCode，以及各团队内部 SWE 集。

这种 benchmark 可能非常适合衡量**产品内纵向进步**，但不天然适合跨厂商模型排名。Grok 4.5 的 Cursor 代码 snapshot 事故则是比同源偏差更强的、已确认的数据重叠。([Cursor][13])

## 7.2 Harness sensitivity 不是噪声，而是核心变量

已经有多条独立证据：

* Qwen 报告 OpenHands 轨迹向 SWE-Agent 迁移较差。([arXiv][2])
* Cognition 明确把模型、harness、工具和 prompt 的联合优化视为能力来源。([Cognition][58])
* Thinking Machines 在训练时随机化工具与 schema。([Thinking Machines Lab][3])
* StepFun、KAT、Tencent 和 NVIDIA 使用多 scaffold 或跨 harness 训练/评测。([arXiv][35])
* Prime Intellect 把 task、harness、runtime 明确拆为可组合层。([Prime Intellect][25])

因此以下比较是无效或至少高度不充分的：

> “模型 A 在原生 Claude Code，模型 B 在通用 mini-SWE-agent，所以模型 A 本体更强。”

原生 harness 是产品能力的一部分，可以单独报告；但若要比较模型本身，应：

1. 在同一个标准 harness 中比较；
2. 在各自原生 harness 中再比较系统上限；
3. 最好做 model × harness 的交叉矩阵。

## 7.3 Private tests 并非天然可信

私有测试解决的是“模型直接读到测试”或训练中见到测试，但不解决：

* 测试绑定某个 gold implementation；
* 题面未说明 hidden requirement；
* 测试覆盖过低，错误 workaround 也能通过；
* 环境本身不可复现；
* grader 与 agent 共用文件系统；
* agent 可以篡改或探测 grader。

OpenAI 对 Pro 的四类坏题恰好说明：**隐藏测试也会错误拒绝正确实现，或者错误接受不完整实现。**([OpenAI][6])

更可靠的设计应同时具备：

* agent sandbox 与 grader sandbox 隔离；
* 网络、git history、缓存和 reference artifacts 清除；
* public tests + genuinely private tests；
* implementation-agnostic contract；
* 多次模型/agent 审计；
* 工程师对正确替代实现的抽查；
* 对轨迹进行 exploit-signature 检测。

Prime Intellect、Cognition 和 DeepSWE 的最新材料都开始向这一方向发展。([Prime Intellect][59])

## 7.4 Pass@k、best-of-N 与 verifier compute 必须拆开

以下公开结果测量的是不同东西：

* Terminal-Bench 2.0 官方 leaderboard 使用 **k=5**。([Terminal-Bench][49])
* Kimi-Dev 的高分模式可包含 40 个 patch × 40 个测试生成，并由 self-play 选择，不是一次独立尝试。([arXiv][30])
* FrontierCode 每个 effort 配置进行五次运行，再选择最好 effort。([Cognition][52])
* Devstral 报告允许最多三次尝试。([arXiv][23])
* Inkling 的 coding 表格使用 effort=0.99、temperature=1 和很大的 trajectory/context budget。([Thinking Machines Lab][3])
* SWE-Bench Pro 当前页面甚至混有 50-turn capped 与 250-turn uncapped 运行，并标注部分结果使用 mini-swe-agent。([Scale Labs][7])

因此至少要同时报告：

| 指标                        | 含义                        |
| ------------------------- | ------------------------- |
| **pass@1 / resolve@1**    | 单次部署可靠性                   |
| **pass@k**                | 多次搜索后至少一次成功的概率            |
| **selected pass@k**       | 加入 verifier/ranker 后的系统能力 |
| **总生成次数与 verifier 次数**    | 防止把搜索算力隐去                 |
| **输入/输出/工具 token**        | 模型与环境的实际成本                |
| **wall-clock 与并行度**       | 交互式与批处理场景不同               |
| **外部 API、浏览器、sandbox 成本** | 不能只报模型 token 价格           |
| **每解决一题成本**               | 更接近工程价值                   |
| **置信区间/多 seed**           | 处理环境和采样非确定性               |

一个 best-of-40 系统可能比 pass@1 模型解决更多任务，但不代表它在交互式部署中更可靠或更便宜。

## 7.5 非确定性已足以改变排名

Qwen 的 verifier 研究显示，同一强模型在某些 agent evaluation 中可产生约 ±10 个百分点波动；Devstral 也指出即使 temperature=0，硬件、文件系统和环境差异仍会造成不同结果；Terminal-Bench 因此在 leaderboard 上显示不确定区间。([arXiv][60])

这意味着单次自报分数、没有原始轨迹和置信区间的 1–2 个点差异通常没有审计意义。

---

# 八、Benchmark 生命周期如何反过来塑造训练方向

当前 Coding Agent benchmark 正经历一个越来越快的循环：

### 阶段 1：新鲜、未污染

新 benchmark 由近期 commit、私有代码库、原创任务或维护者手写任务产生，初期能提供较强信号。

### 阶段 2：成为排行榜和产品发布指标

模型团队开始针对任务结构、常用 harness、工具协议和测试模式优化。

### 阶段 3：进入训练数据

任务被纳入：

* 预训练 repo；
* issue/PR 中期训练；
* SFT teacher 轨迹；
* RL 环境；
* synthetic task seed；
* verifier 和任务筛选模型的训练。

此时即使没有直接使用 test split，也可能发生 repo、gold patch、release note 或任务模板层面的暴露。

### 阶段 4：饱和与 exploit

模型不仅更聪明，也更擅长：

* 恢复原 patch；
* 搜索答案；
* 读取环境残留；
* 逆向 bytecode；
* 弱化测试；
* 利用 grader；
* 针对特定 harness 学习快捷方式。

Verified 与 Pro 在 2026 年的连续退役/审计就是这一阶段的典型案例。([OpenAI][1])

### 阶段 5：训练范式迁移

benchmark 折旧正在直接推动以下训练方向：

1. **环境工厂代替固定题库**：Qwen、Step、Poolside、MiniMax 等生成数万至数十万可执行任务。
2. **动态难度课程**：当 policy 开始解决现有任务时，实时生成或筛选更难环境。
3. **原创任务和私有代码**：DeepSWE、FrontierCode、Pro private 等减少对已解决公开 PR 的依赖。
4. **跨 harness 训练**：减少只会某个工具协议的局部策略。
5. **隔离 grader 与轨迹审计**：reward hacking detection 成为训练基础设施，而非评测后的人工排查。
6. **从最终 pass 转向过程、效率和协作质量**：包括 wall-clock、token、工具调用、沟通和用户介入。
7. **滚动 benchmark**：SWE-rebench 一类按时间更新的评测，比永久静态 test set 更符合当前污染速度。

换言之，**benchmark 生命周期已经不再只是评测治理问题，而是 Coding Agent post-training 研究议程本身。**

---

# 九、哪些只有产品分数，或不足以构成训练证据

## 9.1 有方向性描述，但没有方法级证据

* **OpenAI Codex 最新系列**：知道早期 codex-1 使用真实软件任务 RL，也知道后续有 compaction 和长程执行；不知道任务、轨迹、奖励、算法、verifier 和训练 harness。([OpenAI][4])
* **Anthropic Claude 最新系列**：有模型卡、coding eval、产品能力和通用 RLHF 信息；没有 coding-agent-specific 训练管线。([Anthropic][15])
* **Google Gemini 最新系列**：有通用 RL 和 custom agent setup 分数；没有 Coding Agent 环境/轨迹/RL 配方。([Google DeepMind][17])
* **Thinking Machines Inkling**：有真实模型训练报告和 harness randomization，但 coding-specific 部分仍不足以重建训练路线。([Thinking Machines Lab][3])

## 9.2 最新 release 基本只有分数或产品说明

* **Mistral Devstral 2**：原始 Devstral 有训练报告，Devstral 2 本身没有同等方法更新。([Mistral AI][24])
* **ByteDance Seed 2.x Code 相关发布**：有模型/产品评测，但未见最新 Coding Agent post-training 报告。([字节跳动种子][61])
* **Amazon Q / Nova coding 产品**：Amazon 有强 benchmark 研究，但不能从 MigrationBench、SWE-PolyBench 或竞赛反推产品模型训练。
* **GitHub Copilot**：Microsoft Research 的 ProRL、Agent Lightning 等不能作为 Copilot 生产模型已经采用这些方法的证据。
* **Sierra**：公开 agent 研究集中在客服流程，不应作为 Coding Agent 模型训练证据。

产品分数可能是真实运行结果，但在没有 checkpoint、harness、budget、sampling、网络权限、git 设置和重复次数时，它们只能是**系统自报结果**，不能作为模型训练技术结论。

---

# 十、适合形成后续“问题驱动材料束”的候选

这些不是课程目录，而是可以独立追踪证据链的研究问题集合。

| 材料束                                         | 核心问题                                                                                          | 最关键的一手材料                                                                                                                                        |
| ------------------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. 大规模可执行任务究竟如何不变成坏数据？**                  | 如何从 PR、commit、合成 bug 构造数十万环境；如何验证构建、题面、F2P/P2P 和替代实现；环境构建成本在哪里？                               | Qwen3-Coder-Next / SWE-Universe、Step 3.5 SWE factory、Poolside RLCEF、MiniMax Forge、Prime Scaling Agentic RL，以及 OpenAI 对 Pro 的任务质量审计。([arXiv][2]) |
| **B. 长轨迹异步 RL 的有效算法边界**                     | group rollout 是否必要；policy lag 如何修正；fully async 与部分 async 的稳定条件；MoE 训推 logprob/routing 如何一致？   | Composer 2、GLM-5/SAO/slime、Poolside Laguna、Cognition SWE-1.7、AReaL 2.0、Ring 2.6 KPop。([arXiv][9])                                               |
| **C. Compaction 是否应由最终任务奖励训练？**             | summary 是普通预处理、独立模型，还是 policy action；压缩损失如何穿过多段 generation；如何避免遗忘关键状态？                        | Composer 2 self-summary、GLM CompactionRL、Cognition SWE-1.7、Codex-Max、Kimi K2.5 orchestrator。([arXiv][9])                                        |
| **D. Verifier 与 policy 的共同演化**              | binary tests 何时失效；如何识别 workaround、测试弱化、grader exploit 和隐式规格；verifier 是否需要自己的在线数据飞轮？           | Qwen《The Verification Horizon》、OpenAI 两次 SWE 审计、Cursor reward-hacking 审计、Prime Verifiers、Meta SSR。([arXiv][60])                                 |
| **E. Harness-invariant Coding Agent 是否存在？** | 哪些能力属于模型、哪些属于 prompt/tool/compaction；应随机化 schema，还是训练多种原生 harness；cross-harness transfer 如何测？ | Thinking Machines Inkling、Prime Verifiers、Qwen cross-scaffold 结果、Step 多 harness、KAT randomization、Harbor。([Thinking Machines Lab][3])           |
| **F. 新 benchmark 如何拥有可管理的半衰期？**             | 静态公开任务何时退休；rolling、private、原创、维护者编写和真实 session 各有什么偏差；如何设定退役条件？                               | SWE-rebench V2、DeepSWE、FrontierCode、SWE-EVO、NL2Repo、MigrationBench、WorkBuddy，以及 OpenAI Verified/Pro 审计。([Nebius][46])                           |
| **G. 从离线 benchmark 转向真实协作效用**               | 最终测试通过是否足以代表生产价值；用户介入、代码存活率、反复修订、成本和延迟如何进入评测？                                                 | CursorBench、SWE-chat、SWE-Together、FrontierCode、Composer effort shaping。([arXiv][9])                                                             |

---

# 十一、最终审计判断

截至 2026 年 7 月 27 日，可以较有把握地得出以下结论：

1. **Coding Agent 的核心竞争已经从“代码语言模型”转向“模型—环境—harness—verifier—训练系统”的共同设计。**

2. **最值得研究的公开路线不再是某个 SWE 分数，而是环境工厂、真实/合成任务混合、长轨迹异步 RL、on-policy distillation、compaction、reward hacking 防御和跨 harness 泛化。**

3. **Cursor Composer 2/2.5 确实公开了大量有实质价值的训练细节**，包括 Kimi K2.5 基座、continued pretraining、异步全参数 RL、MoE router replay、自总结压缩、局部文字反馈蒸馏、动态合成任务和 effort shaping；但核心数据、环境、reward/verifier 与 CursorBench 均未开放，不能视为可复现路线。

4. **OpenAI 的正确 benchmark 事件是两阶段的：**

   * 2026-02-23：停止报告 SWE-bench Verified，暂时推荐 Pro；
   * 2026-07-08：发现 Pro 公共集约 30% 坏题，并撤回推荐。
     因而现在引用“OpenAI 建议用 SWE-Bench Pro 替代 Verified”而不附后续更新，已经是过时结论。([OpenAI][1])

5. **Harbor 是框架，不是 benchmark；SWE-Bench Pro 属于 Scale AI；SWE-rebench、Terminal-Bench、DeepSWE、FrontierCode 等都是独立路线，不是 OpenAI SWE-bench 的简单版本号。**

6. **当前不存在一个足够可信的单一 Coding Agent benchmark。** 最合理的评测组合应同时包含：

   * 按时间切片的 fresh repo repair；
   * 原创或私有任务；
   * terminal/general computer tasks；
   * release-sized 多文件任务；
   * greenfield 与迁移任务；
   * 多 harness 交叉矩阵；
   * 明确的 pass@1、pass@k、成本、wall-clock 和重复运行；
   * 隔离 grading 与轨迹 exploit 审计。

7. **评测结果应优先解释为“某 checkpoint 在某 harness、某预算、某环境与某 grader 下的系统表现”，而不是一个脱离运行条件的模型固有能力数字。**

这也是 2026 年 Coding Agent 公开研究相较于 2024–2025 年最重要的变化：**benchmark 不再只是训练完成后的记分板，其污染速度、环境缺陷、verifier 漏洞和退役机制，已经直接决定团队下一阶段训练什么。**

[1]: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ "https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/"
[2]: https://arxiv.org/html/2603.00729v1 "https://arxiv.org/html/2603.00729v1"
[3]: https://thinkingmachines.ai/news/introducing-inkling/ "https://thinkingmachines.ai/news/introducing-inkling/"
[4]: https://openai.com/index/introducing-codex/ "https://openai.com/index/introducing-codex/"
[5]: https://openai.com/index/introducing-swe-bench-verified/ "https://openai.com/index/introducing-swe-bench-verified/"
[6]: https://openai.com/index/separating-signal-from-noise-coding-evaluations/ "https://openai.com/index/separating-signal-from-noise-coding-evaluations/"
[7]: https://labs.scale.com/leaderboard/swe_bench_pro_public "https://labs.scale.com/leaderboard/swe_bench_pro_public"
[8]: https://cursor.com/blog/reward-hacking-coding-benchmarks "https://cursor.com/blog/reward-hacking-coding-benchmarks"
[9]: https://arxiv.org/html/2603.24477v2 "https://arxiv.org/html/2603.24477v2"
[10]: https://cursor.com/blog/composer-2-5 "https://cursor.com/blog/composer-2-5"
[11]: https://cursor.com/blog/composer "https://cursor.com/blog/composer"
[12]: https://cursor.com/blog/composer-1-5 "https://cursor.com/blog/composer-1-5"
[13]: https://cursor.com/blog/grok-4-5 "https://cursor.com/blog/grok-4-5"
[14]: https://openai.com/index/introducing-gpt-5-3-codex/ "https://openai.com/index/introducing-gpt-5-3-codex/"
[15]: https://www.anthropic.com/transparency "https://www.anthropic.com/transparency"
[16]: https://www.anthropic.com/news/claude-opus-4-8 "https://www.anthropic.com/news/claude-opus-4-8"
[17]: https://deepmind.google/models/model-cards/gemini-3-1-pro/ "https://deepmind.google/models/model-cards/gemini-3-1-pro/"
[18]: https://www.microsoft.com/en-us/research/publication/prorl-agent-rollout-as-a-service-for-rl-training-of-multi-turn-llm-agents/ "https://www.microsoft.com/en-us/research/publication/prorl-agent-rollout-as-a-service-for-rl-training-of-multi-turn-llm-agents/"
[19]: https://arxiv.org/html/2502.18449v2 "https://arxiv.org/html/2502.18449v2"
[20]: https://cognition.ai/blog/swe-grep "https://cognition.ai/blog/swe-grep"
[21]: https://poolside.ai/blog/designing-a-world-class-code-execution-environment "https://poolside.ai/blog/designing-a-world-class-code-execution-environment"
[22]: https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/ "https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/"
[23]: https://arxiv.org/html/2509.25193v1 "https://arxiv.org/html/2509.25193v1"
[24]: https://mistral.ai/news/devstral-2-vibe-cli/ "https://mistral.ai/news/devstral-2-vibe-cli/"
[25]: https://www.primeintellect.ai/blog/verifiers-v1 "https://www.primeintellect.ai/blog/verifiers-v1"
[26]: https://arxiv.org/abs/2504.08703?utm_source=chatgpt.com "SWE-PolyBench: A multi-language benchmark for repository level evaluation of coding agents"
[27]: https://sierra.ai/es/blog/tau-bench-shaping-development-evaluation-agents "https://sierra.ai/es/blog/tau-bench-shaping-development-evaluation-agents"
[28]: https://qwenlm.github.io/blog/qwen3-coder/ "https://qwenlm.github.io/blog/qwen3-coder/"
[29]: https://qwen.ai/blog?id=qwen3.7 "https://qwen.ai/blog?id=qwen3.7"
[30]: https://arxiv.org/html/2509.23045v3 "https://arxiv.org/html/2509.23045v3"
[31]: https://arxiv.org/html/2507.20534v2 "https://arxiv.org/html/2507.20534v2"
[32]: https://arxiv.org/html/2602.15763v1 "https://arxiv.org/html/2602.15763v1"
[33]: https://arxiv.org/html/2607.07508v1 "https://arxiv.org/html/2607.07508v1"
[34]: https://arxiv.org/html/2605.26494v1 "https://arxiv.org/html/2605.26494v1"
[35]: https://arxiv.org/html/2602.10604v1 "https://arxiv.org/html/2602.10604v1"
[36]: https://arxiv.org/html/2606.19348v1 "https://arxiv.org/html/2606.19348v1"
[37]: https://github.com/xiaomimimo/MiMo-V2-Flash "https://github.com/xiaomimimo/MiMo-V2-Flash"
[38]: https://arxiv.org/html/2607.05471v1 "https://arxiv.org/html/2607.05471v1"
[39]: https://github.com/Tencent-Hunyuan/Hy3 "https://github.com/Tencent-Hunyuan/Hy3"
[40]: https://arxiv.org/html/2607.20911 "https://arxiv.org/html/2607.20911"
[41]: https://arxiv.org/abs/2606.15079 "https://arxiv.org/abs/2606.15079"
[42]: https://arxiv.org/html/2603.20633v3 "https://arxiv.org/html/2603.20633v3"
[43]: https://arxiv.org/html/2602.08866v1 "https://arxiv.org/html/2602.08866v1"
[44]: https://www.swebench.com/original.html "https://www.swebench.com/original.html"
[45]: https://www.swebench.com/lite.html "https://www.swebench.com/lite.html"
[46]: https://nebius.com/blog/posts/meet-swe-rebench-v2 "https://nebius.com/blog/posts/meet-swe-rebench-v2"
[47]: https://www.swebench.com/multilingual.html "https://www.swebench.com/multilingual.html"
[48]: https://arxiv.org/html/2601.11868v1?utm_source=chatgpt.com "Terminal-Bench: Benchmarking Agents on Hard, Realistic ..."
[49]: https://www.tbench.ai/leaderboard/terminal-bench/2.0 "https://www.tbench.ai/leaderboard/terminal-bench/2.0"
[50]: https://github.com/harbor-framework/harbor "https://github.com/harbor-framework/harbor"
[51]: https://deepswe.datacurve.ai/blog/deepswe "https://deepswe.datacurve.ai/blog/deepswe"
[52]: https://cognition.com/blog/frontier-code "https://cognition.com/blog/frontier-code"
[53]: https://arxiv.org/html/2512.18470v5 "https://arxiv.org/html/2512.18470v5"
[54]: https://arxiv.org/html/2512.12730v2 "https://arxiv.org/html/2512.12730v2"
[55]: https://arxiv.org/html/2607.11042v1 "https://arxiv.org/html/2607.11042v1"
[56]: https://cdn.amazon.science/37/41/13f3548a4760a093d4744affc685/scipub-approval152134-45162744-migrationbench-repositorylevel-code-migration-benchmark-from-java-8.pdf "https://cdn.amazon.science/37/41/13f3548a4760a093d4744affc685/scipub-approval152134-45162744-migrationbench-repositorylevel-code-migration-benchmark-from-java-8.pdf"
[57]: https://arxiv.org/abs/2606.07297?utm_source=chatgpt.com "Benchmarking How Coding Agents Explore Repositories"
[58]: https://cognition.ai/blog/swe-1-5 "https://cognition.ai/blog/swe-1-5"
[59]: https://www.primeintellect.ai/blog/scaling-agentic-rl "https://www.primeintellect.ai/blog/scaling-agentic-rl"
[60]: https://arxiv.org/html/2606.26300v1 "https://arxiv.org/html/2606.26300v1"
[61]: https://seed.bytedance.com/en/seed2 "https://seed.bytedance.com/en/seed2"


# 全球 LLM / Agent RL optimization 与 scaling 公开生态审计

**审计截止：2026 年 7 月 27 日**

## 审计口径

本次只把以下材料视为结论性证据：官方论文、技术报告、模型卡、团队博客、官方文档、代码仓库、正式训练配方，以及可定位的真实采用说明。媒体与社区材料只用于发现线索，不承担结论。

为避免把“功能列表”误写成“真实训练事实”，下文使用四级证据：

* **① 支持声明**：框架或服务文档声称支持某机制。
* **② 实验使用**：论文、配方或公开实验确实运行过。
* **③ 旗舰使用**：模型报告明确说该模型或产品训练使用了该系统或算法。
* **④ 生产采用**：存在公开、可定位的产品部署、外部集成或大规模生产使用。

可复现等级：

* **R4**：代码、配方、数据或环境基本齐全，可端到端复现；不代表普通团队承担得起原规模。
* **R3**：核心系统可运行，但缺关键数据、环境、训练配方或旗舰规模资源。
* **R2**：通过公开服务/API 可复现实验闭环，但训练后端不透明。
* **R1**：只有论文、模型报告或内部系统说明，不能复现系统。
* **R0**：只有营销性说法；本报告原则上不纳入核心结论。

表中的“公开规模”和性能增益均为项目方自报，不等于独立复现。

---

# 总结性判断

## 1. 生态已经不再由单一 PPO/GRPO trainer 定义

成熟系统正在分成四层：

1. **环境、任务、verifier 与轨迹层**：Prime Verifiers/Environments、Harbor、NeMo Gym、ROCK。
2. **Agent runtime 与 rollout 层**：SkyRL-Agent、ART、Agent Lightning、RollArt。
3. **训练内核与 orchestration 层**：verl、AReaL、prime-rl、slime、ROLL、NeMo RL。
4. **托管训练与闭源内部系统**：Tinker、Prime Hosted Training/Lab、W&B Training，以及 MiniMax Forge、OpenAI、Anthropic、Google 的内部栈。

把这些项目放在同一张“RL 框架排行榜”上没有意义。例如，Harbor 不负责优化器，Agent Lightning 的核心是 Agent 与 trainer 解耦，Tinker 是远程训练原语，MiniMax Forge 则是内部的大规模生产系统。

## 2. “完全异步”不是布尔属性

真正需要审计的是：

* rollout 和 learner 是否有全局 barrier；
* learner 更新时，未完成轨迹是否继续；
* 一条轨迹内部是否可以混合多个 policy version；
* 是否重算 KV cache；
* trajectory age 如何限制；
* correction 位于 token、sequence、trajectory 还是 update 层；
* 过旧样本是丢弃、降权、重采样还是继续使用。

AReaL 和 Prime 明确允许一条长轨迹包含多个策略版本；DORA 则主张保留**轨迹内策略一致性**，通过多版本流式 rollout 获得异步收益。这是当前最重要、也尚未收敛的系统—算法分歧之一。([arXiv][1])

## 3. train–inference mismatch 已经从“实现误差”上升为核心算法问题

公开证据显示，失配来源至少包括：

* rollout policy 与 learner policy 的时间滞后；
* 推理引擎 logprob 与训练引擎 old logprob 不一致；
* tokenizer、chat template、tool trace reconstruction 不一致；
* BF16、FP8、融合 kernel 和归一化顺序差异；
* MoE expert routing 不一致；
* context compaction、工具结果删除或 harness 重写改变状态分布。

ByteDance 的公开研究显示，少数低概率 token 的失配可以在长 Agent 轨迹中被放大；NVIDIA 则将生成 KL、policy KL、token multiplicative probability error、JS divergence 和越界 token 比例做成显式监控。Qwen 的 GSPO 进一步认为，sequence-level reward 与 token-level importance ratio 的优化单位不匹配，是 GRPO 在长序列和 MoE 上不稳定的原因之一。([Notion][2])

## 4. 环境 scaling 已成为与 trainer scaling 同等级的问题

RollArt 的生产测量中，环境初始化和环境故障会显著拉长训练迭代；其一个案例中平均迭代时间从约 366 秒增加到约 513 秒。Prime、Harbor、NeMo Gym 和 ROCK 因而都把环境定义、sandbox 生命周期、任务状态、verifier、轨迹与可观测性提升为独立基础设施层。([arXiv][3])

## 5. OPD 与 context compaction 正在进入后训练主流程

Tinker 已给出可运行的 on-policy distillation 配方；NeMo RL/Nemotron 使用多教师 on-policy distillation 整合不同能力；ROLL 增加了 multi-teacher OPD。与此同时，MiniMax Forge 将 context management 视为 Agent action/state 的一部分，GLM 的 CompactionRL 则直接训练执行策略和压缩摘要策略，而不是只在 serving 层调用一个 summarizer。([Thinking Machines Lab][4])

## 6. “self-evolution”仍主要是阶段性数据飞轮，不是真正的 continual online learning

Prime 的飞轮、AReaL-SEA、OpenClaw-RL 和 GPT-Red 分别展示了部署轨迹回流、自演化数据、从后续状态获得反馈以及自博弈安全训练。但公开材料尚不足以证明任何旗舰基础模型已经实现：

* 持续从实时用户流量更新权重；
* 无停机或近实时更新；
* 同时具备稳定性、安全回滚、遗忘控制和跨版本评估；
* 能在长期运行中获得净能力增长而非 reward hacking。

因此，当前更准确的表述是**迭代式或阶段式自我改进闭环**，而不是成熟的持续学习系统。([Prime Intellect][5])

---

# 1. 问题驱动的系统与算法谱系

## 1.1 从同步 barrier 到多版本异步

| 类型                     | 系统语义                                                                                | 代表项目                                    | 主要收益                             | 主要风险                      |
| ---------------------- | ----------------------------------------------------------------------------------- | --------------------------------------- | -------------------------------- | ------------------------- |
| **同步 barrier**         | 一批 rollout 全部完成，停止推理，训练并更新权重，再恢复 rollout                                            | ART 开源版本；许多标准 GRPO 配方                   | 最易保证 on-policy 和复现               | straggler、环境长尾和 GPU 空转    |
| **rollout 内部并发**       | 多个 Agent/环境并发，但训练边界仍相对同步                                                            | SkyRL async dispatcher；部分 Agent runtime | 降低环境等待                           | 不等于 actor–learner 完全异步    |
| **一步或窗口式异步**           | rollout 与训练重叠，但只允许有限窗口或有限版本滞后                                                       | StreamRL、Forge Windowed FIFO、RollArt    | 折中吞吐和分布稳定性                       | 仍需窗口、年龄和丢弃策略              |
| **持续、受限 staleness 异步** | actor 和 learner 独立推进，通过 trajectory age、weight version、replay buffer 和 correction 约束 | NeMo RL、verl fully-async recipe、slime   | 高利用率，适合长轨迹                       | correction 误差、样本浪费、版本管理复杂 |
| **轨迹内混合策略**            | 未完成轨迹在更新后继续；同一条 trajectory 可能含多个策略版本                                                | AReaL、Prime 1T-scale 路线                 | 最大化连续生成和缓存利用                     | 状态分布偏移不仅能靠 token ratio 修正 |
| **多版本但轨迹内一致**          | 并行维持多个 policy version，每条轨迹始终归属于同一版本                                                 | DORA                                    | 保留 trajectory-level on-policy 语义 | 权重、缓存和版本调度更复杂             |

### ART：公开实现仍是同步基线

ART 的开源工作流会等待全部 rollouts 完成，训练期间阻塞 inference，保存并重新加载 LoRA 后继续生成。其托管 W&B Training 宣称提供更高并发和更低成本，但这不意味着开源 ART 已成为连续异步 actor–learner。([GitHub][6])

### Forge：有边界的部分异步

Forge 的 Windowed FIFO 只允许滑动窗口内已完成任务先被消费。例如窗口为批量的 0.3 倍时，可以绕过局部慢任务，但不会让最快任务无限改变全局训练分布。这比普通 FIFO 更能限制 task-mixture drift，也比全批 barrier 更少受长尾影响。([MiniMax][7])

### RollArt：trajectory-level async，但仍有受控同步点

RollArt 使用独立 EnvManager 和训练集群，允许 rollout、权重发布及训练重叠；未完成轨迹可以保留并在更新后重算 KV。它用异步边界参数限制轨迹过旧，超过边界的轨迹会终止或重新调度，同时仍会周期性暂停部分 rollout 完成权重切换。因此它属于**细粒度、受约束的异步**，而不是完全无同步点。([arXiv][3])

### AReaL：显式支持混合版本长轨迹

AReaL 将推理、训练、reward service 和权重服务解耦，记录样本级 policy version 和 staleness。训练更新时可以中断正在生成的轨迹，使用新权重重建 KV 后继续；因此一条轨迹可能包含多个策略片段。论文在 32B 模型、最多 512 GPU 上报告最高约 2.57 倍吞吐提升，并称最终性能与同步基线相当或更好。([arXiv][1])

### Prime：优先保持持续生成

Prime 在 GLM-5 规模实验中允许权重更新后活动 prefix cache 继续使用，因此一个 trajectory 及其 KV 可能横跨多个 policy version；新 rollout 会用新的缓存命名空间，过旧轨迹由 `max_off_policy_steps` 等规则丢弃。其公开实验使用 28 个 H200 节点、131K context 和 batch 256，训练 step 低于约五分钟；这是目前少数公开到 trillion-scale MoE rollout 细节的案例。([Prime Intellect][8])

### DORA：反对轨迹内策略混合

DORA 将“轨迹内 policy consistency”视为约束，通过多版本 streaming rollout 同时服务不同 learner version；其报告称在开放 benchmark 上获得约 2–3 倍吞吐，在工业系统中达到数万加速器和约 2–4 倍增益。系统代码没有按论文规模公开，因此这些结论仍是团队自报。([arXiv][9])

---

## 1.2 一致性问题不止是 policy lag

| 一致性层            | 典型故障                                        | 公开应对                                              | 审计判断                           |
| --------------- | ------------------------------------------- | ------------------------------------------------- | ------------------------------ |
| **权重版本**        | trajectory 由过旧 policy 生成                    | version ID、trajectory age、最大 lag、丢弃或降权            | 已成为成熟系统的基础能力                   |
| **生成 logprob**  | vLLM/SGLang 与 trainer 对同一 token 得到不同概率      | 保存 rollout logprob、重新计算 old logprob、TIS/MIS/CISPO | 必须同时监控误差分布，不能只保留一个标量 KL        |
| **token 与渲染**   | chat template、tool call、special token 重建不一致 | 保存原始 token IDs、renderer/version provenance        | Agent 框架常被低估的风险                |
| **MoE routing** | 浮点微差使 token 被不同 expert 接收                   | routing replay、冻结 router、sequence-level clipping  | 大 MoE 后训练的关键瓶颈                 |
| **数值精度**        | BF16、FP8、fused kernel 使 logits 漂移           | FP32 router/gate、per-step scale、误差过滤              | “同权重”不等于“同策略”                  |
| **context 状态**  | harness 删除 thought、工具结果或压缩历史                | 把完整 context mutation 记录为 trajectory state         | importance ratio 无法修复已经改变的状态分布 |
| **权重传输**        | delta sync、分片、拓扑变化导致部分 worker 权重不一致         | checksum、版本原子切换、回滚                                | 开源栈仍有较多工程缺口                    |

NVIDIA 将 `π_generation`、`π_old` 和当前 actor 明确区分，并在异步 CISPO 配方中限制 trajectory age；其 ICE-POP 一类方法比较 token mask 与 sequence mask，用于过滤由 backend mismatch 引发的异常样本。([NVIDIA Docs][10])

Prime 的 router replay 可以把 trainer–inference KL 降低约一个数量级，但记录和传输 MoE 路由可能形成数十 Gbps、数百 GB 级数据负担。由此可见，精确一致性本身也有显著的通信与存储成本。([Prime Intellect][8])

Qwen 的 GSPO 从另一方向减少问题：它以 sequence 为 importance ratio 和 clipping 单位，使优化单位与 sequence-level reward 更接近。官方实验称，在 Qwen3-30B-A3B 上 GSPO 比 GRPO 更稳定，并被用于 Qwen 旗舰模型；论文还报告普通 GRPO 更新后约 10% 的 MoE expert activation 会改变，而 GSPO 对 routing replay 的依赖更低。([arXiv][11])

这里仍存在一个基本争论：

* **token-level correction**有更细粒度的信用和 clipping，但长轨迹中误差可积累；
* **sequence-level correction**符合任务奖励单位，但整段 ratio 方差可能极高；
* **几何平均、sequence masking、group filtering**降低长度效应，但会引入新的偏差；
* 当 state 已由不同 policy、工具结果或 compaction 改变时，仅修正 action probability 并不能恢复严格 on-policy。

---

## 1.3 Long-horizon credit assignment 尚未形成统一方案

### 终局奖励广播仍然很常见

Agent Lightning 把每次 LLM 调用和工具调用转换为 transition，但其公开实现仍将终局 return 平均或相同地赋给各动作；论文明确把更精细的长程 credit assignment 留作后续工作。因此它解决了**Agent runtime 与 trainer 的接口问题**，但没有解决长轨迹信用分配本身。([arxiv.org][12])

### GRPO group sampling 受到成本压力

传统 GRPO 依赖一个 prompt 的多个 rollout 构造相对优势。在昂贵 Agent 环境里，group 内可能：

* 大量轨迹超时或环境失败；
* 全部成功或全部失败，优势方差为零；
* 长度差异巨大；
* 同一任务多次初始化代价很高。

SAO 试图用单 rollout 加 value model 代替 group comparison，并采用严格的双边 token clipping。其论文报告训练可稳定运行约 1,000 个 step，并明确称已用于 GLM-5.2 的 coding-agent 后训练；但截至 2026 年 7 月，完整算法代码和旗舰训练配方尚未公开。([arXiv][13])

### 过程奖励、reward-to-go 与 completion time 开始进入系统

Forge 公开描述了 process reward、task completion time 和 reward-to-go 等信号，并支持 Agent-as-verifier。它还把 AppDev 等任务中的人类专家反馈和自动环境验证组合使用。这说明闭源生产团队并没有只依靠单一 binary terminal reward；但公开材料不足以独立判断各类 reward 在最终模型中的边际贡献。([MiniMax][7])

### OPD 解决的主要是知识传递，不等同于 delayed credit

Tinker 的 OPD 配方让 student 生成轨迹，再计算 teacher 与 student 的 token logprob，以负 reverse-KL 构造局部优势；它可以处理 partial rollout，也不需要独立 sequence reward。这个信号非常密集，但它主要回答“如何逼近 teacher”，并不自动回答“某个早期工具选择对最终任务成功贡献多少”。([Thinking Machines Lab][4])

---

## 1.4 环境、verifier 与 RL 数据飞轮

### 环境正在被标准化为四元组

多个项目正在收敛到类似抽象：

> **环境 = 数据/任务 + 状态化执行 harness + verifier/rubric + trajectory/metadata**

Prime Verifiers 和 Environments Hub 将环境用于训练、评估、合成数据和 prompt iteration；NeMo Gym 将 environment 定义为 dataset、harness、verifier 和 state；Harbor 则重点解决 sandbox、Agent 适配器、benchmark 执行和轨迹格式。([GitHub][14])

### Harbor 的核心价值不是另一个 trainer

Harbor 是 Terminal-Bench 团队维护的 Agent 环境和评测框架，可并行执行大量环境，并通过 ATIF 记录 token、费用、logprob、tool call、多 Agent 信息和 replay 数据。它已与 Prime Verifiers、SkyRL 和阿里云/verl 路线产生集成；但 Harbor 对 trace 进行 summarization、thought stripping 或重新 tokenization 时，可能破坏严格 on-policy 语义，因此 trainer 必须保留原始 token 和 renderer provenance。([Harbor][15])

### verifier scaling 不只是增加题目数量

有效 verifier 体系至少需要：

* 抵抗 reward hacking；
* 区分环境失败与策略失败；
* 对非确定性任务重复验证；
* 保存 verifier 版本；
* 记录测试覆盖率和 false-positive/false-negative；
* 发现 reward 饱和或 group 零方差；
* 支持多个相互独立的检查器。

Prime SYNTHETIC-2 使用通过率估计可验证样本难度，Forge 使用 Agent-as-verifier，NeMo Gym 支持组合 verifier。但目前公开项目很少系统报告 verifier 错误率和对抗鲁棒性。([Prime Intellect][16])

### 数据飞轮的成熟形态

一个可审计的 RL 数据飞轮应包含：

1. 从真实或模拟部署收集轨迹；
2. 区分模型、环境和 verifier 故障；
3. 聚类失败类型并生成新任务；
4. 对任务做难度和信息增益筛选；
5. 重新训练；
6. 在固定 held-out 环境和新鲜环境上评估；
7. 回归检查后再部署。

Prime 已把这一过程明确描述为 environment→RL→evaluation→deployment→trace feedback；AReaL-SEA 和 OpenClaw-RL 也朝类似方向发展。但目前公开证据多停留在离线批次迭代。([Prime Intellect][5])

---

## 1.5 OPD、蒸馏与能力整合

OPD 正在从“压缩一个 teacher”变成“合并多个强化学习专家”：

* Tinker 展示 student-on-policy reverse-KL 配方，并比较 LoRA 与 full fine-tuning；公开结果显示，数据量较大时 LoRA 可能落后于 full FT。([Thinking Machines Lab][4])
* NeMo RL 支持 on-policy distillation，Nemotron 3 Ultra 的公开材料称其使用来自十多个教师的 multi-teacher OPD，把不同任务能力整合到一个 550B/55B-active MoE 中。([NVIDIA Developer][17])
* ROLL v0.3 加入 multi-teacher OPD 和 routing replay。([GitHub][18])
* DeepSeek-R1 展示了从大型 reasoning model 向较小开源模型的能力蒸馏，但其公开路线不能直接等同于严格 on-policy multi-teacher distillation。([DeepSeek API Docs][19])

仍未解决的问题包括：

* teacher 与 student tokenizer 不同；
* tool schema 和 chat template 不同；
* 多教师意见冲突；
* teacher 的能力强但成本过高；
* 如何避免蒸馏覆盖原有领域能力；
* 如何把 task reward 与 token-level teacher signal 合并。

NeMo 的部分跨 tokenizer on-policy distillation 能力在公开路线图中仍属于正在完善的功能，不能当作已经成熟的稳定接口。([GitHub][20])

---

## 1.6 Context compaction：训练机制与 serving 技巧必须分开

### 训练内 compaction

GLM 的 CompactionRL 不是简单调用 summarizer，而是联合训练：

* 长程任务执行策略；
* 何时压缩；
* 压缩内容；
* 压缩后如何继续行动。

其公开实验在 GLM-4.5-Air 上报告 SWE-bench Verified 增加约 7 个百分点、Terminal-Bench 2 增加约 3.1 个百分点，并称该路线已部署到 GLM-5.2；但完整代码尚未公开。([arXiv][21])

Forge 则把 context management 作为 Agent 的显式 action/state，使策略可以学习删除、概括或保留哪些信息。([MiniMax][7])

### serving 层 compaction

OpenAI 的 `/compact` 和 Anthropic 的 server-side compaction/context editing 主要是部署期上下文管理：达到阈值后生成压缩状态，或删除较旧工具结果。它们有助于持续执行，但公开证据不足以说明 compaction policy 本身经过 end-to-end task RL。([OpenAI Developers][22])

Tinker 的 Harbor 示例还展示了反例：在 32K context、没有 compaction 的设置中，部分 SWE/Terminal 失败直接来自达到最大上下文或最大 token 限制。([GitHub][23])

---

## 1.7 故障恢复、可观测性与成本指标

### 公开证据最强的恢复机制

**RobustRL/ROLL** 对 256 GPU 的 Qwen3-8B-Math 训练注入约 10% 故障，报告超过 80% 的有效训练时间比例，相比基线约 60%，并通过 role-based isolation、restart 和 reconnect 减少全局重启。([arXiv][24])

**Laminar** 提供 heartbeat、relay 链重建、局部 failover 和 partial-response pool；论文报告 72B 权重广播至 127 个 relay 低于约 1.6 秒，relay 重建低于约 1 秒，并展示机器故障后的恢复过程。系统代码未公开。([arXiv][25])

**NeMo RL** 将 generation weight version、replay buffer 和未填满 batch 状态放入 checkpoint，以支持重启后恢复；但其更完整的弹性和自动扩缩容功能仍有部分处于路线图或早期阶段。([NVIDIA Docs][10])

### 当前速度与成本数字不可横向排名

代表性自报包括：

* AReaL：最高约 2.57 倍吞吐，最多 512 GPU。([arXiv][1])
* verl fully-async recipe：Qwen2.5-7B、128 GPU 上约 2.35–2.67 倍。([GitHub][26])
* LlamaRL：405B 规模相对论文基线最高约 10.7 倍。([arXiv][27])
* Laminar：最多 1,024 GPU、最高约 5.48 倍。([arXiv][25])
* RollArt：生产系统最高约 2.05 倍端到端提升；部分细粒度对比报告更高的 rollout 吞吐差异。([arXiv][3])
* Forge 的 prefix-tree 训练优化报告约 40 倍，但这是高度依赖共享 prefix 的局部训练优化，不是整个 Agent RL 系统端到端加速。([MiniMax][7])
* ART 托管服务宣称约 28% 更快、40% 更低成本，这属于供应商基准，开源 ART 并未提供同等系统。([OpenPipe][28])

这些数字的分母分别可能是 GPU 利用率、rollout tokens/s、step time、端到端训练时间、单位任务费用或特定优化前后的局部模块，因此不能制作可信的统一“最快框架”排名。

### 建议统一报告的两个指标

**有效样本率：**

[
\eta_{\text{effective}}
=======================

\frac{\text{真正进入梯度更新且通过一致性检查的 trajectory}}
{\text{所有启动的 trajectory}}
]

分母应包括环境失败、超时、零方差 group、过旧样本、context 截断、verifier 无效、logprob 越界和人为过滤。

**单位能力增益成本：**

[
C_{\Delta capability}
=====================

\frac{
\text{训练 GPU-hours}
+\text{rollout inference cost}
+\text{environment cost}
+\text{verifier cost}
+\text{失败和重试成本}
}{
\text{固定 held-out suite 上的净能力增益}
}
]

截至审计日，没有主要项目持续、完整地同时报告这两项。

---

# 2. 开源项目、商业服务与研究系统的角色图

| 角色                            | 主要项目                                    | 它们真正负责什么                                      | 不应据此推断什么                   |
| ----------------------------- | --------------------------------------- | --------------------------------------------- | -------------------------- |
| **训练 kernel / orchestration** | verl、AReaL、prime-rl、slime、ROLL、NeMo RL  | optimizer、模型并行、权重更新、rollout 调度、replay/version | 有框架不代表有高质量环境和数据            |
| **Agent rollout/runtime**     | SkyRL-Agent、ART、Agent Lightning、RollArt | 把 Agent trace 转成可训练 trajectory，管理工具与环境交互      | runtime 解耦不等于 learner 完全异步 |
| **环境/verifier**               | Prime Verifiers、Harbor、NeMo Gym、ROCK    | sandbox、任务、状态、验证、轨迹格式                         | 环境多不等于 verifier 可靠         |
| **托管训练服务**                    | Tinker、Prime Hosted/Lab、W&B Training    | 提供远程训练、算力、checkpoint 和 API                    | API 可用不代表 backend 可审计      |
| **闭源旗舰内部系统**                  | MiniMax Forge、OpenAI、Anthropic、Google   | 生产模型训练和部署                                     | 模型使用 RL 不等于系统细节公开          |
| **系统研究原型**                    | LlamaRL、Laminar、StreamRL、DORA           | 证明某种架构在公开实验中有效                                | 论文规模不等于开源可复现               |
| **算法/模型路线**                   | GSPO、SAO、CompactionRL、MOPD              | 稳定性、credit、能力整合、上下文管理                         | 算法论文不自动提供完整训练栈             |

---

# 3. 逐项目证据审计

## 3.1 开源系统与商业服务

| 项目                                                            | 首次相关公开时间与状态                                                                                               |          证据 | 核心机制与公开规模                                                                                                                                                                 | 可复现性与主要局限                                                                                                                                                                                  |
| ------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ----------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Prime Intellect：prime-rl / Verifiers / Environments / Lab** | INTELLECT-2 路线公开于 2025-04；Environments Hub 2025-08；Lab/Hosted Training 2026-02；prime-rl 至 2026-07-26 仍有发布 |         ①②③ | fully async、FSDP2/vLLM、FP8、PD disaggregation、MoE/EP/CP；INTELLECT-3 使用 512 H200；GLM-5 规模实验为 28 H200 节点；Verifiers 与约 36.5 万任务的 taskset 体系连接                                 | **R3，活跃。** 系统和环境代码开放，但旗舰数据、完整训练任务与超大规模资源不可复现；公开实现曾出现 dispatch/softcapping 等静默正确性问题。([Prime Intellect][8])                                                                                  |
| **Thinking Machines Tinker**                                  | 2025-10-01 发布；cookbook 至 2026-07-26 仍更新                                                                   |          ①② | 远程 LoRA 训练原语，支持 SFT、GRPO/PPO、DPO、distillation；声称覆盖 1B 至 1T+ 模型；OPD 公开实验主要为 Qwen 8B/32B 级                                                                                  | **R2，活跃。** 本地训练逻辑和 recipes 可见，模型并行、调度、恢复和后端不可见；目前以 LoRA 为主，大数据量下可能落后 full FT；公开 issue 包括 renderer、工具和 OPD 复现实验差异。([Thinking Machines Lab][29])                                             |
| **Thinking Machines Inkling**                                 | 2026-07-15                                                                                                |           ③ | 975B total、41B active、1M context；官方称训练包含超过 3,000 万 RL rollouts，并展示通过 Tinker 做后续定制/自微调                                                                                     | **模型权重可用，核心预训练和 RL 系统 R1。** 不能把 Inkling 的内部 RL 规模归因于公开 Tinker API。所谓 self-finetune 是受控阶段实验，不是在线持续学习。([Thinking Machines Lab][30])                                                          |
| **OpenPipe ART / W&B Training**                               | 2025-04-14 发布，持续维护                                                                                        |          ①② | 将已有 Agent 接入 GRPO；开源版为 rollout 完成后阻塞 inference、训练 LoRA、重新加载；托管服务宣称 2,000+ 并发、28% 更快和 40% 更低成本                                                                             | **开源 R3，托管 R2。** 小中规模 Agent 实验易复现；未见旗舰基础模型明确使用；托管 benchmark 为供应商自报。([OpenPipe][31])                                                                                                        |
| **SkyRL / SkyRL-Agent**                                       | 2025-05 公开；2026 年仍活跃                                                                                      |          ①② | 基于 verl/OpenHands 等构建 Agent RL；SA-SWE-32B 从 Qwen3-32B 出发，SWE-bench Verified 报告 24.4%→39.4%；async dispatcher 报告约 1.55 倍，训练成本降低超过 2 倍                                       | **R3，活跃但演进快。** 后端/config 曾迁移并减少 SGLang 支持；Tinker colocated multi-turn sampling、FP8/delta sync 和多模态 LoRA 仍有 issue；harness 变换可能破坏 on-policy。([UC Berkeley Sky Computing Lab][32])            |
| **AReaL / AReaL 2.0**                                         | 2025 年论文；2.0 于 2026-07-01 公开                                                                              |          ①② | 完全解耦生成、训练、reward 和权重服务；per-sample staleness、interruptible rollout、动态 batching、混合 policy trajectory；32B、最多 512 GPU、最高约 2.57 倍                                              | **R3，活跃/早期。** 是公开混合策略轨迹研究中最完整者之一；2.0 文档、示例和部分 roadmap 尚未完成，公开 issue 涉及 stale trajectory、权重同步和 token-prefix mismatch。([arXiv][1])                                                           |
| **verl / HybridFlow**                                         | HybridFlow 2024-09-28；fully-async recipe 2026-05 更新                                                       |          ①② | hybrid single/multi-controller、3D-HybridEngine；DAPO、agentic RL 和 fully-async recipe；公开异步实验为 7B/128 GPU、约 2.35–2.67 倍；DAPO 有 32B 配方                                        | **特定配方 R4，完整大规模 Agent async R3；活跃。** 不应写成“verl 默认完全异步”；async、partial rollout、sample supplementation 和 backend correction 的成熟度不一，仍有 sequence parallel/fused kernel logprob 问题。([arXiv][33]) |
| **slime**                                                     | 项目在 2025 年进入 GLM 后训练路线；v0.3.0 于 2026-05-31                                                                |         ①②③ | agent-first、fully async、可变 global batch、PD disaggregation；官方明确列为 GLM-4.5 至 GLM-5.2 后训练系统；SAO 和 CompactionRL 用于 GLM-5.2                                                    | **R3，活跃。** 系统主体开放且有旗舰使用证据；但 GLM-5.2 数据、完整环境、SAO/CompactionRL 核心配方尚未公开，因此不能复现旗舰结果。([GitHub][34])                                                                                            |
| **ROLL / ROCK / ROME / RollArt**                              | ROLL v0.3 于 2026-06；RollArt 为 2025–2026 生产系统论文                                                            |         ①②④ | ROLL 负责优化；ROCK 负责 sandbox/environment；ROME 报告超过 100 万轨迹；RollArt 为 Qoder 百亿至数百亿/数百 B 级生产 Agent 模型提供异步系统，公开说法涉及 3,000+ GPU；支持 router replay、multi-teacher OPD、OpenTelemetry | **R3，活跃。** 是环境、训练和生产测量结合较强的开源生态；旗舰基础模型采用证据不如 slime/NeMo，但有明确产品训练证据。([GitHub][18])                                                                                                          |
| **Harbor**                                                    | 2025–2026；截至审计日为活跃项目                                                                                      | ①②④（评测/环境层） | Terminal-Bench 官方 harness；任意 Agent adapter、状态环境、并行执行、ATIF trace；与 Prime、SkyRL、verl/阿里云路线集成                                                                                | **环境与评测 R4，RL 大规模集成 R3。** 它不是 trainer；部分公开数据集曾存在文件、配置或规模不完整问题。([GitHub][35])                                                                                                               |
| **NVIDIA NeMo RL / NeMo Gym**                                 | NeMo RL 2025-07 公开，2026 年持续扩展                                                                             |         ①②③ | Ray、DTensor/Megatron、vLLM；async collector、trajectory age、CISPO、ICE-POP、FP8、router mismatch 监控、OPD/MOPD；Nemotron 3 Ultra 明确使用 NeMo RL/Gym 和 10+ teachers                   | **R3，活跃。** 是公开特性、训练配方与旗舰模型采用结合最完整的栈之一；NeMo Gym 明确标注仍为早期开发、API 会变；部分多 reward integration 和完整 resilience 能力仍不成熟。([GitHub][20])                                                               |
| **Microsoft Agent Lightning**                                 | 论文 2025-08；v0.3.0 于 2025-12-24                                                                            |          ①② | 将任意 Agent runtime 转换为 transition，并与 verl、Tinker、Azure 等训练端连接；提供 OpenTelemetry、dashboard 和 trajectory aggregation                                                          | **R3，维护中。** 强项是接口和可观测性，不是新的大模型 trainer；当前 credit assignment 较粗，不能把“Agent–trainer 解耦”写成完全异步 PPO。([arXiv][12])                                                                               |

---

## 3.2 闭源内部系统与论文级系统

| 项目                           | 时间与证据                                                | 公开内容                                                                                                                                                                       | 审计结论                                                                                                                                |
| ---------------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **MiniMax Forge**            | 2026-02-14；①②③                                       | 明确用于 M2.5；超过 10 万 scaffolds/environments、200K context、每天数百万样本；Windowed FIFO、prefix tree、持续 KL 微调的 speculative draft、PD disaggregation、统一多域训练、context action、process reward | **系统 R1，内部活跃。** 是闭源团队中公开系统细节较多者，但无代码、原始测量、完整消融或独立复现。所谓 40 倍主要是 prefix-sharing 训练模块，不是统一端到端指标。([MiniMax][7])                         |
| **Meta LlamaRL**             | 2025-06-02；②③                                        | 全分布式异步 RL，覆盖 Llama 3 8B/70B/405B，从少量 GPU 扩展至数千 H100；1–n step delay、AIPO correction、分布式权重广播；405B 上对论文基线最高约 10.7 倍                                                           | **R1，论文/内部系统。** 明确用于 Llama 3 后训练，但核心系统未作为完整可运行栈开放。([arXiv][27])                                                                     |
| **DORA / LongCat**           | 2026-04，2026-07 更新；②③                                | 多版本 streaming rollout、轨迹内 policy consistency、bounded staleness；LongCat Agent/Thinking 路线使用                                                                                 | **系统 R1。** 模型和部分材料开放，但没有按论文工业规模开放 DORA 系统。([arXiv][9])                                                                              |
| **Laminar**                  | 2025-10；②                                            | trajectory-level fully async、relay parameter service、动态 repack、failure isolation；最多 1,024 GPU、最高约 5.48 倍                                                                   | **R1，论文系统。** 故障和权重分发测量有价值，但缺公开实现。([arXiv][25])                                                                                      |
| **StreamRL**                 | 2025-04；②                                            | disaggregated streaming generation、一步异步、长度感知调度；报告最高约 2.66 倍吞吐和约 1.33 倍成本效率；消融分别量化 scheduler、streaming disaggregation 和 async                                               | **R1，论文系统。** 适合作为一步异步基线，未形成广泛维护的开源栈。([arXiv][36])                                                                                   |
| **OpenAI**                   | o1 2024-09；后续 coding、reasoning 和 safety 模型持续使用 RL；③④ | 官方材料确认大规模 RL、真实 coding 环境训练、自博弈 red-team 和高计算 RL；gpt-oss 开放权重，但不开放训练栈                                                                                                      | **模型证据强，系统 R1。** rollout 调度、policy lag、logprob、routing 和恢复机制基本不公开。公开 RFT 服务只支持有限模型，且已进入停止接受新用户和逐步下线阶段，不能视为长期通用 RL 平台。([OpenAI][37]) |
| **Anthropic**                | Constitutional AI 2022；Claude 4 及后续模型 2025–2026；③④   | RL from human/AI preferences、宪法式反馈、长程 Agent 与部署期 compaction/context editing                                                                                                | **模型与产品证据强，系统 R1。** 未公开 actor–learner 架构、correction、训练规模或故障恢复；部署 compaction 不应自动当作训练过的 CompactionRL。([Anthropic][38])               |
| **Google DeepMind / Gemini** | Gemini 3 Pro 模型卡 2025-11，2026-05 更新；③④               | 模型卡说明使用 SFT 与 RL，包括 thought traces、多步推理、问题求解、定理证明和 thought-length penalty                                                                                                  | **模型证据强，系统 R1。** 没有足够公开证据审计 rollout/trainer 分离、policy lag 或环境基础设施。([Google Cloud Storage][39])                                      |
| **DeepSeek**                 | R1 2025-01；V3.2 2025-12；②③                           | 大规模可验证 RL、Agent task synthesis、sequence-level masking/correction、模型蒸馏                                                                                                      | **算法和模型证据强，训练系统 R1。** 没有公开旗舰规模 actor–learner 系统代码；第三方框架复现不能替代 DeepSeek 自身系统采用证据。([DeepSeek API Docs][19])                           |
| **Qwen GSPO / SAPO**         | GSPO 2025-07；SAPO/Qwen3-VL 后续公开；②③                   | sequence-level importance sampling/clipping，针对长序列和 MoE routing 稳定性；官方称 GSPO 用于 Qwen 旗舰模型，SAPO 用于 Qwen3-VL 系列                                                               | **算法层可研究，完整系统 R1–R2。** 公式和实验公开，但旗舰数据、训练环境和系统配置不完整。([arXiv][11])                                                                     |

---

# 4. 真实可复现程度与维护状态

## 第一档：最适合做公开端到端基准

### verl

优点是配方多、社区大、trainer 和 rollout backend 可替换，DAPO 等结果有较完整 recipe。局限是“框架功能存在”与“特定 backend 下严格正确”之间仍有距离；完全异步、partial rollout、MoE、FP8 和 fused-kernel 组合应单独验证。([GitHub][40])

### Harbor

环境、评测和 trajectory 层最接近 R4，特别适合建立可重复的 Agent benchmark 和 trace corpus；但它不能单独复现 RL 优化。([GitHub][35])

### ART

小规模、LoRA 和已有 Agent 应用的接入门槛低；其开源同步语义反而有利于作为 correctness baseline。([GitHub][6])

## 第二档：代码真实可运行，但旗舰结果难以复现

* **prime-rl**：大规模特性和环境体系完整，但超大模型、任务集与算力门槛高。
* **AReaL**：异步算法—系统协同研究最系统，但 2.0 仍处迁移期。
* **SkyRL**：Agent 和 SWE 场景实用，依赖链和 backend 变化较快。
* **slime**：有最强的旗舰 GLM 使用证据之一，但新算法和训练数据未完全开放。
* **ROLL/ROCK**：生产系统证据强，生态组件多，完整复现 Qoder/ROME 规模困难。
* **NeMo RL/Gym**：功能与模型采用证据强，但硬件门槛高，Gym 和部分 resilience/API 仍在早期。([GitHub][41])

## 第三档：服务可用，但后端不可审计

* Tinker；
* Prime Hosted Training/Lab；
* W&B Training/ART serverless。

这类系统适合验证算法接口和业务闭环，不适合回答以下研究问题：

* trainer 与 inference 到底如何并行；
* policy version 如何切换；
* logprob 在何处重算；
* 故障是否会造成 silent sample loss；
* 供应商 benchmark 是否来自相同硬件和配置。

## 第四档：旗舰或大规模证据强，但系统不可复现

MiniMax Forge、Meta LlamaRL、OpenAI、Anthropic、Google、DeepSeek，以及 DORA、Laminar、StreamRL 等论文系统属于此类。

这里最重要的纪律是：

> **“旗舰模型明确使用”只提高真实性，不提高可复现性。**

---

# 5. 多团队共识与尚未收敛的分歧

## 已形成的共识

### 共识一：生成、环境、训练和权重服务需要解耦

Prime、AReaL、RollArt、NeMo、LlamaRL、Laminar 与 Forge 虽然实现不同，但都不再把整个 RL step 视为一台机器上的单体循环。([arXiv][1])

### 共识二：异步必须伴随版本、年龄和 provenance

仅仅让 actor 和 learner 并行是不够的。至少要记录：

* generation policy version；
* trainer old-policy version；
* token IDs 与 rollout logprobs；
* tokenizer/renderer/template 版本；
* environment/verifier 版本；
* trajectory age 和截断原因；
* routing 或数值一致性指标。

NeMo、AReaL、Prime、Harbor 和 Agent Lightning 分别覆盖了这些要素的一部分。([NVIDIA Docs][10])

### 共识三：Agent RL 的单位是完整 trajectory，而不只是 token

reward、环境状态、工具输出、上下文管理和 verifier 都以 trajectory 为中心。GSPO、RollArt、Harbor、Forge 和 CompactionRL 都从不同角度体现了这一变化。([arXiv][11])

### 共识四：环境与 verifier 的质量比简单扩大 rollout 数量更重要

大规模生成无效、过易、不可验证或 reward-hackable 的轨迹，只会增加吞吐，不会增加有效学习信号。

### 共识五：蒸馏与 RL 是互补关系

RL 用于环境适应、探索和反馈闭环；OPD/MOPD 用于将多个专家或昂贵 teacher 的能力整合到单一 student。([Thinking Machines Lab][4])

### 共识六：故障恢复不能只依赖重启整个 job

checkpoint 必须覆盖 replay/rollout 状态、版本、未完成 batch 和环境生命周期；角色级恢复和故障隔离正在成为生产要求。([arXiv][24])

---

## 尚未收敛的核心分歧

### 1. 一条轨迹能否混合多个 policy version

* **允许混合**：AReaL、Prime 等优先吞吐，通过重算、版本标记和 correction 控制偏差。
* **拒绝混合**：DORA 认为轨迹内一致性是数据完整性的必要条件。
* **折中**：RollArt、NeMo 通过 trajectory age、异步边界和周期切换控制。

目前没有跨任务、跨模型、跨 horizon 的公开实验足以证明哪种策略总体最优。

### 2. token-level 还是 sequence-level correction

* token correction 细粒度，但长序列乘积和极端 token 会造成不稳定；
* sequence correction 与任务 reward 对齐，但可能有高方差；
* geometric mean、sequence mask 和 GSPO 等方案降低长度偏差，但可能牺牲局部信用。

### 3. GRPO group sampling 是否仍适合昂贵 Agent 环境

* 多 rollout 可以降低无 value model 的复杂度；
* 但会乘数级增加环境成本；
* SAO 主张单 rollout + value model；
* Forge 等生产栈则引入过程 reward 和 reward-to-go。

### 4. 完全异步是否真的优于受限异步

当环境耗时高、轨迹长、模型更新慢时，完全异步有明显优势；当 reward 对 distribution shift 高度敏感、模型更新幅度大或 verifier 噪声高时，windowed/bounded async 可能更稳。公开 speedup 多于质量—staleness 曲线，证据仍不充分。

### 5. LoRA 服务是否足以承担前沿 Agent RL

Tinker、ART 等证明 LoRA 能降低接入成本；Tinker 自身的 OPD 实验也显示，高数据量下 LoRA 可能与 full fine-tuning 拉开差距。LoRA 是否足以完成大幅策略迁移、MoE routing 变化和跨域能力整合，仍没有普遍结论。([Thinking Machines Lab][4])

### 6. Context compaction 是 middleware 还是策略 action

* OpenAI、Anthropic 主要公开 serving-side compaction；
* Forge、CompactionRL 将其纳入 Agent 决策和训练目标。

后者理论上能学习任务相关保留策略，但训练和评估难度更大。

### 7. 多教师能力应在训练前、训练中还是训练后整合

可能路线包括：

* 合并 SFT traces；
* on-policy multi-teacher distillation；
* 先分域 RL，再统一蒸馏；
* 在线调用强 teacher；
* 保持多个专家或 router。

尚无公开统一结论，尤其缺少灾难性遗忘和跨域回归消融。

---

# 6. 近期值得继续跟踪、但证据仍不足的方向

## 6.1 Policy-consistent multi-version async

DORA 的问题定义非常重要：是否可以在保持每条轨迹 policy-consistent 的情况下获得接近完全异步的吞吐。需要等待：

* 公开实现；
* 与 AReaL/Prime mixed-policy 模式的同任务对比；
* 不同更新幅度和 horizon 下的质量—吞吐曲线；
* cache 与多版本权重成本。

## 6.2 Sequence-level correction 的统一理论和工程验证

Geo-MIS、sequence mask、GSPO、ICE-POP 等方法正在趋同，但尚缺：

* 同一框架、同一模型、同一任务上的系统比较；
* MoE routing 与数值失配分离实验；
* 极长 Agent trajectory 上的 variance 和 bias 测量；
* correction 后真正保留的有效 token 比例。

## 6.3 Learned context management

CompactionRL 和 Forge 代表的方向很可能成为长程 Agent 的核心组件，但目前需要核验：

* summary hallucination 是否造成不可恢复状态损失；
* compaction policy 是否 reward hack；
* 是否保留 source pointers；
* 如何在训练和 serving 之间保持 compaction 一致；
* 对 1M-context 模型是否仍有明显收益。

## 6.4 Single-rollout RL 与 value model 回归

SAO 表明昂贵 Agent 任务可能重新需要 critic/value model。尚需公开：

* 与等计算量 GRPO 的比较；
* value error 对长程 credit 的影响；
* changing environment 下的稳定性；
* value model 是否成为新的 scaling bottleneck。

## 6.5 跨 tokenizer、多教师 OPD

NeMo、Tinker 和 ROLL 已经给出方向，但跨 tokenizer、不同工具 schema 和异构 teacher 的严格 on-policy 定义仍不清楚。特别需要审计 teacher logprob 在 student state 上是否真正可比。

## 6.6 标准化 trajectory provenance

Harbor ATIF 是重要起点。下一步需要统一记录：

* 原始 token；
* sampled token logprob；
* trainer 重算 logprob；
* policy/checkpoint hash；
* router assignment；
* precision/kernel/version；
* context edit；
* environment/verifier image hash；
* tool output；
* retry 和故障原因。

没有这些字段，跨框架复现实验很容易出现“reward 一样、训练行为不同”。

## 6.7 Verifier 的对抗鲁棒性

当前大部分项目报告 verifier pass rate，却很少报告：

* false acceptance；
* false rejection；
* exploit discovery；
* verifier ensemble disagreement；
* 人工复审抽样；
* 随模型变强而发生的 verifier 失效。

这可能是下一阶段比纯 rollout scaling 更严重的瓶颈。

## 6.8 真正的 continual learning

值得关注 Prime 飞轮、AReaL-SEA、OpenClaw-RL 和安全自博弈，但在以下证据出现前，不宜称为成熟持续学习：

* 长期在线权重更新时间序列；
* 回滚和版本控制；
* 对遗忘、偏移与安全退化的持续评估；
* 用户数据治理；
* 多轮更新后的净能力曲线；
* 与周期性离线重训的公平比较。

## 6.9 Capability-normalized cost

目前各团队优化的是不同目标：tokens/s、step time、GPU utilization、task cost、训练 wall-clock 或 benchmark score。真正值得追踪的是：

* 每提升一个 held-out 能力点的总成本；
* 每个有效且非重复成功 trajectory 的成本；
* 因环境、verifier、staleness 和 mismatch 浪费的比例；
* 训练后 serving 成本是否上升；
* 某项能力提升是否以其他能力退化为代价。

---

# 7. 后续材料束候选

以下不是课程安排，而是可用于下一轮证据审查的材料分组。

## 材料束 A：异步语义与 policy lag

核心材料：

* AReaL fully asynchronous RL 论文与 2.0 文档；
* Prime “RL at 1T Scale” 与 prime-rl；
* DORA 多版本 streaming rollout；
* NeMo RL async collector、trajectory age 与 CISPO 文档；
* verl fully-async PPO recipe；
* RollArt trajectory-level async；
* Meta LlamaRL；
* Laminar 和 StreamRL。

核心审计问题：每条轨迹包含多少 policy version、KV 如何处理、样本何时丢弃、correction 的对象是什么。([arXiv][1])

## 材料束 B：train–inference consistency

核心材料：

* ByteDance 关于 rollout/training mismatch 的研究；
* NVIDIA ProRLv2、ICE-POP 和 mismatch metrics；
* Qwen GSPO；
* Prime router replay；
* verl 的 rollout correction 文档和相关 issue；
* SkyRL/Harbor 的 token 与 harness 注意事项。

核心审计问题：logprob 误差来自 policy lag、kernel、precision、routing 还是 trace reconstruction；哪种 correction 只修 action、哪种处理 sequence。([Notion][2])

## 材料束 C：长程 credit 与 context compaction

核心材料：

* SAO；
* CompactionRL；
* Forge 的 process reward、reward-to-go 和 context action；
* Agent Lightning 的 credit assignment 限制；
* Tinker OPD；
* OpenAI/Anthropic serving compaction。

核心审计问题：终局奖励如何分配到动作、value model 是否必要、summary 是否成为可学习动作、训练期和部署期 context policy 是否一致。([arXiv][13])

## 材料束 D：环境、verifier 与数据飞轮

核心材料：

* Prime Verifiers、Environments Hub 和 tasksets；
* Harbor 与 ATIF；
* NeMo Gym；
* ROCK；
* RollArt 的环境故障测量；
* SYNTHETIC-2；
* AReaL-SEA。

核心审计问题：环境如何版本化、verifier 如何验证、失败如何归因、任务难度如何自适应、轨迹是否能跨 trainer 重放。([GitHub][14])

## 材料束 E：OPD 与能力整合

核心材料：

* Tinker OPD recipe；
* Nemotron 3 Ultra 与 NeMo MOPD；
* ROLL multi-teacher OPD；
* DeepSeek-R1 distillation；
* 跨 tokenizer OPD 的 NeMo 路线图。

核心审计问题：teacher signal 是 on-policy 还是离线、是否同 tokenizer、如何组合任务奖励、蒸馏后是否发生能力覆盖。([Thinking Machines Lab][4])

## 材料束 F：生产可靠性与真实经济性

核心材料：

* RobustRL；
* Laminar failure recovery；
* RollArt 的环境和集群测量；
* NeMo replay/checkpoint；
* Prime weight/routing 传输；
* Forge effective yield；
* ART 和 SkyRL 的成本声明。

核心审计问题：故障注入后的有效训练时间、silent sample loss、恢复是否保持数据完整性，以及速度增益是否真正转化为单位能力成本下降。([arXiv][24])

---

# 最终审计结论

截至 2026 年 7 月 27 日，公开生态中不存在一个在所有维度占优的“标准 Agent RL stack”。

**公开证据最完整的训练基础设施群**是：

* NeMo RL/Gym；
* prime-rl/Verifiers；
* slime；
* verl；
* AReaL；
* ROLL/ROCK/RollArt。

它们的优势分别不同：NeMo 在一致性与旗舰配方，Prime 在环境—服务—超大 MoE 串联，slime 在 GLM 旗舰采用，verl 在通用研究生态，AReaL 在混合策略完全异步研究，ROLL/RollArt 在生产 Agent、环境与故障测量。

**最清晰的托管训练接口**是 Tinker、Prime Hosted/Lab 和 W&B Training，但三者的后端透明度都不够支撑系统研究结论。

**闭源团队中系统披露最细的是 MiniMax Forge**，但它仍是不可复现的内部系统。OpenAI、Anthropic 和 Google 可以证明前沿模型使用大规模 RL，却不能据此回答 policy lag、rollout 调度、logprob 一致性、恢复或单位能力成本问题。

当前真正的技术前沿已经不再只是“用 PPO、GRPO 还是某个 clipping 公式”，而是四个相互耦合的控制回路：

1. **策略回路**：更新频率、policy lag、importance correction；
2. **轨迹回路**：长程 credit、上下文、工具和多版本 policy；
3. **环境回路**：任务、sandbox、verifier、失败和数据飞轮；
4. **系统回路**：权重分发、路由与精度一致性、恢复、可观测性和成本。

公开生态已经对“需要同时优化这四个回路”形成共识；尚未收敛的是，应该牺牲多少严格 on-policy 性来换取吞吐，以及这些吞吐提升最终能否转化为**可验证、可保持、单位成本更低的能力增益**。

[1]: https://arxiv.org/html/2505.24298v5 "https://arxiv.org/html/2505.24298v5"
[2]: https://yingru.notion.site/When-Speed-Kills-Stability-Demystifying-RL-Collapse-from-the-Training-Inference-Mismatch-271211a558b7808d8b12d403fd15edda "https://yingru.notion.site/When-Speed-Kills-Stability-Demystifying-RL-Collapse-from-the-Training-Inference-Mismatch-271211a558b7808d8b12d403fd15edda"
[3]: https://arxiv.org/html/2512.22560v1 "https://arxiv.org/html/2512.22560v1"
[4]: https://thinkingmachines.ai/blog/on-policy-distillation/ "https://thinkingmachines.ai/blog/on-policy-distillation/"
[5]: https://www.primeintellect.ai/blog/nemotron-3 "https://www.primeintellect.ai/blog/nemotron-3"
[6]: https://github.com/openpipe/art "https://github.com/openpipe/art"
[7]: https://www.minimax.io/blog/forge-scalable-agent-rl-en-1779896141 "https://www.minimax.io/blog/forge-scalable-agent-rl-en-1779896141"
[8]: https://www.primeintellect.ai/blog/rl-at-1t-scale "https://www.primeintellect.ai/blog/rl-at-1t-scale"
[9]: https://arxiv.org/abs/2604.26256 "https://arxiv.org/abs/2604.26256"
[10]: https://docs.nvidia.com/nemo/rl/nightly/apidocs/nemo_rl/nemo_rl.algorithms.async_utils.replay_buffer.html "https://docs.nvidia.com/nemo/rl/nightly/apidocs/nemo_rl/nemo_rl.algorithms.async_utils.replay_buffer.html"
[11]: https://arxiv.org/html/2507.18071v2 "https://arxiv.org/html/2507.18071v2"
[12]: https://arxiv.org/html/2508.03680v1 "Agent Lightning: Train ANY AI Agents with Reinforcement Learning"
[13]: https://arxiv.org/abs/2607.07508 "https://arxiv.org/abs/2607.07508"
[14]: https://github.com/PrimeIntellect-ai/verifiers?utm_source=chatgpt.com "PrimeIntellect-ai/verifiers: Our library for RL environments ..."
[15]: https://www.harborframework.com/docs/agents/trajectory-format?utm_source=chatgpt.com "Agent Trajectory Format (ATIF) - Harbor framework"
[16]: https://www.primeintellect.ai/blog/synthetic-2-release "https://www.primeintellect.ai/blog/synthetic-2-release"
[17]: https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/ "https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/"
[18]: https://github.com/alibaba/ROLL/releases "https://github.com/alibaba/ROLL/releases"
[19]: https://api-docs.deepseek.com/news/news250120/ "https://api-docs.deepseek.com/news/news250120/"
[20]: https://github.com/NVIDIA-NeMo/RL "https://github.com/NVIDIA-NeMo/RL"
[21]: https://arxiv.org/abs/2607.05378 "https://arxiv.org/abs/2607.05378"
[22]: https://developers.openai.com/api/docs/guides/compaction "https://developers.openai.com/api/docs/guides/compaction"
[23]: https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/harbor_rl/README.md "https://github.com/thinking-machines-lab/tinker-cookbook/blob/main/tinker_cookbook/recipes/harbor_rl/README.md"
[24]: https://arxiv.org/abs/2512.22492?utm_source=chatgpt.com "Role-Based Fault Tolerance System for LLM RL Post-Training"
[25]: https://arxiv.org/html/2510.12633v1 "https://arxiv.org/html/2510.12633v1"
[26]: https://github.com/volcengine/verl/blob/main/docs/advance/fully_async.md "https://github.com/volcengine/verl/blob/main/docs/advance/fully_async.md"
[27]: https://arxiv.org/html/2505.24034v2 "https://arxiv.org/html/2505.24034v2"
[28]: https://openpipe.ai/blog/serverless-rl "https://openpipe.ai/blog/serverless-rl"
[29]: https://thinkingmachines.ai/news/announcing-tinker/?utm_source=chatgpt.com "Announcing Tinker"
[30]: https://thinkingmachines.ai/news/introducing-inkling/ "https://thinkingmachines.ai/news/introducing-inkling/"
[31]: https://openpipe.ai/blog/art-trainer-a-new-rl-trainer-for-agents?utm_source=chatgpt.com "ART Trainer: A New RL Trainer for Agents"
[32]: https://sky.cs.berkeley.edu/project/skyrl/ "https://sky.cs.berkeley.edu/project/skyrl/"
[33]: https://arxiv.org/abs/2409.19256 "https://arxiv.org/abs/2409.19256"
[34]: https://github.com/THUDM/slime/releases "https://github.com/THUDM/slime/releases"
[35]: https://github.com/harbor-framework/harbor "https://github.com/harbor-framework/harbor"
[36]: https://arxiv.org/html/2504.15930v1 "https://arxiv.org/html/2504.15930v1"
[37]: https://openai.com/index/learning-to-reason-with-llms/ "https://openai.com/index/learning-to-reason-with-llms/"
[38]: https://www.anthropic.com/news/protecting-well-being-of-users "https://www.anthropic.com/news/protecting-well-being-of-users"
[39]: https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-Pro-Model-Card.pdf "https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-3-Pro-Model-Card.pdf"
[40]: https://github.com/verl-project/verl "https://github.com/verl-project/verl"
[41]: https://github.com/PrimeIntellect-ai/prime-rl/releases "https://github.com/PrimeIntellect-ai/prime-rl/releases"

