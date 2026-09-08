# B 主线：八篇环境来源的完整阅读与证据整合

日期：2026-09-08。材料固定于 RepoHarness `ac0e2e64163fbe49411540e901df439aea16b6b0` 的只读快照。以下是**现有精读笔记的二手证据整合**；本轮没有重新精读原论文、核验远端代码或运行环境/训练。原始链接用于追溯，不表示本轮完成一手核验。

任务前提是有限八卡上的真实 coding/SWE agent RL；B 负责数据、环境、评测与基座诊断，A 负责运行时和训练消费。现有 216 题 SWE-Gym 是候选，不能据数量称为已验收训练集。本稿不确定正式题单，不批准课程、reward 或训练语义变化。

## 1. 实际覆盖与证据等级

逐行完整读完八份成稿和八份对应审查/自查，共 **3,830 行**。范围包含来源、方法、训练、全部结果与负结果、资产、成本、未知项、项目映射及修订记录，没有只摘项目相关小节。表中“原文覆盖”是**笔记作者的记录**，不是本轮重新完成的阅读。

| 成稿及完整行范围 | 审查/自查完整行范围 | 笔记记录的原文覆盖与可信度边界 |
| --- | --- | --- |
| [E2 CalibForge][E2]：1–399 | [独立审查][E2R]：1–111 | 正文及 A–F；独立审查后四项修订落地，原文计数疑点仍在 |
| [E3 Envs-FORGE][E3]：1–158 | [作者自查][E3R]：1–57 | **仅摘要来源对账及关联代码检查；原论文全文待补** |
| [E5 SWE-smith][E5]：1–343 | [独立审查][E5R]：1–74 | 正文及 A–G，含难度分类器、弱迁移与干预负结果；定点修订完成 |
| [O03 R2E-Gym][O03]：1–341 | [独立审查][O03R]：1–110 | 正文及 A–E；三条 SFT、推理排序、负案例；六项修订已复核 |
| [O11 SWE-rebench V2][O11]：1–467 | [作者自查][O11R]：1–82 | 正文及 A–C 文本；Table 8 的一致 v2 图页待补，未独立审查 |
| [Nemotron-Terminal][NT]：1–466 | [作者自查][NTR]：1–73 | 正文及 A.1–A.3、全部领域提示词和消融；未独立审查 |
| [E8 ECHO][E8]：1–454 | [作者自查][E8R]：1–86 | 正文及 A–D、目标分母和实现路径；未独立审查 |
| [R11 RollArt][R11]：1–527 | [作者自查][R11R]：1–82 | v2 全文，无技术附录；v1 仅定点比较，未独立审查 |

## 2. 各来源对 B 有什么用，不能推出什么

