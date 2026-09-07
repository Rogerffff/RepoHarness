# E1 The Interplay of Harness Design and Post-Training in LLM Agents：信息供给、训练时机与接口迁移

这是一项受控的后训练研究，而不是新的 RL 算法或多 harness 混训方案。作者把 ALFWorld 改造成工具调用环境，分别使用三档信息量的 harness，对 Qwen2.5-3B/7B-Instruct 进行 GRPO/GiGPO 训练，并测试同分布、训练后才换 harness、工具协议变化和任务类别变化。结果支持“训练时的接口与信息供给会影响学到的策略”，但不支持“信息越多在每种条件下都更好”，更未证明多 harness 随机化能学出语义不变性。本文恢复完整实验矩阵、算法与附录结果，区分信息增强和功能等价的 schema 变化，并保留训练失败、非单调结果及评分分母问题。

导航：[来源与覆盖](#source) · [环境与实验变量](#design) · [训练配方与公式](#training) · [结果与负结果](#results) · [成本与证据边界](#limits) · [RepoHarness 映射](#project)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**主来源。** Kyungmin Kim、Youngbin Choi、Seoyeon Lee、Suhyeon Jun、Dongwoo Kim、Sangdon Park，*The Interplay of Harness Design and Post-Training in LLM Agents*。前两位作者等贡献，后两位共同指导；机构为 POSTECH 人工智能研究生院与计算机科学与工程系。正式入口 [arXiv:2606.25447][P-abs]；本次读取 [v1 PDF][P] 和 [v1 HTML][H]。2026-09-08 查询的提交历史仅列 **2026-06-24 v1**。arXiv 链出的论文许可为 [CC BY 4.0][LICENSE]；本稿是注明来源的中文重述、表值整理与分析，不是作者认可的译本。

**阅读状态。** 22 个物理页的全部正文、Limitations、相关工作及附录 A–D 文本已读；正文全部 7 幅图已目视检查，Tables 1–8 所在图页已核。**物理页 17–22 的 PDF 截图持续返回 cache miss，因此 Table 9–16 和附录 C 公式尚缺 PDF 图页复核。** 这些部分已通过官方 HTML 与 PDF 提取文本读取和对照，不以“未披露”代替这个访问缺口，也不标成全部图表视觉复核完成。没有取得本机 PDF 或 TeX 副本。

**项目与旧稿。** 项目读取基线为 `Rogerffff/RepoHarness@miles-migration` 的 `b895451cb7ad50619bf94569976fbb2c7a1ddb5f`。旧稿为 [knowledge/summary_harness_interplay_posttraining.md](../../../../knowledge/summary_harness_interplay_posttraining.md)，仅作线索；本次回原文纠正配置总数、任务步数单位和部分结果范围，见 §10。原目录登记的 `pdfs/E1_harness_interplay_2606.25447.pdf` 是本地资产线索，本轮未用它替代实际取得的网络原文。

**代码边界。** 本轮检查论文、arXiv 元数据及精确标题相关检索，未定位到作者明确关联的扩展 ALFWorld 实现、训练配置仓库或 checkpoint 入口。因此没有开展代码审计，也没有借用 GRPO/GiGPO 上游默认值补出本实验配置。这不等于证明作者从未公开代码。

### 1.1 原文覆盖表

页码均为 PDF 物理页，与本版印刷页码一致；“完整”指相应文本已读，图页状态另列。

| 原文位置 | 内容与阅读范围 | 本稿位置／视觉核验 |
| --- | --- | --- |
| pp.1–2，摘要、§1、Fig.1 | 研究动机、静态部署假设、三条 RQ、实验总览，完整 | §2；Fig.1 已看 |
| p.3，§2.1–2.2 | 工具调用与状态重建、序列级 MDP、GRPO/GiGPO 角色，完整 | §2、§5 |
| pp.3–5，§3.1–3.4、Tables 1–3 | ALFWorld、三 harness、三 schema、六任务与难度分组，完整 | §3；Tables 1–3 已看 |
| p.5，§4.1 | split、评测定义、配置组合、算力 remark，完整 | §3.4、§4、§8 |
| p.6，§4.2、Figs.2–3 | zero-shot 与同分布训练，完整 | §6.1–6.2；两图已看 |
| p.7，§4.3、Fig.4 | train-time 与 post-hoc 对照，完整 | §6.3；图已看 |
| pp.7–8，§4.4、Figs.5–7、Table 4 | schema shift、格式/执行失败、task shift，完整 | §6.4–6.6；图和 Table 4 已看 |
| pp.8–9，§5、Limitations | 作者总体结论、单环境与资源限制、未来联合优化，完整 | §7、§9 |
| pp.9–11，References | 检查引用身份与尾部连续性；未逐篇扩读参考论文 | §7、§11 |
| pp.12–13，Appendix A.1–A.3 | 训练方法、harness 搜索、动态工具环境三类相关工作，完整 | §7 |
| pp.14–17，Appendix B.1–B.2、Tables 5–9 | 全部工具描述、观测模板、工具/参数重命名及聚合，完整 | §3；Tables 5–8 已看，Table 9 文本核对 |
| pp.18–19，Appendix C | MDP、两算法全部公式、训练与评测参数，完整 | §4–5；尚缺 PDF 图页复核 |
| p.20，Appendix D、Tables 10–12 | zero-shot、同分布、post-hoc 全部数值，完整 | §6.1–6.3；主图对应整体值已看，细表为文本核对 |
| p.21，Table 13 | 两模型、三 harness、三 schema 的全结果，完整 | §6.4；7B 主图已看，3B 等细值为文本核对 |
| p.22，Tables 14–16 | easy/med/hard 单类别训练后的分任务结果及失败注释，完整 | §6.6；Fig.7 对应 7B 雷达图已看，细表为文本核对 |

本篇不是模型发布报告，原文没有另设数学、科学、多模态、安全或 OPD 实验；没有为了填模板而增写这些训练阶段。详细自查见 [E1 作者自查](reviews/E1_self_check_20260908.md)。

## 2. 作者研究的不是“哪个 harness 最强”，而是训练与信息供给的相互作用

### 2.1 三个研究问题及作者结论

**RQ1**：zero-shot 时不同 harness 造成的差异，经过后训练是否仍然存在？**RQ2**：目标 harness 应在训练中就位，还是低信息 harness 训练后再套上去也可以？**RQ3**：训练时的 harness 如何影响工具协议改变和任务分布改变后的表现？[§4，p.5][P5]

作者用五个 Observation 概括：zero-shot 总体随信息量上升；这种趋势大体延续到后训练；post-hoc 加强 harness 无法恢复训练时就使用它的大部分收益；低信息 harness 训练的模型在强 schema 变化下明显失效；较丰富的先验信息有利于跨任务迁移。结论进一步将 harness-aware post-training 称为稳健 agent 的必要条件。[§4–5，pp.6–9][P6]

**本稿的解释边界：**这些是单个环境、两只开放模型、两种算法与有限训练预算下的经验结果，不能升级为“RL 永远补不回低信息 harness”“所有接口更新都必须重训”或普遍的模型规模规律。数表还有非单调结果，§6 会与正面结果一并保留。

### 2.2 Harness、tool schema 和 task type 是三个不同变量

作者将广义 harness 收窄为通过系统提示 `p` 和工具环境 `TE` 作用于 agent 的包装。它不覆盖一切训练 runtime、权重发布、沙箱安全、权限或网络机制。[§2.1，p.3][P3]

令 `q` 为用户任务，`T_{t-1}` 为此前历史，模型的第 `t` 轮输入为 `s_t=(p,q,T_{t-1})`。模型产生动作 token 序列 `a_t`；随后 `TE` 做两件事：

1. **Tool Calling**：执行／验证动作并产生结果 `e_t=TE((s_t,a_t))`。
2. **State Reconstruction**：把历史、动作与结果组织成下一轮历史 `T_t=TE((s_t,a_t,e_t))`，得到 `s_{t+1}=(p,q,T_t)`。

这里 `T` 是工具调用轮数，而不是 token 数。附录 C 把输入状态与动作空间都写为可变长 token 序列 `V*`，将转移建模为由 `TE` 决定的确定性映射，初始分布为 `P_0`，目标为期望轨迹回报。历史“可能经过摘要”出现在形式描述中，**不代表本篇实际训练了摘要策略或做了 compaction 消融**；它也没有证明任意压缩历史都具有 Markov 充分性。[Appendix C，p.18][P18]

| 变量 | 本实验实际改变的内容 | 没有等同于什么 |
| --- | --- | --- |
| Harness 信息档位 | 工具知识、每步可用工具提示、持有物品状态 | 等信息的纯表述扰动 |
| Tool schema | 工具名、参数键、调用组织方式；功能按设计保持 | 增加一个能自动做多步的智能宏工具 |
| Task type | 六类任务按难度分组后的训练分布 | 全新软件、真实网站或另一类运行环境 |

这个区分是全文最重要的使用前提：**h-low→h-high 主要研究额外信息；v1.0→v1.1/v2.0 才研究功能保持条件下的接口变化。**

<a id="design"></a>
## 3. 环境、harness 与实验矩阵

### 3.1 原环境与任务：不是 SWE/terminal 数据生产论文

作者把 ALFWorld 原有文本动作改为结构化工具调用，例如把移动到抽屉改成 `Go(receptacle="drawer 1")`。底层仍是文本式家庭环境，成功要求在有限工具调用步数内完成任务的全部子目标。[§3.1、§4.1，pp.3、5][P3]

| 数据对象 | 数量与作用 | 必须保留的边界 |
| --- | --- | --- |
| 全部实例 | 3,827 个任务 | 不是镜像数、轨迹数或合成候选数 |
| 训练 split | 3,553 个任务 | 另随机留出 10% 用于选 checkpoint，不能全部算作实际 optimizer 消费题目 |
| 测试 split | 274 个任务，140 seen + 134 unseen | 这是 ALFWorld 标准 seen/unseen 轴，不能与 easy/med/hard 类别 OOD 混用 |
| 训练任务集合选择 | all、easy、med、hard 四种 | 是分别训练，不是四阶段课程或混合采样控制器 |

精确验证题单、各类别样本数、10% 的舍入／抽取规则、每个难度子集是否独立重抽、实际训练数据重复消费量均未给。这里不反推 task manifest，也不把该研究描述为 PR 构建、gold/no-op 审计或隐藏 grader 隔离生产线。

六类任务的分组依据是**最少子目标数**，不是固定实际轨迹长度：[Table 3，p.5][P5]

| 组 | 类别 | 最少子目标 | 任务含义 |
| --- | --- | ---: | --- |
| t-easy | Pick | 4 | 找到、拿取并放置一个指定物品 |
| t-easy | Look | 3 | 在灯光下检查物品 |
| t-med | Clean / Heat / Cool | 各 5 | 清洗／加热／冷却后放置 |
| t-hard | Pick 2 | 8 | 找到并放置两个指定物品 |

例如“找到物品”可能需要多次探索；8 个子目标并不是 8 次工具调用。各组共享导航、寻找、拿取与放置等子技能，这构成作者研究跨任务迁移的依据，并不保证迁移一定发生。

### 3.2 三档 harness 的完整组成

| Harness | 工具描述 | 每步当前可用工具名 | 每步持有物品 | 共同观测内容 |
| --- | --- | --- | --- | --- |
| h-low | 一行简述 | 无 | 无 | 目标、当前位置、当前 step 编号与原始 observation |
| h-mid | 同 h-low | 有 | 无 | 同左 |
| h-high | 丰富描述：前置条件、工具间关系、完成任务的作用 | 有 | 有 | 同左 |

来源：[Table 1，p.4][P4]；[Tables 5–6，pp.14–15][P14]。正文把 h-low 简称为“仅 raw observation”，而 Table 6 实际列出了三档共同的目标、位置和 step 字段；本稿以完整模板说明，避免误以为 h-low 连当前位置也没有。

`Valid tools` 列的是当前可用的**工具名字**，不是带全部正确参数的完整可行动作，也不是已披露的 constrained decoding。h-high 自动呈现携带物品；没有该字段时，模型通常需要调用 `Inventory` 或从历史推断。信息档位因此会改变信息取得的成本和决策负担，而不只是 prompt 的文风。

Table 5 的丰富描述对全部 13 个工具补充了下列知识：[Appendix B.1，p.14][P14]

| 工具族 | h-high 明确提供的知识（重述） |
| --- | --- |
| Go / Open / Close | 操作容器前先到达对应位置；打开封闭容器后物品才可见；关闭并非所有任务都需要 |
| Take / Move | 拿取要求物品可见、必要时先打开容器；一次只能携带一个物品；放置需要持有它并到达目标处 |
| Clean / Heat / Cool / Slice | 清洗、加热、冷却分别依赖水槽、微波炉、冰箱及相应位置／持有条件；切割还涉及刀具 |
| Look / Inventory / Examine | 分别用于观察周围、查看携带物品、检查容器或物品状态；Examine 可以支持重新检查 |
| Use | 在目标设备位置激活它；灯光类任务需要持有目标物品并开启灯 |

这是源文提供给模型的先验知识，不是本文独立验证过的环境执行规范。h-mid→h-high 同时改变**丰富描述和持有状态**，没有逐一去除组件的消融，因此不能把总收益单独归给记忆、描述长度或某一种前置条件。

作者强调，先前 ALFWorld 研究常提供带参数的完整可行动作集合，信息量甚至超过这里的 h-high；产生这种指导需要充分环境知识或有代价的探索。该成本被明确承认，但**没有定量测量人工／探索费用**。[§1、§3.2，pp.2、4][P2]

### 3.3 Schema 变化：13 个工具的重命名，再聚合为 5 个入口

**v1.1** 对 v1.0 的所有工具名及参数键做语义保持的重命名，工具数量仍为 13。完整名称映射如下：[Tables 7–8，p.16][P16]

| v1.0 | v1.1 | v1.0 | v1.1 |
| --- | --- | --- | --- |
| Go | NavigateTo | Open | OpenContainer |
| Close | CloseContainer | Take | Pickup |
| Move | Place | Clean | Wash |
| Heat | Warm | Cool | Chill |
| Slice | Cut | Look | SurveyRoom |
| Inventory | CheckCarried | Examine | Inspect |
| Use | Activate | — | — |

参数按语义重命名：导航／放置的 `receptacle→destination`，拿取来源为 `source`；清洗、加热、冷却位置分别为 `washer/heater/cooler`；`object→item`、`knife→blade`、`target→subject`。不同角色的同名原参数，不是全局替换成同一个新键。

**v2.0** 将 13 个工具按功能聚合成以下 5 个入口，用离散参数选择原有操作：[Table 9，p.17；本轮文本核对][P17]

| 新工具 | action 值／子操作 | 参数 |
| --- | --- | --- |
| ReceptacleControl | navigate_to / open_container / close_container | action, target |
| ObjectTransport | pickup / place | action, item, location |
| ObjectTransform | wash / warm / chill / cut | action, item, instrument |
| Observe | survey_room / check_carried / inspect | action, subject |
| Activate | 单一激活操作，没有 action 枚举 | device |

例如同一个移动动作分别写为 `Go(receptacle="drawer 1")`、`NavigateTo(destination="drawer 1")`、`ReceptacleControl(action="navigate_to", target="drawer 1")`。**v2.0 不是一次调用自动完成导航、开门和拿取的宏动作**，而是原动作的分组表示。

测试时系统提示中的名字、键与描述，以及 `TE` 的验证逻辑都更新到新 schema。模型不是在完全不知新接口的情况下被突然要求猜 API；但沿用旧调用形式仍会收到 `Invalid tool format`。功能按作者设计保持，不等于本轮独立执行了变换的等价性测试。[§3.3，pp.4–5][P4]

这是训练后、测试 episode 使用的接口变化。论文没有测试执行到一半 API 才变化、服务超时、权限漂移、恶意工具或任意第三方 CLI harness。

### 3.4 48 种训练配置，及四类结果协议

每个模型为 **3 harness × 4 训练任务集合 × 2 算法 = 24 配置**；两个模型合计 **48 种名义训练配置**。Limitations 明写“24 training configurations per model”。旧摘要将总数写成 24，需要纠正。[§4.1、Limitations，pp.5、9][P9]

| 分析 | 训练数据／接口 | 测试设置 | 能辨识的变化 |
| --- | --- | --- | --- |
| Zero-shot | 不做本篇 RL | 三档 harness，schema v1.0，全部测试题 | 固定权重下的信息供给影响 |
| In-distribution | all 训练，各自固定 harness 与 v1.0 | 同一 harness、同一 schema、全部测试题 | 后训练后同分布表现 |
| Post-hoc | h-low + all + v1.0 | 仅测试时换 h-mid 或 h-high | 与训练时就用目标 harness 的模型比较 |
| Tool environment shift | all、各自 harness、v1.0 | 保持 harness 档位，改 v1.1/v2.0 | 新 schema 下的表现 |
| Task shift | 仅 easy、med 或 hard，固定 harness/v1.0 | 其他类别为 OOD；附录同时列全部测试类别 | 共享环境与工具上的类别迁移 |

作者总结为 zero-shot 加三种后训练评测 regime，post-hoc 是其中一个单独对照。**ALFWorld 的 seen/unseen split 与任务类别 ID/OOD 是正交的标注概念。** Appendix D 的 task-shift `All` 列包含训练类别的测试题，不能直接叫纯 OOD 分数。

<a id="training"></a>
## 4. 实际后训练流程、预算与运行披露

两只输入模型分别是 **Qwen2.5-3B-Instruct、Qwen2.5-7B-Instruct**，每个配置独立做 GRPO 或 GiGPO 后训练；并非先 GRPO 再 GiGPO。没有新增 SFT、专家教师蒸馏或多 harness 混训阶段。GPT-5-mini 只是 zero-shot 参照，不参与数据生成、评分教师或 OPD。输入已是 Instruct 模型，“本篇直接做 RL”不代表它们此前没有指令训练。[§4.1、Appendix C][P5]

### 4.1 原文参数与单位

| 参数／步骤 | 原文披露 | 阅读限定 |
| --- | --- | --- |
| 更新长度 | 500 training steps | 不给各配置实际提前停止／有效更新记录 |
| 学习率 | constant 1×10^-6 | 优化器类型、betas 等未披露 |
| 每步任务提示数 | 16 | 是 task prompts，不是每个 turn 的训练片段数 |
| 每题采样 | G=8 trajectories | 同一提示的组 |
| PPO minibatch size | 256 | 与 16×8=128 episode 的关系未解释，不能自行改成 128 |
| KL | loss 中加入 low-variance KL penalty，系数 0.01 | 当前策略到 reference 的方向见 §5 |
| 验证 | 训练数据随机 10% 留出，用于选最终 checkpoint | 具体题单、每个子集处理和选择频率未披露 |
| 采样 | vLLM，temperature=1.0 | top-p/top-k、logprob 获取与 replay 未给 |
| 轨迹上限 | 每 episode 最多 50 turns | 不是 50 个子目标或 50K token |
| 输入／单次输出上限 | prompt 3,072 tokens；response 1,024 tokens | 超过历史预算如何裁剪／停止未给完整处理合同 |
| 奖励 | 成功轨迹 +10；每次 invalid action −0.1 | 作者称 sparse，但不是只有二元终局 reward |
| 训练硬件 | 4×H200 | 不是本项目八卡消费级拓扑 |
| 测试 | temperature=0.4；开放模型三 seeds | 原文未拆清 seed 是否覆盖完整重训、评测或两者 |
| GPT-5-mini | high effort，response 上限 4,096，一 seed | 与开放模型输出预算不同，不能作严格等预算规模消融 |

来源：[Appendix C，p.19][P19]。其 “Training” 段字面上写的是 “with GRPO”；正文明确报告了 GiGPO 训练，附录也完整描述 GiGPO 公式，但**没有逐算法分别提供整套运行配置**。不能未经说明把全部该段参数当成每个 GiGPO 配置已独立确认的参数。

“每步 16 prompts、每题 8 条”与“PPO minibatch 256”应原样保留：可能涉及片段单位、累积或其他实现安排，但论文没有解释，本稿不选其中一种猜测。三 seeds 也不自动证明运行了 48×3 次完整且有效的训练。

### 4.2 奖励、终止和系统失效不能混写

目标是环境内全部子目标完成；格式错误、语义上不可执行以及最终任务失败是不同对象。作者给每次 `invalid action` −0.1，却未给足代码说明该惩罚是否同时覆盖 Fig.6 的 `inadmissible` 类、多个无效字段怎样计数，以及成功时如何累计先前惩罚。没有 LLM judge 的披露，成功指标基于环境任务条件。[Appendix C；§4.1、Fig.6][P19]

附录 C 将结束定义为成功或达到工具轮数上限，但未说明截断轨迹是否参加组统计、是否屏蔽自身梯度、是否补采；也没有环境进程失败、真实工具服务超时与正常动作失败的统一状态机。本篇不能作为 SkyRL horizon mask、DIS 或 rh2 丢组约定的另一份证据。

### 4.3 一条可恢复的运行时序，及其边界

从论文可恢复的过程是：固定训练 harness/schema 与任务集合 → 抽取提示 → 行为策略每题采样八条交互轨迹 → 环境执行与返回反馈 → 计算回报、组统计和可选 step-level 优势 → 优化当前策略 → 用留出集选择 checkpoint → 运行规定的测试变化。

这是算法层时序，不是作者公开的 runtime 实现图。原文只明确 vLLM rollout，没有给训练框架名称、同步／fully async 队列、权重发布协议、staleness、缓存、TP/DP、dtype、分布式 mask reduction、沙箱预热或吞吐实验。**不能因为 GiGPO 有上游代码就推定本实验用 verl，也不能因为有 `π_old` 就推定存在异步陈旧策略。**

## 5. 训练目标：按本文附录恢复，不补上其他论文的默认实现

本节公式来自 Appendix C，pp.18–19；使用 `N_i` 等缩写重排版，不改变求和层级。HTML 与 PDF 提取文本已对照，公式 PDF 图页尚缺视觉复核。原文无可复用的公式编号，因此定位到小节而不是编造 Eq.1/2。

### 5.1 GRPO：同题 episode 统计与逐 token 比率

同一系统提示和任务 `(p,q)`，行为策略 `π_{θ_old}` 采样 `G` 条 episode。第 `i` 条有 `T_i` 个 turn，第 `t` 轮动作有 `n_t^i` 个 token，动作 token 总数记 `N_i=Σ_t n_t^i`。token 前缀为 `s_{<tk}^i=(p,q,T_{t-1}^i,a_{t1}^i,…,a_{t(k-1)}^i)`。

$$
\rho_{tk}^i=\frac{\pi_\theta(a_{tk}^i\mid s_{<tk}^i)}{\pi_{\theta_{\rm old}}(a_{tk}^i\mid s_{<tk}^i)},\qquad
\widehat A^i=\frac{R^i-\mu}{\sigma}.
$$

`μ,σ` 是该提示下 G 条 episode reward 的均值、标准差。原文目标为：

$$
\mathcal J_{\rm GRPO}=\mathbb E\left[\frac1G\sum_{i=1}^G\frac1{N_i}\sum_{t=1}^{T_i}\sum_{k=1}^{n_t^i}
\left\{\min\left(\rho_{tk}^i\widehat A^i,\operatorname{clip}(\rho_{tk}^i,1-\varepsilon,1+\varepsilon)\widehat A^i\right)
-\beta D_{\rm KL}\left(\pi_\theta(\cdot\mid s_{<tk}^i)\Vert\pi_{\rm ref}(\cdot\mid s_{<tk}^i)\right)\right\}\right].
$$

来源：[Appendix C，GRPO，p.18][P18]。`π_θ` 是被更新策略，`π_{θ_old}` 是采样策略，`π_ref` 是固定 reference；作者说 reference 通常由初始策略初始化并保持冻结。KL 在 loss 内，不是未说明的另一个教师奖励。

需要保留四个语义：**优势有标准差归一化，不是 LOO；ratio 是 token-level，不是 turn 或整条轨迹；每条 episode 内先除以自身动作 token 数，再在组内平均；同一 episode 的 GRPO 优势赋给全部 turn。** 因此不同长度 episode 的每个 token 并非等权，也不能把它叫固定全局 token 分母。

公式仅对 agent 动作 token 求和；工具反馈作为后续上下文，不是动作。Appendix A.1 也讨论了环境反馈 token 的 masking，但本轮没有实现代码可检查，不能由概念公式推出 thinking、特殊标记、padding、重分词和分布式分母的全部实际行为。`σ=0` 的数值处理、clip 的 ε 值、梯度 detach、截断 mask 与多轮更新细节均未给完整实现。

### 5.2 GiGPO：不是加一个 critic，而是再做一次状态内分组

在同题 G 条 episode 的所有 step transitions 中，用状态识别器 `h(s,s')∈{0,1}` 判断两个 step 的起始状态是否语义等价。按 anchor state `s̃` 划分不相交组 `G(s̃)`；它们覆盖原组的全部 step transitions。相同语义状态可以来自不同 episode，也可以处于不同 turn 索引。这里 **`h` 是状态识别函数，不是 h-low/h-mid/h-high 的 harness 档位**。[Appendix C，GiGPO，pp.18–19][P18]

该 step 的后续折扣回报和局部优势是：

$$
R_t^i=\sum_{u=t}^{T_i}\gamma^{u-t}r_u^i,\qquad
\widehat A_t^i=\frac{R_t^i-\mu_{g_t^i}}{\sigma_{g_t^i}}.
$$

`g_t^i` 是 step 所属 anchor 组，其均值／标准差对该组的 step returns 计算。GiGPO 将 GRPO 目标两处 clipping 项中的 `Â^i` 替换为：

$$
\widehat A^i+\omega\widehat A_t^i,\qquad \omega>0.
$$

逐 token ratio、episode 内归一化以及 KL 项保持同样结构。作者明确 step-return 的 `γ` 可以与定义 episode reward 时的折扣不同；具体 `γ、ω` 没有披露。它不是给每个工具输出训练 value head，也不是本篇训练了过程 reward model。

最影响复用的缺项是 `h` 怎样实际实现：根据完整环境状态、规范化字符串、历史摘要还是其他标识，本篇没有给可追查代码。单成员 anchor、零方差组、重复访问同一状态的处理也未给。**不能把“语义等价”三个字直接当成已解决的任意真实 harness 状态对齐算法。**

一个仅供后续验证的推论是：harness 改写可见状态，可能同时改变策略探索和 GiGPO 的 anchor 分组统计。本文未隔离这两条作用路径，因此不把这个推论写成作者证明的增益机制。

<a id="results"></a>
## 6. 完整结果链：整体趋势、反例与指标分母

以下成功率单位均为 **%**，差值为**百分点（pp）**。开放模型按作者给出的三 seeds 均值记录；`±` 是原表标准差，不是置信区间。Table 13 本身只列均值，尽管 Appendix C 泛称结果表都给标准差，本稿不替该表补误差条。模型简称 3B/7B 均指 Qwen2.5 对应 Instruct。

### 6.1 Zero-shot：总体随信息量增加，不能推广到每个类别

| 模型 | h-low | h-mid | h-high |
| --- | ---: | ---: | ---: |
| GPT-5-mini，high，单 seed | 28.1 | 31.0 | 68.3 |
| 3B | 1.3±0.6 | 3.3±1.1 | 13.9±0.7 |
| 7B | 7.4±0.9 | 16.1±1.7 | 29.0±1.8 |

来源：[Fig.2，p.6][P6]；[Table 10，p.20，细表文本核对][P20]。Fig.2 纵轴成功率，横向比较三模型与三 harness，不是学习步数曲线。其整体值有精确标签，故不使用目测近似替代。

作者观察到更强模型从信息增强得到更大总体收益，但 GPT-5-mini 有更大输出预算、单 seed，模型家族也不同，不能把这三点拟合成受控容量 scaling law。类别级也非处处单调：GPT-5-mini 的 Pick 2 为 **17.1→12.2→61.0**。3B 的该类别三档都为 0；7B 在 h-high 也只有 1.6±1.4。信息增强不能保证弱模型采到困难任务的成功路径。

### 6.2 同分布后训练：harness 重要，但 h-high 并非总是第一

训练 all，schema v1.0；测试使用相同 harness/schema、全部 274 题。[Fig.3，p.6；Table 11，p.20][P6]

| 模型／算法 | h-low | h-mid | h-high |
| --- | ---: | ---: | ---: |
| 3B GRPO | 56.0±1.1 | 61.7±1.0 | 69.7±0.6 |
| 3B GiGPO | 65.6±1.3 | **83.2±1.3** | 82.1±2.4 |
| 7B GRPO | 55.6±0.8 | 76.2±0.2 | 77.9±0.8 |
| 7B GiGPO | 81.0±0.0 | 83.0±0.8 | 86.9±0.4 |

3B+GRPO+h-high 比 7B+GRPO+h-low 高 **14.1 pp**。这支持系统配置的影响可以超过此处模型大小差异，但这是**模型和 harness 同时不同的两个系统**，不是3B裸权重超越7B的证明。

GiGPO 在上述每个同模型、同 harness 的整体比较中都高于 GRPO，尤其7B h-low为81.0 vs55.6。作者解释为更细的信用分配；本研究没有另拆 GiGPO 各组件消融。这个优势也不能推广到后面全部 task-shift 配置。

非单调例外必须保留：3B GiGPO 的 h-mid **83.2** 略高于 h-high **82.1**。两个标准差范围有重叠，不能据均值排序宣称显著优劣，但足以避免写成“每格都单调”。类别层还有明显差异：3B 在 h-low 下两算法 Pick 2 都是0；7B GRPO h-low 的 Look 为0，而 h-mid/h-high 都为86.0±1.9。

### 6.3 Post-hoc：同一个测试 harness，训练时就位更好

下表比较 `h-low 训练→目标 harness 测试`，与`目标 harness 训练→相同目标测试`，数据及 schema 均为 all/v1.0；不是添加更多测试重试。[Fig.4，p.7；Tables 11–12，p.20][P7]

| 模型／算法 | 目标测试 harness | h-low 训练后再换 | 训练时即用目标 harness | 差值 pp |
| --- | --- | ---: | ---: | ---: |
| 3B GRPO | h-mid | 57.5±1.2 | 61.7±1.0 | +4.2 |
| 3B GRPO | h-high | 59.6±0.9 | 69.7±0.6 | +10.1 |
| 3B GiGPO | h-mid | 69.3±0.0 | 83.2±1.3 | +13.9 |
| 3B GiGPO | h-high | 67.6±1.1 | 82.1±2.4 | +14.5 |
| 7B GRPO | h-mid | 55.5±1.1 | 76.2±0.2 | +20.7 |
| 7B GRPO | h-high | 55.4±1.2 | 77.9±0.8 | +22.5 |
| 7B GiGPO | h-mid | 79.6±1.0 | 83.0±0.8 | +3.4 |
| 7B GiGPO | h-high | 82.2±1.1 | 86.9±0.4 | +4.7 |

八个对照全部支持目标 harness 在训练时就位。作者所说 post-hoc “恢复很少收益”是相对训练时就位的差距；不能解释为加 harness 永远零收益。例如3B GRPO h-low原生56.0，换h-high后59.6，仍有改善。

本实验只覆盖 **h-low→h-mid/h-high**，并非完整3×3交叉训练／测试矩阵，也没有“换任意工具版本后做少量适配”的对照。它支持优先测训用一致性，不支持把“任何 harness 更新默认都要重训”写成已证明规则。

### 6.4 Schema shift：完整整体矩阵，以及更强改名也可能帮助 base 的例外

训练模型一律在各自 harness 下用 v1.0/all 训练；测试仅替换 schema，harness 档位不变，任务集不变。Zero-shot 行的 harness 指测试配置。[Fig.5，p.7；Table 13，p.21][P21]

| 模型／训练 | Harness | v1.0 | v1.1 | v2.0 |
| --- | --- | ---: | ---: | ---: |
| 3B Zero-shot | low | 1.3 | 7.2 | 5.4 |
| 3B Zero-shot | mid | 3.3 | 16.5 | 5.2 |
| 3B Zero-shot | high | 13.9 | 16.8 | 14.6 |
| 3B GRPO | low | 56.0 | 19.7 | 5.2 |
| 3B GRPO | mid | 61.7 | 53.2 | 24.3 |
| 3B GRPO | high | 69.7 | 65.6 | 60.9 |
| 3B GiGPO | low | 65.6 | 63.4 | 30.8 |
| 3B GiGPO | mid | 83.2 | 76.4 | 56.4 |
| 3B GiGPO | high | 82.1 | 80.0 | 71.0 |
| 7B Zero-shot | low | 7.4 | 7.9 | 13.5 |
| 7B Zero-shot | mid | 16.1 | 30.3 | 26.6 |
| 7B Zero-shot | high | 29.0 | 26.3 | 35.8 |
| 7B GRPO | low | 55.6 | 54.3 | 2.7 |
| 7B GRPO | mid | 76.2 | 78.2 | **63.6** |
| 7B GRPO | high | 77.9 | 74.8 | 53.0 |
| 7B GiGPO | low | 81.0 | 74.9 | 33.2 |
| 7B GiGPO | mid | 83.0 | 83.0 | 37.8 |
| 7B GiGPO | high | 86.9 | 82.5 | 69.6 |

核心失败例是7B GRPO h-low：v2.0只有 **2.7**，比同测试条件的zero-shot **13.5** 低 **10.8 pp**。这说明同分布提升可以伴随特定接口迁移退化，不是“模型经过RL总更强”。

同样重要的三个限定：**3B GRPO h-low 在轻变化 v1.1 也从56.0掉到19.7**，所以“低信息训练能适应轻变化”不是跨模型普遍结论；**7B GRPO v2.0 的 h-mid 63.6 高于 h-high 53.0**，不能说丰富度处处越高越稳；**7B base h-low 在 v2.0 反而高于 v1.0**，说明“strong shift”指相对训练 schema 的结构距离，不是对所有模型都更难的环境排序。

这组实验没有进行多 harness 随机化训练、跨真实 coding CLI 迁移、联合 task+schema shift，或中途在线学习新工具。

### 6.5 格式正确、当前可执行和最终成功是三个层次

Fig.6 专门分析 **7B GiGPO，训练 v1.0、测试 v2.0**，不是所有模型平均。[Fig.6，p.7；Table 4，p.8][P7]

| Harness | 任务成功下降 pp | admissible：格式正确且可执行 | inadmissible：格式正确但当前不可执行 | invalid：格式／工具名／参数错误 |
| --- | ---: | ---: | ---: | ---: |
| h-low | 47.8 | 18.4% | 0.5% | 81.2% |
| h-mid | 45.2 | 20.2% | 4.8% | 75.1% |
| h-high | 17.3 | 60.8% | 34.9% | 4.2% |

数值取自已目视检查的 Fig.6 标签，分别按同图所有工具调用的堆叠分类解释；由于一位小数舍入，行和可能为99.9或100.1。左图是相对同分布的**任务成功率下降**，右图是**调用级**比例，两种分母不能混用。

**原文存在一处需要保留的表述歧义：**正文说h-high有95.7%合法调用，又称“34.9% of these calls”不可执行；但图中的34.9是与60.8并列的全调用类别，二者相加正好95.7。本文沿图的共同分母记录，不再把34.9%乘以95.7%，也不把它无说明地说成“合法调用中的34.9%”。

低／中信息模型会编造貌似合理但不在新协议中的 `GoTo`、`GoToLocation`、`navigate_to` 等工具名；高信息模型大多用对新格式，却仍会因状态前置条件不满足而得到 `Nothing happens`。这支持细分失败指标，**但不能由格式通过率直接推导模型具备状态理解或可靠完成能力**。

### 6.6 Task shift：三种训练子集都要看，并显式标出失败后用 zero-shot 代填的行

Tables 14–16 分别只用 easy、med、hard 训练，然后按相同 harness/v1.0 测试全部274题。下表收集 `All`，其中包含训练类别的测试题，**不是纯 OOD 均值**。[Appendix D，p.22][P22]

`ZS†` 表示原表注明训练未起效、改报zero-shot，不是一个成功训练 checkpoint 的得分。

| 模型／算法 | Harness | train easy：All | train med：All | train hard：All |
| --- | --- | ---: | ---: | ---: |
| 3B GRPO | low | 23.1±0.6 | 1.3±0.6 ZS† | 1.3±0.6 ZS† |
| 3B GRPO | mid | 33.7±1.4 | 41.5±2.4 | 3.3±1.1 ZS† |
| 3B GRPO | high | 63.1±1.7 | 69.7±1.1 | 13.9±0.7 ZS† |
| 3B GiGPO | low | 37.2±1.0 | 1.3±0.6 ZS† | 1.3±0.6 ZS† |
| 3B GiGPO | mid | 46.6±2.4 | 57.9±1.1 | 3.3±1.1 ZS† |
| 3B GiGPO | high | 53.4±1.0 | 60.2±0.6 | 13.9±0.7 ZS† |
| 7B GRPO | low | 39.2±1.7 | 58.3±2.0 | 33.1±0.2 |
| 7B GRPO | mid | 42.7±1.0 | 53.3±1.9 | 36.1±0.0 |
| 7B GRPO | high | 71.5±1.6 | 77.1±0.4 | 50.6±1.2 |
| 7B GiGPO | low | 54.4±2.4 | 55.7±0.2 | 28.8±0.4 |
| 7B GiGPO | mid | 55.2±0.8 | 60.0±0.6 | 38.8±0.6 |
| 7B GiGPO | high | 66.9±0.8 | 75.4±1.3 | 73.4±2.9 |

Table 15 的失败注适用于3B h-low两算法；Table 16 的失败注适用于全部3B配置。原因只写训练未起效，没有足够日志判断是稀疏成功、全部组零方差、优化不稳定还是别的机制。奖励中还存在invalid惩罚，不能仅凭终局全失败推断“必然完全无梯度”。

#### 6.6.1 论文强调的 hard→其他任务迁移

7B只训练Pick 2时，GRPO的All从33.1到50.6（+17.5 pp）；GiGPO从28.8到73.4（+44.6 pp）。这两个增量是**混合ID/OOD的All**。为了看清迁移，下面保留GiGPO完整类别均值；原Table16给标准差，表中同时带出：[Fig.7，p.8；Table 16，p.22][P8]

| 7B GiGPO，train hard | Pick，OOD | Look，OOD | Clean，OOD | Heat，OOD | Cool，OOD | Pick 2，ID |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| h-low | 41.2±1.0 | 17.2±4.9 | 15.5±0.0 | 3.4±1.5 | 0.0±0.0 | 95.1±0.0 |
| h-mid | 81.4±1.7 | 31.2±1.9 | 7.5±1.0 | 18.8±3.9 | 5.8±1.3 | 83.7±3.7 |
| h-high | 95.5±1.0 | 93.5±3.2 | 54.0±7.0 | 56.4±4.4 | 51.4±5.5 | 94.3±3.7 |

h-low已在ID的Pick 2达到95.1，却在Cool为0；h-high的Pick 2为94.3，Cool为51.4。这比只给+44.6更能说明“训练类别表现好，不保证其他任务可用”。也不应写“所有类别都因h-high提升”：这里ID均值略降，Clean的mid还低于low。

另一个作者强调的GRPO Heat例子是h-low0.9→h-high29.1。但相同h-high的7B zero-shot Heat为35.9（Table10）：**比低信息训练更好，与比同harness的未训练模型更好，是两种比较。** 此例后者并不成立，不能把所有harness差值都称为权重带来的正迁移。

#### 6.6.2 Easy、med 结果和算法排序不能省略

7B GRPO只在med训练时，h-low All为58.3，h-mid为53.3，h-high为77.1；low→mid不是单调增益。3B h-high只在easy训练时，GRPO63.1高于GiGPO53.4；只在med训练时，GRPO69.7也高于GiGPO60.2。因此§4.2的GiGPO同分布整体优势不能扩展成所有任务迁移条件下都占优。

类别之间的迁移也不一致。例如7B只在easy上用GiGPO训练，h-mid的Pick 2为61.0±2.4，h-high为38.2±3.7，而后者的All更高。这正说明雷达图或类别表比一个混合All数更适合判断训练方向。[Tables 14–15，p.22][P22]

Fig.7的每个轴是一个任务类别、刻度为成功率；上排训练med，下排训练hard，加粗轴为训练类别。它不是随时间上升的训练曲线，也不是训练任务数的扩展曲线。主图覆盖7B的med/hard，easy与3B结果在附录，不能只看雷达图就省略那些失败配置。

## 7. 作者的相关工作与限制：没有被本篇实验覆盖的东西

Appendix A.1 讨论专家SFT、自采轨迹学习、implicit world modeling、self-reflection、RL反馈token masking及多轮优化；A.2讨论人工harness和Meta-Harness式搜索；A.3讨论ToolQA-D/ToolEVO、ProEvolve等动态工具环境。它们用于定位本文，而不是本文新增了对应训练阶段。本轮没有全文复读这些被引论文，也不把相关工作中的“RL-only泛化更强”等外部结论算入本实验的证据。[Appendix A，pp.12–13][P12]

作者承认仅在ALFWorld验证，开放模型只有3B/7B，算法只有GRPO/GiGPO，harness只有三个人工档位；更多环境、更广模型和算法，以及联合优化harness与LLM是后续方向。它们限制了结论外推到真实coding/terminal、大MoE、带权限或故障的服务环境。[Limitations，p.9][P9]

本文对“训练时就位”有实际权重更新与匹配测试的证据；对“接口信息不变性训练”没有直接证据，因为**从未训练一个在多harness之间随机切换的策略**。同样，三个档位是人工设计，不是自动获得；作者强调信息获取成本，却没有测其成本—成功率Pareto曲线。

<a id="limits"></a>
## 8. 成本、开放资产与复现程度

| 项目 | 原文／本轮能确认的内容 | 不能推出的内容 |
| --- | --- | --- |
| 训练硬件 | Appendix C写4×H200 | 八张RTX PRO6000的时间、显存和吞吐 |
| 总GPU预算 | §4.1与Limitations写约1,800 H200 GPU-hours | 每个run都是1,800小时；按48或144机械平分即可得到真实单run成本 |
| 数据／环境设计成本 | 作者说明丰富harness需人工先验或探索 | 人时、API费用、CPU/容器成本；没有定量表 |
| GPT评测 | high、4,096输出上限、一个seed | API价格、总token和完整费用 |
| 吞吐／时延 | 无独立系统性能消融 | 本文证明了某种async、cache或packing加速 |
| 可访问论文 | v1 PDF文本、HTML、主图图页及附录模板/表值 | 原文所有尾页图像已检查、实验已复现 |
| 专用实现与权重 | 本轮未在原文、arXiv入口或精确标题检索中找到作者关联的可核查地址 | 断言没有代码；把ALFWorld/GiGPO原仓库当成本篇完整实现 |

本文公开了很多**规范层细节**，例如模板、名称映射、参数映射和目标函数；这些使小规模复现设计成为可能，但不等于全部资产足够一键复跑。仍缺扩展`TE`实现、真实state identifier、版本化题单、checkpoint、运行日志和完整参数。模型/环境/第三方库各自许可也不能由论文CC BY许可自动覆盖。

本轮没有GPU训练、ALFWorld执行或独立重复结果，因此证据仅是作者报告的训练/对照及本次原文核查。没有声明独立复现。

## 9. 最影响后续使用的披露缺口和源文差异

| 项目 | 具体问题 | 本稿处理 |
| --- | --- | --- |
| 配置计数 | 旧稿写总24；原文24/model | 更正为48种名义配置，不猜实际job数 |
| Training段范围 | 参数段字面写GRPO，但全篇有GiGPO结果 | 参数原样记录，GiGPO逐配置设置未完全披露 |
| Batch单位 | 16×8=128 episodes 与PPO minibatch256的关系不明 | 保留两值，不擅改、不猜turn展开规则 |
| 状态分组 | GiGPO的h是语义等价定义，无具体实现 | 不推定拿完整隐状态、字符串或LLM做判断 |
| Reward与终止 | invalid惩罚是否覆盖inadmissible、截断/补采/mask未知 | 不从其他RL框架继承约定 |
| 成本匹配 | 信息更多可能多读token，也可能少调用Inventory | 无实际token/时间记录，不能称严格等计算收益 |
| 单调主张 | 正文部分措辞强于若干表中结果 | 同时保存总体趋势和具体反例，不抹去作者原结论 |
| Fig.6分母 | 正文“of these calls”与堆叠图类别分母不一致 | 沿图列全调用类别，明确原文歧义 |
| Table13误差 | C说表中均有std，Table13却只有mean | 不造SD或统计显著性 |
| Task-shift All | 包含ID类别 | 不把+17.5/+44.6直接称纯OOD增益 |
| 训练失败占位 | 部分3B行是改报zero-shot | 明标ZS†，不当作已训练结果 |
| 未披露 vs 未取得 | 本轮缺TeX/PDF尾页图像，不等于原文没写 | 公式和Table9–16文本已读，图页复核单列待补 |

关键缺项不是为了填满一份工程审计表：它们直接决定“谁在训练”“哪些样本被比较”“分数提高是否来自权重”和“本篇配置能否移植”。其他与本篇无关的完整安全、权限或分布式系统机制不再逐项扩审。

<a id="project"></a>
## 10. 对 RepoHarness 项目一的条件化意义与旧稿修正

映射日期 **2026-09-08**，依据固定基线下的 [CURRENT-STATE-BRIEF](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)。该简报是2026-09-05快照：miles/SGLang承担训练与推理，Claude Code通过现有adapter执行，rh2负责可信环境、评分和训练消费；正式GPU资格与部分首训选择仍开放。本轮不做rh2代码审计，不把这个快照当作最新训练成果。

### 10.1 本篇新增的证据，以及没有新增的证据

它新增的是**目标harness训练时机与权重更新的受控对照**，以及格式错误／状态不可执行／终局失败的不同响应。它不证明接入更多harness本身有增益，也不证明我们需要新建canonical IR、自动harness生成器、GiGPO后端或通用状态平台。

它会削弱两种提前定案：一是“先在简化环境训练，再套真实harness即可无损获益”；二是“只要加多harness随机化，就能学到接口不变性”。前者在这篇有限设置中有反证，后者本篇没有实验。二者都应回到我们的实际harness与任务做测试。

### 10.2 只保留两个小型、可辨识的候选实验

| 候选 | 来源依据 | RepoHarness的最小增量与前提 | 需要看什么 |
| --- | --- | --- | --- |
| 目标harness是否需要训练时就位 | Fig.4、Tables11–12 | 在现有可训练主harness与一个受控简化版本之间设计2×2训练/测试；先确认任务功能和评分不变。复用上游训练，不另建多harness平台 | 相同测试harness下的checkpoint差异；同时记录token、turn、wall time，不能只比较两个不同系统的最高分 |
| 协议迁移与信息供给分开诊断 | Tables1/6/7/9、Figs5–6 | 先无训练做等功能schema改写；把额外状态/错误诊断作为另一项干预。对合法调用用最小回放检查parser，避免测到adapter bug | 格式合法率、状态可执行率、终局通过率三层；base与trained都测，新旧工具文档完整提供 |

如果强提示／adapter修复已经消除了差距，不应再为了采用本论文而启动新训练。若真实部署harness能够提供有价值的状态信息，优先考虑让训练接触该信息，但不从ALFWorld点数估算SWE收益。h-high的构造依赖环境知识，不能把hidden grader或答案偷渡成“状态提示”。

**简历叙事可用的仍须是我方实测**：例如发现一个真实训用接口差距、用受控对照定位原因、在有限成本下改善最终执行。本文可支撑实验设计的必要性，不能替代该结果，更不要求把项目一改为“跨harness不变性”研究。

### 10.3 旧摘要应如何理解

旧稿保留为历史线索，本轮不修改。新稿纠正／收紧如下：总24→每模型24、合计48；“3/4/5/8步”→最少子目标数；“五工具聚合”→13个原操作工具入口聚合成5个；+44.6→包含ID的All增量；34.9%的分母沿Fig.6处理；任意harness变化默认重训→只将训练时就位作为本篇支持的有限候选。旧稿未包含的非单调例外和3B训练失败占位，已进入§6正文。

## 11. 快速查找与关联阅读

| 需要回答的问题 | 本稿 | 原文定位 |
| --- | --- | --- |
| harness到底增加了什么？ | §3.2 | Table1 p.4，Tables5–6 pp.14–15 |
| v2.0是多步宏动作吗？ | §3.3 | §3.3 pp.4–5，Tables7–9 pp.16–17 |
| 配置数、split与预算 | §3.4、§4 | §4.1 p.5，Limitations p.9，C p.19 |
| GRPO分母、GiGPO状态分组 | §5 | Appendix C pp.18–19 |
| 训练时就位比post-hoc高多少？ | §6.3 | Fig.4 p.7，Tables11–12 p.20 |
| 哪些结果不随harness信息量单调？ | §6.2、§6.4、§6.6 | Tables11、13、14–16 pp.20–22 |
| 95.7%、34.9%与成功率的关系 | §6.5 | §4.4与Fig.6 p.7 |
| task-shift是否纯OOD？3B行是真的训练吗？ | §6.6 | Tables14–16 p.22，Fig.7 p.8 |

已存在的关联入口：[SkyRL-Agent](O01_skyrl_agent_sa_swe.md) 用于对照工具增强和训练消费，不将其horizon规则填入本文；[Qwen3-Coder-Next](R3_qwen3_coder_next.md) 可与本文比较工具格式多样性问题。本轮未重读它们的原文，不额外复述其结果。Polar及其他并行笔记交由汇总线程建立交叉比较，不在此创建未知文件链接。

## 12. 交付与自查状态

**正文及附录文本精读完成、作者自查完成；主图视觉核验完成，PDF尾页图表／公式视觉核验有明确剩余项；未独立审查，未复现训练。** 自查记录见 [reviews/E1_self_check_20260908.md](reviews/E1_self_check_20260908.md)。

本线程只新增E1正文及其自查，README、来源目录、批次总状态交由汇总线程维护。没有修改旧摘要、其他阅读笔记或训练实现。源文事实、作者解释、算术推导与项目建议在对应位置区分，不以笔记提交表示项目方案已经获批。

## 官方来源

[P-abs]: https://arxiv.org/abs/2606.25447
[P]: https://arxiv.org/pdf/2606.25447v1
[H]: https://arxiv.org/html/2606.25447v1
[LICENSE]: https://creativecommons.org/licenses/by/4.0/
[P2]: https://arxiv.org/pdf/2606.25447v1#page=2
[P3]: https://arxiv.org/pdf/2606.25447v1#page=3
[P4]: https://arxiv.org/pdf/2606.25447v1#page=4
[P5]: https://arxiv.org/pdf/2606.25447v1#page=5
[P6]: https://arxiv.org/pdf/2606.25447v1#page=6
[P7]: https://arxiv.org/pdf/2606.25447v1#page=7
[P8]: https://arxiv.org/pdf/2606.25447v1#page=8
[P9]: https://arxiv.org/pdf/2606.25447v1#page=9
[P12]: https://arxiv.org/pdf/2606.25447v1#page=12
[P14]: https://arxiv.org/pdf/2606.25447v1#page=14
[P16]: https://arxiv.org/pdf/2606.25447v1#page=16
[P17]: https://arxiv.org/pdf/2606.25447v1#page=17
[P18]: https://arxiv.org/pdf/2606.25447v1#page=18
[P19]: https://arxiv.org/pdf/2606.25447v1#page=19
[P20]: https://arxiv.org/pdf/2606.25447v1#page=20
[P21]: https://arxiv.org/pdf/2606.25447v1#page=21
[P22]: https://arxiv.org/pdf/2606.25447v1#page=22
