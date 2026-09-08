# 项目一 B：评测目标、真实 harness 诊断与反馈证据

日期：2026-09-08。材料固定于 RepoHarness 提交 `ac0e2e64163fbe49411540e901df439aea16b6b0`；以下 9 份笔记与 8 份自查／审查记录共 3,999 行已分块完整阅读，并逐字节核对该提交。本文整合已有精读材料，未重新读取全部原论文、运行上游代码、复现评测或开展训练。引用行号均属于这一固定版本。

B 需要回答的是：约 30B-A3B 候选在真实 Claude Code 中能否完成目标 SWE 工作；任务是否提供了公平、有效的学习信号；训练后的改善是否出现在独立任务上。miles/SGLang 的 runtime 与 learner 语义由 A 负责。八张 96GB 卡是资源约束，不能用旗舰模型成绩或其他硬件的加速比替代本地成本测量。本报告提供后续决策的比较结构，未选最终 benchmark、题单、正式预算或新训练算法。

## 1. 九篇分别提供了什么证据

### N06：防作弊必须与合法解保持一起评价

完整阅读 `N06_hardening_agent_benchmarks.md`。固定 API 模型分别做 hacker、fixer、solver，改的是 verifier／环境，没有 SFT 或 RL 权重更新。KernelBench 的主要外部结果只针对 task001：原循环能把攻击与良性通过率同时降到 0%；headline 的良性 92–98% 依赖额外 autopatch。Terminal Bench 的 77 题上，无提示攻击通过率 39.2%→16.7%，良性通过率也由 76.1%→65.2%。因此，gold 能过只证明至少存在一个可接受解；单一 reference 漏掉合法实现风格，会让“安全加固”实际缩小求解空间。

