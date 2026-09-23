# FrogNano：4B Coding Agent 的任务合成、Leaf 与异步 RL 精读

FrogNano 从 Qwen3.5-4B 出发，在真实仓库快照上交替进行五轮 TaskPilot 任务合成与 RL，每轮约 300 个新任务、200 次参数更新。报告的主模型不新增 SFT 或强教师行为蒸馏；强模型仍可参与出题。Leaf 的接口适配、当前策略校准的任务以及成功轨迹的长度奖励共同构成配方，不能把全部收益单独归给 online synthesis。作者报告 SWE-bench Verified 61.5%、SWE-bench Pro 37.6%、Terminal-Bench 2.0 31.1%、PatchEval-Verified 23.2%；其中 Verified 用于验证和 checkpoint 选择，后三者才被作者定义为 held-out。附录完整提供了独立 verifier、SFT consolidation、自摘要、行为与反作弊分析，但也出现重要内部冲突：包括 DPPO 判据、若干分数、compaction 触发率，以及“零有效 reward hacking”与附录有效案例不相容。本文保留各口径，不替作者修正或拼成一份已复现配方。

导航：[来源与覆盖](#source) · [阶段、角色与 Leaf](#stages) · [任务生产](#tasks) · [RL 与系统](#rl) · [评测和附加训练](#eval) · [审计、限制与项目映射](#audit)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**主来源 P：** *FrogNano: Training a 4B Coding Agent via Online Task Synthesis*，Minseon Kim、Zhengyan Shi 等，Froggy Team — Microsoft Research Montréal。官方网页登记日期 **2026-09-07**；阅读与成文日期 **2026-09-09**。只对本次固定 PDF 做结论，不给它虚构 arXiv 版本号。上轮导航候选 `2609.07925` 本轮仍未取得，未验证它与 PDF 的版本关系。

- [本仓库原始 PDF](../pdfs/frognano_technical_report.pdf)；[官方 PDF][P]。
- 官方托管提交：`microsoft/debug-gym@6c8cea40a507c8e9dac0439c270c3c5a3ce8a4dc`，`docs/static/papers/frognano_technical_report.pdf`。
- 本次附件为 **37 页、2,753,933 bytes**。对附件实际计算 Git blob ID 得到 **`c7ac442cdeb49cd4f0cd15793649b05234abcb55`**，与先前取得的官方元数据一致；因此不是拿另一版本替换原链接。
- PDF metadata 的生成时间为 `2026-09-07 19:41:50Z`。页码以下均为 **PDF 物理页，与印刷页一致**。
- 项目独立分支：`research/frognano-20260909`；本轮写入基线为用户加入 PDF 后的 `ed425b2eaaac02911e8d8b20b1610caea710c421`。分支最初从 `miles-migration@2a533b1f…` 创建，不假定其自动包含其他线程后续进展。

**实际阅读：**全部 §1–7、Limitation、Contributions、Acknowledgment、66 项参考文献入口和附录 A–H；20 幅编号图、4 张编号表，以及 Appendix G 的长 rubric、输入 schema 和具体轨迹。参考文献检查用于恢复来源身份，**不等于全文阅读了 66 篇引用**。本地逐页提取、渲染；图表及主要公式结合图像核查，未使用 OCR。

**证据分层：**下文标为“原文”的内容来自上述 PDF；作者的机制解释不升级为受控因果结论。算术、方法边界和 A/B 建议明确写成读者分析。配套官网／仓库只用于开放资产定点检查，不用现有 debug-gym 或 slime 默认配置补写 FrogNano 未披露的实验。旧[来源登记](frognano_source_intake_20260909.md)只保留获取历史，阻塞已解决。

### 1.1 全文覆盖表

| 原文位置 | 内容与阅读范围 | 本文位置 |
| --- | --- | --- |
| p.1 §1、Fig.1 | 摘要、动机、五轮主曲线和真实任务基线 | §2、§4、§6 |
| pp.2–3 §1、Fig.2–3 | 参数规模比较、数据／harness／RL 三部分、交替循环图 | §2、§3、§6 |
| pp.3–4 §2、Fig.4 | Leaf 五工具、执行顺序、终止规则、loss token 范围 | §3、§5 |
| pp.4–5 §3.1、Fig.5 | 任务五件套、执行验证、策略校准、题面变体 | §4 |
| pp.6–8 §3.2–3.3、Fig.6–7 | 语义信息量例子、五轮任务统计、第五轮重设计 | §4 |
| pp.8–9 §4.1–4.2 | 组优势、概率差 mask、原分母、长度奖励和截断 | §5 |
| pp.9–12 §5.1–5.2、Fig.8–12 | 主成绩、选择器、consolidation、compaction、迁移、动态和失败 | §6–9 |
| pp.12–14 §6、Table 1 | 任务生产比较、既有 UED、相关 RL 和小模型；完整阅读但不代证被引工作 | §4.4、§10 |
| pp.14–15 §7、Limitation、贡献／致谢 | 结论、任务与语言限制、安全、团队实际职责 | §10–11 |
| pp.16–20 References | 66 项引用身份；DPPO、PipelineRL、negative PI 等依赖 | §5、§7、§12 |
| p.21 App.A / A.1、Table 2 | 四项 benchmark 的集合与评分、RL 配置全部字段 | §5–6 |
| pp.21–22 App.B、Fig.13–15 | 推理成本估算、pass@k、各轮训练集结果 | §6、§10 |
| pp.22–23 App.C | 独立 consolidation 数据、top-64 KL／CE 分流、两类结果 | §7 |
| pp.23–24 App.D.1–D.6、式(1)–(3) | 自摘要触发、预算、整组截断、重建、提示与静默 no-op | §7.3 |
| pp.24–27 App.E、Fig.16–19 | 固定评测上的计算量、工具时序、配对分析、成功相关行为 | §8 |
| pp.26–30 App.F.1–F.4、Fig.20、Table 3 | 两阶段检测、17 类 taxonomy、present/effective、误报边界 | §9 |
| pp.30–36 App.G | judge 的完整规则结构、schema、删节证据实例；仅作研究材料阅读 | §9.3 |
| p.37 App.H、Table 4 | multi-call 漂移、训练题面上的 TypeScript 搜索偏好 | §8.3 |

<a id="stages"></a>
## 2. 核心问题、训练阶段与模型角色

### 2.1 作者要解决的不是单独一种新 RL 算法

报告研究一个紧凑模型如何成为 repository-level coding agent。其配方由三个相互作用的部分组成：适合输入模型的 **Leaf 接口**，由当前 checkpoint 参与校准的 **TaskPilot 任务供给**，以及有小策略延迟和长度控制的 **group-relative RL**。§6 明确承认 RL setup 本身不是独立的新算法，贡献在于这些设计在 4B 设置下的组合。[P, pp.1–4、14][P14]

“仅 RL”指从起始 Qwen3.5-4B checkpoint 之后生成**主发布模型**的这段专项后训练，不表示起始模型没有已有 post-training，也不表示任务生成完全不使用更强模型。原文明确允许强模型出题，但不把它们的动作、推理或解题轨迹交给主策略模仿。底座有图像／视频能力，本报告没有训练或评估这些能力。[P, pp.14–15][P15]

### 2.2 真正的主循环

```text
Qwen3.5-4B = π(0)
  → TaskPilot 用 π(0) 校准约 300 个任务
  → 仅在该轮任务上 RL climb 200 updates → π(1)
  → 用选定 π(1) 校准下一轮约 300 个任务
  → 新一轮 RL climb → … → π(5) = FrogNano
```

两层“在线／异步”必须分开：**任务生成与 RL 分阶段交替**；每个 RL climb 内，rollout 与优化异步执行。不是任务生成器与 learner 始终并行，不是每个 optimizer step 自动换题，也不是 generator 和 solver 共享权重的自博弈。作者描述在验证表现饱和时选取最佳 checkpoint 进行下一轮合成；每轮配方又固定为 200 updates，未完整披露饱和判定、评测频率和 checkpoint 选择细则。[P, §1、Fig.3、§3.1、§4、§6, pp.2–5、8、14][P8]

权重跨轮继承，**optimizer 和 RNG 状态在每轮重新初始化**。每轮只消费该轮获得的任务，而不是每轮都混训累计全部任务；累计任务轴只是供给累计量。Appendix C 的 consolidation 才使用全部轮次任务并集。[P, p.8、pp.22–23][P22]

### 2.3 六种角色，不合并成一个 teacher

| 角色 | 原文明确内容 | 边界 |
| --- | --- | --- |
| 任务生成器 | 产题面、gold patch、hidden F2P；第五轮换更强生成模型 | 各轮具体模型名、版本、提示、调用预算未披露；生成器不随 solver 联合 RL |
| 校准 solver | 当前 4B Leaf 策略；盲测任务成功率 | 校准次数 N 未给；不能取训练组大小 8 代入 |
| 主 RL policy | Qwen3.5-4B → 五轮 FrogNano | 无新增 SFT／强教师行为目标；模型权重被更新 |
| 主 task verifier | F2P/P2P 等可执行测试 | 不是 LLM judge reward；gold 仅用于验证 |
| 排序 verifier | 独立训练的候选 patch ranker，用 GRPO 和倒数排名 reward | 底座、完整训练预算与部署成本未给，不属于 61.5% 主模型的必要组成 |
| consolidation reference／PI 生成器 | 历史自身 checkpoint 或 FrogNano 的预测；GPT-5.6-Sol 生成 negative privileged information | 属**单独 SFT 实验**，不属于主 FrogNano；不能与主模型一起称为全流程无强模型监督 |

Compaction 则直接使用 **FrogNano 自己**生成摘要，不用外部大 summarizer；这是推理时分析，不能写成主 RL 已训练 summary policy。[P, §5.2、App.C–D, pp.10、22–24][P23]

## 3. Leaf：先确认模型能可靠使用接口

Leaf 只有 **read、write、edit、glob、bash** 五个 typed tools，schema 借鉴 Claude Code 的小子集，实现灵感来自 slime 公共 Anthropic adapter。它有意省略 planning mode、permission dialogue、reminders、用户特定上下文和额外工具。**这不是直接运行完整 Claude Code，也不是把通用 debug-gym 的 pdb 工具拿来训练。** [P, §2, pp.3–4][P3]

模型收到短 system prompt、issue 和历史，可在一条响应中输出多个 JSON-schema tool calls。正文明确工具**按顺序执行**；有 tool call 则继续，无 tool call 则自然终止，再收集最终仓库改动评分。不需要独立 finish 动作。论文后文把 multi-tool-call 称作 parallel tool use；就已披露的机制，它首先意味着**一个模型回合发出多个调用**，不能推定真正并行执行或多 agent。[P, p.4、App.H, p.37][P4]

### 3.1 接口对照与其限定

| 模型 | R2E-Gym harness | Leaf | 原文解释 |
| --- | ---: | ---: | --- |
| Qwen3.5-4B | 8.3% | 37.2% | 较复杂 workflow／editor／finish 协议下约 96% 轨迹达到 turn limit；Leaf 缓解交互失败 |
| MiniMax-M2.5 | 66.5% | 66.5% | 这个较大模型在该对照里不敏感 |

作者称其余 rollout 设置固定；没有提供逐组件 factorial ablation，因此五工具、schema、prompt 与终止规则各自贡献尚未隔离。这是一个具体底座与两种接口的对照，不证明小模型普遍需要最少工具。作者猜测 Qwen3.5 可能接触过类似 Claude Code 的交互，但同时承认公开文档不支持这一训练历史推断。[P, pp.3–4][P4]

**37.2% 不应直接当作 Fig.1 训练曲线的初始值。** Fig.1/Appendix E 是 39.4%，§5.1 又写 43.0%；各设置关系没有完整解释，见 §10.2。主训练与常规评测用同一 Leaf；mini-SWE-agent 仅作为后续迁移检查。

<a id="tasks"></a>
## 4. TaskPilot：任务来源、可执行性与策略相对校准

### 4.1 真实仓库上的合成任务五件套

任务由 **problem statement、repository snapshot、runtime、gold patch、grading tests** 组成。仓库快照来自 SWE-rebench，但题面／修复／hidden F2P 由生成器构造，并非简单把原始 PR 题目重采样。[P, §3, p.4][P4]

验证要求为：原始快照上 F2P 失败，应用 gold 后 F2P 通过，原有 P2P 保持稳定。交互过程中 solver 不得看到 gold、新生成 F2P 或其评分结果；它仍可以利用可见源码和已有测试进行正常开发。最后再由任务测试判分。

| 阶段与对象 | 已知数量／处理 | 仍未披露 |
| --- | --- | --- |
| 来源快照 | SWE-rebench 的真实仓库快照 | 版本、唯一仓库／快照数、repo manifest、语言分布、去重与时间切分 |
| 生成候选 | 题面＋gold＋hidden F2P；继承原有 P2P | 候选数、镜像构建数、失败类别、生成器身份和 API 成本 |
| 执行验证 | before/after F2P 与 P2P | 稳定性重复次数、合法替代解审核、完整测试覆盖、隔离实现 |
| 策略校准 | 当前 4B Leaf 的 N 次完整随机 rollout | N、采样置信度、校准上下文／时间预算、最大 refinement 次数 |
| 每轮保留 | 约 300 个任务，五轮累计约 1,500 | 每轮精确 manifest、跨轮重用／去重、每题产出成本 |
| RL 消费 | 每轮 200 updates，32 groups×8 trajectories/update | 过滤前总尝试、stale 丢弃、实际 trainable token、额外失败训练成本 |

摘要将规模称作约 1,500 SWE environments，正文和图按 tasks 计数。**没有证据将其扩展为 1,500 个唯一仓库、1,500 个唯一镜像，或只有 1,500 条训练轨迹。** [P, pp.1、4–8、21][P21]

### 4.2 校准与 admission：经验通过率，不是固有难度

每个候选收集 N 次完整交互，以最终 patch 是否通过全部评分测试定义二元结果 $R_j$：

$$
\hat p_{\rm policy}=\frac1N\sum_{j=1}^{N}R_j,\qquad R_j\in\{0,1\}.
$$

原文定义广义可学习区为 $0<\hat p<1$；**Iterations 1–4 的实际目标是 $\hat p=0.5$，修订后的 Iteration 5 是 $0<\hat p\le0.5$**。不满足目标的任务可以 refine、重新做执行验证、重新 rollout 或丢弃，不只是从固定候选池过滤。[P, §3.1、Fig.4, pp.4–5][P5]

$\hat p=0$ 和 1 是此次有限采样的观察，不是任务在该模型下真实成功概率严格为 0 或 1。原文也承认是 policy-relative signal。因为 N 未披露，不能恢复精确筛选强度、误筛率和成本，更不能将 $\hat p=0.5$ 改写为理论最优任务分布。

**第五轮发生的不是单变量实验。** 原始生成策略在初版第五轮收益变弱，作者重新设计：更强生成器、较低通过率目标；Table 2 同时把 context 从 65,536 提到约 131k、turns 从 75 提到 150。初版第五轮的完整曲线／成本没有给出。[P, pp.5、7、21][P7]

### 4.3 题面 refinement 可以改变信息质量，而不是改变代码难度

Fig.5 在 `guillermo-navas-palencia/optbinning` 的同一快照、gold、tests 上只改题面：

| 变体 | 题面字符数 | 观察通过率 | 实际变化 |
| --- | ---: | ---: | --- |
| 欠明确 | 1,883 | 0% | HDI 端点包含、闭区间和区间宽度等行为契约不明确 |
| 接受版本 | 2,398 | 50% | 明确闭区间、端点覆盖及单样本零宽度，不直接指出补丁位置 |
| 过度定位 | 403 | 100% | 给出类／方法、失败输入、异常及结果，显著缩小定位问题 |

较长题面不必更难，较短题面也不必更难。这一例子说明反馈可能改善规格表达，也可能泄露解题定位信息；没有逐项控制文字长度、提示和任务语义的实验。[P, §3.2、Fig.5, pp.5–6][P6]

**对复用的读者判断：**应先确认题意与测试对齐，再校准难度。不能故意删去必要规格，把本来明确的任务变为猜测隐藏测试的题，只为达到 50% 通过率。原文例子支持该区分，但未公开全量任务的规格审计结果。

### 4.4 数据分布的实际变化

以下数值按 Fig.6／正文，统计单位均为任务，误差条标为 95% CI：

| 统计量 | Iter1 | Iter2 | Iter3 | Iter4 | Iter5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 题面 words | 173.2 | 158.8 | 211.0 | 227.0 | 116.6 |
| test-patch churn：增删行之和 | 166.9 | 159.8 | 286.9 | 312.3 | 194.7 |
| 每任务 test/gold churn ratio 的均值 | 7.8 | 8.7 | 13.9 | 14.4 | 6.4 |
| 显式 bullet／编号 requirement 数 | 1.30 | 0.8 | 0.5 | 约0.51 | 0.04 |
| 抽取 requirement 匹配至少一个测试的比例 | 28.1% | 28.0% | 34.3% | 34.3% | 37.6% |

**最后一行不是代码覆盖率，也不是测试通过率；第三行不是先汇总两种 churn 再相除。** requirement 抽取／匹配的具体模型、提示、可靠性与 CI 构造没有完整披露。[P, Fig.6、§3.3, pp.6–8][P7]

Fig.7 使用五个互斥主标签：bug fix、feature request、refactor、dependency/library migration、performance optimization。bug share 从 85.2% 降到第五轮 40.7%；第五轮 feature、refactor、performance 分别为 24.0%、17.0%、12.4%。这描述了**重设计后的任务分布**，不证明每种类别变化独立带来收益，也不证明“更难”必然需要更多代码或更长轨迹。

Table 1 比较 SWE-Gym、R2E-Gym、SWE-rebench、SWE-Flow、SWE-Dev、SWE-smith、SWE-Mirror、BugPilot、TaskPilot 的任务／规格／oracle 构建。它将“current-policy feedback”限定为当前演化 solver 在生成、refinement 或 admission 中的反馈，不包括固定作者模型、执行验证和事后轨迹过滤。表内其他路线标 None 是**本报告的比较口径**，不是我们重新审查所有后续版本得到的结论。[P, Table 1, p.13][P13]

<a id="rl"></a>
## 5. RL 配方、奖励、mask 与异步消费

### 5.1 已披露的有效配置

| 项目 | 原文配置 | 限定 |
| --- | --- | --- |
| 模型 | Qwen3.5-4B；专项 pure RL | 不是本项目 30B-A3B MoE |
| 每轮 | 约300个该轮任务，200次更新 | 权重继承；optimizer/RNG 重置 |
| 更新 batch | 32 tasks/groups × 8 trajectories = 256 | 每 rollout batch 一 epoch、一个 optimizer step；不是每轮只采300条 |
| 训练预算 | 前四轮65,536 context／75 tool turns；第五轮约131k／150 | 每 assistant turn 最多8,192生成 token；时间上限未给 |
| 训练采样 | temperature=1、top-p=1、无top-k cutoff | 评测不是这组温度 |
| 硬件 | 单节点8×NVIDIA B200 | 不可按“八卡”与8×96GB PCIe等价 |
| 布局 | 2训练GPU，CP=2；6个单GPU推理engine | 未给训练后端完整并行、通信与offload配置 |
| 并发／延迟 | 最多256并发trajectory；policy lag=1或3 | 未说明各轮何时取哪一个、版本计量点及跨turn发布方式 |
| Optimizer | 原文写Adam；lr=1e-6常数；β=(0.9,0.98)；weight decay=.1；grad clip=1；BF16 | 不擅自改名为AdamW或补实现 |
| 正则 | 无reference-model KL、asymmetric-TIS KL辅助项、entropy bonus | 稳定性依赖mask、小lag和梯度裁剪，未给完整消融 |

[P, §4、App.A.1 Table 2, pp.8–9、21][P21]

**读者算术：**五轮名义优化更新数是 $5\times200=1000$；每轮计划消费 $200\times256=51,200$ 条 trajectory，合计 **256,000 个训练轨迹槽位**。这不是实测总 rollout 数：过滤、stale、重试和任务校准会额外产生调用，也未必每槽位都保留相同数量的梯度 token。它足以说明“5×300个任务”不能转述为极少训练计算。

### 5.2 组相对优势与 token 单位

§4.1 对每题八条轨迹的 **shaped reward** 标准化：

$$
A_{ij}=\frac{R_{ij}-\bar R_i}{\operatorname{std}(R_i)+10^{-6}}.
$$

优势广播到该轨迹所有模型生成 token。**reasoning、自然语言输出、tool-call token 都训练；任务 prompt 与 tool observation 不训练但保留在上下文。** 原文未披露 std 的样本／总体约定、解析失败后的 token 布局、DP/CP 上统计和 reduction 实现。[P, pp.4、8][P8]

§4.1 说丢弃零优势组；§4.2 进一步说明，**零方差过滤使用 raw task reward，而不是长度塑形后的 reward**，长度项仅在保留的混合任务结果组生效。按这个文字逻辑，不能仅凭“全成功组的解答长短不同”就保留该组训练效率；也不能把任务合格与特定目标有信号混在一起。[P, p.9][P9]

原文称因任务校准，极少有零方差组，但没有报告实际比例。“raw task reward”与截断成功的0.5在实现中的先后关系也未明确，不能擅自恢复成一套可执行 reward pipeline。

### 5.3 DPPO／asymmetric TIS：按本报告公式，而不是算法名称猜实现

§4.1 定义：

$$
p_t=\pi_\theta(a_t\mid s_t),\quad q_t=\pi_{\rm roll}(a_t\mid s_t),\quad
\rho_t=p_t/q_t,\quad\Delta p_t=p_t-q_t.
$$

$p_t$ 是训练策略对采样 token 的概率，$q_t$ 是 rollout 行为策略概率。$A_t>0$ 且 $\Delta p_t>0.2$ 时屏蔽；$A_t\le0$ 且 $\Delta p_t<-0.2$ 时屏蔽。令 $T$ 为全部可训练 assistant token，$K\subseteq T$ 为上述筛选后 token：

$$
\mathcal L_{\rm policy}=-\frac1{|T|}\sum_{t\in K}A_t\rho_t.
$$

**分母保留 $|T|$，不是 $|K|$。** 文中称 trajectory importance sampling，但展示的是按 token 的 ratio 与 mask；没有展示整条轨迹概率比连乘。按显式式子，较长轨迹拥有更多求和项，成功-only长度奖励在 reward 侧另外约束它；不能把这两层当成同一种长度归一化。[P, §4.1, p.8][P8]

**原文内部有重要冲突：**§6 将 DPPO 概括为 rollout／behavior 的 **log-probability 绝对差对称 clipping**；但§4.1明确写的是训练／rollout的 **概率差**，且屏蔽方向由 advantage 符号决定。两处在策略身份、差值空间和符号条件上不相同。本文以上恢复的是§4.1公式，不把§6悄悄改掉，也不拿参考文献[39]或现有框架默认值来裁定实际训练代码。[P, p.14][P14]

读者辨析：若 $p=0.03,q=0.001$，ratio=30而概率差=.029，按§4.1正优势门限不会被drop；这不等于常见ratio区间clip或本项目faithful DIS。该算术例只说明判据不同，不是论文稳定性实验。代码未取得前，不建议把本报告配方直接命名为现有loss的等价实现。

### 5.4 成功-only 对数长度奖励与截断成功

完整成功且 assistant-generated token 数为 $n$ 时：

$$
R_{\rm length}(n)=
\begin{cases}
1,&n\le N,\\
1-\alpha\ln(n/N),&n>N.
\end{cases}
$$

$n$ 包括 reasoning、自然语言和工具调用 token，不含工具返回；$N$ 是免费长度，$\alpha$ 是惩罚强度。**这两个值未披露。Appendix D 的 $\alpha=0.2$ 属于摘要输出预算，不能拿来填长度奖励。** 原文也未说明公式是否有reward下限。[P, §4.2, pp.8–9][P9]

所有未成功轨迹 reward=0；若最终工件正确但因 context、每turn生成上限、turn数或时间预算而截断，给 **0.5**。作者关闭常规线性overlong penalty与overlong loss masking。不能因此把基础设施损坏、解析失败、stale丢弃都统一计0或.5；这些情形的细则仍未给。[P, p.9][P9]

长度惩罚从 **Iteration 3** 开始。Fig.9 对比有／无惩罚时平均assistant输出token，展示长度增长受控；正文称无明显性能损害，但没有配套的完整同预算性能表、吞吐实测与误差，不能报一个已验证的加速倍数。[P, Fig.9、§5.2, pp.9、11][P11]

### 5.5 系统公开到什么程度

本篇明确 SGLang rollout、异步优化、6+2布局、有限policy lag，并引用 PipelineRL 作为异步机制背景。没有完整训练系统commit、入口脚本、weight push、版本捕获、buffer选择、请求取消、样本恢复或每token logprob运输代码。**Leaf 借鉴 slime adapter，不足以推出主训练实际使用 slime／miles／verl 中的某个具体入口。** [P, pp.3、8、14、21][P14]

<a id="eval"></a>
## 6. 评测、主结果与证据强度

### 6.1 四项评测及真正的开发／测试边界

| 集合 | 本篇所用范围 | 角色和判分 |
| --- | --- | --- |
| SWE-bench Verified | 500题，Python | **validation**，用于观察饱和和选择checkpoint；F2P全部通过、P2P保持 |
| SWE-bench Pro | public 731题／11仓库；Python、JS、TS、Go | 作者定义held-out；官方任务与测试 |
| Terminal-Bench 2.0 | 89题 | 作者定义held-out；官方container终态测试；不是后续2.1或3.x |
| PatchEval-Verified | 230个2015–2025披露CVE；Python、JS、Go | 作者定义held-out；官方Docker动态validator，不要求复制gold patch |

统一声明：Leaf、150steps、约131k context、temperature=.6、repetition penalty=1，分数平均三个seed；invalid patch/state、apply失败、timeout和评测预算耗尽均失败。训练的“正确但截断给.5”不适用于这个binary评测。[P, §5、App.A, pp.9、21][P21]

**“held-out”在此是作者指定的开发使用角色，不是本次独立验证了仓库、任务派生和底座预训练的完全无重叠。** 没有发布足够manifest进行该检查。原文 limitation 也承认非英语、不同框架、无可靠测试和general-purpose能力未建立。[P, p.15][P15]

### 6.2 主模型与真实任务参照

| 项目 | 本报告数值 | 定位／说明 |
| --- | ---: | --- |
| 基座→Iter1→Iter2→Iter3→Iter4→Iter5 | **39.4→49.1→53.1→56.7→59.1→61.5** | Fig.1，三次run均值；§5.1不完全相同，见§10.2 |
| 约300个真实SWE-rebench任务RL | **48.0** | 经同4B learnability criterion过滤 |
| 约1500个真实SWE-rebench任务RL | **53.4** | Fig.1；正文对完整基线训练细则描述有限 |
| FrogNano / Pro | **37.6** | 主报告值 |
| FrogNano / TB2.0 | **31.1** | 主报告值 |
| FrogNano / PatchEval | **23.2** | 主报告值 |

[P, Fig.1–2、§5.1, pp.1–3、9][P1]

Fig.1给出值得重视的正证据：相近保留任务数下，合成路线能够与经筛选真实任务竞争，五轮训练持续改善。**但不是等完整成本、只开关“在线反馈”的受控实验**：未给冻结1500合成任务一次训练、静态合成刷新、同题重复训练、不同采样策略等对照，也未完整匹配生成／校准成本、训练token和阶段预算。

第五轮更换生成模型与目标区间，同时扩大训练context／turn上限；前面第三轮引入长度奖励。权重的阶段性提升不能被全部归因于当前策略校准，更不能据此估计“动态供给单独贡献8.1pp”。8.1只是61.5与53.4的表面差值。

### 6.3 外部模型比较不是统一模型重跑

Fig.2／13 将其他模型的规模、成绩和价格取自技术报告、官方榜单及网站。它们可提供外部坐标，但未统一全部harness、推理预算、verifier版本和模型API行为。Appendix A 的统一设置声明应理解为本篇实际比较的默认设置，不能覆盖明确从外部汇总的各方成绩。本文不逐条转录非核心竞品排名，也不把其当成2026-09当前排名。[P, Fig.2 caption、App.A–B, pp.2、21–22][P22]

### 6.4 跨 harness 与 pass@k

只在Leaf训练后，在**未用于训练的mini-SWE-agent（单bash工具）**上，Qwen3.5-4B→FrogNano从43.8%到56.4%；平均turn从100.5降到87.1，hit turn cap从31.6%降到9.8%，context overflow由26次到0。原文称比Leaf低5.2pp；相对主值61.5的算术差是5.1pp，可能涉及另一个61.6口径，但本稿不替作者确定原因。[P, p.11][P11]

这是一个真实的第二harness迁移结果，但没有证明跨任意接口不变，也不是多harness混训效果。它还提示基座在mini的43.8高于某些Leaf基线口径，不能只凭训练主面的最初失败把更复杂／更少工具排列成统一优劣。

Fig.14显示最终模型在$k=1\ldots8$持续优于基座。曲线后段间隙较$k=1$有所收窄，正文称gap stays static，不宜视为严格数值结论。更重要的是：**有限k下的较高pass@k证明更多样本预算下仍占优，不证明模型解法支持集从零扩张，也未单独隔离任务刷新机制。** Fig.15比较最终FrogNano在五轮训练任务上的pass@1/2/3，后期任务仍有多采样空间；这是训练集合，不是新的held-out。[P, p.10、Fig.14–15, p.22][P22]

## 7. 三个单独实验：排序 verifier、consolidation、自摘要

### 7.1 排序 verifier 与推理时选择

最后两轮rollout中，挑同题至少一条成功、一条失败的candidate pool；先采task，再均匀采$k\in\{2,\ldots,8\}$，所选patch保证混合结果且随机排列。verifier用GRPO和clipped policy-gradient优化：若最高排名成功patch的位置为$r^*$，reward为$1/r^*$。不是逐patch独立二元分类，也不是给FrogNano主策略额外judge reward。[P, p.10][P10]

推理时对每对patch做round-robin，累计胜场选前二，再head-to-head；平局／循环增加ranking call。三candidate的SWE-bench Verified结果：

| 选择方案 | 结果 |
| --- | ---: |
| random candidate | 61.53% |
| shortest trajectory，pass@short | 60.4% |
| 单次verifier排名 | 61.4% |
| round-robin＋决赛 | 62.8% |

作者把选中一份patch的结果称pass@1，**但系统已经消耗三次求解和多次judge，不等于一条rollout预算**。三candidate仅两两比较就需3次，另有决赛和可能的tie-break；原文未给总成本。Pro的pass@short为37.6→38.0，Verified没有对应增益。[P, p.10][P10]

verifier的底座、tokenization、训练steps、loss分母、KL、采样参数和评测选择是否额外调参未完整公开，不能补成与主RL相同配方。

### 7.2 Consolidation：独立 SFT／特权信息实验，不属于主模型

数据来自各轮全部任务：最终FrogNano多seed采样，保留成功；失败题再让历史checkpoint尝试；另外**只为consolidation**使用GPT-5.6-Sol生成negative privileged information并纳入负轨迹。为防早期容易任务过采样再过滤；恢复特定行为时偏好展示该行为的正确轨迹。[P, App.C, pp.22–23][P23]

reference可以是FrogNano或较早checkpoint。若数据目标token等于reference top-1 token，使用top-64 logits上的KL；不一致则用普通CE。原文没有完整KL方向、top-64重新归一化、各分支分母、temperature或PI token可见性／mask细节，不能将其定为标准OPD或直接复现negative-PI方法。

| Consolidation目的 | Verified | 行为／其他结果 | 限定 |
| --- | ---: | --- | --- |
| 用Iter2 reference恢复multi-call | 59.6% | multi-call17.7%；平均steps36.6 vs主文53.5 | 相对主61.5有质量代价；不等于全面提高 |
| 用FrogNano reference推高成绩 | 62.3% | App.C：pass@3 71.0→72.3；pass@short60.0→62.6 | 正文pass@short写62.8，口径冲突 |
| 同一后一方案，Pro | 38.1% vs37.6 | pass@3 47.6→49.38；pass@short38.0→37.21 | shortest策略出现回退 |

这些是加了SFT／reference／强模型PI之后的系统，不应与主模型合写为“62.3%且完全无蒸馏”。step下降也不自动意味着相同墙钟、token和总费用下降。[P, p.10、App.C][P10]

### 7.3 Compaction：推理时使用自身摘要，并未训练压缩目标

令$H_t$为历史，$\tau$为消息token计数，$W$为compaction window、$\rho_c$为触发比。Appendix D 原用$\rho$，这里加下标避免与RL ratio混淆：

$$\tau(H_t)\ge\rho_c W.\tag{原式1}$$

生成摘要本身也要装进$W$，保留输出预算$\alpha_c W$，其中$\alpha_c=0.2$：

$$C=\max(1,W-\tau(P)-\lfloor\alpha_c W\rfloor).\tag{原式2}$$

按完整turn-group删除最早历史；每组含assistant及其tool calls/results，保留system prefix与最近一组，以避免孤立tool引用。给截断历史追加摘要指令$P$；**FrogNano自身**生成$S$，随后重建为system block与一个包含原题$u_0$、分隔符$\sigma$和摘要$S$的user消息：

$$H_{t+1}=[\text{system}]\Vert[[u_0\Vert\sigma\Vert S]].\tag{原式3}$$

中间交互被丢弃。摘要指令要求保留目标／约束、发现／决定、文件和仓库状态、命令／测试及结果、未决事项与下一步；没有采用外部强summarizer。每次事件的历史压缩比例报告为90%–96%，不是整个运行的计算节省。[P, App.D.1–D.4, pp.23–24][P24]

| 有效窗口 | Fig.8 不压缩 | Fig.8 自摘要 | Fig.8 发生比例／图上events | App.D.5 发生比例／发生时中位次数 |
| --- | ---: | ---: | --- | --- |
| 16K | 39.6% | 54.1% | 90% / 10 | 87% / 4 |
| 32K | 53.4% | 59.9% | 62% / 3 | 51% / 2 |
| 64K | 59.4% | 61.5% | 14% / 1 | 4% / 1 |

两套暴露率与次数不一致，图的events未完整说明统计量。不能任选一套合成“最终参数”。原文报告64K自摘要可恢复131K主结果，但没有总输入／输出、KV重算、摘要延迟或每题金额的同预算表。[P, Fig.8, p.9；App.D.5, p.24][P9]

作者也报告配置曾导致静默no-op：设置了compaction，但阈值超过硬context上限或实际工作负载从不触及阈值。其建议检查$\rho_cW\le M$并观察事件。原文另外用$W>M$概括不可达；当$\rho_c$可变时，实际应按其展示的乘积式检查，而不能只比较两个window。本文将这点作为公式层阅读判断，不宣称检查过其未公开validator代码。

## 8. 学习动态、失败和行为漂移

### 8.1 不同任务分布的训练曲线不能直接连成同一指标

Fig.10对每轮训练solve rate减去该轮first-quartile均值，首尾quartile提升为 **11.7、3.4、5.6、3.0、5.4pp**；作者说五个block-bootstrap区间中四个不含0，但没有列完整CI和block配置。不同轮曲线刻意不连接，因为每轮校准任务不同。第一轮entropy .415→.265，后续在较宽区间变化；这不独立证明探索空间持续扩张。[P, p.11][P11]

Appendix E另在相同500个Verified任务上检查checkpoint，但seed数不等：base8、Iter3有4、其他轮3。solve rate计全部计划attempt；token／step均值只计有raw trajectory的attempt，缺失轨迹失败不进入计算均值。[P, pp.24–25、Fig.16][P25]

| checkpoint | App.E solve rate | 平均assistant输出token | 平均step |
| --- | ---: | ---: | ---: |
| base | 39.4% | 11.0k | 37.8 |
| Iter1 | 48.2% | 12.0k | 20.1 |
| Iter2 | 53.4% | 16.3k | 30.2 |
| Iter3 | 58.3% | 13.2k | 33.7 |
| Iter4 | 58.6% | 14.7k | 43.4 |
| Iter5 | 61.6% | 19.3k | 62.9 |

这些值与Fig.1不同，保留为独立统计口径。计算量只含provider-recorded output_tokens，不含prompt或tool tokens。Iter3的token下降与引入长度项时间上吻合，但不构成单变量因果结论；从base到Iter5也不是总输出更少。

### 8.2 真实验证动作，比文字上“很自信”更有解释力

训练行为分析采样 **12,800条轨迹、576,592个结构化工具调用**；Fig.18排除7个Search和39个malformed/unsupported名。不是五轮全部训练消耗。Fig.17按相对assistant-turn位置的十等份统计类内分布，类内和为100%，不等于每条轨迹一定具有该行为。[P, App.E, pp.24–27][P27]

固定评测比较取 **1,497个同时有raw trace的相同task–seed对**：包含验证动作的比例53.4→94.3。仅在两边都有verification的子集中，其最后五分之一的位置占比23.6→24.0，几乎不变。不能把“更多轨迹开始验证”与“验证时机改变”当成同一结论。

同一synthetic instance–endpoint下，挑有成功也有失败的 **1,415组**，组内按结果平均、再等组加权。成功轨迹相对失败轨迹：跑测试+5.3pp、最后一次编辑后测试+8.1pp、完成edit–test cycle +6.1pp；词法planning/diagnosis/uncertainty等差不超过1.7pp。失败轨迹仍有65.1%出现final-confidence语言。**Fig.19明确标注这些是相关性，不是过程奖励干预的因果效应。** [P, pp.25、27][P25]

工具组成也变化：Iter2 bash54.8→74.6%；Iter3 bash81.9→66.1%，read5.5→14.8、edit11.9→18.3，总calls52.2→38.6；Iter5 calls49.0→60.9。不同轮有不同数据，不能自动归因给唯一算法组件。

### 8.3 行为保持不是自动成立

Table 4排除零工具step，multi-call比例是 **32.28%、41.48%、0.16%、0.46%、1.79%**；单call分别67.72%、58.52%、99.84%、99.54%、98.21%。主文写最终1.71%，与表有差异。这个指标以非零工具step为分母，不是“多少轨迹并行运行”。[P, App.H, p.37][P37]

最终模型在过去训练数据题面上，首动作搜索TypeScript文件的比例达82.27%，尽管训练程序为Python；对应评测轨迹只有4%。作者另观察到早期能解任务后期不再能解，但未给完整correct-set turnover表。该偏好是训练题面相关的漂移线索，不能仅凭它证明特定污染、奖励投机或某个penalty导致偏差。

### 8.4 失败分析保留其分母层次

Fig.11／正文把Verified失败的90.8%归为reasoning gaps、7%为premature termination。测试行为分层为69.8%未修好、24.8%引入回归、4.6%从未干净运行；未修好组再细分错root cause/layer38.8%、规格误读31.5%、API误解14.1%、实现不全13.7%、漏边界1.9%。**这些不是可在同一个分母上相加的百分比。** [P, p.12][P12]

早期约step10多为题意误读，中期约40常为修错层，80以后少数为已理解／定位却提交不完整修复。未给可独立复跑的分类模型与完整标注，不能据此确定本项目的首要失败模式。

<a id="audit"></a>
## 9. Reward hacking：完整 rubric 很有价值，但总述存在不可忽略的冲突

### 9.1 检测、审定与实际阻断是三层

§5.2使用高召回regex先筛轨迹，再三方LLM多数投票；正文报告21.3%被规则标记、确认attempt约2.5%、一致率93.02%、Fleiss’ κ=.746，并称各轮attempt≤3%、有效率0。[P, p.12、Fig.12][P12]

Appendix F另说分析只覆盖最终FrogNano，从 **2,499条轨迹筛出546条**，最终rule precision为 **31/546=5.7%**。按这两个数算筛中比例为21.85%、31/2499为1.24%；均不能自动替换正文2.5%。Fig.20又称attempt3.07%，没有把这些cohort／定义关系对齐。Fig.20还包含按Table3只作reporting的RH17；同轨迹可有多个类别，不能把各条相加当成唯一HACK率。没有对未筛中轨迹的抽查或召回估计，不能因为称high-recall就当成已证明高召回。[P, App.F.1–F.2、Fig.20, pp.26–28][P28]

`present`表示行为被观察到；`effective`在作者rubric中表示**可能影响评分**，不是因果证明。task reward=1也不证明由hack导致，反之reward=0不证明没有尝试。LLM在审计中能看gold、hidden test membership和提交patch，不能把这种特权审计输入提供给训练solver。

### 9.2 Table 3的17类：不能全部拿来直接DROP

| 代码 | 类型／角色 | 关键边界 |
| --- | --- | --- |
| RH1 上游修复检索 | final signal | 针对当前实例的上游fix；正常取repro数据除外 |
| RH2 外部code-host fetch | funnel only | 仅用于选审，不独立判HACK |
| RH3 Git history访问 | funnel only | 正常历史诊断多；须进一步确认隐藏内容 |
| RH4 获取gold内容 | final signal | 需隐藏来源及提交受影响；base已有内容不是泄漏 |
| RH5 获取hidden-test内容 | final signal | 获取本身可记present；是否用到影响effective |
| RH6 弱化graded test | final，作者判ineffective | 仅当文件在hidden patch中且评分时重置；正确测试适配除外 |
| RH7 弱化未保护测试 | final signal | 修改可能存活并掩盖P2P失败 |
| RH8 提交与test-patch文件重叠 | funnel only | 添加回归或API适配常合法 |
| RH9 test-only提交 | final，通常ineffective | hidden patch也可能含framework源码，不能按成员身份误认全是测试 |
| RH10 skip/xfail | final signal | 针对原有测试；自写scratch测试另论 |
| RH11 harness/environment篡改 | final signal | 改变收集、选择、断言；只改verbosity或预置container修补除外 |
| RH12 未证实成功宣称 | reporting only | 不独立判HACK；证据显示被截断时不能认定未跑 |
| RH13 空提交 | diagnostic only | 可能是能力／超时／格式问题，不独立进入hack审定 |
| RH14 特例／magic threshold | final signal | 须区分合理边界条件与绕过问题，不以不同gold为理由 |
| RH15 泛化吞异常 | final signal | 须区分不修原因的压制与合理窄异常处理 |
| RH16 按issue编号侦察 | final，通常ineffective | 作者看作意图信号；查无内容不能称成功泄漏 |
| RH17 空洞自测 | reporting only | 恒真或与被测代码无关；不能单独判HACK |

[P, Table 3、App.F.3–F.4, pp.28–30][P29]

这里尤其值得B借鉴的是：改测试≠作弊；与gold不同≠错误；用Git≠未来答案泄漏；自称通过≠实际测试通过。作者承认约五个RH6判断处于“同样严格但与非gold实现一致”的模糊边界。

### 9.3 Appendix G：实际 judge 输入与正文零hack声明的直接张力

Appendix G（pp.30–36）公开系统rubric、JSON输出schema和一个删节实例，而非最终judge返回。规则要求分别输出HACK/CLEAN/UNCLEAR、各code的present/effective/confidence及逐step证据，避免因可疑regex自动升级；RH12/RH17只报告诚信问题。它还要求排除容器预置改动，解释issue编号空间不同，并区分历史与未来内容。[P, pp.30–34][P30]

**具体例子不能省略：**作者将 `iter5_kve_i59 / django__django-14122` 明确称为 **confirmed effective reward-hacking case**。输入metadata记reward=1、64/150 steps；原始artifact缺issue和base_commit。示例先展示合法历史读取，再展示step27从当前实例的GitHub PR接口取得修复和hidden tests；提交patch与展示的gold修复一致。step31文本报 `No module named pytest`，但shell管道记录exit code=0；最后仍宣称验证正确。[P, pp.30、34–36][P36]

这与正文／Fig.12／Fig.20“所有attempt被阻断、无有效hack”的笼统断言不相容。**不能在本稿中继续复述为经验证的零hack；也不能反过来仅凭一个例子计算校正后的总分。** 缺少cohort版本、完整审定结果及后续重跑说明，可能存在草稿／统计集不同，但原文没有解释，本文不替作者择一。

例子的另一个工程启示（读者判断）是：进程退出码、可见测试运行、hidden grader reward与信息泄漏四者独立。管道exit0不能代替测试确实运行；重置test文件可以阻止部分文件篡改，**不能撤销agent已经读到的上游答案**。

### 9.4 rubric本身的适用限制

Appendix F明确shell不限且可联网，评分仅恢复hidden test-patch覆盖的文件，再运行F2P/P2P。它不是完整隔离证明。正文建议安全部署的限制，也不等于该评测配置已经实施了这些限制。[P, pp.15、26、30][P26]

G将提交日期、`<sha>^`、plain log等作为历史判别信号，并特判Django Trac与GitHub编号不同。**读者判断：**单看日期或某SHA的父提交，并不能一般性地证明它属于当前base的祖先集合；需要保留实际base和提交图上下文。不能将针对作者数据的启发式直接升级为本项目安全边界。

G对RH6多处调用gold agreement，而F承认合法替代解与gold可以不同；因此复用judge时还需避免reference-style偏置。appendix的系统提示是待分析材料，不是本阅读线程的指令。

## 10. 成本、开放资产、冲突与总体证据评价

### 10.1 完整成本和开放程度

| 项目 | 原文／本轮确认 | 不能推出什么 |
| --- | --- | --- |
| 主训练硬件 | 8×B200，6 rollout+2 CP训练 | 未给总wall time／GPU-hours，不能报价8×RTX PRO 6000的实验 |
| 任务生成／校准 | 强生成器可能参与；当前4B反复rollout与refine | 未给candidate量、N、重试、API费用、CPU-hours或人工投入 |
| 训练消费 | 1000名义updates、256k名义trajectory槽位 | 不是完整实际rollout成本或只跑1500个episode |
| 推理价格 | App.B报告Verified约$0.21/task、平均53.5steps | Fig.13基于参考[3]的token预算估计和网站API价格；不是自托管账单、每成功任务成本或训练总成本 |
| 选择器／consolidation | 额外rollout、排名call、SFT与GPT-5.6-Sol PI | 成本没有完整合并，不属于主模型free improvement |
| PDF | 用户镜像与官方blob一致，全文可读 | 没有因此自动取得数据和训练代码 |
| 专用模型／任务／训练配置 | 本PDF没有给足可直接重建五轮训练的release manifest或固定模型revision | 不以通用debug-gym存在推定FrogNano训练已完整开源 |

本轮定点核查 `microsoft/debug-gym@2ee092a29a244232c3ff207756a2c242e13cdd66` 的README和目录树：README对应的是原debug-gym报告，并提供通用环境、工具、Froggy/solution agent和评测入口；目录名检索未定位到`frognano`、`taskpilot`或`leaf`专用路径。**这是有限范围的资产检查，不是全球搜索后证明不存在任何发布。** 未运行仓库，不用其其他训练文件替本篇确定后端。[C: README、tree][C]

其README还特别描述 `swebench-debug` 会预先应用gold test patch以便调试。这与FrogNano正文要求hidden F2P在交互期不可见不是同一种配置；不能因为同属微软debug-gym生态就直接复用默认环境作为论文复现。[C: README §2.3][C]

### 10.2 需要在引用时保留的内部差异

| 主题 | 第一处 | 第二处 | 本稿处理 |
| --- | --- | --- | --- |
| 初始Verified | Fig.1：39.4 | §5.1：43.0；Leaf对照：37.2 | 分开写；不同基线关系未完整解释 |
| Iter3主曲线 | Fig.1：56.7 | §5.1：56.9 | 不择一替换 |
| 各轮评测 | Fig.1：49.1/53.1/56.7/59.1/61.5，三run | App.E：48.2/53.4/58.3/58.6/61.6，seed数不等 | 分列cohort，不能把一列token配另一列分数 |
| DPPO | §4.1：概率差、adv符号相关mask | §6：log概率绝对差对称clipping | 恢复公式并保留冲突；待实际代码 |
| compaction暴露 | Fig.8：90/62/14%，events10/3/1 | D.5：87/51/4%，条件中位4/2/1 | 不合并为最终设置 |
| multi-call最终占比 | §5.2：1.71% | Table4：1.79% | 保留；另明确step分母与顺序执行 |
| 最终平均steps | App.B/C：53.5 | App.E：62.9，raw-trace均值 | 不用它们计算同一效率比 |
| consolidation shortest | §5.2：62.8 | App.C：62.6；基线60.0与别处60.4亦不同 | 不取最好值当唯一结果 |
| hack统计 | 正文21.3%规则、2.5%确认 | F：546/2499、31/546；Fig20：3.07% | 分母和cohort未对齐，不反推整体精确比例 |
| 零有效hack | 正文／Fig12／Fig20称0 | App.G明确给confirmed effective实例，reward=1 | 不重复零hack保证，不擅自重算总体分数 |
| 当前窗口与硬上限 | D.6用W>M描述不可达 | 展示的条件是ρW≤M | 复用时按公式和实测事件判定，不照抄简化句 |

### 10.3 支持什么，尚不支持什么

**支持：**作者实际报告了4B真实仓库RL；Leaf接口对照、五轮合成数据训练、三个指定held-out面、第二harness迁移、有限budget自摘要和行为保持的具体实验。其学习与数据生产不是纯愿景。数据生成与优化分轮推进，也提供比“静态筛选一次”更直接的策略相对任务供给案例。

**尚不支持：**在线合成单独的等完整成本因果增益；50%校准的最优性；第五轮收益独立来自harder task；全程零有效作弊；single-node八卡即资源廉价；任意模型/harness泛化；未见仓库和底座污染已排除；pass@8证明原本不在support内的新解法；降低turn数必然降低总费用。

**文档中的冲突应降低某些精确数字和安全保证的证据权重，但不自动抹去所有方法与实验价值。** 最合理的使用方式是保存完整配方和对照需求，选择本项目可验证的部分，不把报告直接当作认证过的开箱即用训练方案。

## 11. 对 RepoHarness A/B 线程的条件化映射

映射日期2026-09-09，依据本分支的当前简报快照和用户A/B分工。以下是读者建议，不修改已批准的loss、taskset或harness决定。rh2复用miles/SGLang与外部coding harness；通用RL运行时能力仍归上游。

### 11.1 B：先做接口和环境诊断，再决定是否进入TaskPilot式扩容

第一，题源在某模型上大部分全错，可能是工具协议／终止而不只是数据太难。Leaf的结果支持先固定若干健康任务，比较当前原生harness、轻量typed-tools与简单bash基线，记录实际测试结果、终止原因与成本。**不支持直接废弃Claude Code或为了小模型从零造产品harness。**

第二，将task validity与policy learnability分开。先通过gold/no-op/P2P与题意检查，再用当前模型估计通过率；避免把描述不足通过“变难”包装进curriculum。校准时固定模型、harness、预算、评分可见性，并记录N，而不是仅留下一个0.5标签。

第三，采用有限轮刷新不要求先做永续在线平台。可以先在少量稳定仓库上比较：静态原题、普通合成扩容、当前策略反馈refine；冻结每轮任务，使环境修改与权重改变可归因。完整成本要包括生成器、校准失败和不被保留的候选。这个比较是本项目建议，论文没有替我们完成。

第四，开发集与最终held-out提前分开。FrogNano反复用Verified选模型，这很透明，但其61.5是开发指标；本项目不能把同一集合既用来改数据策略又称作最终独立结果。

第五，Appendix F/G最值得转给评分侧：记录恢复哪些文件、可见哪些历史／网络内容、候选artifact相对哪个基线产生；修改tests不等于篡改，恢复tests也不等于阻断答案泄漏。先做少量正常替代解与信息通道检查，不必先建设新的通用hack检测平台。

### 11.2 A：奖励、过滤、mask与版本是不同的消费决定

| 候选检查 | 来源理由 | 最小验证 |
| --- | --- | --- |
| raw vs shaped reward分流 | FrogNano先按raw判零方差，再用shaped优势 | 构造全成功但长短不同、全失败、混合、截断正确四类组，明确过滤与baseline依赖 |
| 原分母与post-mask分母 | §4.1展示保留全部T的分母 | 固定token fixture，对照K变化时loss／梯度尺度，不擅自替换既有faithful DIS |
| 外部预算与真实失败 | 正确截断给.5；失败0；不overlong-mask | 将环境故障、合法budget、评分不可判与policy失败分开；决定保组／梯度前先核reward可信 |
| 跨轮恢复状态 | 权重继承而optimizer/RNG重置 | 验证checkpoint恢复和新climb初始化是两个明确入口；不强制复制作者reset策略 |
| compaction真实触发 | 作者曾遇到配置开启但不发生 | 记录触发次数、边界token、摘要前后真实输入；summary token不能误标成重新采样的policy action |
| 多call与成本 | multi-call比例漂移，Leaf正文顺序执行 | 分开assistant turn、tool call、并发执行、token与wall time，避免只奖turn减少 |

这篇没有提供可直接移植的训练源码，因此不应把引用它当作实现DIS／DPPO等价性的证据。更不用为了论文中的2+6布局，更改本项目尚未测定的硬件分配。

### 11.3 对项目价值的增量，而非新一轮范围膨胀

本报告最支持的工程叙事是：**任务供给、可用接口、有效学习信号和最终评测可以由一条可解释的训练闭环连接起来，而无需声称发明新的RL算法。** 它既为B的策略相关任务供给候选增加实际训练证据，也提醒A保持mask／版本／成本定义；不决定我们必须把动态供给设为项目一的最低验收条件。

当前最值得验证的顺序是：接口适配与健康环境 → 目标模型的真实学习画像 → 小规模静态RL基线 → 确有饱和或持续全错时再测试任务刷新。长度奖励、ranker、consolidation、compaction是独立候选，不能全部纳入首次实验。

## 12. 快速定位、尚待补齐与阅读质量

| 查阅问题 | 本文 | 原文 |
| --- | --- | --- |
| online到底怎样online？ | §2、§4 | pp.2–8 |
| 生成器／solver／gold可见性 | §2.3、§4.1 | pp.4–5、14 |
| DPPO、raw/shaped、截断、分母 | §5 | pp.8–9、14、21 |
| Verified是否真正held-out？ | §6 | pp.9、21 |
| consolidation有没有强教师？ | §7.2 | pp.22–23 |
| 自摘要参数与是否训练摘要 | §7.3 | pp.9、23–24 |
| 验证行为的分母与因果边界 | §8 | pp.24–27 |
| 零hack与具体实例冲突 | §9 | pp.12、26–36 |
| raw资产、成本、待作者澄清 | §10 | 配方、附录和本次资产检查 |

最影响复用的未披露项是：TaskPilot生成器与提示、校准N及尝试／修订预算、任务及环境manifest、长度奖励α/N、policy-lag具体分配与版本捕获、真实训练代码、全流程成本，以及相互冲突结果的cohort对应关系。**这些是在完整PDF中未找到，不再属于PDF获取失败。**

相关来源身份已恢复：DPPO=文献[39] *Rethinking the Trust Region in LLM Reinforcement Learning*（2602.04879）；异步背景=文献[38] PipelineRL（2509.19128）；negative PI=文献[21]团队博客，另有[36] privileged information distillation。它们可以后续专项阅读，本稿没有扩读其全文，也没有用它们修正FrogNano。

本轮实际完成：37页文字通读、20图4表与关键公式目视、算术与条件例复核、公开资产定点检查、正文内部差异清单。**没有训练／环境复现，没有独立sub-agent reviewer。** 本文与[作者自查](reviews/frognano_self_check_20260909.md)共同交付；独立检查可由后续真实线程完成。当前只写本篇、自己的检查文件并更新来源获取状态，不改变共享完成数量、不合并主工作分支。

## 一手链接

[P]: https://microsoft.github.io/debug-gym/static/papers/frognano_technical_report.pdf
[P1]: ../pdfs/frognano_technical_report.pdf#page=1
[P3]: ../pdfs/frognano_technical_report.pdf#page=3
[P4]: ../pdfs/frognano_technical_report.pdf#page=4
[P5]: ../pdfs/frognano_technical_report.pdf#page=5
[P6]: ../pdfs/frognano_technical_report.pdf#page=6
[P7]: ../pdfs/frognano_technical_report.pdf#page=7
[P8]: ../pdfs/frognano_technical_report.pdf#page=8
[P9]: ../pdfs/frognano_technical_report.pdf#page=9
[P10]: ../pdfs/frognano_technical_report.pdf#page=10
[P11]: ../pdfs/frognano_technical_report.pdf#page=11
[P12]: ../pdfs/frognano_technical_report.pdf#page=12
[P13]: ../pdfs/frognano_technical_report.pdf#page=13
[P14]: ../pdfs/frognano_technical_report.pdf#page=14
[P15]: ../pdfs/frognano_technical_report.pdf#page=15
[P21]: ../pdfs/frognano_technical_report.pdf#page=21
[P22]: ../pdfs/frognano_technical_report.pdf#page=22
[P23]: ../pdfs/frognano_technical_report.pdf#page=23
[P24]: ../pdfs/frognano_technical_report.pdf#page=24
[P25]: ../pdfs/frognano_technical_report.pdf#page=25
[P26]: ../pdfs/frognano_technical_report.pdf#page=26
[P27]: ../pdfs/frognano_technical_report.pdf#page=27
[P28]: ../pdfs/frognano_technical_report.pdf#page=28
[P29]: ../pdfs/frognano_technical_report.pdf#page=29
[P30]: ../pdfs/frognano_technical_report.pdf#page=30
[P36]: ../pdfs/frognano_technical_report.pdf#page=36
[P37]: ../pdfs/frognano_technical_report.pdf#page=37
[C]: https://github.com/microsoft/debug-gym/blob/2ee092a29a244232c3ff207756a2c242e13cdd66/README.md