**E2：有效环境之后，还需测指定求解器的学习机会。** 构建、自解通过后，首次强弱探测仅 19% 落在作者指定关系，61% 两者都过；修订可以改题意、环境或测试。合法整体加密被逐字段布局测试误杀的案例，直接提示检查替代解。四臂各 1,300 题的 SFT 分数为 22.47/24.34/29.21/31.09%，支持外部反馈校准值得比较，但不是等生成成本、等训练 token 实验。外部强过弱败也不是本项目模型通过率。最多 50 轮不含无显式上限的验证修复；不能拿 96% 最终接受率证明低成本。公开 5,431 题可作资产线索，镜像可用性仍需实跑。审查保留 19%/15% 与早停关系、评分有效分母、batch 和轨迹发布位置缺口。（笔记 §4、§7–9，L75–145、257–339；[原文 v1](https://arxiv.org/abs/2608.06352v1)）

**E3：目前只能支撑“导出结构完整不等于执行验证成功”。** 摘要的 100 个验证环境与历史 1,824 口径尚未对账；六动作、MILP、RL 配方均不能用旧摘要补齐。所读关联示例将文件存在且非空记为 `accepted`，Harbor smoke 另跑且不回写主导出，模板消息也不是实际求解轨迹。因此可保留合成前选改写方向的研究问题，不能列为已核实的动态课程方案或现成 gold-verified 生产线。优先缺口是拿到同版本全文并恢复实验身份，其次才核关联分支是否对应论文。（§1–5，L3–138；[来源入口](https://arxiv.org/abs/2608.14312)）

**E5：固定可执行仓库后注入 bug，有望摊薄安装成本。** 100,074 候选成为 50,137 任务，但只在 8,686 唯一题上采集，最终 SFT 为 5,016 轨迹；不要把任务、尝试与训练样本混算。`patch` 是引入 bug 的方向，反向才是参考解。原论文 F2P 测试可见，且承认未系统检查题面泄漏/欠明确，不宜直接作正式评测。等 700 轨迹的多仓对照支持多样性；难度上升使专家成功率 58.6%→17.0%，等 500 轨迹的收益却不单调。$1,360 仅局部构建 API 成本，不能据此给合成路线最低价排名。需核当前任务分支、测试恢复/评分语义、血缘与完整成本；后发 SkyRL 接线不是论文 RL 收益。（§2–7，L40–67、164–221、245–266；[原文 v2](https://arxiv.org/abs/2504.21798v2)）

**O03：真实修复 commit 加测试与反译题面，是另一条生产路线。** 4,578 题去测试仓库重叠子集仍偏集中，历史依赖恢复明确半人工。生产测试生成可见 gold，求解模型不应继承该特权。三种模型均 SFT；32B 单候选 34.4%，51% 是 26 个编辑候选后的混合选择，另有测试 agent 与 verifier 成本。生成测试可能无区分或偏爱错误补丁，说明“有测试”不能代替错误解/替代解审计。优先复用小批环境可避免先重建半人工工厂，但必须核数据版本、镜像中的修复提交/历史、期望状态映射及评分解析。笔记提到的双空映射等只是当前代码条件性风险，不能当论文已误奖。（§2–7，L43–74、173–216、225–269；[原文 v1](https://arxiv.org/abs/2504.07164v1)）

**O11：真实 PR 资产应分交付等级，并显式计算低产率。** 32,079 主集带镜像；126,300 PR 派生条目置信度较低，不能承接主集全部保证。583,809 候选到最终主集约 5.49%；26,400 build job-hours、26.36 TiB 与约 $1.9K setup 推理是不同成本。双态全套件、补丁后 rebuild、三次稳定测试和逐测试 ID 解析均有可借鉴性。A/B 标签只作诊断；B1 可能是合法回归要求，A 也不是目标策略可学证明。509 题 PR 题面审计中 117 有某种泄漏，其中 12 为明确解答泄漏，不能泛化全库比例。复用前需核缺失预测回退 gold、严格 passed 列表匹配、字段/镜像接口差异；作者自查未构成独立复查，更无 RL 训练消融。（§3–11，L90–149、199–236、332–413；[原文 v2](https://arxiv.org/abs/2602.23866v2)）

**Nemotron-Terminal：SFT 行为资产与可评分 RL 环境必须分开。** Adapter 无 tests；synthetic 明确不生成 oracle，SWE suffix 也未还原完整原仓库。九个领域基础镜像只复用不可变环境，不免除每题隔离成本。公开 366,154 行对应 adapter+skill，论文 490,520 样本另含未释放的 seed 部分。No-filter 12.4% 高于 success-only 5.06%，同时样本数为其 3.17 倍；与 E5 的成功过滤优势不能拼成普适规则。简单混合 13.03% 胜过一种两阶段 SFT 的 10.39%，支持先保留简单基线，未证明动态 RL 课程无效。先核可测试任务包和目标接口；32B 的 128 GPU 配置没有八卡成本承诺。（§3、§7–9，L75–150、298–398；[原文 v1](https://arxiv.org/abs/2602.21193v1)）

**E8：有 RL 学习证据，但其主要贡献不是环境生成。** GPT-5 至多 16 次尝试至少一次成功，只证明该筛选设置下可解，不估计本项目策略的组内成功分布。2,700 既有题加 6,170 合成题的完整资产尚未在笔记查阅范围定位。辅助观测 CE 在 8B/14B 提升，但专家 SFT 起点 TB2 pass@1 仅 +0.23 个百分点，pass@3 下降；无 reward 的追加适应在 TBLite 下降 3.9 个百分点。B 可借它判断反馈是否与动作后果相关、是否值得训练；不能据预测 CE 下降批准 terminal 主训练或取消 verifier。数据分割、目标文本来源、训练/附录/代码差异先核，目标 mask 与归一化归 A 的后续设计边界。（§2–9，L135–148、199–225、296–313、320–394；[原文 v1](https://arxiv.org/abs/2605.24517v1)）

**R11：环境供给效率应与学习质量一起测。** 正常 SWE probe 的 generation 占 53.8%，故障时瓶颈转向 reset；生产 fully async 作业仍可能在 `get_batch` 等待。优先测启动、工具、评分的关键路径和尾部，比预设“GPU 推理最慢”有依据。放宽 staleness 可缩短 step，却延后达到目标分数；冗余择快可能改变消费分布，论文未给独立学习对照。主实验 128 GPU、异构硬件与外部 serverless 不能外推同构八卡；PD 的 30B-A3B 实验也是 32 卡，3P1D 最差。B 可提供环境供给、失败和缓存数据，通用调度/陈旧度由 A 和上游承担；缺任务 manifest 和完整费用，不能用于数据源质量排名。（§3、§6–12，L99–126、251–321、344–410、467–480；[原文 v2](https://arxiv.org/abs/2512.22560v2)）

## 3. 这些证据支持的先后顺序

1. **先确定小批任务能否可靠运行和评分。** 从 216 候选及可取得的外部现成资产做有范围的复用核查；记录来源/版本、no-op、参考修复、重复 reset/评分、代表性错误解与合法替代解、评分材料可见性。现成资产是减少前期生产未知量的默认起点，不是实验前的质量冠军。每阶段分别记候选、可信任务、尝试和实际消费量。
2. **再做固定基座、harness 和预算的诊断。** 不用外部强弱模型、人工修复分钟或 A/B 标签代替当前策略采样。重复测通过率、完成率、交互长度、超时、格式/环境/评分失败及成本；将 SWE 与少量 terminal 探针分开报告。先辨认失败来自工具接口、仓库知识、任务说明、评分或执行资源，再决定是否需要预热、补题或预算调整。
3. **缺口被测出后，才比较新增供应路线。** 缺仓库/真实修复覆盖时比较真实 PR/commit；稳定环境中缺某类 bug 时比较固定版本合成；缺指定终端技能时比较现成 terminal 或小规模技能合成。三者要比较同一目标下的新增可信任务、有效训练 token、API/CPU/GPU/存储/人时及独立学习收益，不能仅按候选单价或论文 headline 排序。
4. **先有静态采样/简单混合与独立评测，再论证校准或课程。** 保持源仓库、原始 PR/bug 及派生族边界，避免用最终测试来修题或选策略。只有固定预算的训练对照出现可重复差异，才能把“通过率不同”升级为“学习价值不同”；E2 的外部校准、O11 的标签建议、Nemotron 的阶段负结果都不足以单独批准动态课程。

目前证据支持 **SWE 维持项目主线，terminal 先作为有明确问题的小规模诊断或迁移候选**；这是基于当前范围和证据缺口的工作顺序，不是 terminal 价值较低的统一结论。是否把 terminal 升为第二训练域，需要先证明任务/评分可复用、目标模型存在学习空间、收益超过新增环境和评测成本。尚未完成的原文回查与运行核验已在逐篇段落列明；本轮完整读完笔记不关闭这些缺口。

[E2]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md
[E2R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/04_E2_review.md
[E3]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/E3_envs_forge.md
[E3R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/E3_envs_forge_self_check_20260907.md
[E5]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/E5_swe_smith.md
[E5R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/11_E5_review.md
[O03]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/O03_r2e_gym.md
[O03R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/12_O03_review.md
[O11]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/O11_swe_rebench_v2.md
[O11R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/O11_self_check_20260907.md
[NT]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/nemotron_terminal_data_engineering_2602.21193.md
[NTR]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/nemotron_terminal_self_check_20260907.md
[E8]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/E8_echo.md
[E8R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/E8_echo_self_check_20260907.md
[R11]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/R11_rollart.md
[R11R]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/R11_rollart_v2_self_check_20260907.md