跨强模型、外部攻击提示和共享防御分别测试不同迁移对象，不等于未见任务族泛化；autopatch 用过失败良性样本，最终良性评测的开发隔离仍不充分。论文的同容器威胁模型也须与 rh2 的 fresh grader 实际边界比较。约 5,000 美元为 API 费用估计，不能移作本项目训练预算。[笔记 §3–7、§10，L87–336、L414–430][N06]；[原论文](https://arxiv.org/pdf/2606.08960v1)。

### N13a：测试失败可能来自任务契约不成立

完整阅读 `N13a_swe_verified_audit.md`。Verified 审计中的 59.4% 分母是依据 o3 运行表现挑出的 138 题，不能推广成全部 500 题坏题率。`pylint-4551` 隐藏测试强制未规定的 helper 名；`sympy-18199` 的 PR 合并了多个问题，评分范围超过单题描述。污染探针恢复修复细节支持暴露风险，却没有全量训练数据或去污染对照，不能计算某模型多少分来自记忆。

这篇没有后训练方法实证。对 B 的直接要求是：区分环境完整性与题意—测试一致性，并将本项目内部划分与基座历史污染分开。内部 held-out 不会抹去模型可能已经见过的公开 PR。[笔记 §3–7、§8，L36–133][N13a]；[原文](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)。

### N13b：成功任务也必须检查需求覆盖

完整阅读 `N13b_coding_eval_signal_noise.md`。731 道 Pro 公开题初筛出 286 道，两条深入审查分支分别认定 200／249 道有问题；不是随机抽样，也不是先 200 再扩成 249。两分支共用初筛，未标记题的漏检率未知。六个案例覆盖题意冲突、过严测试、未说明要求和低覆盖；低覆盖允许不完整修复通过，与主动作弊不是同一标签。

独立人审应先看题意、仓库惯例、测试与 gold，再看 agent 摘要；成功／失败、被标记／未标记均需抽查。这篇同样没有 SFT/RL 配方。OpenAI 2 月曾建议 Pro，7 月已撤回；这条时间线不能压成“当前推荐 Pro”，也不证明它对所有模型和用途都无效。[笔记 §3–7，L37–141][N13b]；[原文](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)。

### E1：训练时接触目标 harness 有受控证据

完整阅读 `E1_harness_interplay_posttraining.md`。ALFWorld 中两只 Qwen2.5 Instruct 模型分别做 GRPO／GiGPO，共 48 种名义配置。三档 harness 改变工具知识和状态信息；schema 改名／聚合是另一变量。八个相同测试 harness 对照中，训练时即采用目标 harness 均优于训练后才换；7B GRPO 在低信息配置训练后，强 schema 变化使成功率 55.6%→2.7%。因此需先查工具协议、可执行状态和终局成功，不能只看总分。

这是单环境实证，没有新增 SFT，也没有多 harness 随机化训练。3B 部分困难配置训练未起效，丰富信息和 GiGPO 都非逐格最优；task-shift 的 `All` 混合 ID/OOD。约 1,800 H200 GPU-hours 是整体研究口径，不能换算本项目单次实验。B 可借鉴分离“等功能接口改写”和“增加合法信息”，不能把隐藏评分信息包装成状态提示。[笔记 §3–4、§6、§8，L72–208、L261–428][E1]；[原论文](https://arxiv.org/pdf/2606.25447v1)。

### R0 Polar：真实 harness 适应与数据生成应分开认领

完整阅读 `R0_polar.md`。Qwen3.5-4B 在 293 道 SWE-Gym 题上分别用四个原生 harness 做 RL；Claude Code 的 Verified 为 29.8%→34.6%，Codex 为 3.8%→26.4%。基座起点本就相差很大，四行没有完整交叉测试、精确统一预算或重复种子，不能据此直接给 harness 排名，更不能称混训泛化。

另一条 122B 分支生成 504 条通过 F2P/P2P 的轨迹，未训练验证下游 SFT；90/10 按仓库分层，使各仓库同时在两边，不是未见仓库评测。其 64 GPU-hours 属离线生成；5.39× 属三个训练步的表示方式对照，均不是四个 RL run 的总成本。逐请求广播终局 reward 还观察到 reward hacking，说明捕获完整调用不等于奖励归属正确；相关训练消费问题交 A 验证。[笔记 §5–7，L158–294][R0]；[原论文](https://arxiv.org/pdf/2605.24220v1)。

### R5b：旗舰协议脚注比单一最高分更有用

完整阅读 `R5b_glm5_2_blog.md`。文章报告 critic-PPO、单 rollout、压缩子轨迹、十余专家并行 OPD，以及规则筛查→LLM 判意图→阻断调用→返回替代观察→继续执行。继续执行不证明违规 token 保留梯度；没有 guard-off 对照，不能把在线拦截效果认成权重学会诚实。两天只指所述 OPD 阶段，未计专家生产或给出卡数。

19 项评测混合答案准确率、任务成绩与 dominance。TB2.1 的 Terminus-2 有 4 小时限制，Claude Code 配置取消墙钟限制、输出上限与采样也不同，81.0／82.7 不是纯 harness 消融。数据划分、污染和合法解检查缺少披露，跨官方页面还有数值差异。B 应记录实际预算、网络、资源、judge、重试和 history 配置，不能以“支持 1M”概括全部评测。[笔记 §4–9，L113–324][R5b]；[官方正文](https://huggingface.co/blog/zai-org/glm-52-blog)。

### R5c：只可作为明确标记的预读线索

完整阅读 `R5c_glm5_3_blog.md` 的预读记录，**官方博客全文仍未取得，不能计作原文精读完成**。固定官方 README 支持“普通 5.3 沿用 5.2 的 base、改善来自后训练”的发布主张，不能推出从公开最终 checkpoint 直接续训；普通版与 Flash 也不可混用。`reasoning_effort`、`clear_thinking` 提醒 B 记录推理条件，但环境审核、训练配方、完整评测、`1e-7` 和 `>2.3×` 仍未回博客核验，不纳入承重结论。[预读 §1–5，L8–95][R5c]；[待补原博客](https://z.ai/blog/glm-5.3)。

### Agent Lightning v1.0：筛选配方与训练收益有实证，泛化范围有限

完整阅读 `agent_lightning_v1_2608.17528.md`。三个独立案例覆盖搜索、通用指令与 coding；coding 是 Qwen3.5-9B＋mini-SWE-agent，无新增专项 SFT。SWE-smith 先排空描述／缺分支／高测试负担，再每题四次校准，保留约 5K 成败混合题与 1K 的 0/4 难题；最终约 6K train／400 test。中间分母、仓库切分与筛选消融不完整，不能断言中等通过率优于静态抽样。

三臂内部验证峰值为 35.0／33.1／38.2：只改 rollout 级优势不如基线，优势与 loss 归一化同时调整才最好。外部 41.8%→56.4% 属 step208 的另一次 Verified 评测，并非上述峰值或未见 harness。Git／网络获取答案的实际观察支持隔离必要性，但缺合法解保持和攻击率对照；本轮原图未核，不补编熵曲线或 2× 加速的细节。[笔记 §6–10，L206–399][AL]；[原论文](https://arxiv.org/abs/2608.17528)。

### N07 SDPO：丰富反馈有用，不能用同题适应冒充 SWE 泛化

完整阅读 `N07_sdpo.md`。自教师在反馈条件下重算原回答的概率，常规步骤无需另生成教师修复答案，仍需额外 forward 和教师状态。科学／工具实验按题划分；coding 的 131 道 LCBv6 题则反复训练，按 tests 验证，当前配套代码的验证还保留完整 tests。48.8% 对 GRPO 41.2% 是这一协议内收益；不是未见题、更不是真实 Claude Code 仓库修复实证。

反馈组合、信用粒度、教师正则和 SFT 对照均有实验：无正则自教师会发散，增加完整失败回答可能强化错误锚定，弱模型收益有限；能力保持均值仍由 43.5 降至 42.4。TTT 的 19 道难题还经过事后可解性筛选。B 应先用允许公开的诊断测试模型是否能利用反馈，再比较修复轨迹 SFT、GRPO 与反馈目标；private grader 输出不能自动成为训练提示。generation 效率不等于 GPU 或总费用效率。[笔记 §5–8、§10.1、§12，L180–461、L507–511、L575–591][N07]；[原论文](https://arxiv.org/pdf/2601.20802v2)。

## 2. 决定任务与评测时，应并列比较的选项

下表是待决结构，各行可以组合；先明确要支持的结论，再选择数据和执行条件。

| 决策轴 | 应比较的选项 | 取舍与所需证据 |
| --- | --- | --- |
| 能力目标 | 仓库 issue 修复；受控合成 bug；终端／性能类补充 | 明确真实工作、可观察结果及工具要求；终端或代码生成成绩不替代 SWE 主目标 |
| 独立性 | 同仓库未见任务；按 PR／派生 bug 家族隔离；未见仓库；公共外部坐标 | 前者偏域内，后者分布更远且成本可能更高；记录共同祖先、重复 patch 和题意，不能只随机切轨迹 |
| 难度选择 | 模型无关分层；独立校准后按难度分层；保留困难覆盖的混合 | 区分任务无效与当前模型未解决；报告被删除的仓库、长度、机制和资源分布，避免按测试表现反复挑题 |
| Harness 比较 | 原生 Claude Code 固定配置；等功能 schema 扰动；另一原生 harness | 额外状态／提示单列干预；先做固定权重诊断，再判断是否需要训练；跨 harness 要有交叉矩阵 |
| Grader 质量 | 原 F2P/P2P；离线语义审查；有界攻击—修补—良性回归 | 同测 gold、no-op、错误／不完整解、多种合法解；修补开发样本与最终正常解复核分开 |
| 学习路线 | 提示／接线修正；成功或修复轨迹 SFT；既定 RL 候选；丰富反馈目标 | 用真实失败分布决定；比较数据生产、teacher、训练成本与独立任务收益，不能按方法名加组件 |
| 预算口径 | 固定每次尝试上限；固定总计算预算；能力—成本曲线 | 同时记 token、turn、wall-clock、CPU/GPU、评分、重试；更长预算的最高分不能直接归因权重 |

开发集用于诊断与选配置，最终 held-out 用于回答事先声明的问题。公共 benchmark 可作为外部坐标，须同时说明污染与任务质量限制；将公开题纳入 held-out 只保证本项目未主动训练这些题。失败排除规则应依据任务有效性，不能因某个 checkpoint 做不出就删题。上述安排是项目设计建议，不是九篇共同执行过的协议。

## 3. B 的基座真实 harness 诊断顺序

先冻结候选权重、tokenizer／模板、Claude Code 和 adapter 版本、工具面、thinking／history、context／输出、超时／网络及 grader 配置。A 提供真实调用运输与训练身份的验证证据；B 在可审计任务上检查模型如何使用它们。避免把静态配置存在写成真实执行成功。

第一步做最小工具回放与少量真实任务：分别统计请求／解析失败、工具名参数错误、格式合法但状态不可执行、环境／资源失败、评分异常和有效解题失败。E1 表明这些层次能随接口变化大幅移动；Polar 表明原生 harness 起点必须实测。若修正 prompt 或 adapter 即恢复能力，应先完成该诊断，再讨论权重学习。

第二步核任务契约：gold 与 no-op 是入口检查，随后检查满足题意的替代实现是否被误杀、不完整修复是否被误奖励。按预定规则同时抽成功与失败、可疑与未标记任务；对无法由终态观察区分的过程要求，登记可观测性缺口。不要仅增加断言，也不要让 LLM judge 标签自动变成新 reward。

第三步用独立校准任务描述候选的成功分布与费用长尾，再决定数据构成。0/4 是有限采样现象，不能判真实成功概率为零；4/4 也不证明长期稳定成功。若反馈可合法提供，先比较无反馈、简洁执行诊断和完整失败上下文，记录模型纠错能力与新增费用；这只是固定权重诊断，不能预先认领 SDPO 收益。

最后做同题、同协议的 checkpoint 配对比较，分列原始评分、审查后解释、环境失败、排除和成本。平均成功率、`any-of-N` 与连续重复全部成功率回答不同问题；不把调用／训练行数当独立任务数。保留任务级配对的不确定性；存在同仓库相关性时同时按仓库／任务族分层展示。正式样本数、阈值、重复次数和停止条件由后续具体成本与目标决定。

## 4. 阅读完整性与仍未补齐的证据

八份记录也已完整阅读：[N06 自查][SN06]、[N13 独立审查][SN13]、[E1 自查][SE1]、[R0 自查][SR0]、[R5b 自查][SR5b]、[R5c 自查][SR5c]、[Agent Lightning 自查][SAL]、[N07 自查][SN07]。N13 两篇有既有独立审查；其余记录的作者自查不升级为独立审查，文件名 `16_N07_review.md` 也不改变其性质。

仍需保留：N06 的 Algorithm1／Table4–8 原页图像缺口；E1 的 PDF p17–22 图表／公式目视缺口；R5b 的 effort、MTP、serving 技术图待补；R5c 官方博客全文未取得；Agent Lightning 原始 PDF／全部图形及版本历史未完整核验；N07 p36 Table7–8 原页目视缺口。R0 的离线发布数据、各篇完整历史配置／最终 checkpoint／原始审计标签也不能由代码入口存在推定已经核验。

本报告没有新增运行时 finding、修改评分或训练语义。最小后续产物应是任务—划分—harness—grader—预算的具体比较表，以及对应基座诊断证据；仅当证据指向需要新方法时，才进入相应决策。

[N06]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/N06_hardening_agent_benchmarks.md#L87
[N13a]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/N13a_swe_verified_audit.md#L36
[N13b]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/N13b_coding_eval_signal_noise.md#L37
[E1]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/E1_harness_interplay_posttraining.md#L72
[R0]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/R0_polar.md#L158
[R5b]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/R5b_glm5_2_blog.md#L113
[R5c]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/R5c_glm5_3_blog.md#L8
[AL]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/agent_lightning_v1_2608.17528.md#L206
[N07]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/N07_sdpo.md#L180
[SN06]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/N06_hardening_self_check_20260908.md
[SN13]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/06_N13_review.md
[SE1]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/E1_self_check_20260908.md
[SR0]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/R0_polar_self_check_20260907.md
[SR5b]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/R5b_self_check_20260908.md
[SR5c]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/R5c_self_check_20260908.md
[SAL]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/agent_lightning_v1_2608.17528_self_check_20260907.md
[SN07]: https://github.com/Rogerffff/RepoHarness/blob/ac0e2e64163fbe49411540e901df439aea16b6b0/docs/harness_improve/external_paper_references/reading_notes/reviews/16_N07_review.md
