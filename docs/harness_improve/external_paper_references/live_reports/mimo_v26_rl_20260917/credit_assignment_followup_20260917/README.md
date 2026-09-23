# SWE 中的 judge、过程反馈与 advantage 重分配：MiMo 后续研究

调查日期：2026-09-17。作者：Codex。性质：一手资料核对、机制分析与实验建议；不是 MiMo 算法复原，也不是本项目训练配方定案。未运行论文实验，未修改训练代码。

**结论：值得尝试，但要把两类证据分开。SWE-RM、SWE-TRACE 提供了在 SWE RL 中增加轨迹评分的直接证据；DRACO、IAPO 给出了更明确的轨迹内 advantage 重分配机制，但实验领域不是 SWE。将两者结合，是需要检验的新假设。冻结 judge 可以降低接入门槛，却不一定比 learned value critic 便宜。**

本轮核对了 14 篇论文的相关内容，重点递归阅读其中 11 篇的 TeX 方法、实验或附录；另外检查了 DRACO 的 advantage 改写代码和 OpenClaw-RL 的 SWE 接线说明。来源版本、检查范围及未解决问题见 [证据清单](evidence_notes.md)。完整 HTML、文本与选读 TeX 保存在 [sources](sources/)，没有把第三方摘要当作论文证据。

## 1. MiMo 的公开字段究竟支持什么

