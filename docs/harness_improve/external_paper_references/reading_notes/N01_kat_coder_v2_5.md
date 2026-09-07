# N01 KAT-Coder-V2.5 Technical Report：后训练与项目一精读

## 1. 来源、版本与阅读范围

- **正式标题**：KAT-Coder-V2.5 Technical Report；机构/署名：快手（Kuaishou）的 KwaiKAT Team。PDF 首页署团队，arXiv 元数据列 Bo Huang 等 53 位作者，贡献名单见 §8/p20。
- **版本**：arXiv:2607.05471v1，提交于 2026-07-06 08:14:02 UTC；阅读日期 2026-09-07。本轮 arXiv submission history 仅列 v1，未用后续版本或旧 KAT 报告替代。
- **正式入口**：[摘要与版本记录](https://arxiv.org/abs/2607.05471v1)、[HTML 全文](https://arxiv.org/html/2607.05471v1)、[PDF](https://arxiv.org/pdf/2607.05471v1)、[TeX source](https://arxiv.org/src/2607.05471v1)。保存的原文：[本地 PDF](sources/N01/2607.05471v1.pdf)、[原始 TeX 压缩包](sources/N01/2607.05471v1-source.tar.gz)、[main.tex](sources/N01/tex/main.tex)、[版式文本](sources/N01/2607.05471v1-layout.txt)。PDF 保持下载原样；来源与校验值见[快照记录](sources/N01/SOURCES.md)。
- **实际阅读**：通读 main.tex 全部正文，读参考文献条目以核引用身份；结合 24 页 PDF 提取文本定位，目视核对图1–5、表1–4、公式1–8。没有独立编号的 Appendix；p23–24 是 §4.4 的浮动表1–3，排在参考文献后，不能漏掉或虚称“未提供奖励细则”。
- **页码口径**：下文 pN 指 PDF 从1开始的物理页。p2–24 的页脚与物理页一致；首页无可见页脚，仍称 p1。图2在 p3、图3在 p6、图4在 p10、图5在 p11；表4在 p19，表1在 p23，表2–3在 p24。
- **配套资产边界**：报告给出[StreamLake 产品入口](https://streamlake.com/product/kat-coder)，本轮网页工具访问超时（400 Timeout fetching）。报告正文、文末、arXiv 入口未给可直接核验的 V2.5 训练代码、权重、数据或镜像发布链接；未沿不相干框架追代码，故无“实际查阅的训练代码 commit”。这是本轮来源边界，不是对互联网所有资产作“绝未开源”的断言。
- **旧稿**：[外部pro1.md](../../../agentic_RL/repo_harness_rh2_workstreams/tmp/外部pro1.md)与[项目设计外部pro.md](../../../agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md)仅作查证线索，原文件不改。主要纠错在 §9.2。

### 1.1 先按原文目录建立的覆盖表

本表以原文目录/TeX 层级为依据，再映射到笔记；没有以 SWE 提问范围裁剪其他后训练内容。全部后训练条目均精读。纯预训练/架构章节在此版本中不存在。

| 原文章节与实际页 | 阅读深度与内容范围 | 本笔记位置 |
| --- | --- | --- |
| Abstract/p1；§1 Introduction/p2–3；图1/p1 | 全读：三个瓶颈、五专家关系、结果主张 | §2、§3、§7 |
| §2 Agentic Software-Engineering Capabilities/p3；图2/p3 | 全读：环境/轨迹两条扩展轴 | §4.1–4.3 |
| §2.1 Environment Scaling Engine/p4：Verifiable Task Mining；Verifiable Environment Construction | 精读：描述重建、AutoBuilder、结构化测试、去泄漏 | §4.1 |
| §2.2 Data Scaling Flywheel/p5：Hint-Boosted Rollout Pass Rate；Process-Score-Driven Trajectory Filtering；Harness Rewriting for Robustness | 精读：提示恢复/无提示重建、过程筛选、接口改写与故障扰动 | §4.2–4.3 |
| §3 General Agentic Capabilities；§3.1 Overview of KwaiClawEnv/p5–6 | 精读：真实服务/模型模拟/手写 sandbox 的局限、Skill+Task 合成 | §4.4 |
| §3.2 Pipeline/p6–7；§3.2.1 Service Layer、§3.2.2 Task Layer、§3.2.3 Eval Layer/p7；图3/p6 | 精读三层、记录字段、SFT-ready 输出和反馈 | §3、§4.4 |
| §3.3 Environment Scaling/p7–8；§3.3.1 Service-level Scaling；§3.3.2 Task-level Scaling/p8 | 精读两级扩展、所有规模与复杂度指标 | §4.4 |
| §3.4 Data Validation and Reliability Assurance/p8–9 | 精读三阶段一致性验证、三种处置、两层轨迹过滤 | §4.4、§9 |
| §4 Reinforcement Learning；§4.1 Harness Scaling/p9–10 | 精读三类过拟合、三变化轴、白盒/黑盒实际训练 | §6.1 |
| §4.2 RL and Sandbox Infrastructure/p10；§4.2.1 Gateway Server/p10–11；图4/p10 | 精读调用链、buffer、token 保真 | §6.2 |
| §4.2.2 Sandbox Optimization/p11–12；图5/p11 | 精读全部工程失败、统计和曲线限制 | §6.3、§7.3 |
| §4.3 Asymmetric PPO/p12；§4.3.1 PPO Objective and Advantage Estimation/p12–13 | 精读理由、式1–3、符号/分母边界 | §5.1 |
| §4.3.2 Hindsight-Augmented Critic/p13 | 精读特权上下文、式4、部署区别 | §5.2 |
| §4.4 Harness-Oriented Reward Framework/p13–15；§4.4.1 Rule-based Reward，三个 paragraph；表1/p23 | 精读完整10项（含正文列表漏列的清理项） | §5.3 |
| §4.4.2 Model-Based Reward与 GRM Training/p15；表2–3/p24 | 精读 rubric、全部展示条目/坏例、人工标签、式5 | §5.4 |
| §5 Multi-Teacher On-Policy Distillation/p15–16；式6 | 精读五教师、按域选择、reverse KL | §3、§5.5 |
| §5.1 Stabilizing Long-Context OPD/p16–17：Off-policy cold start；Drift-aware dynamic truncation；式7–8 | 精读全部稳定性问题、前缀保留、mask、分层 batching | §5.5–5.6 |
| §6 Evaluation、§6.1 Benchmarks/p17–18：KAT Code Bench、KAT Claw Bench | 精读构建、审查、七类业务任务与混合评分 | §7.1 |
| §6.2 Main Results/p18–19：Repository-level SWE、Long-horizon tool use、Terminal and scientific coding；表4/p19 | 精读六项结果、榜单脚注、弱项 | §7.2–7.3 |
| §7 Conclusion/p19–20 | 全读：终端/科学任务、信用分配、环境扩展的未来方向 | §2、§9 |
| §8 Contribution/p20；References/p21–22 | 核署名与来源身份；参考文献不是附带论文已读证明 | §1、§9.3 |
| 文末浮动表1–3/p23–24 | 已逐项读并目视核对；无其他附录 | §5.3–5.4 |

## 2. 核心问题与结论

**外部事实**：作者把 coding agent 的训练对象从单轮代码答案扩展到真实仓库内的完整交互。方法把可执行环境、需求与验证的一致性、过程质量、长程 RL、不同 harness 的适应以及专家融合放进同一后训练体系（§1/p2–3）。报告最具体的工程证据是 AutoBuilder 的构建成功率从16.5%升至57.2%，以及 sandbox 反馈错误率从约16%降到低于2%（§2.1/p4；§4.2.2/p11–12）。这些都是作者报告的系统观察；采样量、置信区间和完整成本未给。

**训练事实**：白盒 mini-swe-agent 与黑盒 ClaudeCode、Codex、OpenClaw、OpenHands 等参与 RL；策略采用 PPO、GAE 和可读事后信息的 critic；奖励包含测试、行为约束、失败进展和经专门 RL 训练的 GRM；最后五个领域专家通过教师轨迹冷启动加学生自采样 MOPD 融合（§4–5/p9–17）。这足以证实“真实黑盒 harness 可以进入训练”的实践先例，但不提供现成的共享前缀计权、压缩 token mask 或 staleness 配方。

**结果与限制**：报告表4中 SWE-Bench Pro 65.2、KAT Code Bench 53.1均为五模型中的第二；PinchBench Avg 94.9最高，但来自2026-07-02榜单快照；Terminal-Bench 2.1 的60.7低于其余四个对照。没有固定数据/训练算力只改变 harness、critic、reward 或 MOPD 的独立消融，也没有融合前后五专家能力表（§6/p17–19）。因此，不能把总成绩分解成某单项机制的因果增益，不能据此替 RepoHarness 定案 PPO，更不能推导八卡可复现成本。

## 3. 后训练流程与模型关系

正文没有 base 参数规模、架构、预训练语料、mid-training、初始 checkpoint、tokenizer 或通用 SFT 训练表。不要把 KAT 家族前代报告配置转移到 V2.5。明确披露的关系如下（§1/p2–3、§3.2.3/p7、§4–5/p9–17）：

| 路径/阶段 | 输入与产物 | 披露的学习信号 | 未确定的连接 |
| --- | --- | --- | --- |
| SWE 数据生产 | PR/commit、golden/test patch → 可执行任务与精选/恢复轨迹 | 测试验证、过程规则与分数；正负标签可供偏好学习、rejection sampling、过程奖励建模 | 这些产物分别进哪轮 SFT/RL、比例、具体模型均不明 |
| KwaiClawEnv | 人工 Skill、LLM Service、真实 task seeds → 多工具轨迹与 SFT-ready 格式 | 一致性校验、硬规则、LLM judge | “SFT-ready”不等于披露了实际 SFT 步数/用量 |
| 五领域专家 | SWE、通用 agentic reasoning/Claw、terminal、web coding、general knowledge | §4介绍 PPO+奖励框架；§1称其余专家遵循相同 recipe | 独立专家分支，不是五阶段串行；各自初始化、训练次序、并行日程未给 |
| GRM 判别器 | 历史轨迹+人工 rubric 触发项/理由 → 专门 judge | 式5：真项召回减误报数惩罚，通过 targeted RL 学判别 | 不应把 GRM 当第六个融合专家；其基座、参数量和 RL 算法细节未给 |
| MOPD 冷启动 | 五专家生成的轨迹 → 学生初始化 | 式7：教师采样轨迹的逐 token 负对数似然 | 是明确披露的离线监督目标，但不代表全部后训练只有这一轮 SFT |
| MOPD 主阶段 | 冷启动学生自采样；按样本领域 d 取对应教师 | 式6：学生到教师的 reverse KL；式8控制权重与截断 | 未给各域混比、teacher refresh/freeze 实现、学生初始权重来源 |
| 部署 | 最终统一学生/actor | 保留正常 harness 可见上下文 | hindsight critic 只在训练用，部署丢弃；GRM非部署策略 |

**未展开的领域也在阅读范围内**：通用 agentic 推理有 §3 的明确数据流程；terminal、web coding、general knowledge 只有专家存在与同 recipe 的陈述，没有单独数据/奖励/预算。全文未设数学 RL、多模态后训练、独立安全对齐或 DPO 配方章节。引用文献中的数学/多模态论文不构成 V2.5 使用了这些训练的证据。安全相关实披露是剔除 unsafe/exploitative 轨迹、工具黑名单、状态一致性和代码奖励防作弊意图（§2.2、§3.4、§4.4）；不能扩写成已完成一般安全/拒答对齐。

## 4. 数据、环境与轨迹生产

### 4.1 AutoBuilder 与 SWE 数据漏斗

任务定义为“明确描述、可执行仓库环境、验证测试”三元组，agent 从初始状态产生 patch，正确性按全部验证测试通过判定（§2.1/p4）。描述不直接照抄 issue：problem statement 主要依据 golden patch；requirements 主要依据 test patch；interface constraints 从两者推断 API、变量、结构和兼容性，再做清晰性检查。

AutoBuilder 的 build agent 分析仓库、生成从 clean checkout 装依赖并跑测试的脚本；verification agent 在隔离 sandbox 执行并解析**结构化测试框架输出**。接收条件是收集到**超过90%预期测试**且跨运行 pass/fail 可重复；不是“90%测试通过”，也不是“所有测试必须100%被收集”。失败的结构化信息回送 build agent 迭代修复。预配置底座、语言/构建模板、成功配置检索库共同减少重复试错（§2.1/p4；图2/p3）。

| 阶段/对象 | 数量与分母 | 生成/排除逻辑 | 成本与未知 | 定位 |
| --- | --- | --- | --- | --- |
| 原始仓库/PR/commit | 未给仓库/PR总数与时间窗 | 真实 PR/commit 为主，提取 golden/test patches | 来源清单、许可、去重与切分未给 | §2.1/p4 |
| 清晰任务描述 | 未给过滤前后数 | 歧义、不完整、欠规定、内部矛盾被删 | generator模型、prompt、调用预算未给 | 同上 |
| 环境构建成功 | 16.5%→57.2%，是环境构建成功率 | 上述模板/复用/反馈 loop 的组合 | 分母候选数、同池控制、重复次数未给；不是RL通过率 | 同上 |
| 验证环境 | >100,000 environments，12 languages | >90% expected tests collected，F2P/P2P可复现 | 不等于独立仓库数、镜像数、题目数或learner消费量 | 同上；图2/p3 |
| 原零通过任务提示恢复 | 提示后通过率约20% | 面向 near-miss 的过程提示 | 零通过的每题原采样n、恢复重试n、任务数未给 | §2.2/p5 |
| 无提示重建/最终训练轨迹 | 未给数量/存活率 | 冻结已验证patch，从原上下文重新生成，再查验证、提示泄漏和一致性 | 20%不能代替这一阶段存活率 | 同上 |
| 最终RL/SFT实际消费 | 未给各域任务/轨迹/token数 | 过程门控+评分，具体消费配比不明 | 无完整候选→验证→保留→学习漏斗 | §2–5 |

为避免 setup 淹没编程任务，参考变更中**不属于编程挑战**的依赖/配置改动预先应用。清除 git history、commit metadata 等参考解线索（§2.1/p4）。这不是严格 held-out/预训练去污染证明：未给基于仓库/PR派生关系的切分、时间截止、基座污染审计。原文提“提供的描述、仓库状态与可执行测试”，但未完整定义 actor能看哪些测试、private grader的所有权/隔离。F2P/P2P 图示与核心奖励不等于已公布 no-op、gold、合法替代解、完整 evaluator 控制面验证矩阵。

### 4.2 近成功恢复与过程过滤

near-miss 指已定位主要代码但漏关键检查、精确 schema、既有机制或后续诊断的失败。两步恢复是：先给“读哪里/核什么”的定向过程提示帮助获得 verified patch；再固定该 patch，从原始上下文重新生成无提示轨迹，只有同时通过执行验证、无提示泄漏、与patch/测试结果一致的样本留下（§2.2/p5）。不能简化成删除原对话中的 hint 文本，也不能称学生完全 on-policy 的失败重放。

规则层移除无效、不稳定、作弊轨迹；启发式过程层评价探索、定位、修改前推理、规格忠实、仓库惯例、patch最小性、验证质量、恢复、诚实性。通过但依赖硬编码/绕机制/改测试的轨迹被降权或删除；可救失败回恢复链。正负注释可用于偏好学习、rejection sampling 和过程奖励建模；没有偏好优化具体算法、pair构造或独立效果表（§2.2/p5）。“通过”与“值得作为监督”被区分，但合法替代解被误杀的统计未给。

### 4.3 数据阶段的 harness 改写与异常扰动

工具名、参数约定、输出格式和prompt模板随机改写，保持工具功能一致；同一任务仍用结构化测试结果验证。另注入缺失/不匹配依赖、瞬态命令失败、截断输出、噪声日志，以训练持续诊断（§2.2/p5）。这是作者提出的鲁棒性训练设计，未给注入概率、训练采样权重、异常严重度或受控泛化增益。刻意构造的可处理任务扰动与 §4.2.2 的错误 sandbox 反馈是两件事，不能把后者污染奖励合理化为训练鲁棒性。

### 4.4 KwaiClawEnv：SWE 以外的通用 agent 数据

动机是实际业务系统权限/安全/稳定性限制、LLM纯模拟的幻觉与状态不一致，以及手写sandbox成本。方案把 Skill 定义和真实 Task seeds 变为可执行服务，支持异构工具与多服务长链任务（§3.1/p5–6）。

| 层/扩展机制 | 实际流程与质量条件 | 原文数量及边界 | 定位 |
| --- | --- | --- | --- |
| Service | 人写 Skills + LLM生成 Services；原子服务链式/嵌套组成复合能力；先查执行、接口、逻辑 | 未给原子/复合服务准确数 | §3.2.1/p7 |
| Skill转服务 | 解析社区Skill的API、参数schema、约束，生成OpenAPI、容器配置、fixture | 这一路径生成成功率>90%；无候选分母 | §3.3.1/p8 |
| 类别引导生成 | 补长尾领域Skill变体，组合服务并做语义/多阶段校验 | 作者称环境规模较手建扩一数量级；无同预算/产量表 | 同上 |
| Task | 真实种子含目标、tool-use exemplars、机器可验标准；参数扩展、约束增强、工具链编排 | 数百万候选→超过十万高质量instances；不是AutoBuilder十万环境 | §3.2.2/p7、§3.3.2/p8 |
| 执行轨迹 | 配置难度、工具链长度、工具来源；并行rollout记录决策、调用、输出、状态转移 | 平均15次tool calls；最长>100 steps；两种单位不强行统一 | 同上 |
| Eval | 统一成如SFT-ready的训练格式，补辅助/缺失字段，过滤并反馈Service/Task | §3.3总述“数万多样交互轨迹”；与>十万instances不是同一计数口径，未给换算 | §3.2.3/p7、§3.3/p7 |

一致性验证三阶段（§3.4/p8–9）：(1)服务可用性：endpoint连通、OpenAPI完备、服务依赖；(2)任务：schema、工具引用、参数与可机器验证性；(3)容器执行：启动、fixture、交互、轨迹完整性与评分正确性。产物分 repairable failure、rejected defect、production-ready output，而非遇错误都归零奖励。

轨迹再过两层：硬规则检查工具黑名单、文件存在、必需工具覆盖、状态一致性，排除不安全/无效/幻觉；LLM-as-Judge评分语义正确、执行效率、交互自然度，两层都通过才进训练。早期确实发现schema错误、未实现endpoint被引用、轨迹与fixture冲突，不是只有正面宣传（§3.4）。judge模型/阈值/标注一致性、闭环迭代次数、在线或离线更新节奏不明；不能扩写为已证明最优的动态RL curriculum。writing、data analysis与业务工具链是原文真实覆盖，当前项目不据此建设通用服务合成平台。

## 5. 学习目标、奖励与实际语义

### 5.1 PPO、GAE与分母

作者选择PPO的理由是：压缩/sub-agent/query rewriting会把同一session拆成不同前缀样本，统一的trajectory group baseline难定义；critic能读训练期特权信息；GAE配reward shaping可定位到turn上的坏行为（§4.3/p12）。这是算法选择的作者解释，报告没有PPO对GRPO等算力对照，不能推出GRPO在所有此类harness上数学上不成立。

式1（p12）最大化：

\[
\mathcal J_{\mathrm{PPO}}(\theta)=
\mathbb E_{q\sim P(Q),\,o\sim\pi'(\cdot\mid q)}
\left[\frac1{|o|}\sum_{t=1}^{|o|}
\min\{r_t\hat A_t,\operatorname{clip}(r_t,1-\epsilon,1+\epsilon)\hat A_t\}\right],
\qquad r_t=\frac{\pi_\theta(a_t\mid s_t)}{\pi'(a_t\mid s_t)}.
\]

q是任务输入，o是行为策略采样的输出序列，s_t为条件状态，a_t为当前token动作，πθ为更新策略，π′为行为策略，ε为ratio clip宽度。**式1先对每个o按|o|平均，再在样本分布取期望**，不是整个batch总token数做分母。文中未精确定义o是完整session、分段请求还是某种训练拼接；不能据式1补出fan-out或共享前缀的计权规则。

式2–3（p13）原文为：

\[
\hat A_t=\sum_{l=0}^{T-t-1}(\gamma\lambda)^l\delta_{t+l},\qquad
\delta_t=r_t+\gamma V'(s_{t+1})-V'(s_t),
\]
\[
R_t=\hat A_t+V'(s_t),\qquad
\mathcal L_{\mathrm{critic}}(\psi)=\mathbb E_{(s_t,R_t)\sim\mathcal D}
[(V(s_t;\psi)-R_t)^2].
\]

V′是前一迭代价值网络，ψ是当前critic参数；γ与λ分别是折扣和GAE系数，T是轨迹终点的记号，数值/terminal bootstrap约定未给。**符号冲突必须保留**：式1后的r_t明确定义为概率比，式2又在TD residual的即时奖励位置使用r_t。上述忠实转录原式；阅读解释时把前者称“ratio”，后者称“即时奖励”，不是把ratio加到value上。原文没有正式勘误或代码可核其实际变量。

### 5.2 非对称 hindsight critic

Actor只读截至当前turn的工具输出、文件片段、压缩摘要等正常交互历史。Critic训练时额外读c_t，**可能包括**最终pass/fail、测试分布、coverage、patch diff、任务元数据、轨迹统计、后续turn；“may include”不是每项在每域必用。式4（§4.3.2/p13）：

\[
\mathcal L^{\mathrm{asym}}_{\mathrm{critic}}(\psi)
=\mathbb E_{(s_t,c_t,R_t)\sim\mathcal D}
[(V(s_t,c_t;\psi)-R_t)^2],\qquad
R_t=\hat A_t+V'(s_t,c_t).
\]

GAE的value项替换为非对称value，actor仍用式1；推理丢弃critic和c_t。作者称其降低方差、不改变部署输入。**阅读者保留问题**：事后最终结果/后续行动可能与当前动作相关，部署不读取c_t并不自动证明该baseline不引入梯度偏差。报告未给相应无偏性推导、c_t构建/遮蔽规则、或受控value ablation；也未细化相邻value如何各自绑定c_t。因此只记为报告提出并采用的机制，不替作者补理论保证。不可从被引的mini-critic论文推断KAT critic更小或actor/critic共享参数。

### 5.3 规则奖励：完整十项

§4.4.1/p13–15及**表1/p23**列出三层。主任务项权重最高，但无数值、加权总式、归一化或裁剪区间。

| 层 | 项 | 准确含义与限定 |
| --- | --- | --- |
| Core | 1 Core Task Score | 只有所有F2P和P2P都通过才得满分；不能推出reward只取0/1，因为还有部分奖励/惩罚 |
| Behavior | 2 Content Repetition | 正文谈thinking/final冗余；表1具体指think/content过量重合；没有重复率实现 |
| Behavior | 3 Garbled Content | 异常/乱码/非法字符惩罚 |
| Behavior | 4 Tool Invocation Accuracy | 参数缺失/错误导致调用失败；正文举`<tool_use_error>` |
| Behavior | 5 Invalid Tool-call Placement | tool call错误放入reasoning/think字段而非指定输出区域 |
| Behavior | 6 Redundant Intra-turn Tool Calls | 同轮冗余重复调用同工具；不可推成所有同工具批量调用禁止 |
| Behavior | 7 Tool-call Parallelism | 允许合理batch，惩罚超过未披露阈值的并发 |
| Behavior | 8 Debug Artifact Cleanup | 任务后清理临时复现/验证脚本、日志、cache；**此项在表1有，正文六项bullet没有** |
| Failed trajectory | 9 File Search Accuracy | 按F₂评价相关文件检索，兼顾precision/recall；相关文件gold集合来源和计算细节未给 |
| Failed trajectory | 10 Unit Test Pass Rate | 失败中部分测试通过可给正反馈；表1强调取得进展且不引回归，但未定义P2P失败时如何与F2P部分成功合成 |

F₂的通常定义是5PR/(4P+R)，偏重召回；**这只是标准术语释义，报告未印该公式或给边界情况实现**。Core规则意图是抑制硬编码、绕逻辑、弱化测试的reward hacking；F2P/P2P全过本身不证明反作弊完全。报告没有完整测试控制面隔离、恶意patch审计、攻击成功/误杀率，所以不能将作者的“prevents”当安全性证明。

### 5.4 Rubric与GRM：训练judge不等于训练actor

规则难判断测试充分性、策略调整和失败覆盖；作者人工分析真实轨迹的调用、环境反馈、改动和测试，抽象触发条件、适用范围、奖励信号，再用trajectory级judge补充（§4.4.2/p15）。正文三维是故障诊断/复现、修后验证、执行策略；表2/p24把回归测试另列，展示四类八条，而不是仅三个打分标签。

| 表2类别 | 两个展示标准与适用边界 |
| --- | --- |
| Bug Reproduction | 修改前无复现/测试/调试；静态根因定位（列出未动态复现、但经源码/既有测试/历史/框架推理准确定位根因的情形；奖惩方向未披露） |
| Post-Fix Validation | 缺针对题述失败场景的自定义验证；存在相关既有测试却修后未跑（没有相关测试时不适用） |
| Regression Testing | 只测直接场景、未做更广回归；尝试更广测试但语法/配置/调用错误，未产生有效证据 |
| Behavioral Strategy | 复杂多步`python -c`引入转义/编码/可读性问题；重复错误测试命令、目录、label、框架或module路径 |

表2标注Partial Display；没有每条奖惩符号/权重，不能把“静态定位”一律当违规。表3/p24也是Partial Display，四类坏例是复杂inline代码执行、替换字符串不存在等tool失败、用Bash而未用专门工具、调用环境中不存在的pytest模块。它们用于解释rubric来源，不是任务失败比例的统计。这类“应使用专门工具”规则也体现harness依赖，不能直接移植为跨harness统一准入条件。

GRM训练输入是历史agent轨迹与人工标注的rubric触发项及理由，人工排除证据不足/模糊标签。原始base judge不严格遵循rubric，因此用targeted RL训练专门GRM。式5（p15）：

\[
r_{\mathrm{GRM}}=
\begin{cases}
|GT\cap Pred|/|GT|-|Pred\setminus GT|\lambda,&GT\ne\varnothing,\\
1-|Pred\setminus GT|\lambda,&GT=\varnothing.
\end{cases}
\]

GT是人工真触发项集合，Pred是judge预测集合，λ为每个误报的惩罚系数；此λ与GAE的λ语义不同，原文复用字母。奖励是**真项召回减误报数量惩罚**，不是precision/F1、不是actor任务reward总公式，可能为负且未给下界clip。原文称RL后judge更会看完整上下文、少靠关键词，但没有GRM held-out准确率/误报率、样本数、独立重复或actor增益消融；不能声称已定量证明judge可靠。

### 5.5 五教师MOPD的完整目标

§5/p15–16：每个(x,d)按domain d选择一个教师πT_d；不是每个token五教师投票或平均logits。学生πθ先在自身策略下生成y；相应教师对相同学生前缀提供token级logit监督。K=5已明确，专家域见§3。式6（p16）：

\[
\mathcal L_{\mathrm{MOPD}}(\theta)=
\mathbb E_{(x,d)\sim\mathcal D}\mathbb E_{y\sim\pi_\theta(\cdot\mid x)}
\left[\sum_{t=1}^{|y|} w_t\,
\mathrm{KL}\big(\pi_\theta(\cdot\mid x,y_{<t})\,\|\,
\pi_{T_d}(\cdot\mid x,y_{<t})\big)\right].
\]

KL方向是**学生到教师**，作者称reverse KL；w_t∈[0,1]。公式是每个位置的完整分布KL表达式，再逐token求和，**未出现1/|y|或Σw_t分母**。作者称其倾向teacher高置信模式，减少多域干扰；同时承认错误模式也可能被放大。不能从数学分布式直接认定实际实现做full-vocab forward/storage：实际full-vocab、top-k近似还是sampled-token estimator、teacher logits取得接口、温度、KL梯度估计以及tokenizer兼容均未披露。式8的top-k用于兼容性测量，不等于KL也只在top-k求和。

### 5.6 长上下文蒸馏稳定性与截断

§5.1/p16–17明确负面现象：学生长前缀偏离teacher训练分布，使teacher条件预测不可靠，造成loss振荡、entropy collapse、gradient norm spikes；reverse KL可能向错误局部模式过度集中。两项处理：

1. **Off-policy cold start**：先用各域教师采样y进行学生监督训练。式7/p16为 \(\mathbb E_{(x,d),\,y\sim\pi_{T_d}}[-\sum_t\log\pi_\theta(y_t\mid x,y_{<t})]\)。采样者是教师，这一步不称on-policy；它预对齐学生分布，降低早期前缀漂移。数据数/步数/学习率不明。
2. **Drift-aware dynamic truncation**：式8/p16定义 \(\rho_t=|\mathcal T_t^k\cap\mathcal S_t^k|/k\in[0,1]\)，分别是teacher/student top-k预测集合。w_t是ρ_t的单调函数，兼容性低的token减权或归零；连续m个token低于hard threshold时截断，不对后续token反传。k、m、threshold和权重函数均未给。

原文p17保留截断点前所有valid prefix tokens，只以**gradient masking**实施而不设显式长度目标，并用length-stratified batching维持长上下文样本比例。这里“valid”不必意味着每个前缀token都是权重1，低兼容token仍可能减权。作者同时说把计算重新分配给新样本，却未给是否真实停止后端生成、teacher forward是否提前终止或在线队列策略。不能把这段写成“丢整条长轨迹”或“保证所有长度偏差已消失”；保留前缀和分层batch不证明被截后缀梯度无选择偏差。

### 5.7 不应补造的训练消费细节

已查§2–5和文末表1–3：每题采样数、batch/minibatch、每批更新次数、optimizer/LR、PPO ε/γ/λ、KL reference penalty、entropy系数、actor/critic初始化及大小、优势归一化未给。π′明确是behavior，不是额外reference；式1不是faithful DIS配方。PPO assistant/thinking/tool observation/compaction mask、分裂session的样本单位、shared-prefix去重、终止/截断bootstrap均不明。规则惩罚和数据过滤不等于已披露失败/解析错/超时样本如何进入组统计、梯度或补采；这三个问题分别未知。MOPD没有GRPO式group统计的披露，不把“全零reward组过滤”当它的已用机制。

## 6. Rollout、harness与infra

### 6.1 Harness作为训练分布

§4.1/p9–10把过拟合分成动作格式、上下文排列、控制流依赖。变化轴包括function calling/代码块/tag协议，全历史/滑窗/摘要压缩/不同observation截断，简单ReAct到规划/反思loop。**两类均实际参与RL**：白盒mini-swe-agent无压缩、调用规模较小、结构清晰；黑盒ClaudeCode/Codex/OpenClaw/OpenHands等贴近真实部署的上下文重组。作者用“白/黑盒”描述训练系统如何看轨迹和控制流程，不等同于软件许可证是否开放。图4/p10还展示SWE-agent与Codex CLI；图示不够推断每个harness的实际样本占比。

未给各harness版本/commit、随机化配比、cross-harness held-out矩阵、等算力消融；“降低三种过拟合”是设计动机/作者解释。保持功能的工具模板变化，与引入压缩、subagent等信息/执行能力变化应分开判断。

### 6.2 Gateway与token保真

图4/p10和§4.2.1/p10–11给出的顺序：harness在KwaiEnv执行；Gateway中介所有环境–Rollout Engine通信；Rollout Engine产生策略响应；一条轨迹完成后Gateway写入Experience Buffer；Train Engine从buffer采样batch更新，再同步weights到rollout。图4画N个rollout workers、M个train workers、request-level data、token-in/token-out，以及Anthropic/OpenAI Chat/Responses协议适配。

作者观察约200-turn agent任务中**约40%的samples发生retokenization drift**，不是40%的token错，也不是所有harness/长度的普遍发生率。实现绕过推理后端chat的apply_chat_template/重分词，直走`/generate`，作者据此声称trainable token与behavior生成token一致（§4.2.1）。外部harness仍可用Chat/Responses协议，由Gateway桥接；“绕过chat”指后端路径。

此图与文字支持训推交互解耦，但未给fully-async调度、策略版本标签/权重发布原子性、staleness阈值、backpressure、长尾策略、重试/取消、partial rollout/resume、KV复用或prefix cache，也没有logprob捕获/采样支持集、路由重放与数值精度细则。通过`/generate`是token一致性的必要工程线索；**阅读者推论**：仅端点名称不能独立证明压缩/重写/分叉后的训练覆盖与计权都正确，需要实现/测试支持。

### 6.3 环境错误比“再调算法”更直接的证据

§4.2.2/p11–12从V2早期崩溃/慢收敛讲起，初先归因算法并调参，后来抽审发现约16%轨迹含至少一个sandbox自身故障。最严重的边界错位让后续约40步observation为空。V2.5集中修复稳定性和执行正确性。

| 作者报告的观察 | 修复前→后 | 分母/比较边界 |
| --- | --- | --- |
| 镜像/磁盘压力 | 峰时磁盘约95%→优化后稳态约60% | 一个是peak，一个是steady-state，不是同分位数内存/吞吐对比 |
| 镜像GC/初始化超时导致无效rollout | 全rollout约6%–7%→<1% | early-release删除后续不太会再用的镜像；非无条件删除活跃环境；无cold-start时延实数 |
| 远程初始化环境变量覆盖系统配置，verifier读错 | 样本约6%–7%输出受污染→<1% | 错反馈相当于翻转reward；非模型tool-use失败率 |
| 总sandbox反馈错误 | 约16%→<2% | 初始定义是抽审轨迹中至少一次sandbox故障；前后审计样本数/窗口未给 |
| 训练collapse频率 | 约降一数量级 | 未给每多少step/run/hour归一化，不能换算成明确概率 |

不能简单把两个6%–7%与16%相加核算：可能重叠，口径/窗口未披露。修复后图5/p11显示SWE reward上升，目视大致从0.51到0.63、横轴到约180余step；此处是**读图近似**，未给原始数据/平滑定义、reward组成、对照曲线、预算或测试集含义。它不是pass@1、完整训练步数或独立泛化收益证明。

## 7. 评测、结果与负结果

### 7.1 内部bench的构建与评分

**KAT Code Bench**（§6.1/p17）：快手内部真实开发任务，12语言，涵盖bug、功能、接口兼容、行为一致、跨模块、回归修复；冻结base commit、环境、verification入口。策展迭代采样/执行/人工复核/轨迹审计，排除不可复现环境/flaky tests、过度绑定参考实现误杀正确替代解、描述–verifier不符和过模板化泄漏路径。记录全轨迹，作者还把它用于数据选择、失败归因、增广。**未知**：题数、split、时窗、与训练池隔离及是否最终测试不参与反馈；不能自动称它独立held-out。

**KAT Claw Bench**（§6.1/p18）：真实业务query先扩展，按真实性/可行性/可评估性筛选，转成描述、材料、类别、难度、rubric完整任务。客观输出自动查文件/数值/格式/可执行性；开放交付按任务类型结合自动与人工分层评分。多模型检查自包含与评分有效性，跨模型验证发现歧义/评分不稳定即修或删。

七类是个人效率与办公、内容创作运营、软件工程、数据分析洞察、信息检索处理、自动监控告警、投资分析决策；场景包括短视频、直播、电商、广告、办公。其“持续情报”等只是评测业务场景，报告未由此展开长期记忆/世界模型训练。题数、难度分布、评分权重、人工一致性、跨模型审查是否形成selection bias均未量化。

### 7.2 表4完整结果与协议例外

下表逐项转录表4/p19（图1/p1为相同结果的可视化）。**只称原文报告分数**；除PinchBench明确Avg外，报告没有足够定义把各列统一改标成pass@1或成功任务百分比。

| Benchmark | KAT-Coder-V2.5 | GLM-5.1 | GLM-5.2 | Kimi-K2.6列 | Opus 4.8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SWE-Bench Pro | 65.2 | 58.4 | 62.1 | 58.6 | 69.2 |
| KAT Code Bench | 53.1 | 49.6 | 50.3 | 48.9 | 57.3 |
| PinchBench (Avg) | 94.9 | — | 87.0 | 80.7* | 93.5 |
| KAT Claw Bench | 85.5 | 84.4 | 86.8 | 85.2 | 90.7 |
| Terminal-Bench 2.1 | 60.7 | 61.8 | 77.9 | 73.0 | 84.6 |
| SciCode | 50.3 | 43.8 | 50.5 | 53.5 | 53.5 |

* PinchBench 80.7属于**Kimi-K2.7-Code**，不是该列其他行的Kimi-K2.6。PinchBench所有分数注明从[榜单](https://pinchbench.com/)取Avg，取数日期2026-07-02；本笔记保留报告时点，没有拿今天榜单替换。
* §6开头/p17说除特殊说明外统一Claude Code，并固定工具、context budget、执行环境、decoding config。表4的PinchBench是明确例外；不能声称“六项全部是作者在同一Claude Code预算下重跑”。
* 报告把terminal/scientific两行归“AA Coding Index”，没有定义一个额外综合平均，也没说明这两行外部取数的完整路径；不能据标签断言与当前AA榜完全相同。
* SWE-Bench Pro split/revision、SciCode配置、PinchBench Avg的内部平均分母、所有benchmark题数与重复数、temperature/top-p/effort、token/context/turn/wall-clock上限、harness版本都未给数值；仅“统一”声明不能还原预算。Terminal版本明确是2.1，不能换成2.0/4.0。

表中可计算差值（阅读者计算，不是额外实验）：SWE Pro距Opus为4.0分，KAT Code为4.2分；PinchBench高1.4分，无区间不可宣称显著；KAT Claw为第三，低Opus5.2分；Terminal为五者最低，低Opus23.9分；SciCode低GLM-5.2 0.2分，低并列第一3.2分。“科学编程接近GLM-5.2”不能掩盖terminal弱项。原文SciCode把GLM-5.2下划线作“第二高不同分值”，前面已有两个并列53.5；不可误算KAT名次。

### 7.3 什么实验没有做、哪些负结果不能省

完整检查§2–7、图1–5和表1–4后，**没有**如下受控表：同底座PPO/GRPO、去hindsight、去rubric/GRM、去near-miss、固定数据/compute去harness随机化、五专家→冷启动→MOPD→截断消融，或同等teacher/API总预算比较。16.5%→57.2%是组合构建流程前后，16%→<2%是工程修复前后，不能给每个子机制分功劳；图5没有消融基线。

明确负面经验包括：只调RL超参没有解决真实环境错误；自动生成会出现schema/endpoint/fixture不一致；只保成功轨迹仍含作弊/低质；纯长上下文OPD可能loss振荡、熵塌缩、梯度尖峰；权重合并和顺序多域SFT存在作者称的see-saw风险；terminal/scientific覆盖尚待加强（§2.2、§3.4、§4.2.2、§5–7）。最后的合并/OPD解释没有独立量化对照，不能转成证明“任何参数平均都不行”或“本MOPD无跨域退化”。

## 8. 成本、开放资产与复现程度

| 成本/资产面 | 已披露 | 仍缺（核查范围） |
| --- | --- | --- |
| 环境/数据生产 | 构建成功率、环境规模、Claw候选/保留实例量级、调用长度 | CPU/存储/人工/API、模型身份、重试/每题校准n、墙钟；§2–3 |
| 教师与GRM | 五域logit教师、教师生成cold start、人工rubric GRM RL | 教师/GRM参数量、访问接口、tokenizer、forward/API总量与费用；§4.4–5 |
| RL/MOPD | PPO/GAE目标、critic与cold/MOPD/drift公式 | GPU型号/数量/GPU-hour、并行拓扑、MoE/precision/offload、优化器和总steps/tokens；§4–5 |
| 评测 | 六bench表分数、默认harness、Pinch榜日期 | 题数、重复、预算、置信区间、CPU/GPU/API成本；§6 |
| 服务/代码/数据 | 报告链接StreamLake服务 | 服务网页本轮超时；论文/入口未列可核训练代码、weights、数据、镜像revision；全文及arXiv元数据 |

不能把>100k环境说成低成本，不能以未报参数规模的“较大通用模型”比较推断KAT是某个30B模型，也不能把图5约180步当总训练预算。当前可复用的是方法证据与失败类型；可完全复现实验的配置/资产不足。

## 9. 证据边界、旧稿纠错与原文内部问题

### 9.1 最影响项目判断的未知

| 问题 | 查过的位置 | 保留结论 |
| --- | --- | --- |
| 模型与资源是否适合8卡 | §1–7、图4–5 | 参数规模、全局预算未给；不可做同量级成本承诺 |
| 无提示恢复实际增加多少训练价值 | §2.2、图2、§6 | 约20%只在原零通过任务提示阶段；重建保留率/独立学习增益不明 |
| 数据是否严格独立/许可可用 | §2.1、§3、§6.1 | 删除history与内部策展不是完整split/污染/许可证明 |
| PPO split/GAE如何落地 | §4.3–4.4、表1–3 | 公式可读，mask/共享前缀/终止/critic因果合法性实现不明 |
| 黑盒训练是否完全faithful | §4.1–4.2、图4 | `/generate`报告保真，但无端到端token/概率/路由/重写计权实现证据 |
| MOPD是否full-vocab、教师冻结、同tokenizer | §5–5.1、式6–8 | 数学KL+logit监督已知；实际计算、teacher更新规则、支持集转换未给 |
| 指标是否同预算并有显著差异 | §6、表4、图1 | 默认统一条件声明，Pinch榜例外；预算值/样本量/区间缺失 |
| 安全/偏好/数学/多模态是否另有后训练 | 全文含p23–24 | 有数据安全过滤/偏好用途/通用专家；没有独立训练配方；不由引用文献填空 |

### 9.2 对指定旧稿的更正与保留

1. **KAT引文错指Qwen**：`项目设计外部pro.md`约1025与1147行把Qwen3-Coder-Next和KAT训练陈述共同挂到引用[7]，末尾[7]是2603.00729v1。KAT事实须单独引用2607.05471v1 §4.1/p9–10；不能用Qwen工具模板消融替KAT提供证据。旧文件保留，本篇纠正引用绑定。
2. **白盒/黑盒参与训练**：旧稿方向正确，现核到§4.1明确“两类均参与RL”；同预算harness随机化消融缺失的旧限制也保留。不能进一步声称未见harness泛化已被独立证实。
3. **五专家MOPD**：`外部pro1.md`约214行的“五专家”核实为K=5（§5/p16）。补上按域选单teacher、off-policy cold start、reverse KL、top-k兼容截断；不能与E7另一篇同名机制自动视作相同实现。
4. **40% drift**：`外部pro1.md`约305行的约200轮、近40%大意正确；精确定义是该实验规模中出现token drift的**sample比例**，不是token错误率、任务失败率或本项目发生率（§4.2.1/p10–11）。
5. **成本unknown**：旧稿关于训练硬件/GPU-hour/费用未知的判断保留，现已查完整正文、文末表，仍无数值。不是“读到一半没找到”或“只有摘要没写”。

### 9.3 原文内部不一致/含糊处，不默默修平

- 式1/2复用r_t指ratio和reward；本篇§5.1保留原式并解释。
- §4.4.1正文行为列表六条，表1多Debug Artifact Cleanup；以完整披露记录七项，不虚称正文已有。
- §6默认统一harness的泛述，与表4的PinchBench榜单例外需同时保留；图1的Kimi横轴仍写K2.6，表4脚注明确Pinch数据是K2.7-Code，使用有脚注的身份。
- §4.2/p10写“Similar to KAT-Coder-V2”却引参考[14]，p22对应2025的《Kat-coder technical report》（2510.18779）；§1引[1]才是《KAT-Coder-V2 Technical Report》（2603.27703）。只核V2.5的参考条目身份，没有因此精读两篇前代，更不会用错链补V2.5配置。
- 表2静态定位举commit history为潜在证据，§2.1又说SWE环境删除history；报告没说明rubric源历史轨迹与当前环境的关系。它提示rubric例子不可逐字当所有rollout可见材料规范。
- MOPD截断声称避免length bias、融合减少see-saw、PPO critic降低方差，均缺对应受控量化或证明；保留作者解释与阅读者判断之分。

## 10. 对RepoHarness项目一的意义

**映射日期2026-09-07**。已读[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)（2026-09-05）与[项目一建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)（2026-09-07）。后者§4.1纳入2026-09-06审查，列REALIGN/rewrite/FORK覆盖、概率/分母、deadline与评分控制面缺口，更新了简报“链已搭完”的乐观快照；不是新实施批准，也不意味着已修。没有展开全仓审计。基线仍是miles+SGLang+外部coding harness，rh2负责环境/评分/训练消费边界；GRPO n=8+faithful DIS仍是候选，C包未定事项不由此论文决定。

| 候选借鉴 | 来源事实 | 上游/我方/暂不适用 | 最小验证与成本边界 |
| --- | --- | --- | --- |
| 结构化测试而非exit code验环境 | AutoBuilder >90%收集及跨次可复现，§2.1 | 复用既有builder/任务资产；rh2验证所选parser和评分材料边界，不必新造AutoBuilder | 小批目标Linux真运行，报collected/expected、no-op/gold/合法替代解和稳定性；不能盲照90%阈值 |
| 黑盒上下文变化后的真实token消费 | Gateway token-in/out与40%sample drift，§4.2.1 | TITO/推理/异步基础优先复用miles/SGLang；rh2候选增量是现adapter正确接入与覆盖验证 | 固定真实请求检查生成→保留→训练token与共享前缀权重；先核上游，不能重新造Gateway当原创 |
| 区分环境错反馈与模型失败 | sandbox 16%→<2%，§4.2.2 | rh2应用层环境/评分边界与失败归因；不建新监控平台 | 少量真实轨迹审计，分母是全部尝试，错评分/timeout/成本单列；无对照不声称同样收益 |
| near-miss反馈价值 | 提示恢复后无提示重建，§2.2 | 数据候选；先保持可信静态池与完整轨迹SFT基线 | train/dev同题等API预算普通重试vs过程提示修复，报告无提示重建保留率与held-out收益；不是先上复杂蒸馏 |
| 多harness泛化 | 两类实际参与RL，§4.1 | 先外部第二harness评测；随机化训练暂为条件扩展 | 固定checkpoint/任务预算，分格式与能力变化；确有迁移缺口后再做同数据/compute训练对照 |
| PPO hindsight、复杂reward、五教师MOPD | §4.3–5 | 暂不作为首版必做；非原文无价值，而是新增critic/teacher/rubric与归因成本大 | 需要自身瓶颈和等预算实验；不据本报告改GRPO/DIS、组准入或token分母 |
| KwaiClawEnv多服务业务面 | §3 | 当前coding/SWE/terminal之外主要暂不适用 | terminal优先用现成可执行任务作迁移探针，不为办公/投资/监控建通用平台 |

可支持项目叙事的是**上游复用下的真实harness训练消费、可信环境/评分、静默失败定位**有产业报告先例。不能据文献把上游通用机制称原创，不能把作者数据当自身结果。简历上的效率/学习改进仍需本项目实际消费成本、正确基线和独立任务学习结果；本次阅读未改代码、未运行训练、未租GPU、未新增语义定案。

## 11. 快速定位与关联阅读

- 来源/版本/全覆盖 → §1；[本地PDF](sources/N01/2607.05471v1.pdf)。
- 环境/恢复/通用服务 → §4；原§2–3/p3–9、图2–3。
- PPO/critic → §5.1–5.2；原§4.3/p12–13、式1–4。
- 规则奖励/GRM → §5.3–5.4；原§4.4/p13–15、式5、表1–3/p23–24。
- MOPD/cold start/截断 → §5.5–5.6；原§5/p15–17、式6–8。
- Token/环境故障/预算 → §6、§8；原§4.2/p10–12、图4–5。
- 六项结果/协议例外 → §7；原§6/p17–19、表4/p19。
- 关联资料编号：E7 MOPD（独立论文，不能互填配方）、E13 MiMo-V2-Flash（术语来源）、N11 miles/TITO（上游能力对照）、E1 Harness Interplay与N16 Harness-Bench（受控/评测证据边界）、N07 SDPO和N08 OPSD（自教师与本篇五外部专家不同）。这些编号不是声称本任务已读其全文。

## 12. 独立检查与修订记录

2026-09-07，在本任务内由 **GPT-6 Astra / high**、干净上下文（`fork_turns="none"`）的一名独立sub-agent完成审查，没有递归分派。审查者先按原文目录独立列覆盖清单，再比对初稿，并目视核对全部公式、图表；审查范围和逐项证据见[独立审查](reviews/03_N01_review.md)。

审查未发现P0/P1/P2错误或后训练覆盖遗漏，提出 **R1/P3**：§5.4“允许静态定位”比表2原文更强，可能误读为已披露的复现豁免规则。已改为“列出未动态复现但准确定位根因的情形；奖惩方向未披露”，并保留表2只是Partial Display、没有每条奖惩/权重的限制。证据是原文表2/p24及TeX `Static Bug Localization` 行；处理记录已追加到审查文件末尾。此修订不改变训练机制解释，不需要补造实现或新增政策。

**本任务精读完成**：全部后训练正文及文末技术表已读，独立审查与修订已完成。残余来源缺口为StreamLake网页访问超时，以及原文未提供的模型/预算/实现/评测细节（§8–9）；这些是明确记录的证据边界，不以本轮笔记已完成冒充论文实验已复现。