这里仍使用最初冻结快照：**Pro step 12 / Flash step 15，09-17 02:24 UTC 开始采集**。不能与用户后来截图的 step 14 / 17 混成同一时刻。原始字段见 [指标目录](../metric_catalog.md:1382)，来源是 [MiMo 官方面板](https://mimo.xiaomi.com/rl/)。下面对未定义字段的解释均为推断。

| 字段 / 读数（Pro / Flash） | 较合理的解释 | 不能据此认定 |
| --- | --- | --- |
| `routed/select_v4` 406 / 412；`select_v4_nogold` 510 / 386；`off` 872 / 706 | 组被送往不同评分处理分支；`nogold` 暗示缺少某种参考解或参考实现 | `gold` 必然是人类修复；这些分支是随机消融；所有任务都用同一种 credit 算法 |
| `select_pass_new_tests_rate` 0.754751 / 0.715734；`select_above_gold_share` 0.347784 / 0.314955 | 评分中可能检查额外测试，并与参考方案比较 | 新测试一定由 LLM 生成；这些是 held-out 成功率；超过参考就证明修复更正确 |
| `select_rank_score_conflict` 10 / 5；`select_rank_invalid` 27 / 17；`select_tier_mismatch` 272 / 223 | 有排序、评分、分档一致性检查 | 冲突解决规则；A/B/E/P/S 各维含义；H/T1/T2/T3 的质量等级定义 |
| `select_tq_adv_rows_rewritten` 13,541 / 10,316 | **有明确命名为 advantage 行重写的非零计数** | 一行等于一个动作；只改了轨迹中的某些 token；确切执行顺序 |
| `select_adv_group_sum_abs_mean` 约 1.3e−16 | 被统计的组内 advantage 和接近零，符合重新居中等处理 | 做过标准差归一化；一定使用 GRPO；每条轨迹内部 token 总和守恒 |
| `select_factor_mean` 0.824 / 0.835；`select_renorm_k_mean` 1.193 / 1.175；`select_renorm_capped_rate` 5.16% / 2.42% | 存在缩放及重归一化相关诊断，且部分归一化系数触及限制 | factor 和 k 互为倒数；保留的是 L1、L2、正负总量还是其他量 |
| `select_groups_skipped_uniform` 58 / 57 | 可能跳过没有区分度的组 | “uniform” 指奖励相同、排序相同，还是处理因子相同 |
| `penalty/signed/*` 命中 token、正量移除、负量增加、缩放 | 与按 advantage 正负分支进行调整相容 | 已经实现动作级或 token 级语义定位；存在 value critic |

一个有用但有限的旁证：847 个已评分组 × 16 = 13,552，与 Pro 的 13,541 行重写非常接近；Flash 为 646 × 16 = 10,336，与 10,316 接近。这更符合“一条 rollout 对应一行”的解释，但仍缺少 row 定义。**改写一整行 token advantage，并不意味着这一行内部每个位置拿到了不同数值。**

`signed` 的正侧 scale 略大于 1、负侧略小于 1，且训练侧 penalty 前后正负总和在公开精度下相同，支持“局部改变后恢复某种总量”的假设。不过恢复的范围可能是 batch、组、轨迹或某个切片，尚不能确定。generic `tq_adv_rows_rewritten` 等字段为零，而 `select_tq_adv_rows_rewritten` 非零，也不能拿前者的名字推断动作级支路已经开启。

因此应分开三句话：

1. **有 advantage 重写和评分分支的公开记录：可以确认。**
2. **可能先做组相对 advantage，再用 judge 修改并重新居中：合理假设。** 先修改 reward、随后重算 advantage，同样能产生这类指标。
3. **已经确认单条 rollout 内部的具体动作被区别加权：证据不足。** 需要前后 advantage 向量、动作跨度或实现代码。

另外，`end2end_success_rate` 约 0.96 / 0.94 与评分流程完成有关，不能当作 SWE 解题成功率；`hack_attempt_rate` 的判据未公开，不能翻译为“四成轨迹确实作弊”。

## 2. 把改动位置说清楚

记一条轨迹的最终测试结果为 y_i，judge 分数为 q_i，组相对 advantage 为 A_i。

| 改动位置 | 计算流程 | 它回答的问题 |
| --- | --- | --- |
| 轨迹 reward shaping | 测试 + judge → R_i → 组比较 → A_i | 同样通过或同样失败的两条轨迹，哪一条更值得学习？ |
| 组内轨迹重分配 | 先有 A_i → 根据组内排序/因子重写各 A_i → 可再居中 | 这个组的正负学习信号应该更多分给哪条轨迹？ |
| 轨迹内重分配 | 先有 A_i → 给轨迹内动作 j 分权重 → A_ij | 一条轨迹的学习信号应该落到哪些动作？ |
| 过程奖励 / 新 advantage 估计 | 动作反馈、后续回报或 V/Q 估计 → A_ij | 动作自身是否有独立的正负训练信号？ |
| 过程引导采样 | judge → 分支、剪枝、保留 → 原有 RL | 有限 rollout 预算应该花在哪条路径？ |

上表是不同设计轴，不是互斥算法名称。GRPO、RLOO、GSPO、importance correction、judge、credit redistribution 也不是同一层的选择。冻结 judge 可以与组 baseline 共存；使用 judge 不自动消除整组等待。

“critic”一词也要看目标：预测策略未来回报的 V(s) 是 value critic；对完整修复打分的 verifier/RM 是奖励来源；对动作给出质量归因的 judge 是过程标注器。后两者可以是训练过的模型，但不因此变成在线训练的 V(s)。

## 3. 直接 SWE 证据：最值得先读的几篇

各行只做**论文内部比较**。模型、harness、训练题单和评测协议不同，不能用绝对分数跨论文排名。

| 工作与一手来源 | 实际改变什么 | 相关结果与边界 |
| --- | --- | --- |
| [SWE-RM，HKUST + Qwen](https://arxiv.org/html/2512.21919v1) | 30B-A3B verifier 读取 issue、轨迹、patch；将分数与测试结果组合，再做组相对优势估计和 GSPO | SWE-bench Verified，execution-only 51.8 → hybrid 54.8；是 RL 后单条 greedy patch 的 +3.0 个百分点。不是动作级 ADV 重写；62.0/74.6 等另一些高分属于 TTS |
| [SWE-TRACE，vivo](https://arxiv.org/html/2604.14820v1) | issue rubric + 完整轨迹评分，与二元测试结果混合，再 GRPO | 同一 cascaded-SFT 起点：4B 36.2 → 38.9；30B-A3B 61.1 → 63.5。相应 token 数 29.8k → 26.8k、30.6k → 27.6k。正文明确没有给每个步骤发数值 RL reward；不能被摘要的“dense process”措辞误导 |
| [Agentic Rubrics，Scale AI](https://arxiv.org/html/2601.04171v1) | agent 先查 repo，为问题生成准则；judge 按准则评 patch | 有 SWE 候选重排证据，主要是 Best@16；没有 RL 更新收益实验。适合借鉴 rubric 构造，而非宣称已经验证过程 RL |
| [OpenClaw-RL](https://arxiv.org/html/2603.10165v1) / [SWE 实现说明](https://github.com/Gen-Verse/OpenClaw-RL/blob/f48ac358adf9873b5cb2210f1cb234a52ed8a8a3/swe-rl/README.md) | 用动作后的观察给局部反馈；SWE 接线提供可选 PRM | 可借鉴工程接口与评分提示。论文 SWE 曲线是相关训练运行表现，不能当作独立 held-out 增益；process-vs-outcome 消融在 GUI/tool-call，不能移植成 SWE 因果证据 |
| [PaTR](https://arxiv.org/html/2607.15610v1) | PRM / judge 指导树分支和剪枝，最终仍用原有 outcome RL | SWE Verified：GRPO 22.2，随机树 24.8，judge 树 26.0，PRM 树 27.2。judge 相对随机树是 +1.2，不是 +5.0。它改变采样，不能当作直接改写 ADV 的实例 |

SWE-RM 的另一个重要发现是：**Best-of-K 选择能力接近的两个 RM，在 RL 中可能表现悬殊。** 只检查能否从 16 个 patch 里选中最好的，不足以判断它适不适合提供训练信号；还要检查误排序和分数可靠性。概率型分数可查校准，普通 rubric 分数不能未经定义就套 ECE。[论文实验](https://arxiv.org/html/2512.21919v1#S3)

SWE-TRACE 的实际训练信号为：

\[
R_i=\gamma y_i+(1-\gamma)q_i,\quad q_i\in[0,1],\quad \gamma>1/2.
\]

通过轨迹落在 [γ,1]，失败轨迹落在 [0,1−γ]，保留测试结果的严格排序，同时在同一结果类别内区分质量。它使用 rubric 生成和偏好训练得到评分器；并非“随便调用一个通用 LLM judge 就已复现论文”。其关键步骤索引用于记忆管理，不作为逐动作 RL 奖励。[方法正文](https://arxiv.org/html/2604.14820v1#S3)

Agentic Rubrics 值得借鉴的一点是：问题级 rubric 可以跨同题多个 rollout 复用；打分可以只读取相关代码/patch，而不必每次吞下完整长轨迹。不过动作归因仍需要过程证据，不能仅凭最终 diff 给之前每个动作贴标签。这一工程延伸是本报告的建议。

## 4. 真正“先算 A，再改轨迹内 A”的参考

### 4.1 DRACO：最明确的实现证据，但评测不是 SWE

[论文](https://arxiv.org/html/2609.04094v1)研究 AppWorld 和服务型 agent；[固定版本代码](https://github.com/IBM/draco/blob/cfafd0f81f2c49aa36a4b25a2a7b6ac6e119f47b/training/src/verl_appworld/credit_advantage_patch.py)明确包装 `compute_advantage`：**先调用原始计算，再替换逐 token advantage**。这正是用户问的“组归一化之后再处理”的一个已公开实例，但不能据此认定 MiMo 也如此。

依据[实现说明](https://github.com/IBM/draco/blob/cfafd0f81f2c49aa36a4b25a2a7b6ac6e119f47b/training/docs/CREDIT.md)，judge 为 rubric 的通过/失败引用步骤，得到步骤质量 Q_j；正 A_i 用 Q_j，负 A_i 用 1−Q_j。未引用步骤用已引用步骤质量的均值，缺少有效信息时回退原 A_i。若动作 j 有 n_j 个 token，N 为被映射到动作的 token 总数：

\[
w_j=\begin{cases}Q_j&A_i\ge0\\1-Q_j&A_i<0\end{cases},\qquad
A_{i,t}=\frac{A_iNw_j}{n_j\sum_k w_k}\quad(t\in j).
\]

由此 Σ_j n_j A_ij = N A_i。这里分配的是**步骤总量**，再除以步骤长度；没有动作归属的 gap token 被置零且不计入 N。因此守恒是相对于同一组 credited tokens，不是相对于原始所有 response tokens。

论文中 Qwen3.6-27B 的动态 rubric 无 credit → 有 credit，AppWorld TN 从 82.1 到 85.3；但固定 rubric 在 challenge split 加 credit 为 60.5 → 59.4。**有效性依赖评分依据，不是普遍增益。** 这些数字也不是三个独立训练 seed 的复现结果。[结果表](https://arxiv.org/html/2609.04094v1)

### 4.2 IAPO：有符号的影响关系加权

[IAPO](https://arxiv.org/html/2608.24588v1)用冻结标注模型读取轨迹，建立动作之间的支持使用、错误传播关系；正负 A_i 使用不同规则。其形式是 A_ij = A_i w_j，按动作 token 长度归一，使 Σ_j n_j w_j = Σ_j n_j。它与 MiMo 的 signed 命名相容，但没有证明对应关系。

实验是 τ² 等工具服务任务，**不是 SWE**；其 Qwen3-8B 在 τ² 的 GRPO 29.61 → IAPO 42.18，不能直接外推 repo 修复。标注模型是 Qwen3-32B，也不能因为它被冻结就认为便宜。本次取得的 v1 HTML/TeX 没有正文引用的若干附录，无法核实那些附录中的额外成本/审计细节。

### 4.3 这两种“守恒”不是同一个长度方案

以下是本报告构造的算例：A_i=1，两个动作分别有 100 与 900 个训练 token，质量相同。

| 分配规则 | 动作 1 每 token 的 A | 动作 2 每 token 的 A | 两个动作的总量 |
| --- | ---: | ---: | --- |
| 原本广播 / token 乘权、权重全 1 | 1 | 1 | 100、900 |
| DRACO 式步骤总量均分 | 5 | 5/9 | 500、500 |

两者总和都是 1,000，但学习权重不同。**如果实验采用 DRACO，必须加“只有步骤长度归一化、没有 judge 质量差异”的对照**，否则无法区分收益来自语义归因还是长度处理。

还要区分 advantage 标量和梯度向量：Σ_t A'_t = Σ_t A_t，并不推出 Σ_t A'_t ∇logπ_t = Σ_t A_t ∇logπ_t。各 token 的梯度不同，重新分配本就会改变更新。它不自动保持无偏，也不等价于准确估计 V(s)。DRACO 的实现文档使用了较宽泛的“gradient mass”措辞；论文附录 E.4 明确限制为 total advantage 的守恒。

### 4.4 OAR 以及其他候选的适用边界

| 工作 | 方法位置 | 本次判断 |
| --- | --- | --- |
| [OAR](https://arxiv.org/html/2601.07408v1) | 依据 token 扰动或输入梯度敏感度计算权重，再保留 advantage 总和 | 数学推理；不是 LLM judge。逐 token 遮蔽需要额外模型计算，不适合直接当作长 SWE 轨迹的便宜方案；敏感度也不是已验证的因果贡献 |
| [TRIAGE](https://arxiv.org/html/2606.32017v1) | judge 给动作角色，向原 A_i 加局部修正，再 whitening | ALFWorld/WebShop/SearchQA；不是 SWE。与乘权法不同，能产生新信号或翻转符号，也承担更强的错标风险 |
| [AEM](https://arxiv.org/html/2605.00425v1) | 用动作/response 熵计算 advantage 权重，不另请 judge | 有 SWE 消融：42.3 → 43.7。可作低成本控制组；论文 1.1% overhead 来自小模型 ALFWorld profiling，不能当 SWE 成本保证 |
| [RTMC](https://arxiv.org/html/2604.11037v1) | 合并 rollout 的近似状态/动作，估计 Q/V，无神经 critic | 有 SWE：49.0 → 52.2，但 step-reward 对照已达 50.4。状态合并有工程与偏差成本；其三次运行投票和最佳 checkpoint 口径不同于标准平均 pass@1 |
| [SWE-Shepherd](https://arxiv.org/html/2604.10493v1) | SWE 过程评分引导推理 | 本轮筛选未找到可用来支持上述 ADV 训练收益的直接消融 |
| [HCAPO](https://arxiv.org/html/2603.08754v1)、[RLAnything](https://arxiv.org/html/2602.02488v1) | 其他过程反馈 / agent 自改进 | 本轮阅读没有建立它们对 repo 级 SWE ADV 改写的直接证据；不混入上面的 SWE 训练结果 |

## 5. “judge 比 critic 便宜”需要怎样验证

**冻结 judge 通常省掉了新 value 网络的训练与稳定性问题，这是实现上的优势；推理计算、读长上下文和等待并没有消失。** 也有共享 backbone 的 value head，不能一律按“额外训练一个完整大模型”计 critic 成本。

DRACO 报告 100 个训练 step 的 judge 参考费用约 **$1,607**；self-judge 方案约 **$316**，但模型表现也改变了。这是其评分开销，不是全部训练费用，更不是同预算 judge-vs-critic 比较。它把 frontier judge 描述为流程中的最大成本项；完整动态组评分每 6 条 rollout 约需 20 次 judge 调用。[论文成本分析](https://arxiv.org/html/2609.04094v1)

MiMo 的 `stage_credit_group/time_total_sec_mean` 为 554 / 577 秒，最大值 3,469 / 7,244 秒。它们是评分流程延迟，不能直接换算 GPU-hours，但足以说明长尾等待值得观测。[原始字段](../metric_catalog.md:1903)

评估成本时至少分别记：

- actor rollout 与训练的 GPU 时间；judge 的输入/输出 token、模型大小、并发和实际计费/算力；额外生成测试的环境开销。
- judge p50/p95/p99 延迟、整组可用时间、进入训练时 policy lag；失败重试和评分后过期的浪费。
- **固定总成本下的 held-out 提升**，以及达到同一分数所需的时间和总成本。

每条完成轨迹评分一次，和每个动作都重读完整前缀，是完全不同的成本模型。后者若无缓存且各步长度相近，总输入 token 可随步数呈平方增长。先缓存问题级 rubric、只读取必要证据、对不确定部分升级 judge，可能更经济；是否损害归因准确性要一起测。

## 6. 针对 RH2 + miles 的建议实验

下列均为建议，不改变当前 reward/loss 定案。优先顺序是 **离线评分审计 → 小规模对照 → 同总成本比较**。

### 6.1 先用已有轨迹检查 judge，而非直接在线强化它

可先选约 100–200 条已完成轨迹作探索集，涵盖通过、失败、成功中含错误尝试、失败中含有效进展等情况；数量是建议，不是统计充分性承诺。输出固定结构：任务 rubric、轨迹分数、step ID、引用的工具观察或 diff、动作角色、置信/弃权标记。先冻结模型、提示和 rubric 版本。

SWE 上最应该人工抽查的误判包括：为了复现 bug 主动运行失败的测试；`grep` 没命中但成功排除了假设；有效的探索被当作无用步骤；修复了正确部位但验证预算耗尽；模型表述得自信却没有工具证据。**工具非零退出码不等于坏动作。** 按本项目既有语义，基础设施中断不应被塞成普通任务失败；修改测试也不能单凭动作名自动定性作弊。

对整条轨迹查排序质量及偏好噪声；对步骤查证据是否存在、动作范围是否对齐、关键负反馈的误报。judge 间的一致率仅是稳定性指标，不是真实正确率。没有可靠标签时应允许弃权。

### 6.2 分开检验三件事

| 实验臂 | 唯一主要改动 | 要回答的问题 |
| --- | --- | --- |
| A：现有基线 | 原有测试奖励、advantage 与 loss | 当前基线是什么？ |
| B：轨迹评分 | outcome + 固定 rubric judge 分数，再按同一规则计算 advantage | SWE-RM / SWE-TRACE 那种同结果轨迹区分是否有用？ |
| C：轨迹内乘权 | 保留 A 的 reward 与 A_i，只在动作内分配正的、有约束的权重 | 不新增结果奖励时，定位学习信号是否有额外收益？ |
| D：归因对照 | 对 C 的步骤标签按合适长度分层打乱；沿用同一数值处理 | 收益来自语义位置，还是单纯重新加权？ |

若 C 采用 DRACO 的步骤总量分配，还需单列无 judge 的长度处理对照。AEM 可作为另一种不调用 judge 的廉价候选，但不要与第一轮所有变量同时叠加。

两个特别重要的预期：

1. **非负乘权保留 A_i 的符号，A_i=0 则始终为零。** 它不能让负 A 的轨迹中好动作获得正奖，只能少惩罚；不能让正 A 中的坏动作变成负奖，只能少强化。若要解决同结果全零组，B 或加性过程反馈是不同实验。
2. **小 reward 系数不保证小更新。** 若一组 y_i 相同，R_i=c+εq_i，那么忽略数值稳定项时，(R_i−均值)/标准差 = (q_i−均值)/标准差，ε 被抵消。B 应单独记录这些组的贡献、judge 分数方差和置信度，不能靠“只加 0.1”宣称信号保守。

保持相同训练题单、基座、harness、动作/上下文预算和冻结 held-out 集；不要将判分用参考答案暴露给 actor。先用相同 rollout 数隔离机制差异，再计入评分开销做同总预算比较。训练平均 reward 不作主要成效标准；记录 held-out solve rate、token/环境时间、回归和更新稳定性。小试验有噪声时报告不确定性，不把最佳 checkpoint 或多次试验中最好一项当作稳健增益。

### 6.3 与当前训练消费语义的关系

已核对 [faithful_dis_loss.py](../../../../../../rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py)。现有链路按完整 execution 的 provenance token 数 D_e 归一，再使 execution 等权；DIS 拒绝的 token 保留在 D_e 中。

若后续实现 C，建议在 advantage 构造/转换处加明确的可关闭算子，使用捕获时的真实 token 与动作跨度，不通过重编码展示文本猜位置。沿用现有 loss mask、behavior logprob、DIS gate 和 D_e。监控 mask 后、DIS 前的 advantage 总量与范围；同时记录 DIS 后实际加权信号，但不要为了“守恒”擅自对 accepted token 重设分母。

即使 DIS 前满足 Σ m_t A'_t = Σ m_t A_t，经过随 token 变化的 f(r_t) 后也未必保留 Σ m_t f(r_t)A_t，更不保留梯度向量。这个区别应该进入消融解释，而不是被当作数值 bug。

## 7. 研究边界

本轮找到的是可借鉴机制与论文内部实验，没有找到 MiMo `pos_mass_removed`、`select_v4_nogold` 等字段的确切公开算法源码。不能确认其 judge 模型、评分 prompt、gold 含义、信用分配粒度或执行顺序，也没有证据确认可训练 value critic。

论文表现均为作者报告，未独立复现；代码只静态阅读，未执行。对没有完整 cost accounting、seed 消融或严格同预算对照的工作，不补充作者未给出的结论。建议优先验证 **“测试信号 + 可审计 judge”**，再测过程定位；不建议一开始同时换 judge、reward、ADV、采样树和 clipping 配方。
