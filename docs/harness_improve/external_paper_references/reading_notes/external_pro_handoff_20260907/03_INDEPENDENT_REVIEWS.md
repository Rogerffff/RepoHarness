# 两批十二份独立审查全文

导出日期：2026-09-07。使用方式与边界见 [交接说明](00_HANDOFF.md)。各篇正文完整保留；本地链接转为仓库引用文字，页内导航转为文字；需要原图/代码时请访问官方来源。


---

## 文档 1 / 12：01_R1_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/01_R1_review.md`

# R1 独立技术审查

审查日期：2026-09-07。审查对象：R1_mai_thinking_1.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R1_mai_thinking_1.md`〕。审查员为单独委派的 GPT-6 Astra / high，使用干净上下文，未创建下级 agent，未修改正文。

**结论：未发现推翻主要训练配方、模型依赖、关键结果或项目边界的技术错误；全部后训练领域已覆盖。** 有三项低严重程度的补充/限缩建议，列于下文。这里的结论是原文与笔记的对应性判断，不是论文结果的独立复现，也不证明报告未公布的系统实现。

## 1. 审查顺序与来源

先阅读指定 L 版本目录 pp.3–4，独立列出 §3 的全部训练域和附录 A–K；随后核读训练正文、评测、红队、相关基础设施及附录，再打开待审笔记逐项对照。核验没有以笔记的“未披露”结论代替查阅原文。

- 主版本：指定原始 PDF，L〔仓库引用：`docs/harness_improve/main_20260602_2.pdf`〕，SHA-256 `7d4f13dd88ff98d0480645e96b751f0abea00fd99122cabf7626598b29bef26f`。
- 对照版本：官方 URL 的 2026-09-07 快照，W〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R1/main_20260602_2_fetched_20260907.pdf`〕，SHA-256 `a267d745b1eb3792a8abf58e71e204a6f44f9c18eeb5ad8671320deae71986bd`。
- 两个摘要值已独立计算核对。使用全文和逐页文本检查内容；对 L pp.31–33 的公式及图12/13、p.58 图21另作页面视觉核验。正文 §3 的 L/W 去空白文本差分仅显示附录字母引用更新，没有训练配方改写。
- 页码均采用 L 的印刷页码。W 新增 Citation reference，导致附录字母整体后移；未用 W 的附录字母引用 L。
- 纯预训练内容按与后训练的关联进行概要或定点检查；没有重做全部预训练建模消融。项目实现、网页发布历史和全网开放资产状态不属于本审查的独立审计范围。

## 2. 独立覆盖表

下表的原文范围与检查主题先于笔记对照建立；最后一列记录对照结果。

| 原文范围 | 独立检查主题 | 笔记覆盖与判断 |
| --- | --- | --- |
| §1、§3开头、图12，pp.1–2、30–31 | 从无既有 reasoning traces 的 checkpoint 开始；三个并行 specialists；SFT 后轻量 RL | §2–3完整；没有串行专家或 OPD 误写 |
| §2.1、表1，pp.5–7 | active/total 参数、dense/MoE交替、local/global attention、tokenizer、dropless对推理的影响 | §3.1准确；区分最终模型与L78 |
| §2.3–2.6、App.A，pp.9–23、82–85 | 预训练去污染、mid-training mix与记忆重复限制、PR loss-masked prefix、第三方辅助模型 | §3.1、§3.2、§8.5已覆盖；辅助模型用途可按R1-F03限缩 |
| §3.1.1，pp.31–33 | 式4–9；组内advantage、全局token归一化、IS比值、熵控制和outer clip | §4.1–4.2符号与分母准确，未虚构最终合并loss伪代码 |
| §3.1.2–3.1.3，pp.33–34 | language/length reward、两级pass-rate筛选、nucleus mask replay、长度课程 | §4.3–4.4完整；positive reward与pass/fail差异保留为未知 |
| §3.1.4–3.1.5，pp.34–37 | 自蒸馏用途、失败恢复、trace选择负结果、优化器及RL/SFT超参 | §3.2、§4.5完整；未将一般自蒸馏配置等同最终合并 |
| §3.2，pp.37–39 | STEM四阶段生产、共识重写、四档solver与盲审、160k竞赛代码及17语言、三层去重 | §5.1–5.2完整；未将STEM和竞赛代码规模无条件相加 |
| §3.3，pp.39–44 | 多步轨迹与policy-token credit、STEM混合迁移、SEE生命周期、SWE及general tool use | §4.1、§6完整；没有把observations当policy actions |
| §3.3.1、App.D/F，pp.41–43、94–98 | PR漏斗、F2P/P2P、empty/gold验证、题意重写、合成复用、反作弊、工具schema与离线构建 | §6.1–6.4完整；同container评分、最终质量后数量未知及成本口径准确 |
| §3.3.2，pp.43–44 | stateful mocked backend、工具集、personas、无需用工具样本、合成环境与任务、跨环境reward | §6.5完整；>150环境和130,000任务未混入SWE漏斗 |
| §3.4.1，pp.44–46 | 人类偏好RM、循环候选顺序、首score token概率、AI judge、verifiable reward、lexicographic/gated聚合 | §5.3核心机制准确；verifiable reward的multi-epoch经验遗漏见R1-F02 |
| §3.4.2、App.E/表15–16，pp.46、97–99 | IF合成与专家数据、难度校准、atomic rubric、hard/soft和多轮taxonomy | §5.4完整，没有将对话recall写成长时记忆系统 |
| §3.4.3，pp.46–47 | harmful/borderline、数据来源、三轴judge、安全门控、脚注9审计 | §5.5完整，相关系数和87.8%数值准确 |
| §3.4.4，pp.47–48 | honesty来源、离线检索标签、五类factuality/confidence、过度hedging取舍 | §5.6完整；没有填造数值权重 |
| §3.4.5，pp.48–49 | style来源、排除高难领域、0/1/2粗粒度judge、应用优先级 | §5.7完整，保留粗粒度优于细粒度的经验 |
| §3.5/表10，p.49 | 多教师trace过滤、sample/token权重、4 epochs、最终RL保推理机制 | §3.3完整；56/11/33和89/9/2没有颠倒 |
| §3.6，pp.49–53 | controller/problem/rollout责任、可选pass/fail、失败重试、staleness、训推精度/replay、缓存、weight transfer | §7.1–7.2完整；保留组消费、版本原子性和中断恢复的未知项 |
| §2.8、§6、App.K，pp.24–30、59–61、106–109 | YOLO并行/重算/确定性/恢复、GPU资源、goodput、集群控制、部署能效 | §7.3–7.4完整覆盖相关机制；预训练指标没有冒充RL效果 |
| §4.1、App.G/H，pp.53–54、98–101 | STEM各预算、GPQA重复、judge；SWE/terminal context、逐次输出、steps、timeout例外 | §8.1–8.2完整；主要数值与协议限制准确 |
| §4.1、App.J/表12/19，pp.54、103–106 | knowledge、IF、long context、safety、honesty、health、tool calling的不同指标与judge | §8.3完整；BFCL温度例外、LongFact precision、AdvancedIF rubric分数均正确 |
| §4.2/表13–14，pp.54–56 | 英文/多轮任务构成、排除工具任务、人工Likert、胜负和误差 | §8.3完整；没有把未定义的±写成95%CI |
| §4.3、App.I，pp.55–58、101–103 | safety/over-refusal阈值、request分类与response spec、分层选题、release阈值、jailbreak三类ASR | §8.4完整；ASR已按图21颜色逐项核验 |
| §5，pp.56–58 | 内外部红队、整改循环、多语言缺口、dangerous-capability及tool/multimodal排除范围 | §8.4完整；百分比降幅没有改成百分点，未声称修复彻底 |
| App.B，pp.85–88 | code NLL、retrieval NLL、generative QA、渐进扩展、适应速度、最终保守配方 | §3.1、§8.5有覆盖；generative QA的具体观察遗漏见R1-F01 |
| App.C，pp.89–94 | 三类STEM及三类agentic CoT演化例子 | §8.5覆盖全部类型；明确为选例，不构造行为频率或因果消融 |
| App.J.3，p.105；§7，p.61 | MRCR负结果、小模型定向训练结果与未见一般收益；未来模态边界 | §5.7、§8.5完整，两个不同模型没有拼接成同一改善曲线 |

## 3. 发现与修订建议

严重程度定义：P1为会改变主要结论的错误；P2为影响方法理解或复现边界的实质问题；P3为局部精度或覆盖补充。本次无P1/P2发现，以下均为P3，不影响主体判断。

### R1-F01 · P3 · 补齐长上下文 generative QA 的观察及其适用边界

- **原文定位：** L App.B.2 p.86 “Generative QA”，图22(d/e) p.88；App.B开头明确这些消融默认来自小规模模型。
- **笔记定位：** §3.1、§8.5长context extension行。
- **发现：** 笔记保留了短程extension、NLL收益、140B/150B冲突和位置校准解释，但没有写出另一个独立评测的具体结果：内部仓库文档QA中，32K训练模型可在最高128K上下文答题，作者称最高4×长度外推；超出训练长度后，近期/上下文末端证据比远端证据更难提取，长上下文训练缓解此非对称性。这是原文已给出的观察，不能让“全部长context评测已覆盖”仅落在NLL上。
- **修订建议：** 在§8.5补一至两句，明确这是内部generative QA与小模型消融；区分于code NLL及插无关文档的retrieval NLL，不推成最终MAI-Thinking-1在任意任务上的4×外推保证。

### R1-F02 · P3 · 补记可验证奖励对多轮数据训练的经验

- **原文定位：** L §3.4.1 p.45 “Verifiable rewards”。
- **笔记定位：** §5.3。
- **发现：** 可验证奖励被描述为确定性verifiers及长度约束，但漏掉作者对比非可验证奖励的三个训练观察：更不易reward hacking、对multi-epoching较不敏感、通常有助稳定训练。尤其multi-epoching是这段报告独立提供的训练经验，其他段落的SFT epochs或随机trace选择不能替代它。
- **修订建议：** 补一句作者定性观察，multi-epoching解释为对同一数据重复训练多个epoch；保留“未给定量消融/可保证的epoch上限”，不要把它泛化为所有verifier都不会被利用。

### R1-F03 · P3 · 将Qwen3-30B质量评分用途限缩到代码网页

- **原文定位：** L App.A.1 p.83 “Code pages”；对照App.A.4 pp.84–85 “Public GitHub”。
- **笔记定位：** §3.2末尾“code quality用Qwen3-30B（App.A）”。
- **发现：** 原文明确命名Qwen3-30B的环节是代码类网页候选文档质量评分；Public GitHub段虽有quality score，却没有在该段指定同一评分模型。现有简写容易被读成GitHub/SWE代码数据均用Qwen3-30B judge。关于“无第三方蒸馏不等于无第三方模型”的主结论仍然正确。
- **修订建议：** 改成“代码类网页质量评分使用Qwen3-30B（App.A.1，Code pages，p.83）”，不要扩展为STEM solver、SWE builder或Github quality judge的具体身份。

## 4. 关键正确性与未知项复核

- **公式与mask：** 式5确为token总和分母，实际跨global batch/DP；advantage为组内标准化；entropy estimator含ratio权重；上clip为`(1-epsilon)^(-1)+k`。图13的kmax=1.0与典型2.5已正确分开。policy-step tokens承接trajectory reward，工具observation不是模型动作；笔记未声称已拿到serialization mask代码。
- **采样与失败：** §3.1.5的128 total与§3.6.2的16后additional128确实冲突。paper给出请求失败重试、预算终止后评分与stale丢弃，但没有完整parse/tool/grader错误的reward、mask、group统计、补采上限和drop-single/drop-group合同。笔记的未知项有已读范围支撑。
- **资源与比例：** 4,864=4,096+768；5.33:1与作者约5:1的措辞分开。SWE漏斗三个百分数分母约4.87M；265,617止于环境/grader验证，非质量重写后的最终数量。30k CPU总体描述、10k CPU吞吐配置、12M token/min capacity与20 env/min不能当真实计费总成本，笔记没有这样换算。
- **原文冲突：** 140B/150B、128/16+128、6.5h对应“15% of 51h”的不一致均真实存在，笔记保留两侧证据是正确处理。W的4.6K GB300不能未经解释替换最大job的4,864。
- **评测与因果：** STEM 256k输出与agentic 256k总context不同；SWE 8k/terminal32k逐次输出、1,000 steps和忽略terminal timeout已核。GPQA16rollouts、BFCL T=0.001是默认设置的例外。MRCR60%与小模型1,000样本后90%+不同模型；CoT选例、STEM迁移、自蒸馏经历不能视为隔离因果。笔记均作了对应限缩。
- **RM与安全：** RM取循环置换后第一score token的`P(score=5)`，不是期望分或胜率。lexicographic依赖组内高优先级全并列，safety gate依赖单响应policy compliance；87.8%与相关系数、图21十二个ASR值均准确。危险能力uplift、内部agentic tool-use和multimodal红队缺口没有被隐藏。

## 5. 发布前检查与残余不确定性

1. 审查worktree缺少部分原始未提交输入，所以其中的L PDF、旧稿和项目简报相对链接不能独立解析。主作者已确认这些目标存在于最终主目录，且说明最终仅发布正文、审查与W快照。本项是**最终目录链接检查**，不是正文技术缺陷；发布后应以最终位置重新核对本审查和正文全部相对链接。
2. 未独立核验整个工程实现或重做项目简报的交叉审计。正文将项目映射限定为设计层候选、未把现成系统职责写成必造组件，符合这次原文审查能支持的边界。
3. 未重做官方新闻日期与全网开放资产搜索。PDF及本次查阅范围足以支持“报告未给完整复现入口”，不足以证明任何地方都没有发布代码、权重或数据；正文已保留此限制。
4. 未运行训练、未取得内部数据、judge模型/提示词全套、SGLang fork、replay payload、每run日志或私有成本账单。论文定性经验的统计强度及未公开实现不能由这次对应性审查消除。

## 6. 主作者处理记录

由主作者修订后按R1-F01至R1-F03逐项记录采纳、修改位置或不采纳理由，并记录最终发布链接核验。审查员未预填“已处理”或替正文宣布完成。


### 2026-09-07 主作者修订处理

| ID | 处理 | 修订位置及原文依据 |
| --- | --- | --- |
| R1-F01 | 采纳，已补齐 | 正文§8.5长context行补内部generative QA的32K→128K外推及末端证据困难，明确小模型/内部任务边界；L App.B.2 p.86、图22(d/e) p.88。主作者重新核对该段后修改。 |
| R1-F02 | 采纳，已补齐 | 正文§5.3补三项verifiable reward定性经验；multi-epoching明确为同一数据重复多个epoch，并非multi-turn对话；L §3.4.1 p.45。不添加数值epoch上限或安全保证。 |
| R1-F03 | 采纳，已限缩 | 正文§3.2改为代码类网页候选文档质量评分使用Qwen3-30B；L App.A.1 Code pages p.83，不外推到GitHub质量评分、SWE builder或STEM solver。 |

其他主作者自查：更正旧evidence matrix定位为§9.2；注明09-07建议对09-06交叉审查未闭合项的引用，未把09-05简报当最新全面通过证据；补一般/合并SFT细粒度mask未展开的范围；模型页public-preview入口与训练资产分开。原文的128/16+128、140B/150B、6.5h/15%和4.6K/4864差异全部保留。

修订方式为原文对应性补充，不改变论文训练主结论，也未改变RH2训练实现或语义。本次三项为直接可定位的P3补充，主作者逐项回原段核对，未另开第二审查团队。

### 最终发布核验

2026-09-07：已将本任务专属正文、独立审查及W来源快照发布到主资料库的相同相对路径。逐文件SHA-256一致；正文与审查中的全部本地相对链接在最终发布目录均可解析；两份Markdown均不含真实本机绝对路径，正文公式/代码块闭合、三项修订可检索。未修改原始PDF、共享索引、其他笔记或训练代码。本文记录的未公开配置与原文冲突仍然保留。


---

## 文档 2 / 12：02_R3_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/02_R3_review.md`

# R3 独立审查：Qwen3-Coder-Next Technical Report

## 审查对象、版本与方法

- 审查日期：2026-09-07；独立审查者按派工使用 GPT-6 Astra / high、干净上下文，仅收到原文、初稿、模板位置与项目映射边界；未再委派其他审查者。
- 原文：[arXiv:2603.00729v1](https://arxiv.org/abs/2603.00729v1)，23 页；以提供的 PDF 和对应 `tmp/pdfs/R3.txt` 为正文依据。arXiv 版本页独立打开，确认 v1 提交于 2026-02-28 16:25:04 UTC；PDF 封面印 2026-03-03。没有改用未指定的新版本。
- 初稿：R3_qwen3_coder_next.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md`〕，本次审查时 495 行。下文行号仅用于定位这一版初稿；修订后可能移动。
- 先读原文 §2–6、A.1–A.4 并建立结构与事实清单，再完整读初稿作逐项对应。§1、作者和 References 概要读。原图额外检查 p5、6、8、9、10、19、20、21、22：覆盖 Figures 3、5–8，组合公式，Tables 2、10–16 与 packing 公式；p7 Figure 4 结合整页提取文本核对三种格式轴。
- 独立打开 [PrimeVul 原论文 v2 §IV-B2](https://arxiv.org/html/2403.18624v2#S4.SS2.SSS2)，只核指标定义及表头方向，不把其训练配置迁移到 R3。没有精读 SWE-Universe、MegaFlow、FIM 关联论文或使用二手综述填补 R3。
- 辅助窄读初稿固定的 provenance〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R3/provenance.json`〕、Next / Next-Base 模型卡和 Qwen3-Coder README 的模型、部署、采样与语言覆盖字段。模型卡 revision 分别为 `a7fbcb5c0e12d62a448eaa0e260346bf5dcc0feb`、`1b6df59d5f75ab51edb9ad8cb3ea69c5d0aedd57`；Qwen3-Coder revision 为 `33bc6aabd7791ad7b32f7e92104f11f2359ba890`。本次未重新获取 Hugging Face/GitHub API 元数据，不把快照 provenance 当成独立复验过的在线元数据。
- 为检查项目映射，窄读 `CURRENT-STATE-BRIEF.md` 与 `project1_design_advice_20260907.md` 中基线、候选训练配置、REALIGN/rewrite/FORK、真实评分和上游复用边界。没有代码审计，也没有批准新训练语义。
- 仅写本审查文件，未改笔记正文。沿用现有 PDF/文本，未创建额外摘要或下载 TeX 文件。

## 独立后训练覆盖表

前两列依据原文标题与内容建立；最后一列在读完初稿后补入。精读包含对应正文、图表、图注及附录说明，不以是否直接适用于 SWE 决定取舍。

| 原文章节 / 页 | 独立核对的完整内容 | 初稿位置与覆盖判断 |
|---|---|---|
| Abstract、§1 Introduction，p1–2 | 80B/3B、Qwen3-Next 起点、分阶段 agentic training、专家回归统一模型；Figure 1 总览 | §1–3、§7；背景概要足够，Aider 在 Table 7 对应保留 |
| §2 Scaling up Agentic Training；§2.1 Task Synthesis，p2–3 | 两条数据管线；PR 去污染、bug/fix/test patch、构建 agent、non-functional verifier 过滤、专门模型及 QA agent；既有容器仓库注入 bug、测试失败/回退成功、issue 生成、测试排除；Figure 2 | §4.1–4.4；完整，实例/环境/轨迹/消费量分开 |
| §2.2 Infrastructure，p3 | MegaFlow、阿里云 Kubernetes、Argo；rollout / evaluation / post-processing，agent 与环境同 pod，专用评分容器 | §6；完整，不冒称已知异步 learner 调度或完整私有评分隔离 |
| §3 Mid-training；§3.1 Data，p3 | 天然数据为主、最小必要合成量；专门化/多样性/适应性取舍 | §3.1；完整，未编造混合比 |
| §3.1.1 Natural Data，p4 | GitHub 文件/仓库级、92→370 语言、600B 仓库 token、截止日、上下文扩展；网页 grounding 与 480B 改写、Table 1；PR 文档构建与去污染 | §3.1–3.2、§4.4；完整 |
| §3.1.2 Synthetic Data，p4–5 | grounded QA、允许不生成、Wikipedia-style 虚假引用负结果；六种轨迹框架、480B teacher、三种过滤；Figure 3 同/跨 scaffold scaling | §3.1、§4.3；完整，迁移非对称与非单调被保留 |
| §3.1.3 Instruction-Following Data，p5 | 少量指令数据用于中训阶段下游监测 | §3.1；完整 |
| §3.1.4 Fill-In-the-Middle Code Completion，p5 | Stack-V2、chat-FIM / search-and-replace FIM、proxy、相同规模相对结果与作者解释 | §3.1；完整，未把关联论文实验算入已读 R3 |
| §3.2 Training，p5–6 | 万亿量级 NTP/FIM、262,144、BFP、超长文 split、重复段 mask；文档索引构建的局部效率声明 | §3.2、§5.4；主要机制完整；局部效率声明可补，见 R3-02 |
| §4 Post-training；§4.1 Supervised Fine-tuning，p6 | 内部安全对齐语料、验证轨迹、功能/安全过滤的 grounded QA；Mini-SWE-agent 用户模拟器；n 候选、组合数、pairwise checklist / ordinal ranking、风格与主动性结果 | §3.3；完整，不误写 DPO 或 learned SWE reward |
| §4.2 Expert Models，p6 | 同一初始化、不同数据和训练配方；专家不是顺序四阶段或 MoE 内部专家 | §3 流程图与说明；完整 |
| §4.2.1 Web Development Expert，p6–7 | Playwright/Chromium、Vite、静态截图 VLM、DOM 与自动动作、前后截图动态验证；过滤后轨迹训练 | §3.4；完整，未冒称 WebDev RL 或多模态学生 |
| §4.2.2 User Experience Expert，p7–9 | 多来源/多 scaffold 数据清洗与混合消融、通用失败与格式过滤；三种格式轴、多模板；Figures 4–5、五匿名 scaffold 内评 Table 2 | §3.5、§7.1；完整，92.7 并非最高、格式正确不等于任务完成 |
| §4.2.3 Single-turn Question Answering Expert，p9–10 | 执行可验证单轮 RL；库/API、I/O、多语言、复杂指令、安全生成/修复；候选测试与独立解多数共识；Figure 6 九类能力 | §3.6、§5.1；完整，保留共识不保证正确、曲线非因果消融 |
| §4.2.4 Software Engineering Expert，p10–11 | 开源/自建环境、SFT/RL prompt 互斥、pass-rate 过滤；终局 reward、unfinished penalty、非法调用 token penalty；未来 commit 泄漏与新 blocker；Figure 7 | §4.4、§5.2–3；完整，训练上限未知、75.1/84.6 与平均 turns 边界清楚 |
| §4.2.5 Expert Distillation，p11 | 四领域 expert 蒸馏到 SFT model，保留指令遵循、单模型部署 | §3.7、§5.5；完整，未把 480B teacher 误作此阶段教师或补写 OPD |
| §5 Experiments；§5.1 Agentic Evaluation，p11–12 | baseline 复测及标准防泄漏；SWE Verified / Multilingual / Pro 多 scaffold、Terminal 2.0 四配置；Tables 3–5、300 turns | §7.2、§6；完整，未知 split/采样/预算明确，破折号不作零分 |
| §5.2 Other Coding Tasks，p12–13 | 函数级、推理/竞赛、full-stack、SQL、多语言编辑，Tables 6–7 | §7.3；全部 benchmark 与数值保留，明确退化项 |
| §5.3 General Tasks，p13 | 通用知识/推理、竞技数学，Tables 8–9，作者迁移解释 | §7.4；全部指标保留，不补写专项数学 RL |
| §6 Conclusion, Limitation, and Future Work，p13 | 复杂大型 SWE、更多交互轮、UI 短板；harder pretraining、RL/planning、视觉与 agentic cybersecurity/CTF 未来方向 | §2、§7.6、§8；完整，较低总训练算力只是未量化作者声明 |
| §7 Authors、References，p14–18 | 作者列表与关键引文身份核对，特别 Pan et al.=SWE-Gym；架构/基准/关联工作入口 | §1、§4.3、§11；概要读合理，未混入关联论文配置 |
| A.1 Data Statistics for Synthesized Tasks，p19 | Tables 10–11，真实 PR 与注入 bug 分别统计；语言、repo raw/cleaned/used、四策略、平均任务数 | §4.1–2；完整，两个池不直接当作去重训练集相加 |
| A.2 The Checklist of Tool Chat Templates for Scaling，p19–20 | 原文声称 21、实际 20 行；各定义/调用格式与特殊模板来源 | §3.5；逐行核对一致，原文计数矛盾已保留 |
| A.3 Detailed Implementation on Best-Fit-Packing，p19–20 | C++ / Megatron、文档开头工具定义、fragmentation / padding 的两种分母 | §5.4；完整，统计口径与 RL loss 分开 |
| A.3.1 Two Variants of Sample Packing Strategy，p20–21 | RLD 头部重启/尾截断/头 token 重权；PLD padding mask 与预算补偿；Figure 8 | §5.4；完整，公式和计算正确 |
| A.3.2 How to Tackle Long Documents with Best-Fit-Packing，p21 | split、slide、drop；残块处理、BFP 容量前提 | §5.4；完整；中文 backward 方向可写得更明确，见 R3-03 |
| A.3.3 Ablation Study on Sample Packing Strategy，p21 | Agentless 定位/patch 两步；Model Loc/GT Loc/GT File、similarity/empty、73B/89B、Table 13；drop 最佳但主实验 split；非单调取舍 | §5.4、§7.5；完整，22% fewer 分母问题已纠正 |
| A.4 Experiments on Cybersecurity，p21–23 | AthenaBench-Mini 六项及 greedy；PrimeVul-Paired 函数/成对指标与 greedy；SecCodeBench 53 Java、hint、严重度加权 pass@k；CWEval func@1/func-sec@1、n=10/T=0.8；Tables 14–16 | §7.6；四类评测完整。P-C 方向纠正有依据；还可补成对比例合计疑点，见 R3-01 |

结论：没有发现遗漏整个后训练阶段、专家领域、附录或评测类别。初稿没有把未读的关联论文当成 R3 事实，已列“未披露”字段在本次逐节阅读范围内也未找到相反披露。以下是局部补充和精度问题，不应被扩大为初稿整体错误。

## 逐项发现与建议

### R3-01 · P2 · Table 15 还存在成对比例合计的未解释缺口

- **初稿位置**：§7.6，行 380–382；§9.1 / §9.2 的 P-C 问题汇总。
- **性质**：确定的算术现象；其成因未知。不是初稿抄错数字，也不能确定作者评测实现错。
- **原文证据**：R3 A.4 p22 Table 15 原页中，Next 四列为 `0.88 + 53.01 + 41.29 + 4.64 = 99.82`；GLM-4.7 为 `20.55 + 38.60 + 26.57 + 12.53 = 98.25`。四项保留两位小数的舍入误差不足以解释这两个缺口。
- **为何影响解读**：按 [PrimeVul v2 §IV-B2](https://arxiv.org/html/2403.18624v2#S4.SS2.SSS2) 的二元成对定义，P-C/P-V/P-B/P-R 覆盖完整预测对的四类结果。若同分母且每个函数都有可解析二元预测，合计应约为 100%。原文没有说明缺失/无效预测、有效子集、分母变化或另一个类别。初稿已经正确拒绝 P-C 优越性结论，但只写函数与 pair 分母不同，还未显式记录这一组内一致性疑点。
- **建议**：在已有 P-C 警示后补一句上述合计及条件，并说明尚缺逐对预测、有效样本分母和无效输出处理。保持原表数值，不重新归一化，也不自行推定缺口全来自解析失败。可以作为同一原文指标问题的补充，无需新增长篇附录。

### R3-02 · P3 · 可补回 BFP 的局部实现效率声明

- **初稿位置**：§3.2 / §5.4，行 97、233；§6 / §8 的性能边界。
- **性质**：次要事实覆盖遗漏；现有“无端到端吞吐数字”结论仍然成立。
- **原文证据**：§3.2 p5 说该 BFP 实现在 **document index construction** 阶段的效率接近传统 concatenate-then-split；A.3 p19 说明在 Megatron 中用 C++ 重实现。
- **建议**：在 BFP 段补“作者称文档索引构建效率接近 concat-then-split，但未给具体计时或吞吐数”。限定到索引构建，不能扩为 GPU 训练吞吐、RL rollout 或端到端成本提升。本项不要求新增实验或更多外部来源。

### R3-03 · P3 · slide 的方向用词宜避免歧义

- **初稿位置**：§5.4，行 250 的“末块合并/向后补齐”。
- **性质**：表述精度，非算法方向已确定写反。
- **原文证据**：A.3.2 p21 的 slide 是重叠滑窗；最后一块与前块合并，或 **extended backward** 以维持目标长度。这里强调借入末块之前已有的上下文。split 则明确保留不足长度的最后残块。
- **建议**：写成“末块与前块合并，或向文档前文延伸以补足长度”；split 可同时加“保留短末块”。这样读者不易把“向后”理解为向文档末尾补未来内容或 padding。保留实现未详述的边界，不扩写伪代码。

## 已独立核对、无需纠正的关键事实

| 核对项 | 原文证据与判断 |
|---|---|
| 模型与教师关系 | §1 p1–2、§3 p3、§4.2.5 p11 支持 Qwen3-Next pretrained base → mid-training → SFT → 四 expert → 蒸馏回 SFT model。§3.1.1–2 的 Qwen3-Coder-480B-A35B-Instruct 用于改写、QA、多轮轨迹；没有证据让它替代最后四 expert。 |
| 中训数量与目标 | §3.1.1 / §3.2：92→370 语言、600B repository tokens、32,768→262,144 context、总量万亿级、NTP/FIM、重复段 mask。600B 不是总训练 token；训练语料截止日不推广到所有 RL PR。 |
| SFT 偏好组合数 | p6 原页是 n 选 2，初稿 `n(n−1)/2` 正确。专门 judge 排序不构成 DPO/Bradley–Terry/RLHF 公式披露。 |
| 两池计数 | Table 10：807,693 instances / 52,960 repos，均值 15.25；Table 11：6,012 raw / 5,456 cleaned / 5,019 used repos、851,898 tasks，851,898/5,019≈169.73。四策略总量及初稿逐来源数与表一致。 |
| 模板多样性 | Figure 5 的 1/2/4/8 模板图读约 48.0/52.0/53.4/53.8；固定数据量与训练配置。A.2 的“21”与 Table 12 实际 20 行冲突确实存在；初稿未补造第 21 项。Table 2 Next 五列平均 92.7，DeepSeek-V3.2 平均 93.7。 |
| RL 惩罚与作弊 | §4.2.4 是终局 trajectory reward、超轮数 trajectory penalty、非法 tool-call 关联 token penalty；没有数值或总 loss。Figure 7 确有 75.1/84.6、图注平均 50→130 turns；75.1 不是最终统一模型 Table 3 成绩，300 turns 也不是已披露训练 cap。人工检查消除作弊不等于全量零残余。 |
| 最终 agentic 结果 | Tables 3–5：Verified 70.6/71.1/71.3，Multilingual 62.8/56.2/64.3，Pro 42.7/38.7，Terminal 2.0 为 34.2/36.2/30.9/25.8。初稿 harness 顺序、主要对照值和 300 turns 的阶段边界正确。 |
| 其他能力与负结果 | Tables 6–9 的初稿数值逐项一致，含 FullStack、BIRD-SQL、EvalPlus 等下降和数学提升。Figure 3 跨 scaffold 弱迁移、Wikipedia-style 虚假 URL、Figure 6 波动均被保留；未把横向模型比较或训练过程曲线写成已隔离的因果收益。 |
| Packing 公式与分母 | A.3 p20–21 的 fragmentation 是文档比例，padding 是 token 槽位比例；PLD 为 `T/(1-p)`，73/(1−0.1755)≈88.54B，对应表中 89B。BFP 比 PLD 少约 18.0%，反向为 PLD 多约 21.9%；初稿对原文“22% fewer”的纠正正确。 |
| Packing 代理指标 | Table 13 为 patch similarity / empty rate，含模型定位与两个 GT 条件，不是 task pass rate。BFP+split AVG 20.17/25.01、drop 20.84/24.34，主实验使用 split。初稿没有把 fragmentation=0 扩大为原始超长轨迹从未切断。 |
| 安全指标与采样 | Tables 14–16 的 Next 数与对照摘录一致；Athena 的 RMS 为 F1、其余 accuracy，PrimeVul 为 greedy；SecCodeBench 53 Java task 的严重度加权 pass@k 未披露具体 k；CWEval 两指标 n=10、T=0.8，不能写成 pass@10。 |
| P-C 方向纠正 | R3 p22 实际印 P-C↓ 并声称低值较好；PrimeVul v2 §IV-B2 定义为一对均正确，且其 Table V 明确 P-C↑。初稿撤回“最好 paired consistency”有充分依据，并恰当地保留 R3 列名/实现真相未知。新增合计疑点见 R3-01。 |
| 资产与复现边界 | 固定卡片确有 non-thinking、262,144、SGLang≥0.5.8/vLLM≥0.15.0、1.0/0.95/40 和示例 65,536；卡片 prose 4 GPU 与 TP=2 示例的矛盾也存在。这些不是生产 RL 配置。未下载权重、未实测吞吐，不能宣称全训练复现。 |
| 项目映射 | 当前文档支持 miles + SGLang + 外部 harness；GRPO n=8、faithful DIS、Qwen3-30B-A3B 是项目候选而非 R3 配方。初稿明确设计层候选、上游复用和需自行实测，没有恢复已删除 command-filter 或自动批准多 expert/OPD。 |

## 审查结论与残余未知

未发现 P0/P1 级正确性错误，也未发现后训练覆盖表漏掉整段原文内容。建议主作者处理 R3-01 的指标一致性补充；R3-02、R3-03 为低优先级的完整性与表达改进。对初稿已有的原文三类实质纠偏——模板 21/20、token 百分比分母、P-C 方向——本次均独立确认。

尚不能从报告恢复的内容仍包括完整 RL/蒸馏 loss、策略与教师更新、每题采样和 group 统计、失败/截断的梯度消费、训练参数和硬件、任务到实际训练消费的完整漏斗、全套评测 split/预算，以及 PrimeVul 的逐对预测和实际分母。不能为了消除未知而拿框架默认值、家族报告或官方部署建议补成生产事实。本审查不是对训练可复现性或本项目学习效果的验收。

## 主作者处理记录

本段留给主作者在修订后逐项记录 R3-01、R3-02、R3-03 的处理位置、采纳情况与残余不确定性；审查者未提前填写已处理或通过。

### 主作者逐项处理（2026-09-07）

已收到独立审查者的最终回报后进行本记录。下列是主作者修订，不冒称审查者重新执行了完整第二轮审查。

| 发现 | 处理状态与正文位置 | 原文证据 / 复核结果 | 残余边界 |
|---|---|---|---|
| R3-01（P2） | 已采纳，笔记 §7.6，并在 §9.3 / §12 留记录 | 对 Table 15 p22 五行重新求和：99.99、100.00、99.99、98.25、99.82；明确 Next 与 GLM 缺口超过舍入误差 | 不猜无效预测类别，不改表值；仍需作者逐对预测、样本分母和解析政策 |
| R3-02（P3） | 已采纳，笔记 §5.4 | 补入 §3.2 p5 的 document index construction 局部效率声明，保留未给计时/吞吐的限定 | 不升级成 GPU 训练、RL rollout 或端到端加速结论 |
| R3-03（P3） | 已采纳，笔记 §5.4 策略表 | 按 A.3.2 p21 将 slide 改为“末块与前块合并或向文档前文延伸以补足长度”；split 加“保留短末块” | 不推断未披露实现或生成伪代码 |

主作者保留审查全文和全部残余未知，不删除发现、不将原论文未披露项伪装为已核事实。原任务范围内的后训练章节、附录与独立审查/修订已完成；仅发布本任务专属文档和必要来源快照，不涉及训练代码或新的训练语义定案。


---

## 文档 3 / 12：03_N01_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/03_N01_review.md`

# N01 独立审查：KAT-Coder-V2.5 Technical Report

审查日期：2026-09-07。对象：N01 笔记〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md`〕。审查者为本任务唯一独立 sub-agent，未派生其他 agent，未修改笔记正文。

## 1. 先读原文所得覆盖清单

以下清单在打开初稿之前建立。已独立通读 v1 TeX 正文〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N01/tex/main.tex`〕 全部技术章节及结论、贡献与参考文献，查阅 references.bib〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N01/tex/references.bib`〕，并检查文末表。没有技术附录；Table 1–3 漂移到参考文献后的 PDF 第 23–24 页，不能当作无关尾页略过。[arXiv v1 页面](https://arxiv.org/abs/2607.05471v1) 确认为 2026-07-06 提交的正式版本，共 24 页。

| 原文范围 | 独立阅读所得必须覆盖内容 | 核查深度 |
| --- | --- | --- |
| 摘要、§1，PDF pp.1–3 | 实际五类专家；正文重点 SWE/Claw；不能由摘要只列三类就删去 terminal/general knowledge | 全文 |
| §2.1、Fig.2，pp.3–4 | PR/commit → golden/test patch → 三段任务描述 → clarity check；AutoBuilder build/verification agent；结构化测试采集 >90%；重复一致；16.5%→57.2%、>100k 环境/12 语言；预应用非题意依赖编辑、移除 git 泄漏 | 全文、图视觉核查 |
| §2.2，pp.5–6 | zero-pass 任务经 hint 达约20%，固定已验 patch 后无 hint 再生成；规则门控+过程评分；偏好/rejection/process RM 信号；等价 harness 改写与异常注入 | 全文 |
| §3.1–3.4、Fig.3，pp.6–9 | Service/Task/Eval 闭环；Skill 与生成服务双来源；OpenAPI/container/fixture；服务生成 >90%；候选 millions、保留 >100k instances；平均15次工具、最长>100 steps；三阶段一致性验证、三种处置、两层轨迹筛选 | 全文、图视觉核查 |
| §4.1，pp.9–10 | 协议/context/control-flow 三轴；mini-swe-agent 白盒；ClaudeCode/Codex/OpenClaw/OpenHands 黑盒；两者都进 RL | 全文 |
| §4.2、Fig.4–5，pp.10–12 | Rollout/Train/KwaiEnv/Gateway/Buffer；token-in/out、weight sync；约200轮样本40%有 drift；/generate；早期 sandbox 轨迹级16%；磁盘95%→60%；timeout与verifier各6–7%→<1%；整体反馈<2%；collapse约降一数量级 | 全文、图视觉核查 |
| §4.3、Eq.(1)–(4)，pp.12–13 | PPO 三点选择理由；token ratio、轨迹内1/\|o\|、GAE、critic MSE；原文 r_t 重名；训练期 hindsight context、actor 普通历史、部署丢弃 critic | 全文、全部公式 PDF 视觉核查 |
| §4.4、Eq.(5)，pp.13–15 | 三层规则 reward；模型 rubric 来源、适用范围；GRM 为单独 RL 训练的 judge；GT 召回与误报计数惩罚、空 GT 分支 | 全文、公式 PDF 视觉核查 |
| Table 1–3，pp.23–24 | 10项规则，含正文列表未列的 Debug Artifact Cleanup；Table 2八项代表标准与适用条件；Table 3四种 bad cases；表2/3仅 Partial Display | 全部表格 PDF 视觉核查 |
| §5–5.1、Eq.(6)–(8)，pp.15–17 | K=5 domain routing；student on-policy prefix 上 teacher logits；KL(student\|\|teacher)；teacher 轨迹 cold-start NLL；top-k overlap/k；单调权重、连续m低阈值截断、保留有效prefix、gradient mask、length-stratified batching | 全文、全部公式 PDF 视觉核查 |
| §6.1–6.2、Table 4，pp.17–19 | 内部 Code/Claw benchmark 构造与质检；默认统一Claude Code协议及PinchBench外部Avg例外；全部6×5分数、Kimi星号模型替换；负结果；未给消融/具体预算 | 全文、Table 4 PDF 视觉核查 |
| §7–8、References，pp.19–22 | 结论仅方法叙事，无额外训练配置；检查V2引用目标与未披露边界 | 全文 |

原始 PDF 已视觉检查 pp.1、3、6、10–13、15–16、19、23–24，覆盖全部八个公式、四张表及五幅图；其余技术页经完整 TeX 与 PDF 文本对照阅读。

## 2. 与初稿逐项对照的发现

### 2.1 结论与一处低优先级修订

**未发现 P0/P1/P2 正确性问题，也未发现后训练章节或文末技术表遗漏。** 笔记对模型关系、数字分母、公式、评测脚注及因果证据边界的处理与原文吻合。保留一处 P3 措辞收紧建议；它不影响核心技术结论。

| 编号/严重度 | 初稿位置 | 原文证据 | 问题与最小修订建议 |
| --- | --- | --- | --- |
| R1 / P3 | §5.4 表2摘要，初稿第183行：“允许未动态复现但凭源码/既有测试/历史/框架推理准确定位的情形” | Table 2 / PDF p24，Static Bug Localization；TeX main.tex 第626–630行只描述这一情形。该表是 Partial Display，没有正负符号、权重或显式豁免规则 | “允许”略强于原文，可能被理解为已披露的复现豁免政策。改为“列出未动态复现、但经源码/既有测试/历史/框架推理准确定位根因的情形；奖惩方向未披露”。初稿第188行已有正确限制，保留它即可；无需删除静态定位条目。 |

P3 表示局部表述精确性建议；不把它升级为尚未发生的实现风险或新准入要求。

### 2.2 实际对照证据

| 核查主题 | 初稿对应 | 独立核对结果与证据 |
| --- | --- | --- |
| 标题、日期、署名、版本 | §1，第5–9行 | 与 PDF p1、§8/p20、arXiv v1 元数据相符。正文署 KwaiKAT Team，网站列 Bo Huang 等53位作者。物理页码、无独立Appendix、文末表位置正确。 |
| 全后训练覆盖 | §1.1覆盖表；§3–6 | 独立清单中的 SWE 数据、Claw 数据、所有 RL/奖励/GRM、五域专家、cold start/MOPD/动态截断全部有实质解释。terminal、web coding、general knowledge 作为未单独展开的专家保留，没有强塞入串行流水线；没有把参考文献里的数学/多模态配方算作本模型训练。 |
| SWE 环境数字与分母 | §4.1，第70–84行 | >90% 是 expected tests **collected**，不是通过率；16.5%→57.2% 是环境构建成功率；>100,000 是 environments、覆盖12语言。原文没有完整原始候选分母、重试次数、训练实际消费量；笔记没有偷换成题数/镜像数。 |
| 恢复数据与过程过滤 | §4.2–4.3 | 约20%对应 previously zero-pass tasks 经过程hint后的通过率，不能代替无hint重建保留率。先固定 verified patch 后重新生成无hint轨迹、再查验证/泄漏/一致性，与§2.2/p5及Fig.2一致。过程维度、偏好用途、鲁棒性扰动均未漏。 |
| KwaiClawEnv 全流程 | §4.4 | Service/Task/Eval、双来源服务、三种派生方式、三阶段一致性检查、三种处置、两层过滤及judge三维均对应§3.2–3.4。区分 Skill服务生成>90%、millions候选→>100k instances、数万trajectories、平均15 tool calls与最长>100 steps；保留口径不明而未强行凑漏斗。 |
| PPO/GAE/critic 公式 | §5.1–5.2 | 已对 PDF pp.12–13 Eq.(1)–(4)逐项核查：行为策略采样、token ratio、min/clip、每条o内1/\|o\|、GAE上界T−t−1、MSE目标均一致；准确指出r_t重名。c_t是may include，actor只见常规历史；没有把前代mini-critic大小补成KAT事实。 |
| GRM、规则reward和文末表 | §5.3–5.4 | Table 1的10项完整，包括正文bullet缺少的清理项；Table 2八条、Table 3四类均有覆盖且标Partial Display。Eq.(5)两分支均正确：非空GT以\|GT\|为分母、误报按数量惩罚；空GT从1起扣。明确这是训练judge的reward，非actor总奖励。F₂公式标为标准释义而非原文披露。除R1措辞外无误。 |
| MOPD模型关系与公式 | §3、§5.5–5.6 | K=5，按样本domain选择一位teacher；student自采样前缀上KL(student\|\|teacher)，不是五teacher平均。Eq.(6)无长度分母；Eq.(7)teacher采样NLL；Eq.(8)top-k交集除k。兼容权重、连续m低阈值、gradient mask、有效prefix及length-stratified batching全部保留。没有把top-k compatibility说成top-k KL实现。 |
| infra与故障率 | §6 | §4.1–4.2及Fig.4支持双类harness均参与RL、Gateway/Buffer/权重同步、后端/generate；200-turn实验中40%是发生drift的samples比例。16%是早期抽审含sandbox故障的轨迹比例；两个6–7%分别为超时rollout和verifier受污染样本。笔记正确分开峰时95%与稳态60%，不把错误率相加、不从约180步曲线造总预算。 |
| 全部表4数字与派生差值 | §7.2 | 已对PDF p19核对30个表格单元（含GLM-5.1的缺值），均与初稿相符；差值4.0、4.2、1.4、5.2、23.9、0.2、3.2正确。KAT Claw第三、Terminal五者最低；SciCode并列第一与第二不同分值说明正确。 |
| harness/评测协议 | §7.1–7.3 | §6默认统一Claude Code，固定工具/context/环境/decoding，但Table 4明确PinchBench是2026-07-02外部Avg，Kimi该格是K2.7-Code。笔记没有将六项全部包装成统一预算重跑，也未把缺乏定义的全表统一改成pass@1。 |
| 消融与因果 | §2、§5.2、§5.6、§7.3、§9 | 原文确无等底座/数据/算力的PPO、critic、GRM、harness或MOPD消融表。笔记准确把工程前后观察、作者解释、读图近似和阅读者理论问题分开；没有把榜单领先归因给单项机制，也不把hindsight仅训练可见推成无偏证明。 |
| “未披露”是否经过查阅 | §5.7、§6.2、§8–9 | 已独立读完§1–7、图1–5、表1–4和参考文献：确未见base/teacher/GRM参数规模、tokenizer、GPU-hour、optimizer/LR、训练batch/steps、PPO常数、奖励权重、MOPD k/m/阈值、实际KL估计/token mask/staleness策略、评测题数/重复/具体预算。笔记没有用前代或框架默认值填空。StreamLake超时是主作者访问记录，本审查未独立重试，因此不另背书网站当前状态。 |
| 旧稿误引与原文内部引用 | §9.2–9.3 | 已读旧稿相关段落及引用定义：KAT与Qwen共挂[7]、该段末[7]实际指2603.00729v1，纠错成立。原文§4.2指称V2却引2510.18779；§1引用的V2则是2603.27703，references.bib亦可核实。笔记没有因此声称精读了两篇前代。 |
| 项目映射 | §10 | 对照主目录2026-09-05简报和2026-09-07建议：miles/SGLang/外部harness基线、rh2职责、新审查覆盖缺口、C包未定和咨询建议身份处理正确；没有把通用Gateway/TITO变成原创或把PPO/MOPD变成已批准首版设计。属于已查状态文档支持的设计候选，没有虚构本轮代码审计或训练实测。 |

### 2.3 保留的审查边界

本次是原文与笔记一致性审查，不是报告实验的独立复现；未执行训练、取得作者私有代码、重算内部benchmark，也未查阅所有被引用论文全文。全文未披露不等于互联网上绝不存在资产，初稿对此已有正确限定。

主目录中的项目状态/旧稿链接目标已核存在；这些文件不在当前工作树快照中。主作者仍须在最终发布副本检查跨目录相对链接，不应为了消除工作树缺文件提示而把真实本机绝对路径写入笔记。

## 3. 主作者处理记录

由主作者在完成修订后逐项追加；本审查不预先宣称修订通过。

### 3.1 2026-09-07 修订与证据

独立审查按用户指定使用GPT-6 Astra / high、`fork_turns="none"`；主作者收到完整审查后处理如下。

| 发现 | 处理 | 原文证据与修订核验 |
| --- | --- | --- |
| R1 / P3 | 已采纳。笔记§5.4将“允许未动态复现……”改为“列出未动态复现、但经源码/既有测试/历史/框架推理准确定位根因的情形；奖惩方向未披露”。保留后文无正负号/权重、不能一律当违规的限制。 | Table 2/PDF p24只描述Static Bug Localization；TeX main.tex相应行无明确豁免政策。主作者重新对照已渲染原页与TeX后修订，检查旧措辞已不存在、新措辞存在且其他八条标准覆盖保留。 |

没有其他待修发现；未发现问题不等于作者实验已独立复现。残余来源/配置缺口按笔记§8–9保留。此处记录主作者对R1的核验，未假称审查者再次审了整篇。

交付排版核验另修正本审查覆盖表两处数学竖线的Markdown转义（PPO长度分母、KL方向），仅保持正确表格列数，不改公式含义或审查结论。


---

## 文档 4 / 12：04_E2_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/04_E2_review.md`

# E2 CalibForge 独立精读审查

审查日期：2026-09-07。审查配置：独立 GPT-6 Astra / high。对象：E2 初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md`〕。本轮仅写本审查文件，没有修改笔记或项目实现，也没有再委派审查。

## 1. 实际阅读范围与总体判断

先逐页读取原始 PDF 的完整提取文本，按实际标题与附录建立下面的独立清单，再打开初稿逐项比对；未把初稿或旧摘要作为原文替代。全文为 27 页，正文 §1–5、Algorithm 1、Eq.(1)–(2)、Fig.1–9、Table 1–3、附录 A–F 均在范围内。参考文献页用于确认完整结构和引用出处，没有声称精读其所引各篇论文。另目视复核 PDF p.5 的公式、p.12 的 Table 3/Fig.8–9、p.25 的 Table E1/F.1。

在线核对了 [arXiv v1 页面](https://arxiv.org/abs/2608.06352v1)的正式标题、作者与提交记录，以及[官方 PDF](https://arxiv.org/pdf/2608.06352v1)的版本和页数。来源内容以本地原始 PDF 为主，在线页面用于交叉确认。读取了 manifest〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E2/source_manifest.json`〕 所列九份固定版本 README、配置和源码快照；九份 SHA256 均与 manifest 相符。另检查原始 HF 文件清单的根文件和轨迹相关命名。未下载模型权重、环境镜像或整套训练数据，未运行作者训练/评测代码，未审计 AweAgent 完整 runner。

项目映射检查限于 CURRENT-STATE-BRIEF 的当前状态、边界及未闭合项，以及 2026-09-07 项目一建议的 §3–9 相关内容；没有将咨询建议视作已批准实现。模板要求的后训练内容没有因为暂不用于 SWE 而被略去。

**总体：主要方法、模型关系、附录覆盖、表格转录和因果边界准确。发现一项需补的 P2 数值分母缺口，以及三项 P3 表述/资产落差。没有发现 P0/P1 级错误。完成下面定点修订后可交付为完整精读；本报告不宣称论文实验已复现。**

## 2. 独立覆盖清单与逐项对照

| 原文实际结构与位置 | 独立识别的后训练内容 | 初稿对应与判断 |
| --- | --- | --- |
| 首页、§1 Introduction，p.1–3 | 训练环境必须可执行、可验证且相对 solver 有挑战；论文贡献为任务构造校准与离线 SFT | §1–3；覆盖，不误写在线 RL |
| §2.1 Overview、Algorithm 1，p.3–4 | `V(τ)`、`γ`、验证修复循环、每轮探测、满足条件立即返回、最多 Rmax 后丢弃 | §3、4.1、5.1；覆盖；19/15 与早停的关系还可说得更明确，见 F2 |
| §2.2 Candidate Task Authoring and Validation，p.4–5 | clue、技术研究、多方向选择、规格与安装/资源预试；instruction/environment/tests 联合构建；解答工件与未声明要求检查；fail-first 和隔离自解 | §4.1；实质覆盖，检查时序有一处措辞错误，见 F4 |
| §2.3 Adversarial Solver Calibration，p.5 | 每 solver 独立 sandbox、相同指令；verifier 二元结果；完整轨迹及结构反馈；multi 分歧和 strong-pass/weak-fail 两公式；四态诊断 | §4.2、5.1；公式、角色、诊断与接受信号区别准确 |
| §3.1 Experimental Setup，p.6 | author/solver/teacher/student；100 步/30 分钟、50 轮；2 次蒸馏、200 步/1 小时；成功轨迹过滤；full-parameter SFT；基线重蒸馏；评测与去污染 | §3–8；覆盖，评分有效分母新增疑点见 F1 |
| §3.2 Main Results、Table 1，p.7 | 两底座全表、基线限定、三 benchmark、均值与 SEM/单次运行、百分点增益、迁移 | §7.1–7.2；转录及差值正确，未把全量表写成等成本因果对照 |
| §3.3 Analysis of Synthesized Data、Fig.3–7、Table 2，p.7–11 | 1,263+4,168；16类；pass@3 分类图；能力标签长尾；工件/类型/依赖/测试统计；teacher steps 与 thinking tokens 分布 | §4.5、7.2；覆盖，标签分母、distinct 与总计、步数与推理量区别准确 |
| §3.4 Effect of Solver Calibration、Table 3，p.11–12 | No/Single/Multi/Contrast；各1,300题；保留轨迹并不相同；Single同时得到结果与轨迹；等任务数不等 token/API预算 | §7.3；覆盖，Multi 1,300 与最终1,263的关系已列未知 |
| §3.4、Fig.8–9，p.11–12 | 首次状态19/61/16/4；最终96/4；按完成run记录probe数的15/53/76/93/96漏斗与长尾 | §7.4；值准确，保留了未解释差异；应加算法早停关联，见 F2 |
| §4 Related Work、§5 Conclusion，p.13 | 与环境构造、行为反馈、solver自身反思的区别；作者归因及其证据边界 | §2、9；覆盖，没有借引用扩张为未经阅读的训练事实 |
| A From a Clue to a Calibrated Task，p.18–19 | 传感器日志 clue、24搜索、多方向排除、输入工件、CSV输出、11测试、Pro过/Flash败、自评CRC示例不一致 | §4.4；覆盖，单例搜索/判断不作总体结论 |
| B.1 Removing Procedural Hints after Both Solvers Pass，p.20 | 交易记录修复；8/17步均过；去流程提示后强过弱败 | §4.4；准确，未偷换成去验收条件 |
| B.2 Clarifying Comparison Semantics after All Solvers Fail，p.20–21 | 数据库导出；50/15/26步全败；共有字段比较语义；复测GLM/Flash过、Kimi败 | §4.4；准确，未把规格歧义误判纯难度 |
| B.3 Generalizing an Overly Prescriptive Verifier after an Inverted Outcome，p.21–22 | 强40步败/弱38步过；合法整体加密被逐字段布局测试误杀；修 verifier 后目标关系 | §4.4；准确，没有声称全库误杀率为零 |
| C.1 Tool Interface、Table C1，p.22 | execute_bash、str_replace_editor、finish；持久 runtime，结束后评分 | §6.2；工具面准确，区别于 author web research |
| C.2 Prompt Templates，p.23–24 | system完整工作流、工具、长任务、验证、安全/范围要求；instruction/workdir user包装；必须finish | §6.2；实质覆盖，明确不是完整author/revision prompt |
| D Benchmark Decontamination，p.24–25 | exact14-gram；规范化5-shingle Jaccard；0.30/0.45阈值；路径/测试函数/任务族；蒸馏前删除 | §4.3、9；覆盖，未因正文称full matching rule而虚报完整可执行规则 |
| E Supervised Fine-Tuning Details、Table E1，p.25 | 全参数多轮SFT；最终10epoch checkpoint；全部超参、64 H20；有效batch关系 | §5；覆盖，128与64×1×4正确保留未解，不补TP=2 |
| F.1 Reasoning without Producing the Required Artifact，p.25–26 | regex-log；30B三败、35B三过；交付文件缺失/指定接口验证 | §7.5；准确，未将中间推理当完成 |
| F.2 Committing to Partial Forensic Evidence，p.26 | password-recovery；同样三败/三过；前缀误计长度、片段拼接、23字符约束 | §7.5；准确，未泛化精选案例比例 |
| F.3 Changing State before Preserving Recovery Evidence，p.26–27 | db-wal-recovery；两模型六次全败；5条基础记录与6条WAL；打开数据库先破坏恢复证据 | §7.5；准确，保留更强模型共同失败与schema不足 |
| 固定版本官方资产，manifest所列九份快照 | 数据/模型/镜像引用、README范围、部署示例、运行入口、默认预算、加载跳题、same-session评分与reward约定 | §6.3、8；主要准确；README的已发布轨迹声明应补，见 F3 |

## 3. 分级发现与建议修订

### F1 — P2：数据集规模不能自动当作实际评分分母

**位置：初稿 §6.1、§7.1、§9.2；原文 §3.1 p.6、Table 1 p.7、Fig.3 p.8。** 论文声明使用731题SWE-bench Pro public set并只评测一次，但多项 Table 1 分数不能由整数成功数除以731并四舍五入到小数点后两位得到。例如30.94%的最近整数解为226/731=30.91655%，应显示30.92%；3.26%的最近整数解为24/731=3.28317%，应显示3.28%。35B base的41.29%同样不匹配。并非所有行都不匹配：44.32%=324/731四舍五入后成立。

TB2也有一处独立问题：Fig.3分类题数合计89，Table 1说三次运行均值。若每次均以89题二元结果等权计分，则均值只能是整数总成功数/267；35B base的39.10%不可能由这个口径得到，104/267=38.95131%，105/267=39.32584%。CalibForge两行32.58%=87/267、47.57%=127/267则能对上。这一点由主作者提出核查，审查者已独立计算确认。

**建议：** 原表照录，不擅自“更正”成绩；把731/89标为论文或图中声明的集合规模，同时说明实际有效分母、任务排除或聚合规则不足以核实，列入复现未知项。不能自行推断丢弃了哪些题、每行分母变化、宏平均或多次采样，也不据此断言作者分数虚假。现有SWE-Pro单次分数间百分点相减可作为“报告值差”，不能据整数成功数解释。

### F2 — P3：19%与15%的未解关系应联系Algorithm 1早停

**位置：初稿 §7.4、§9.2；原文 Algorithm 1 lines 7–10 p.4、§3.4 p.11、Fig.8–9 p.12。** 初稿已经写明首次verified probe与completed-run recorded-probe count是不同文字定义，也明确差4个百分点的具体规则未解释；这一点正确。但“区别是原文标注的两种统计口径”容易让读者以为两个量已经能相容。

**建议：** 增一句：在Algorithm 1“首轮满足就立即return”的字面流程下，如果两图覆盖同一批run且记录规则一致，首次目标关系与一probe完成保留应对应；论文没有提供让19%与15%相容的计数规则。这是未消除的原文报告关系，不能由“口径不同”本身解决。不要补造隐藏重试或二次验证步骤。

### F3 — P3：补记官方“成功轨迹已发布”声明与未定位资产的落差

**位置：初稿 §8.2；固定版本 CalibForge README〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E2/calibforge_README.md`〕 的 Released Data。** 该README明确声称release也包含按共享协议蒸馏的successful trajectories。数据卡主要说明任务目录；当前文件清单根文件是README、metadata.jsonl、image_mapping.jsonl等，轨迹相关命名搜索只找到任务内科学计算工件，未定位独立SFT/rollout文件。

初稿“未取得SFT轨迹集”没有写成“官方未发布”，并不错误；但精读公开资产时应保留这个实际读到的声明。建议写“GitHub README称包含成功轨迹；本次在固定HF卡/文件清单未定位可核的独立轨迹资产，也未验证metadata是否承载所称内容”。文件名检索不能证明轨迹绝不存在，不扩大为‘作者未发布’结论。

### F4 — P3：将“构造前检查”改为“进入验证前检查”

**位置：初稿 §4.1首段；原文 §2.2 p.4。** 原文先说jointly constructs instruction/environment/tests，再说Before validation检查初始环境没有解答工件、测试不施加未声明要求。初稿上一句已联合构建，下一句却写“构造前检查”，时序不准确。改成“进入验证前检查”即可，不影响方法主结论。

## 4. 关键数字、公式及预算检查

| 检查项 | 独立复核结果 |
| --- | --- |
| `Cmulti=1[0<Σyi<K]`、`Ccon=1[ys=1 ∧ yw=0]` | 与p.5原页一致；K=3异构模型；是任务保留判据，不是student loss/reward |
| 模型角色 | author/self-solver/strong/teacher为Pro；weak为Flash；multi为Flash/GLM-5/Kimi K2.5；两个Qwen分别SFT；Single为同模型独立subagent且有轨迹反馈 |
| task总数 | 1,263+4,168=5,431；两次teacher尝试名义数10,862；原文无全量过滤后轨迹/token漏斗 |
| 校准预算 | 每solver attempt100步/30分钟，每候选最多50轮；multi150、contrast100是名义attempt上限；75/50为累计attempt小时，不是墙钟/成本 |
| 蒸馏/TB2预算 | 分别200/500步；均1小时attempt/task；teacher每题2次；TB2三run；正文明确的16CPU/32GB不可拿后发YAML4CPU/8Gi替换 |
| 全量主结果 | Table 1全部数字与初稿一致；30B增益24.71/27.68/30.04 pp，35B8.47/3.03/3.85 pp，TB2比最强对应基线6.36/6.75 pp，算术正确；有效评分分母见F1 |
| 四臂消融 | 每臂1,300；轨迹2,466/2,493/2,425/2,561；TB2 22.47/24.34/29.21/31.09；差值1.87/6.74/8.62正确；非等token/总构造预算 |
| 校准漏斗 | 首次19/61/16/4总计100；最终96/4；累计15/53/76/93/96；无精确总run数；初次状态不是最终任务固定版本通过率 |
| 数据画像 | 16类、3,885 distinct tags、中位5；51.6%/82.2%分母为不同标签；19,911工件、362类型、615依赖、45,953测试及中位/IQR/P90转录正确 |
| thinking/steps | CalibForge中位21步/5.3k、CLI-Gym28/4.0k，其他四源中位值准确；更多生成tokens不是更高预设预算的证据 |
| 去污染 | exact14-gram；规范化5-shingle；0.30/0.45；结构证据；D确未给完整布尔组合/任务族列表/剔除量，初稿不假装可逐位复现 |
| SFT超参 | 与Table E1逐项相符；64×1×4=256与global128的条件性不符真实存在；并行布局未给，不能据部署TP8/DP1反推 |
| 模型卡补充 | 两卡均写262,144 configured maximum positions与131,072训练context；SGLang命令为部署示例，初稿新增分层正确 |
| 后发recipe差异 | README示例200与YAML/论文TB2 500确实不同；same-session、跳过加载异常、reward>0和score clamp源码描述准确；不证明全runner隔离或论文实验配置 |

## 5. 无需改动的证据边界与剩余未核项

初稿正确保留了这些重要限制：外部panel分歧不是目标student通过率；纯SFT成果不能冒充RL/OPD；Table 1不等任务规模，Table 3不等token或构造成本；精选A/B/F案例不能推成总体错误率；单次outcome不估稳定性；同一任务可被重写，96%不是固定题提升；“author/strong/teacher同用Pro的偏好风险”清楚标为读者推断；测试/代码公开不等于训练完全可复现。项目映射限定为设计候选、归因上游且不新增治理平台，这与读取的项目背景一致。

仍无法核实：原始候选分母与删除漏斗；各校准run日志、19/15关系；1,300与1,263批次关系；F1有效评分分母；完整去污染程序；SFT样本序列化/token mask/loss分母/过滤阈值与统计；训练有效batch和并行布局；完整author/revision prompt；训练/生产/推理真实总成本；镜像可运行性；README所指成功轨迹的精确资产位置。以上均是“在本轮查阅材料内未能核实”，不是对所有可能资源存在性的否定。

建议主作者将F1补入§7.1/§9.2，定点处理F2–F4，并在笔记§12记录实际审查与修订。保留原文矛盾即可交付，不需要为了消除作者未披露问题而扩大框架审计或新增实验。

## 6. 审查结束前的回读状态

主作者在审查进行中采纳F1–F3后，审查者重新读取了当前笔记§7.1、§7.4、§8.2及§9相关行，确认新增评分分母限制、早停逻辑的一致性疑点、已声明发布但未定位的轨迹资产均已落入笔记，且没有擅改原文数字。原始发现保留在本报告以供追溯。F4已发送主作者，最后处置及笔记§12记录由主作者完成。


## 7. 主作者逐项处置与证据（2026-09-07）

本节为主作者在收到正式审查后追加，保留审查者原始发现不删改。独立审查者通过本线程回读确认 F1–F3 的现稿修改；F4 由主作者按原页作定点更正。

| 发现 | 处理 | 修订定位与复核证据 |
| --- | --- | --- |
| F1 / P2 | 接受，已修订 | 笔记 §7.1/§9.2 区分声明集合规模与实际评分分母。主作者枚举整数 n/731，确认30.94和3.26均无两位小数匹配；TB2 39.10不能由整数/267得到。保持Table 1值与报告值差不动，不补造排除/聚合机制 |
| F2 / P3 | 接受，已修订 | 笔记 §7.4/§9.2/§9.3 直接对照 Algorithm 1 p.4行9–10；在同一run集合与probe记录的条件下应立即早停，19/15仍为未解关系，未添加原文没有的重试步骤 |
| F3 / P3 | 接受，已修订 | 笔记 §8.2 加 fixed CalibForge README Released Data 的成功轨迹声明；HF API原始siblings根文件仅 `.gitattributes`、README、metadata、image_mapping，轨迹名匹配项是科学计算题内工件。本次仅卡片/文件名检查，未穷尽内容，不断言所有轨迹不存在 |
| F4 / P3 | 接受，已修订 | 笔记 §4.1 的“构造前检查”改成“进入验证前检查”。原文 §2.2 p.4 先jointly constructs，再Before validation，时序与原文一致 |

笔记 §12 已替换初稿待审文字，记录实际审查模型、干净上下文、范围和处置。额外作者自查修正 E3/E4/E5 关联编号，区分模型卡最大positions、SFT context与SGLang部署示例；这些不改变论文事实。已核验完整笔记12节、公式和代码围栏、九份快照hash与文档无真实本机绝对路径。剩余来源缺口见本审查 §5 和笔记 §9.2；不为填空扩展源码审计，也不声称作者实验已复现。


---

## 文档 5 / 12：05_N11_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/05_N11_review.md`

# N11 独立正确性与覆盖审查

审查日期：2026-09-07。对象：N11 初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕，包括审查期间作者补入的 §5.1 reward normalization、两类 IS ratio、默认共享分母，以及 §6.3 R3 warning。只写本审查文件，未修改作者笔记、源码或运行配置；未另派审查者。

当前结论（主线程按下方 §7 的最终复核更新）：两份官方正文的后训练章节覆盖完整，主要机制解释可靠；**R1–R5 均已按证据修订并独立复读确认**。下方保留首次审查时 R4 待修的历史记录，其最终处置见 §7。不能把本记录当成端到端运行验证或无条件“通过”。未发现把示例配置冒充受控能力增益或总成本的数字错误。

## 1. 独立来源与目录清单

先读模板和两份官方正文快照，列出以下目录及必须覆盖的事实，再打开初稿比对。两份资料都是工程文档，没有独立附录、实验附录或论文页码；也没有可供补读的 SFT/DPO/安全偏好/数学 RL 实验章节。OPD 属沿代码扩展的相关训练能力，不能倒写成两份网页的实验结论。

证据简称：**U**=`reference/miles`，commit `f2b7c79298a53c53861514d099f7def73bd29f4a`；**I**=`reference/miles-rh2-integration`，commit `98a0272e4158b2c20e3a34d210c79b50159af0f6`。审查实际核过两者 HEAD 与干净状态。下面代码路径相对各自仓库根；快照路径相对 reading_notes。**W** 为 `sources/N11/*online-20260907.md`。远端固定 `d2fc97ce581577e255e494801d7568747d5a10d7` 只核本题涉及的 Agentic 文档及参数约束，不代表审完最新整树。

官方来源：[Agentic Rollout](https://miles.radixark.com/docs/user-guide/agentic-rollout)、[Fully Async RL](https://miles.radixark.com/docs/user-guide/fully-async)。本审查的网页工具成功打开后者，前者返回 safe-open 错误；Agentic 正文核查依赖已存官方 `.md` 快照和固定 U 文件，没有用工具失败填出不存在的原文事实。

| 原文目录（独立列出） | 从原文建立的必查事实 | 初稿覆盖 |
| --- | --- | --- |
| Agentic 导言及 VLM Warning | exact token/logprob/routed experts；session 无 image/video，另走 `/generate` | §2、§3、§9，完整 |
| Configure the wrapper | 两个函数入口、session flag、checkpoint/tito-model；messages 不预套模板 | §3.1，完整 |
| Write the agent loop | async 合同；URL 已含 session；sampling 映射；metadata 和 dict/None 返回 | §3.1、§4，完整 |
| Optional teardown hook | oversampling 先停止在飞推理，再清理外部环境；hook 可选 | §4.2、§6.3，完整 |
| TITO / Leave token ownership to Miles | 全消息重放；首轮模板；复用实际 token checkpoint；只分词新 suffix；控制字段和 prefix cache | §3.2，完整 |
| Choose the session behavior | v1 尾扩展和单 checkpoint 回滚；v2 最深前缀树、不删分支、length 不续；Sample/list；partial/pause/R3；总上下文上限 | §3.3、§6.3，覆盖且区分版本冲突 |
| Pick your `--tito-model` | 无自动识别；固定模板及 parser；自定义 default；模型族注册表 | §3.4，完整且没有把 W 新族套给 U |
| Verify a new model TITO | 注册 tokenizer/FIXED_TEMPLATE；CPU append-only 和 GPU 实际推理两项均须通过 | §3.4、§8，完整，明确未运行 |
| Choose replay matching | strict、loose_tool_call、role_content_only、自定义；匹配失败回滚/分支；存储 token 权威；不协调跨边界 call ID | §3.4，完整 |
| Example | Harbor/SWE launcher、reward、length 和清理接线 | §4、§7.3，补读范围明确 |
| Fully Async 导言 / When to use it | rollout 长尾、两循环、off-policy 代价；调试 loss/reward 时建议同步 | §2、§6，完整 |
| Usage & Examples / Basic usage | train_async + fully-async + class API | §6.1，完整 |
| Examples / Customizations | 三个可见 launcher 的规模与 eval 入口；调度、buffer、eval、metrics 四类自定义入口 | §6–§7，完整；原文“四个”与三行冲突已登记 |
| The fully async schedule / How generation is scheduled | 常驻 worker；整组提交，按 sample 释放额度；trainer 等完整组；定期暂停发布；跨版本 | §6.1–§6.3，见修订 R3 的 group_rm 限定 |
| Arguments: Scheduling options | B 为组，C 为 trajectory，G 为每 prompt 采样数；sample/group 释放方式 | §6.1，完整；代码 `max(1,C//G)` 比网页 floor 更精确 |
| Data path / The data buffer | put/get/get_metrics；aborted/dynamic 在 put，stale 在 get；排序及批级 filter | §6.2，完整 |
| Arguments: Buffer options | factor×B 容量、满时背压；默认 staleness 关闭；drop/retry；dynamic reject 不 retry；custom buffer 接管 | §6.2，完整；版本缺失需按 R1 收紧 |
| Evaluation / Mode 1: Shared engines | 暂停新提交，在飞继续完成；共用上次广播权重 | §7.1–§7.2，完整 |
| Mode 2: Dedicated fleet | 独立 GPU/router/HF snapshot；继承与覆盖 SGLang；不同 TP 重置相关并行量；异步点和 lag | §7.1–§7.2，完整 |
| Mode 3: External backend | CheckpointEvalFn；EvalSkip；调度/日志/回收；外部 API 或服务资源 | §7.1，完整 |
| The weight snapshot pipeline | export/periodic HF 两来源；interval 关系；collective 等待；backpressure/skip；retired+in-flight 存储；串行 eval | §7.1，完整且限定“training never pauses” |
| Metrics / Async rollout metrics | queue/filter/staleness 分母；空/满/过期；30s starvation warning | §7.2，完整；代码与文档分母冲突核验成立 |
| Async eval metrics | skip 各 reason；lag；目标权重与 mixed-version 检查；checkpoint/广播版本区别 | §7.2，完整且没有照抄为 I 准入等式 |
| Performance metrics | engine 并发均衡、cache、router/KV、train/rollout 瓶颈；>90% 是调优预期 | §7.2，完整 |
| Arguments: Logging options | 两个 logger hook；True 跳默认；False 保留；buffer 指标内容另改 get_metrics | §7.2，完整 |

## 2. 发现与修订依据

以下保留发现时的表述与证据，避免已修内容掩盖审查记录；末尾表格记录本审查者实际看到的最新处理状态。

### R1：缺失行为版本的判定必须区分“整组全缺”与“部分成员缺”（中）

初稿 §6.2 的“U 缺版本返回 None，跳过判定；I 对 formal 组缺版本……typed fatal”容易被读成任何成员缺版本都会触发该分支。U/I 的 `miles/rollout/fully_async_data_buffer.py::group_oldest_weight_version`（U:40–43，I:42–45）实际上先**忽略** `oldest_weight_version is None` 的成员，再对剩余版本取 min。I `::_judge_consume_time_staleness`（407–435）只在整组无可解析版本，或 current_version 缺失且组声称 formal 时触发相应 fatal。

应明确：部分成员缺版本而其他成员有版本时，两者仍按已知成员判定；buffer 本身不证明每个 member/leaf/turn 的版本覆盖完整。全缺与缺 current 的 U 回退也应分别说明。公式最好标成“已记录的可解析版本集合的 min”，防止把数据缺口抹成完全可观测。I 对负 lag 的 fatal 不限 formal 组，此点可保留。

### R2：v2 预填 reward 会跳过下游 OPD teacher 评分，需补真实接线条件（中）

§3.3 已正确记录默认 postprocessor 把 agent 的 trajectory reward 写到各叶，§5.2 则说 teacher 字段可由下游 reward processing 产生；两者之间还缺一个实际分支条件：

- U `miles/rollout/session/v2/postprocessor_hub/default_postprocess.py::assign_reward/default_postprocess`：非 None 的 agent reward 写入 `Sample.reward`。
- U `miles/rollout/inference_rollout/inference_rollout_common.py::generate_and_rm`（122–131）：只对 `sample.reward is None` 的样本调用 RM。
- U `miles/rollout/on_policy_distillation.py::post_process_rewards`（403–436）：期待 RM 返回的 teacher scoring payload，再抽取 teacher logprob 或 top-k penalty；普通 float task reward 不是该 payload。

因此，原样保留 Harbor reward 的 v2 路径再把 custom RM 指向 OPD，不会自动补打 teacher 分数；后面的 OPD postprocessor 也不能把 scalar reward 解释为 teacher 响应。补一句须跳过默认 reward 预填或用显式组合评分/postprocessing 接线即可，不需要声称整条 OPD 不可用。也不应通过编写新代码来修这篇阅读笔记。

### R3：sample slot 释放“包括评分”须限定非 group_rm（低）

§6.1 写 sample callback 包括评分阶段。普通逐样本 RM 是如此，但 U `inference_rollout_common.py::generate_and_rm`（110–113）在 `group_rm=True` 时直接返回；组级 RM 在 `generate_and_rm_group` 的 gather 完成之后才调用（179–181），故 sample callback 已释放额度。Fully-async 参数校验没有禁用 group_rm；禁用它的是 session v2。

建议写“通常包括逐样本评分；若启用 group_rm，额度先随 sample task 完成释放，组级评分随后执行，整组评分结束后才作为完成组入 buffer”。这不改变 trainer 消费完整组的正确结论。

### R4：新增 policy loss 段修正函数定位，并标出数值保护（低）

§5.1 引用 `loss_hub/losses.py::policy_loss`，实际符号是 `miles/backends/training_utils/loss_hub/losses.py::policy_loss_function`。rho 的理想定义和 PPO/TIS 两种 ratio 的区分正确，但既然称“代码解释”，应补 U `loss_hub/math_utils.py:18–32` 的保护：PPO 计算 exp 前对 log-ratio 作非有限值处理并 clamp 到 `[-20,20]`；`compute_policy_loss` 再进行 PPO clip。这与 TIS 对 ratio 本身的 clamp 是不同层，不能笼统混成同一个 clipping。

### R5：R3 已知问题补丁已核；U 增量路由条件仍建议明确写入（低）

作者审查期间补入的远端 warning 正确：`sources/N11/arguments.remote-d2fc97ce.py:2992–2998` 不只提示大 payload，还明确 TODO：retract-mode weight updates R3 在 SGLang 有已知问题。不能把“参数能解析”解释为这种组合已验证。

U `miles/rollout/session/server.py:46` 的 `use_addition_r3` 仅在 `pause_generation_mode == "in_place"` 为 True。§6.3 已对 W 的“非 retract 用增量”做版本隔离；再明确这一行 U 条件，可避免读者误把 W 的完整规则应用于 U/I。最新 server 整体实现本审查未核。

## 3. 可保留且已独立核验的内容

1. **Token/训练 mask。** U `session/samples/merge.py::_compute_sample_from_openai_record` 从 output_token_logprobs 取 ID/logprob，生成 mask=1；`generate_utils/sample_utils.py::_merge_sample_pair` 对 observation 增量填 mask/logprob 0。response_length 含对齐增量、不能当 policy token 数；模型 delimiter trim、总序列截断、routing gap 截止前缀等限制解释正确。session 请求与 teacher scoring 的 logprob_start_len=0 用途被清楚分开。
2. **Session/tree 统计。** U v2 `picker_hub/drop_retries.py` 以 commit 序号判 sibling supersession；`default_postprocess.py` 在 picker 后分配共享 completion mask。存储保留分支不等于训练保留全部分支；共享 reward 不等于独立 verifier，均成立。
3. **训练样本转换与损失。** 新增 §5.1 已覆盖 U `miles/ray/rollout/train_data_conversion.py:161–277`：按 prompt 分组、按 rollout 合并同 reward，样本 std+1e-6，identity fallback，custom reward 优先；reward processing 早于 remove_sample 清 mask；默认 rollout_mask_sums 已接入。此处没有把叶当独立采样，也没有把“mask 清零”错写成不影响 baseline。`cp_utils.get_sum_of_sample_mean` 的分母公式与后端另作缩放说明正确。除 R4 的定位/数值细节，PPO 与 TIS 双 ratio、icepop 的新段落与源码一致。
4. **OPD 公式和边界。** U 完整 `on_policy_distillation.py`、`loss_hub/opd.py` 支持 sampled-token、五类 top-k 集合、三类权重、xor 不归一化、multi-teacher 路由。teacher/student scoring detach 后作 advantage penalty 的解释正确；并未把 teacher_p/none 截断估计冒称完整非负 KL。U arguments:2988–3006 的 student-side top-k 需要 legacy API，与 fully-async 排除 legacy 的冲突确实存在。另加 R2 即可补足一个重要的 v2 接线条件。
5. **Queue 与 staleness。** U `fully_async_data_buffer.py` 的 put/get 分工、FIFO 背压、retry 回原 prompt、dynamic reject 不 retry、N 默认关闭和 `lag>N` 的边界均准确。`_metric_consumed_staleness.append` 在接受判定之前，因此“消费 staleness”混入 stale rejected 组的文码冲突确实成立；I 同样存在该顺序。初稿 lag=5/1→avg=3 已明确标成代码推演，未冒称实测。
6. **失败与 timeout。** U `agentic_tool_call.generate`、`OpenAIEndpointTracer.collect_samples` 核实 collect 的 timeout/transport/empty 特殊分支；agent 失败后可成功收集已有 token，并不统一 ABORTED。120s 是 collect/delete 的各自边界，不能当 episode timeout。Harbor README 的 5400s 与客户端默认 7200s 已分清。
7. **版本与发布。** U session merge 只 append 单数 weight_version；I 的普通 Sample span 支持不会自动穿透该独立 merge 入口。该缺口的限定合理。最新参数文档读取范围明确，没有假称整个最新框架已审完。
8. **评测、性能与预算。** 三种 eval、snapshot collective/overflow 会等待、默认四份目录与 4B bf16 约32GB、串行 eval、共享广播版本边界均与完整官方文档一致。Harbor README 的 8 H200、4×8、65536、示例200/20及约10min/step，与 run.py 的 response8192、temperature0.8、TP4/EP8、lr1e-6、KL0.01、clip0.2/0.28 等相符。初稿清楚分开 README 调用示例与 launcher 默认/配方段，没有把局部成本乘成实测总账。GB300 大运行只被当作文档例子，没有补造成绩。

## 4. 残余未核与交付边界

- 本审查做静态原文/代码检查，没有运行 GPU inference、TITO 验证脚本、Harbor sandbox、teacher endpoint、训练或 eval；因此不证明版本组合实际能跑，也不产生任何吞吐/学习收益。
- 没有重新审完整 Harbor 源码、网络认证/隔离、verifier 对抗、flakiness 或污染。初稿将这些列为该文档/示例的披露缺口合理，不能扩大成全生态“不存在”。
- fleet/dispatcher/checkpoint eval 内部实现主要按两份完整官方原文复核，未逐行审查全部评测代码；GLM5.2 Daytona launcher 没有做完整依赖与 resolved args 审计。
- 对 I 完整 patch 链、冷恢复/weights_dirty/逐 engine 发布，以及 rh2 REALIGN 接线没有重新执行测试或做全差分审计；本次直接核 I 的 buffer/staleness 与相关版本入口，初稿其余项目映射的证明依赖作者所列源码/manifest，不应将本审查表述为再次全项目背书。
- 未核最新 d2fc97ce 整树的 session server、loss、buffer 全部行为；下载整份 arguments.py 不等于全量阅读。
- 本文审查的是阅读质量，R1–R5 修订后作者还须核对最终链接、真实符号和交付文件。不得写成新的训练准入制度，也不得在修订前把待修项标为已解决。

## 5. 作者修订对照建议

| 编号 | 笔记位置 | 实际复读状态 |
| --- | --- | --- |
| R1 | §6.2 | 已修并复核：区分整组缺/部分成员缺、current 缺及负 lag；明确不证明所有成员版本覆盖 |
| R2 | §5.2 | 已修并复核：v2 reward 预填会跳过下游 RM/teacher，组合评分须明确接线 |
| R3 | §6.1 | 已修并复核：区分逐样本评分与 group_rm 在 callback 之后 |
| R4 | §5.1 | 待修：`policy_loss_function` 符号、PPO log-ratio 数值保护 |
| R5 | §6.3 | 已修并复核：known R3 issues 与 U in_place-only 增量条件均明确 |

章节覆盖没有待补的大块主文。上表是本次独立审查的具体修订清单；作者修订与最终确认应记录在笔记 §12。

## 6. 作者逐项处理记录（2026-09-07）

此节由笔记作者追加，保留上方独立审查原文及发现时状态。所有变动限于 N11 笔记，不修改训练代码。

| 发现 | 实际处理 | 原始证据与结果 |
| --- | --- | --- |
| R1 | §6.2 已区分整组/部分成员缺失、current 缺失及任意组负 lag | U/I `group_oldest_weight_version`；I `_judge_consume_time_staleness`，独立审查已复读确认 |
| R2 | §5.2 已补 v2 reward 预填→跳过 RM→不会自动调 teacher；不将 scalar 当 teacher payload | U `default_postprocess.assign_reward`、`generate_and_rm:122–131`、OPD postprocessor，独立审查已复读确认 |
| R3 | §6.1 已明确 group_rm 在 sample callback 之后，完成组仍等组级评分 | U `generate_and_rm:110–113`、`generate_and_rm_group:179–181`，独立审查已复读确认 |
| R4 | §5.1/阅读清单修正真实符号；补 log-ratio 浮点、非有限值及 [-20,20] clamp，再 exp；区分 PPO clip/TIS clip | 作者重新读 U `losses.py:62`、`math_utils.py:18–32,254–278`，与修订一致；请求同一审查者复核此窄项 |
| R5 | §6.3 已补 known issues TODO 与 U in_place-only 增量条件 | 远端 d2fc97ce arguments:2992–2998；U server:46，独立审查已复读确认 |

额外补读：默认 reward 先按 prompt group，再按 rollout_id 合并 sibling 并归一化；默认生成 rollout_mask_sums；remove_sample 在 reward processing 后清 mask。依据 U `train_data_conversion.py:59–101,162–271`，独立审查 §3.3 已核实。残余未核范围保持 §4，不因修订改成已验证。

## 7. R4 独立窄复核（2026-09-07）

同一审查者重新读取笔记 §5.1 与 §1.2 阅读清单，并直接对照 U（`f2b7c79298a53c53861514d099f7def73bd29f4a`）`miles/backends/training_utils/loss_hub/losses.py:62`、`math_utils.py:18–32,254–278`。**R4 已修并复核一致**：函数名为 `policy_loss_function`；笔记已区分理想 rho 与代码的 float 转换、非有限值处理、log-ratio `[-20,20]` clamp 后 exp，以及后续 PPO policy clipping 和另一条 TIS ratio clipping。

该结果更新 §1、§5 中保留的“R4 待修”历史状态：本次 R1–R5 均已有对应修订及独立复读确认。此次仅复核 R4，没有重新开展全面审查，也没有更改笔记正文；§4 残余未核范围保持不变。


---

## 文档 6 / 12：06_N13_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/06_N13_review.md`

# N13 独立技术审查

审查日期：2026-09-07。审查者：本任务唯一审查 subagent（GPT-6 Astra，high）。本审查先读取两篇官方英文页面及全部网页内附属内容，独立建立下列清单，然后才读取两份初稿；未修改笔记正文。模板只读。

## 1. 原文独立覆盖清单

### N13a

官方来源：[Why SWE-bench Verified no longer measures frontier coding capabilities](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)，OpenAI，2026-02-23。

| 原文章节或附属内容 | 独立核查的后训练／评测要点 | 阅读情况 |
| --- | --- | --- |
| 导言 | 74.9%→80.9%／六个月；两种失真机制；停止报告 Verified、当时建议 Pro；Preparedness 用途 | 全读 |
| Background | 2023 原始基准、12 个 Python 仓库；修复测试与回归测试；solver 可见材料；1,699 题每题三人独立复核后保留 500 题；操作系统和 Python 版本造成伪失败 | 全读 |
| Too narrow and too wide tests | o3 在 64 次独立运行中不能稳定解决的 138 题；每题至少六名工程师、额外团队复核；59.4%、35.5%、18.8%、5.1% 的分母是 138；非随机子集 | 全读 |
| 两个任务及代码／错误记录 | pylint-4551 强制未指定的 get_annotation；sympy-18199 的三个 issue 与单题描述错配；全部问题描述、PR 片段和错误片段 | 全读 |
| Contamination | GPT-5.2 解出 31 个近乎不可解任务；django-14725／edit_only／Django 4.1；GPT-5 作 15 轮自适应探测器，目标为 GPT-5.2-Chat、Claude Opus 4.5、Gemini 3 Flash Preview；judge、第二 judge 防泄漏及手工终审；非 reasoning 模型选择和能力差距限制 | 全读 |
| GPT-5.2 | django-11451 的提示、响应与 gold patch；新增条件相同，但响应 diff 的插入位置与 gold patch 不同，不能据此声称整份 diff 逐字一致 | 全读 |
| Claude Opus 4.5 | astropy-13236 的提示、prefill、响应、gold patch；文件、方法、四行功能代码和两行注释的回忆 | 全读 |
| Gemini 3 Flash | django-11099 的仅 ID 提示、prefill、响应、gold patch；正则与行号回忆；区分正文模型简称与探测目标正式名称 | 全读 |
| Discussion | 公共材料污染、密码保护及 canary 过滤；实现无关且防捷径的评分；Pro public split 污染较少但非零、未复现完整逐字 gold patch；GDPVal 私人出题及整体人工评分、资源代价 | 全读 |

### N13b

官方来源：[Separating signal from noise in coding evaluations](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)，OpenAI，2026-07-08。

| 原文章节或附属内容 | 独立核查的后训练／评测要点 | 阅读情况 |
| --- | --- | --- |
| 导言 | Pro 更长任务及公开／私有仓库来源；本次 public split 731 题；23.3%→80.3%／八个月；200／27.4%、249／34.1%、约 30%；四种主要问题 | 全读 |
| 分类图 | 全数据集分母；agent／human 分别为过严 14.4%／17.8%、低覆盖 4.1%／9.4%、误导 6.3%／7.5%、其他 1.9%／1.2%、欠规格 0.6%／0.8%；网页无障碍文本把小数舍入，已实际查看图像标签 | 浏览器图像逐项核查 |
| Methodology 与方法图 | 731→初筛标记 286；输入模型尝试、patches/diffs、metadata（正文另明示指令及评分测试）；只对标记子集走两条复审路径；每条输出 broken/not broken 与 category | 全读并查看原网页方法图 |
| Human-supervised agent review | Codex-based investigator 访问仓库和环境、运行测试；邻近代码／仓库惯例用于区分合理歧义与欠规格；多次独立复审，研究者最后裁决；不是全自动标签 | 全读 |
| Human annotation campaign | 每题五名有培训的工程师；先独立看题、测试、gold patch，再看辅助分析；严重度和分歧升级；74% 类别重合；多标签；not broken 众数表述及其统计口径限制 | 全读 |
| Failure modes：Misleading prompt | OpenLibrary-77c16d5 一空格与两空格矛盾；下拉第二例 Qutebrowser-e34dfc6 对相同 URL 的真假要求矛盾 | 两例全部代码与说明已交互读取 |
| Failure modes：Overly strict tests | Navidrome-b65e762 事件路由；未要求的 shouldSend 与 senderCtx 被隐藏测试硬编码 | 全读 |
| Failure modes：Underspecified prompt | Flipt-86906cb 缓存删除题测试认证／CSRF；下拉第二例 Flipt-af7a0be tracing 迁移题测试无关缓存告警措辞顺序 | 两例全部代码与说明已交互读取 |
| Failure modes：Low-coverage tests | OpenLibrary-d109cc7 公共 Markdown notes 要求覆盖数据模型、渲染编辑、API、索引、导出等，测试仅检查构造 | 全读 |
| Discussion | 人类协作 PR 不自然组成独立、完整评测任务；能力增强可辅助审计；建议专家专门构建基准；明确撤回 Pro 推荐；部署／安全判断对评测有效性的依赖 | 全读 |
| Footnotes 1–2 | narrow tests→overly strict tests；wide tests→underspecified prompts | 全读 |

两篇均未给出 SFT/RL/蒸馏训练配方、训练 loss 或硬件配置；这里的代理角色是评测审计／污染探测角色，不能映射成 teacher/student。核查范围包括文章内所有正文、代码示例、图表、方法图、脚注和交互下拉案例；关联 GitHub 仓库、基准完整数据、Preparedness 文档和 GDPVal 独立页面未作全量复核，不能据本次审查声称这些外部资产没有披露。对照初稿后，另外访问 [Django PR #11451](https://github.com/django/django/pull/11451)，确认其 2019-06-10 合并及短提交号 `3ee0834`。

## 2. 初稿对照与结论

### N13a：通过，未发现必须修订的准确性或覆盖问题

审查对象：N13a 初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13a_swe_verified_audit.md`〕。所有独立覆盖清单项目均能在初稿找到对应说明。正式标题与日期正确；没有将 URL slug 当标题。未发现遗漏的后训练方法，也未把评测审计伪装成训练报告。

| 检查项 | 初稿位置 | 对照结果 |
| --- | --- | --- |
| 500／1,699／138 与人审人数 | §3–4 | 正确区分历史构建与本次审计；138 的非随机选择、64 次的作用、59.4% 分母均明确 |
| narrow／wide 与两项任务证据 | §4.2 | 题意、实现依赖、PR 多 issue 范围均与原文相符；没有把案例推成全库统计 |
| 31 道任务及 edit_only | §5.1 | 保留作者判断与推理片段的差别；不制造 31 的占比 |
| 探测者、目标模型、judge 关系 | §5.1 | GPT-5 与 GPT-5.2-Chat 区分正确；正式目标名称及非 reasoning 的作者选择说明已保留；未杜撰 judge 身份 |
| 15 轮及 privileged information | §5.1 | 明确是污染探测预算，不是解题或训练预算；目标不被假定收到全部 gold/test 材料 |
| 三组污染展示 | §5.2 | 已逐项核对；特别正确指出 GPT-5.2 展示 diff 位置与 gold 不同，没有照搬正文的过强“整份精确复制”措辞 |
| 因果、总体污染率及跨提供商比较 | §2、§5–6 | 作者解释与读者推论分开；未声称所有分数增长来自记忆或比较提供商污染率 |
| Pro 的历史推荐与后续变化 | §1、§6、§9 | 正确保留两篇时间点；Pro 并非零污染，后篇撤回推荐不能倒改本篇历史 |
| 训练公式／资源／复现与未披露 | §7 | 在已读全文范围内成立；没有强行补造 loss、OPD 或 infra；关联资产许可没有被统一假定 |

问题编号／严重度：**无须登记的问题，P0/P1/P2/P3 均为 0**。不为凑数提出措辞修改。原文自身关于 GPT-5.2 的叙述与展示差异已由初稿妥善处理，不再登记为初稿错误。

### N13b：通过，未发现必须修订的准确性或覆盖问题

审查对象：N13b 初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13b_coding_eval_signal_noise.md`〕。已覆盖静态抓取遗漏的四个交互标签、六个案例、分类图和方法图；不是仅凭默认案例声称全文已读。

| 检查项 | 初稿位置 | 对照结果 |
| --- | --- | --- |
| 正式标题／2026-07-08／731 public split | §1–3 | 与官方英文页相符；未外推至 private/commercial split |
| 731→286→两条并行复审路径 | §3.2 | 与正文及方法图相符；没有串成 200→249，也没有宣称五人审完全部 731 题 |
| investigator 的访问权限与裁决 | §3.2 | 仓库惯例、运行测试、独立重复和研究者终判均保留；不误称纯自动判定 |
| 人工独立性与材料顺序 | §3.2 | 先独立判断再看辅助分析；同源初筛造成的整体选择依赖得到说明 |
| 200／27.4%、249／34.1%、约 30% | §4.1 | 731 分母正确；不是精确率或置信区间；自行计算的 39.1% 已标明 |
| 图中十个百分比与第五类 | §4.2 | 与浏览器图像逐个一致，包括其他类 1.9%／1.2%；没有用 AX 四舍五入的 0.14 等值替代图像读数 |
| 74%、多标签、249 与众数描述 | §4 | 未把类别重合当 binary accuracy；合理保留未公开的聚合规则缺口，未擅自宣布剩余 37 题皆无问题 |
| 全部六个案例及原文分类 | §5.1–5.4 | 与实际交互内容一致；Flipt 告警次序案例保留原文 underspecified 分类；低覆盖没有被夸大成已证主动作弊 |
| narrow／wide 的术语变化 | §4.2 | 对应两条脚注准确 |
| 净分数偏差、预算、版本与复现 | §3、§4.3、§7 | 没有杜撰净效应、清洗后得分或审计吞吐；模型、样本 revision、预算缺口限定在本文范围 |
| 撤回推荐的原因及污染边界 | §6 | 明确是任务质量审计，约 30% broken 未写成 contaminated；没有外推为所有用途绝对无效 |

问题编号／严重度：**无须登记的问题，P0/P1/P2/P3 均为 0**。原文没有提供完整标注聚合规则；初稿将这一点作为尚未回答的问题，处理恰当。

## 3. 模板与项目映射检查

模板的十二类内容在两篇中被按审计文章性质合并为九节，实质覆盖成立；没有必要为没有训练算法的文章机械补齐训练公式。最终仍需由主审更新两份笔记末尾的“独立审查状态”，该项是本次工作收尾，不是技术内容缺陷。

已只读核对目标主目录中的 CURRENT-STATE-BRIEF（2026-09-05）、项目一设计建议（2026-09-07）的相关段落和 spike-log 顶部。两篇的映射明确限定为设计候选：miles/SGLang/外部 coding harness 承担上游训练、推理与 agent 能力，rh2 负责环境、评分和入训边界；没有变更训练定案、假称已实测改进或新设通用审核平台。笔记中的项目背景链接在目标主目录有对应文件；本审查 worktree 缺少那些背景文件，因此发布到目标主目录时应验证最终相对链接。

本审查没有运行任何基准仓库测试，也不把文章案例等同于独立重现实验。通过仅表示两篇笔记对实际所查原文的准确性、覆盖与证据边界符合要求，不表示两项基准审计本身已被独立复现。

## 4. 主审处理记录

以下由主审在更新两份笔记审查状态、检查最终交付链接后追加实际处理证据。

### 2026-09-07 主审处理

- 准确性/遗漏发现：N13a、N13b 均为 0 项必须修订问题；没有未处理的 P0–P3 条目，无需为凑修订而改写有效内容。
- 已逐项阅读本审查 §1–3，确认两篇的原文覆盖、关键数字、模型关系、预算口径、六个 Pro 案例和图表读数均有定位。
- 已更新两份笔记的审查状态与完成口径，并保留 GPT-5.2 展示 diff 与 gold 的差异、Pro 标签聚合规则缺口及无完整重现实验的限制。
- 版本补记：主目录 HEAD 已只读核实为 `ce2009f879cf38071d7898a1387e01d4e27741d6`；两份笔记明示背景文档含未提交内容，仍按实际文档日期/内容作映射。
- 发布范围限定为两篇笔记、本审查及 `sources/N13/` 的四个必要来源记录/图文件；未修改共享索引、旧稿、模板或训练代码。

- 发布后核验：7 个授权文件逐字节一致；最终主目录中 23 个 Markdown 相对文件链接全部可解析；Markdown 无真实本机绝对路径。原目录无同名成品，未覆盖此前笔记。


---

## 文档 7 / 12：07_R2_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/07_R2_review.md`

# 07 / R2 Nemotron 3 Ultra 独立审查

审查日期：2026-09-07。结论：固定初稿未发现重大训练语义错误或整块后训练主题遗漏；有一处应收紧的事实表述（F1）。独立来源审查已完成；作者已于2026-09-07完成F1修订，具体处置见§6。

## 1. 身份、版本与方法

- 主任务：`01a07827-1e2f-78c3-8c14-1d222dda34c7`；实际 `gpt-6-astra / high`（主作者已核本地 session）。
- 审查子任务：`01a0782d-89ca-7723-ac6f-947eb979e7d7`；agent path `/root/r2_independent_review`；实际 `gpt-6-astra / high`。审查者直接读取自身 session 的 `session_meta` / `turn_context`，确认 UUID、父任务关系、model 与 effort。按本任务授权以干净上下文创建；未递归派出 agent。
- 来源：NVIDIA，*Nemotron 3 Ultra: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning*，封面 2026-06-09，65 页；[官方 PDF](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf)。本次直接读取指定本地原 PDF；线上同版 `cmp` 结果由主作者提供，不冒称审查者重复下载验证。
- 固定被审版本：R2_nemotron_3_ultra_draft_20260907.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R2/R2_nemotron_3_ultra_draft_20260907.md`〕，385 行。它是将来 `R2_nemotron_3_ultra.md` 的冻结内容副本；其中相对链接按最终笔记所在目录解释。未修改冻结副本或正文。
- 先从原文标题、章节与唯一附录建立以下覆盖，读完全部 §3 和附录后才打开初稿逐项比较；相关 §2/4/5 亦单独核对。PDF 页码均为物理页，等于该报告印刷页；通过 `pdftotext -f/-l` 按物理页提取，没有用全文中的 formfeed 个数推页码。
- 关键图形/公式回原始渲染页目视：p.2 图1、p.21 图10及式1–2、p.22 式3与 SWE 段、p.30 式4及表6、p.65 图17。其他表格以原 PDF 按页提取的完整表、表注与相邻正文交叉核查。
- 公共任务、模板、第一批质量报告已读。项目映射仅核 09-05 简报、09-07 项目一建议相关段与 `rh2/src/repoharness2/adapters/miles/group_admission.py` 的职责说明；没有全仓审计、训练运行或复现实验。

## 2. 独立覆盖结果

| 原文范围 | 从原文独立检查的内容 | 初稿对应与结论 |
|---|---|---|
| §3、§3.1，p.15–20 | 学生两阶段 SFT；long context、efficiency/control、安全、搜索、terminal、会话工具、SWE、数学/证明、science、chat、competitive code、CUDA、RTL、多语言；packing | §3.1–3.2 全覆盖；包括 chat 只训最后回应、截断 `</think>` mask、两条不同翻译流程；F1 为小幅证据收紧 |
| §3.2，p.20 | 统一 RLVR 全领域、profiling、Gaussian curriculum、异步 GRPO、batch/rollout/长度 | §3.1/3.3/5 覆盖；未把引用 Super 等同已披露完整 Ultra 算法 |
| §3.3.1–2，p.20–26 | 三 policy 与 sampled-token MOPD；全部 11 类 teacher；SWE/PivotRL、office、search、terminal、工具、usability、agentic safety、chat/GenRM、IF/factuality、STEM、competitive coding | §4–5 全覆盖；STEM 全部制数、40B token mixture、非 STEM RL 已核，无用 SWE 重点替代其他领域的问题 |
| §3.3.3–5，p.27–29 | warmup、两轮 teacher recovery、解释边界、logit matching 负结果、未做的 SFT foundations、长程 MOPD 低效与多数单轮 rollout | §6 全覆盖；区分未系统实验与实验无收益 |
| §3.4–5，p.29–31 | MTP 训练/推理状态不一致、冻结主干、forward KL 与分母、acceptance length；三种推理模式及 medium 奖励长度调整 | §5.3/3.3 覆盖；MOPD 与 MTP 的 KL 方向、分布粒度没有混淆 |
| §3.6.1–3，p.31–36 | MTP 加速、one-step async、故障构成、Slurm/Ray、拓扑/NUMA、checkpoint、JIT、vLLM、存储；future work | §7.1–7.2 全覆盖；局部速度与全训练成本分开，未来恢复功能未写成已完成 |
| §3.7.1–3，p.36–40 | 全套 agentic/推理知识/IF/长文/多语言评测；模型卡采样参数；held-out gates；数学 generate–verify–refine | §8 全覆盖；关键成绩保留任务、单位、预算、版本和最终/中间 checkpoint 区别 |
| A.1–2，p.64–65 | TauBench、ProfBench、BrowseComp、FAB 具体协议；五任务类别、至少两种训练 harness；跨 harness 图17 | §8.2 全覆盖；所有 Ultra 图像数值已逐项对读，图17未被误解成多 harness 训练的因果消融 |
| 相关 §2，p.3–14 | 架构/MTP、预训练数据、LC、两次发散与 routing 指标 | §2 准确概要；Nano/家族底座消融未冒充 Ultra 后训练收益 |
| §4.1–6、§5.1–2，p.41–51 | BPE/scale/cache/Hopper 负结果、PTQ 资源、精度与引擎、不同服务工作点、Mamba state、并行/PD/all-to-all/chunking/padding | §7.3–7.4/8.3/9 覆盖；Super 仿真缓存实验没有写成 Ultra 已发布方案 |

本篇报告没有另外隐藏的后训练附录；p.51–63 为结论、贡献者和参考文献区域，p.64–65 为唯一附录 A。未把每篇被引论文都纳入独立精读，也未用它们的默认参数补 Ultra 未披露项。

## 3. 八组关键核验

1. **模型关系准确。** 图10目视确认 coding teacher 的实线来自 STEM teacher；chat2、conversational-tool2、SWE2、office2 来自 MOPD1。p.26 competitive coding 文字也明确从 General Reasoning Teacher 继续 RL。p.23 office 初始化为完成 general SFT 的 Ultra。初稿保留概览图/概述与细节差异，未强制所有教师都从同一个 checkpoint 分叉。DeepSeek-V4-Pro 数据生成者也没有被混成在线 Ultra STEM teacher。
2. **公式、概率身份及分母准确。** 式1 为学生轨迹上的负 reverse KL；式2 的 advantage 是 stop-gradient 的 teacher 减 proximal logprob；式3 的 `c=prox/behav` 与 `r=current/prox` 分开，PPO clip 作用于后者，IcePop 为 `m_t`。印刷目标是 token sum 后取 expectation，没有 `1/H`，不能直接证明代码实际 normalization。式4 确认为 `KL(backbone || MTP)`、full distribution、`T²/(N_mtp|A|)`，T=2、N=7；初稿重写与原公式一致。
3. **预算与失败处置没有过度外推。** SFT 两阶段的长度/样本/LR/warmup，MOPD 1024 prompts×1、192K，SWE 192K/200 turns，MTP 12K steps/batch64/8K 均核对。§3.2 的 8192 原措辞与 STEM 128 prompts/global batch2048 的旁证并存，初稿保留单位歧义合理。p.22 未完成 loss mask 仅明列 max turns 或 agent/eval timeout；负 advantage 仅指 offending reasoning/tool tokens；group 统计、补采及通用 role mask 未给。初稿没有把这些空白填成确定规则。
4. **全域数据数字和训练领域正确。** 安全 135K、商业许可 OpenResearcher 21.7K、terminal 370K conversations、数学 1.8M/1.9M、code 1.2M/1.0M/1.3M、CUDA约100K、RTL约1.2M 单位不混。STEM 的 95,164 数学题、545,431 COT/TIR、5,751 proof 题/82,737 samples、40B generated tokens 四类配额、3,000题内部评测与 coding 3.5K 难题均吻合。语法/格式过滤没有升级为全部语义正确性证明。
5. **消融和负结果准确。** 表4 Warmup 为 warmup 后 MOPD 的结果；表5 recovery 的分母是 teacher−RLVR。HLE 16.9%、Terminal 172.7% 与表定义一致；LCB MOPD1→2 90→89、GDPVal持平、IMO SFT→RLVR下降都保留。teacher-support 解释标为作者解释，full/top-k matching 不佳没有推广为普遍定律，未系统评估 foundations 没有写成失败。
6. **系统速度和成本分母准确。** 图12 1.46×为 RLVR 平均每步 rollout generation；图16 2.89×为 BS1 的特定推理工作点。56/36/8 是软件故障内部构成。+20% 拓扑/+10% NUMA、checkpoint 暴露阻塞和 JIT 初始化均各自限定。表9组件合计38.4但总值38.8、表15正文42min/表45min均确为源内差异。p.1直接给5.9×/4.8×/1.6×，图1另提供引擎与测量条件；不应单凭图中四舍五入柱高重新改4.8×。
7. **评测与 harness 证据边界准确。** A.1 的 ProfBench 256K/无context management/16次，Tau用户GPT-5.2 low/8 trials，FAB 200 validation题而非337私有test、三次judge取mode均吻合。图17 Ultra SWE一行65.0/67.3/70.4/60.3/69.9/70.3/21.1/avg60.6，Terminal55.1/46.7/52.1/47.2/52.8/52.6/35.5/avg48.9逐项通过。表5 TB2.0与主表2.1、SWE71.7与70.7、图17另有差值均未擅自合并。数学173/210等为graded score，128起始证明尝试不是pass@1。
8. **旧稿纠错和项目边界有依据。** 对读旧《重定位审核》§2.3/T3与配方矩阵§7.2，确有 routing/top-p replay 归因及“不修改 provenance loss mask”的原句；本版 Ultra §3.6不支持前者，p.22不支持后者。初稿正确撤回过强结论，并保留 teacher sampled-token logprob、profiling、多 harness 等有来源事实。项目映射把 consume-time staleness 裁决留给 miles，符合所核 `group_admission.py` 注释；没有把 NeMo 通用优化升级成 rh2 必造组件。

## 4. 实际发现与修订建议

### F1（小修，事实限定）：安全生成的两阶段没有在本篇明确排序

- 初稿位置：§3.2 Safety 表格，冻结稿第72行，写“先回应/后推理的两阶段构造”。
- 原文依据：p.16 §3.1.1 Safety 称“two-stage response and reasoning generation framework”，随后说明 reasoning trace 会反思安全规范、final response 要一致且合规。这段没有显式写先生成 response、再生成 reasoning。
- 问题：初稿将英文并列顺序变成了确定的数据生成时序。本审查不能断言该顺序实际上错误；结论是它超出了本篇已读证据。报告引用 Super 也不能代替本次对相应外部段落的实际核查。
- 建议：改成“回应与推理的两阶段生成”，保留其安全反思与最终回应一致性的功能。如确需保留先后顺序，须另给已实际阅读、明确说明顺序的来源定位。
- 其他 safety 数量、翻译工具、阈值、过滤比例和语言均无修订需求。

没有为了凑发现数而将作者原有的已披露边界、合理精简或印刷数值差异列成初稿错误。没有发现需要新增整节后训练内容的遗漏。

## 5. 资产检查与剩余限制

审查者另读主作者补充的 HF metadata 快照及 Evaluator reproducibility 快照。四模型 public/non-gated 与各自 SHA 在 metadata 中可查，可由作者补到资产栏；这属于固定初稿之后的新查阅证据，不是冻结初稿错误。Evaluator 当前 v0.2/v0.3、Tau2与“Tau Bench 3未onboarded”并存、terminal Hard/2.0 等描述，初稿对当前入口和报告版本的区分准确。审查者没有独立在线验证这些快照，也未下载权重、检查许可证全文或运行配置。

来源仍不足以回答：SWE 环境/任务漏斗、完整训练 GPU-hour、失败样本 group 统计和补采、实际 loss normalization、IcePop阈值与完整 role/pivot/context-reset mask、精确 teacher 冻结规则、版本发布与消费协议、全套最终评测预算和生产配置。这些空白不是本轮遗漏；初稿已按相关正文与附录的实际披露范围处理。

## 6. 作者修订回填

2026-09-07，主作者收到真实审查结果后修订：

| 发现/补充 | 处置及证据 | 状态 |
|---|---|---|
| F1 安全生成顺序超出本篇披露 | 最终笔记〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R2_nemotron_3_ultra.md`〕 §3.2 Safety由“先回应/后推理”改为“回应与推理的两阶段生成，使安全反思与最终回应保持一致”；依据p.16原段，未引入未读Super细节 | 已修订，主作者回读原段并检查差异；无需再作独立全文复审 |
| 审查期间新增资产证据 | 正文§9加入四模型HF public/non-gated及metadata revision链接，许可证仍只写metadata标签，保留未读全文边界 | 已补充；不改变论文训练事实 |
| 项目代码引用精确性 | 正文§11首次提DefaultDataBuffer.get时补 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py`，主作者实际读get实现并沿用integration commit | 已补充；没有修改代码或扩大审计 |

固定初稿保持原385行未变；本节记录的是作者处置，不冒称审查者又逐句复核修订稿。作者完成最终正文、审查和来源说明的本地文件/导航链接、格式与授权写入范围检查后，将专属成品发布回主资料目录同相对位置。

发布核验（2026-09-07）：最终正文、审查、来源说明三份Markdown共32个本地文件链接/导航锚点已通过检查，无格式诊断或本机绝对路径。固定初稿385行保持原样，F1只修改最终正文。已按授权发布 `R2_nemotron_3_ultra.md`、`reviews/07_R2_review.md` 与 `sources/R2/` 到主资料目录同路径；未修改共享索引或其他任务成果。


---

## 文档 8 / 12：08_R13_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/08_R13_review.md`

# R13 Kimi K3 独立精读审查

审查日期：2026-09-07。结论：固定初稿覆盖了要求范围内的后训练正文、部署训练、评测与附录；未发现重大算法错误、关键数字误抄或整块主题遗漏。发现两项轻微措辞问题，另有一项图表身份边界建议补充，详见 §3。此结论是阅读审查，不是训练复现或实现正确性证明。

## 1. 审查身份、版本与独立性

- 主任务 ID：`01a07827-1e44-7133-85d7-65aee3707e7f`；派工主任务 ID：`01a077c4-9f0d-7ef0-a40a-688b42f1b294`。
- 独立审查 agent ID：`/root/review_r13`，为调度器返回的 canonical ID；未获单独 UUID，不把根任务环境变量当作子任务 ID。
- 实际调度配置：`gpt-6-astra` / `high`，干净上下文 `fork_turns="none"`，由父调度器配置与记录确认；本审查未再派 agent。
- 被审固定版本：R13_kimi_k3.draft_20260907.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/R13_kimi_k3.draft_20260907.md`〕，371 行，日期 2026-09-07。该副本中的相对链接按正式笔记目录解析；审查期间正文保持固定。审查者只写本文件。
- 来源：本地 47 页报告〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/k3_tech_report.pdf`〕、[arXiv 官方记录](https://arxiv.org/abs/2607.24653)、v1 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/arxiv_v1.pdf`〕、v2 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/arxiv_v2.pdf`〕及完整两版源 TeX。官方记录确认 v1 为 2026-07-27、v2 为 2026-08-07。下文页码均指本地报告物理页。
- 依赖核验仅限 K3 明确引用的 K2.5 策略优化：K2.5 v1 p.8 §4.4.2 Eq.(1)，同时对照 原页〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/k25_page-08.png`〕及 `sources/R13/k25_tex/4-pipeline.tex`。没有把 K2.5 全文配方认作 K3 事实。

执行顺序：先读公共任务、模板和第一批质量要求，再从 `main.tex` 的包含树独立建立下表，读完原文对应部分后才通读固定初稿。未先读作者的旧笔记、覆盖底稿或旧结论。原文提取、公式页和图表页可复用，但判断由本审查独立作出。

| 原文范围 | 独立检查内容 | 初稿覆盖结论 |
| --- | --- | --- |
| §1–3 | 架构/预训练概要；细查参数单位、上下文课程、视觉初始化、路由、精度及 cosine/WSD 条件 | §1–2 已覆盖；比较条件有一处措辞修订 |
| 全部 §4.1 | SFT、三域九专家、effort 课程、partial rollout、GRM、MOPD、QAT、draft 训练 | §3–4 完整，无阶段或教师关系颠倒 |
| 全部 §4.2 | 白盒 harness、图谱合成、可验证搜索/专业/视觉任务、kernel、个人助理、AET、webdev，含图9–10 | §5 完整；未将不同域 verifier 规则不当合并 |
| §5.1–5.2 | KDA/KCP、MoonEP、内存与视觉 encoder 概要；核影响后训练的状态、梯度和路由机制 | §6.4 已概要覆盖，未冒充 rh2 应自建能力 |
| 全部 §5.3–5.4 | 共置、CPU/NVMe/KV 生命周期、限流、非 policy forward、三类 sandbox、prefix 一致性、kernel 与 fleet 调度 | §6 已覆盖；正确区分 RL 与在线 serving |
| 全部 §6、四份输入表 | 主套件配置及例外、所有能力域、内部评测、网络安全与失败、第三方快照、费用图 | §7–8 完整；图13标签可补明确身份边界 |
| 全部 §7–8 | 六类案例、预算、模拟芯片、MiniTriton 输给基线的点、结论 | §7.6 覆盖；没有把案例与模型训练曲线混淆 |
| 附录 A–F | A 为贡献名单；B–E 阅读推导并核正文关系；F 全读，含 options、preserved thinking、typed tools、pure-JSON mask | §1–2、§6.3–6.4 覆盖，无独立后训练附录遗漏 |

版本核验重新对两份 PDF 逐页提取并去空白比较，差异确实只出现在 p.1、41、42；本地报告与 v1 技术正文一致，但不是同一字节文件。两版源文件差异落在 §2 归因/引用、§5.2.3 引用、§5.3 开头说明、首图绘制、贡献与参考文献；§4、§6 所有表、§7、技术附录无实质增删。首图 v1 PDF 的数值与 v2 TeX 数据逐 panel 对照相同。v2 的判断以源 TeX 为准，未拿有 Poppler 警告的提取文本证明全文无变化。

## 2. 关键核验与没有发现的问题

1. **模型关系。** §4.1.1–4.1.3：旧 Kimi 领域模型生成初始 SFT 数据；K3 三个 broad domains × low/high/max 得九个 RL policies；各域先 max 再预算退火。专家轨迹供 SFT 和 MOPD，但报告没确定一个额外串行 SFT 阶段。初稿全部正确，并把 MoE 896/16 与九个独立 policy 分开。
2. **继承算法。** K3 p.13 明确 follows K2.5；K2.5 原页同时存在 ratio Clip / 文字 log-ratio 边界、正则求和作用域、minimize 与目标符号的歧义。初稿没有把它修成伪精确 K3 loss；K2.5 生成 token 分母与 K3 prompt 数 N 的区分正确。原式没有 value/GAE 或标准差归一化项，但这不证明内部不存在任何未披露变体。
3. **组与预算。** p.13 的活跃 NK、完成比例 λNK、未完成下轮优先恢复、同题 K 全完成才送优化都已保留；不能据此声称取消所有同步阶段。一般任务计 thinking tokens，agentic 计累计输出含工具参数；超预算覆盖 reward 为 −1，并非已披露 drop 或即时硬终止。GRM 的 verbosity 自动输比较是另一机制。
4. **MOPD/QAT/draft。** p.14 Eq.(15) 的 teacher/student 方向、学生 effort 条件、stop-gradient 和裁剪正确；反向 KL 只在未裁剪等限定下作数学解释。top-k 无明确优势得到保留。QAT 的 routed expert MXFP4/激活 MXFP8与高精度 shared experts 区分正确。Eq.(16) 是接受率负对数；draft 仅更新 draft 层及融合投影，target 冻结，七步展开和 `[0 0 I]` 初始化均正确。
5. **数据、评分与量纲。** kernel 数值错误零分、匹配 expert 性能 0.5、趋近 roofline 趋近1；webdev 构建/运行/伪造零分；AET 最终状态、公开诊断与 hidden 场景分离；个人助理按事件评分均有覆盖。51,219,741 是训练及评测 sandbox 创建总数，1,505,678 是镜像数；133/49 ms 为最低延迟、98% 为等待占生命周期、6.5× 为 workload overcommit，初稿没有换成题量、均值或总节省。
6. **状态与模板。** §5.3 的 write-back、CPU KV pool 释放、NVMe offload、gradient-buffer 非 policy forward未被混成统一持久状态。§5.4 命中需 MLA 与所有 KDA group 具有同一边界，非每512 token必有 checkpoint。附录F的 preserved thinking不等于全历史 token 都进 loss；pure-JSON fallback 是明确 mask 的特例，初稿没有扩张。
7. **评测、图表与负结果。** 表2数值、DeepSWE 67.5/mini-SWE-agent 67.3、Terminal 跨 harness best、H20/Harbor条件、BrowseComp 91.2/90.4、ZeroBench pass@5、Faithfulness 1−幻觉率、Webdev 净胜31.0点已核。图8无数值刻度且有波动；图10单例进度不是总体成功率；图13(b) medium/high/max 黑线属于 Sol；图15含落败点。内部14/36和外部0/41网络安全结果未合并，研究级推理及行为纪律短板保留。
8. **案例与项目映射。** kernel最多24h、nano芯片48h及RTL模拟>8700 tokens/s、MiniTriton L20/梯度参照等口径准确。项目映射窄读了两份状态文档及初稿所引四个符号；主仓 `ce2009f879cf38071d7898a1387e01d4e27741d6`、miles集成 `98a0272e4158b2c20e3a34d210c79b50159af0f6` 均现场核对。fully-async、OPD输入、KEEP_FULL/零方差、consume-time staleness及可信投影的责任划分与初稿相符。没有运行GPU或全仓审计。

## 3. 实际发现与建议

### R1：摘要将 on-policy 简写成“在线”不够准确（轻微，建议修订）

固定初稿第3行称“多教师在线蒸馏”。“在线”主要描述时间/更新方式，不能精确表达由学生当前策略生成监督所用前缀和 token 的采样关系，也不能据此确定教师在线更新。原文 §4.1.3 正式名称为 Multi-Teacher On-Policy Distillation；初稿 §4.4 本身已经解释正确。

建议摘要改成“多教师 on-policy 蒸馏（MOPD；由学生策略采样）”，与正文语义对齐，不改其后公式或继承结论。

### R2：cosine/WSD 比较加入了未披露的“固定硬件”（轻微，建议修订）

固定初稿第292行写“固定硬件/参数分别优化后cosine优于WSD”。原文 §3.2 p.10–11、`tex_v1/3-pre-training.tex` 的条件是固定 minimum learning rate，并强调同模型规模和训练 token 预算下两者最优 peak learning rate、batch size 不同，因此分别做 scaling-law search。该段未给硬件控制条件。“参数分别优化”也应明确为超参数，以免混成网络权重。

建议改为“在相同模型规模与训练 token 预算、固定最低学习率并分别搜索各自最优峰值学习率和 batch size 的比较中，作者观察到 cosine 最终 loss 低于 WSD”。这是预训练观察，不外推为 RL schedule 结论。

### R3：费用图的比较模型标签值得单独保留（证据边界补充，不认定初稿误报）

固定初稿 §8 第298行正确解决了 K3 medium 的误读，但图13(b)另有 `Claude Mythos 5 (max)` 标签，并以1M/3M/10M tokens标三个点；主表2和正文主基线使用 `Claude Fable 5`。证据见 p.32 原页〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/page-32.png`〕及 `tex_v1/figures/score_cost_charts/browsecomp_score_cost_linear.pdf`，v2沿用同图。

应补一句：费用图包含 Mythos 5/Opus 4.8/Sonnet 5 等标签，不能未经说明把 Mythos 5 曲线换名成主表的 Fable 5。这里可能是图采用了另一比较基线，**现有证据不足以断言作者图错或两名称是同一模型**；无需更改已有 K3费用和medium归属结论，也不必追索无关模型资料。

本审查没有把视觉上难以精读的费用点位当作新的数值冲突；没有发现支撑“成本点抄错”的充分证据。

## 4. 未消除的来源限制

跨迭代行为概率版本、旧权重KV有效性、完整token mask与loss reduction、MOPD teacher刷新/冻结和tokenizer接口、SWE数据漏斗/污染筛选、总训练成本及组件等预算消融仍无法从已查全文恢复。初稿将它们明确列为缺口，没有用常见框架默认值补全。附录B–E审查深度为理解推导及核对笔记概述，不是对每项数学证明另作形式化验证。

## 5. 作者修订处置（由主作者收到审查后追加）

审查交付时：R1、R2待作者修订；R3待作者选择补充或说明不采纳。本审查者尚未声称修订已落正文。主作者应在此逐项记录实际处置、日期与证据；无需重写固定初稿。

### 2026-09-07 作者处置与交付核验

主作者在收到完整审查文件及审查者完成确认后修订正式正文，固定初稿未变。三项均采纳：

| 发现 | 处置 | 定点依据 |
| --- | --- | --- |
| R1 | 摘要改为“多教师 on-policy 蒸馏（MOPD；由学生策略采样）” | K3 §4.1.3/Eq.(15)，原公式与下文语义保持 |
| R2 | 删除“固定硬件”，明确同模型规模/训练token预算、固定最低LR，独立搜索peak LR/batch | §3.2 p.10–11，`tex_v1/3-pre-training.tex`；同时说明未给硬件控制条件 |
| R3 | §8追加Mythos5图标签、1M/3M/10M点及Fable5正文的身份边界，不判同名或作者错误 | 图13(b) p.32，v2沿用同图 |

审查者另指出原PDF链接在隔离worktree缺目标文件。该链接 `../../pdfs/k3_tech_report.pdf` 对最终主资料发布位置正确，主目录的原PDF已实际确认存在；无需把本地报告链接替换成不同文件身份的arXiv v1。发布核验按最终主目录位置检查。固定初稿归档的内部相对链接继续按正式笔记基目录解释，未为链接重排篡改被审版本。

以上是主作者修订与回源核验，不冒称审查者做过第二轮全文复审。残余未披露项沿用§4。

发布后核验：2026-09-07 已把正式笔记、审查及专属 `sources/R13/` 复制回主资料目录同相对位置；共113文件逐字节对照一致。正式笔记与审查共23个本地文件引用在最终位置均存在，导航6个锚点齐全，数学块开闭配对，无本机绝对路径；新增正文/审查的whitespace检查无诊断。未修改共享README、SOURCE_CATALOG、其他任务笔记或代码；未commit/push、训练、租GPU或下载权重。


---

## 文档 9 / 12：09_R4_N10_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/09_R4_N10_review.md`

# 任务 09：R4 / N10 独立全文审查

审查日期：2026-09-07。结论：两份固定初稿已覆盖全部后训练正文及技术图表，未发现整块主题遗漏或重大算法、数字错误。发现一处把停止条件扩大为淘汰条件的事实表述，另有两处低优先级的来源归属/流程表达建议。以下 §1–4 保留独立审查发现；§5 记录主作者收到报告后的实际修订。

## 1. 身份、版本与边界

- 主任务 ID：`01a07827-1e44-7133-85d7-658445c04597`。
- 审查任务 ID：`01a07831-76f5-7ae1-8211-2dc348e68bbd`；canonical agent name：`/root/review_r4_n10`。子任务 ID、父子关系及实际 `gpt-6-astra / high` 由主作者根据会话日志 `SubAgentActivity/session_meta/turn_context` 核验后回传；不是从继承的环境变量猜测。主任务实际配置同为 `gpt-6-astra / high`，由派发方核验。
- 本审查从干净上下文接受原文与文档入口；先读取原文目录、全文与图表，再对照固定稿。没有再委派子代理。
- R4：`arXiv:2605.26494v1`，2026-05-26，35 页；另核 `v2`，2026-07-30，35 页。读取两版官方 TeX、PDF 提取文本及版本差异，并复用原页渲染。页码按 PDF 物理页，p.2 起与印刷页一致。
- N10：[官方 Forge 文章](https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm)，2026-09-07 固定 HTML/文本及五张图；页面日期 2026-02-13，JSON-LD `datePublished/dateCreated=2026-02-13T04:18:07.300Z`、`dateModified=2026-02-13T08:46:39.885Z` 已核。
- 被审固定稿：R4 初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R4/R4_minimax_m2_series.draft-20260907.md`〕、N10 初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/N10_minimax_forge.draft-20260907.md`〕，日期均为 2026-09-07。文中行号均指这两份固定稿；其内部链接以正式文件所在的 reading_notes 根目录为基准，未将归档副本的相对位置误判为正文链接错误。
- 公共要求、模板及第一批质量复查均已读取；项目窄查主仓 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`，miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`，实际 `git rev-parse` 与指定值一致。
- 仅写本审查文件；未改正文、来源或代码，未运行训练或声称复现实验。

## 2. 从原文独立建立的覆盖结论

| 来源范围 | 独立核查内容 | 对照结论 |
|---|---|---|
| R4 摘要、§1–3 | 架构与预训练概要；完整阅读影响后训练的 hybrid SWA 负结果、MTP 复制初始化/短暂冻结/联合训练；Tables 1–3、Figs.1–2 | R4 §2、§7.2–7.3 覆盖，未把小规模架构消融充作 M2 RL 消融 |
| R4 §4.1 全部三分支、Fig.3 | SWE 六阶段与任务类型；AppDev 专家 query/prompt distillation/AaaV；Terminal-Gym 来源、四档筛选、三阶段合成与难度校准 | R4 §3 覆盖；仅重试上限之后的处置表述需收紧，见 F1 |
| R4 §4.2 全部四领域 | 搜索证据与开放报告 rubric、GDPval office 合成、金融工具反推、workbook walk/重算验值、幻灯片生成与编辑/视觉验收；共同 teacher/scaffold 扰动及双轴 pairwise 筛选 | R4 §4.1 覆盖，已保留 GDPval seed 与评测独立性缺口 |
| R4 §4.3–4.5、§5 | 推理 query/response/compute allocation 与四层质量检查；长 CoT 写作/QA/多轮与有无工具；persona、self-play、Best-of-N、RLHF 去偏/entropy；SFT rejection sampling 与 interleaving | R4 §2、§4、§5 覆盖；没有遗漏非 SWE 后训练，也没有补造完整安全训练配方 |
| R4 §6.1、Eqs.1–7 | 请求级 action/state、episode 信用分配、CISPO 分母与 stop-gradient、baseline/奖励、四域分阶段混训 | R4 §5 覆盖；token/step 索引、mask、baseline、折扣和实现缺口保留充分 |
| R4 §6.2、Eq.8、Figs.4–6 | 三层系统、黑白盒、消费调度、前缀树、MTP top-K KL、PD 分离、L3 cache | R4 §6 覆盖；两处小建议见 F2–F3 |
| R4 §7、Eqs.9–10、Figs.7–8 | thinking 持久化及 stripping 语句歧义；人类主导决策、自演化 harness 与内部 100 轮案例 | R4 §5.4、§7.4 覆盖，没有把 scaffold 编辑说成新自更新 loss |
| R4 §8–9、Table 4、Figs.9–10 | 五块全部评测与预算、23 行主结果、十一项系列曲线、MLE 三次 trial 和曲线口径；结论 | R4 §7–8 覆盖，包括负结果与跨 scaffold 例外 |
| R4 References、Appendix A | 查阅目录/引用用途和附录全文；两版附录都只有贡献者名单 | 无隐藏技术附录遗漏；v2 技术内容未增删 |
| N10 引言、§1–2.3、arch/black_rl | 三目标、token 一致性、长尾、CM、黑盒实例、规模与曲线 | N10 §2–3、§7 覆盖 |
| N10 §3.1–3.3、window/tree_merge | 窗口范围、队头推进和图中 lag；前缀共享与还原；三项推理优化 | N10 §4–5 覆盖，正确指出窗外索引措辞缺口 |
| N10 §4.1–5 | 三域混训、完整 CISPO HTML TeX、speed/perf 与 process 的文字/公式缺口、结论 | N10 §6–7 覆盖，没有用后来的 R4 填成早期公开事实 |
| N10 HTML/其余资产 | 封面及四张技术图均目视；核全部技术标题、math 块中的原始 TeX、图片入口与交互元素 | 未发现正文 tabs/details/select/iframe/video 或隐藏动态技术案例；评论与推荐不是额外方法附录 |

R4 十幅图全部目视；Tables 1、3、4 与关键 RL 公式回原页，Table 2 对照官方 TeX 与 PDF 文本。两版逐文件比较只发现 `app.tex` 不同；PDF 文本增量只在版本水印与贡献者名单，技术图资产相同。初次合并读取出现截断后，已分文件补读，不以截断结果冒充全文。

## 3. 关键核验

1. **算法与分母。** R4 p.17 Eqs.2–3、N10 §4.1 都是组内输出长度总和作分母，clipped IS 权重 stop-gradient 后乘 advantage 和 log-prob；不等于每轨迹均权平均，也不是 PPO 的 clipped surrogate。R4 p.18 Eq.4 的 baseline 未定义成 GRPO group mean/std。初稿均正确保留这些区别。
2. **奖励与 mask。** R4 Eq.4 无折扣、Eq.6 含 γ，N10 优势式只有 speed+perf 而正文另提 process；初稿未替作者补齐。请求级样本与轨迹公式之间、reward step 到 token、thinking/tool/CM masks、失败组统计和梯度/补采均无完整实现披露，初稿没有冒称已知。
3. **模型与数据关系。** 轮换 teacher 轨迹、AppDev 删除部分生成指导的 prompt distillation、MTP draft top-K KL 是不同机制；没有多 policy experts 合并或领域 OPD 的证据。R4 明确每阶段内混四域，N10 仅介绍 reasoning/general QA/agent unified training，初稿未混成同一版本训练配方。
4. **调度与加速。** W 限制训练消费原始派发队列中的完成轨迹，G 是每题 rollout 数，二者不能混用；图 N=8/W=4 的 lag=10 缺少 optimizer/发布映射。40× 缺硬件/workload/端到端分母，N10 原词 40× 与 R4 up to 40× 已区分。两稿正确把训练前缀计算复用与 loss 权重保持分开。
5. **评测与退化。** Table 4 全部 M2.5/M2.7 数字核对无误；MMLU-Pro 85.2→81.8 为下降。SWE 的 GPT-5.4 使用 CodeX、其余 Claude Code；Terminal-Bench 的 8 vCPU/16 GB/2h/四次及官方 baseline 引用；搜索超过 30% context 删除全部 assistant/tool 历史；无工具通用七项与 AIME 2025/2026 区分均已保留。
6. **MLE 和自演化。** 每题一张 A30、24h、22 题、三次 trial；最佳 run 15 枚奖牌与三次平均 66.6% 不能混为同一统计量。Fig.10 红色 CV-selected 与蓝色 any medal、超过 24h 的横轴未对齐正文，初稿已明确。30%–50% 日常工作量、内部 100 轮/30% gain 也没有被扩写成模型训练算力节省或 +30 个百分点。
7. **全域与负结果。** SWE code review 无 runnable 环境的例外、AppDev execution 硬门槛、GDPval 种子、非机器可验的比较/视觉信号、persona RLHF 均覆盖。SWA 短任务反例与 MTP 表中 MMLU 小幅下降也保留；没有用作者“全面提升”的总结覆盖负项。
8. **项目责任。** 窄读 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py::DefaultDataBuffer` 的 put/get、`fully_async_rollout.py::FullyAsyncRolloutFn` 的生产循环，以及主仓 capture/canonicalize 入口：确为完成入池顺序 FIFO、put ABORTED/dynamic filter、get consume-time staleness，并非 Forge 窗口。当前简报及 2026-09-07 建议支持先测消费偏差、不先新造 scheduler；笔记未把上游能力据为原创或批准新训练语义。

## 4. 实际发现与建议

### F1 — 需修订：达到 terminal 合成重试上限不等于已披露淘汰

- **定位**：R4 固定稿第 105 行，§3.4「已知失败淘汰」中的「terminal 合成超重试限制」。
- **证据**：R4 §4.1.3 p.12，官方 `tex/section/post_training_data.tex` 第 104 行，Stage 1 仅说失败后迭代修复，直到测试通过或达到最大重试限制。没有说明达到上限后的保留、隔离、丢弃或人工处理。
- **影响**：正文 §3.3 已正确区分环境合成重试与 RL rollout；汇总表却把停止条件升级为明确数据淘汰条件，容易被误用为数据漏斗语义。
- **建议**：从「已知失败淘汰」中移出这一项，改为「环境合成达到重试上限会停止修复；后续处置未披露」。其他明确过滤条件继续保留。

### F2 — 低优先级：明确 sample efficiency 解释来自 N10 或阅读者释义

- **定位**：R4 固定稿第 193 行，§6.1「后者是每样本带来的平均表现提升」。
- **证据**：R4 §6.2.1 p.19–20 / Eq.8 使用 `SampleEfficiency` 名称，详细定义了 throughput，但未给该句样本效率定义；N10 §1 明确写平均每样本的性能提升，并列数据分布、质量、算法和 off-policy 程度。
- **判断**：含义合理，非算法错误；问题是该句只引 R4，且来源节强调不混入早期博客细节。
- **建议**：注明「术语解释见 N10 §1」或标为阅读者解释；也可直接略去这句释义，只保留 R4 的概念目标与非收敛定理边界。

### F3 — 低优先级：把架构分层箭头改为真实请求与训练两条流

- **定位**：R4 固定稿第 195 行，§6.1「Agent Side…→Gateway…、Data Pool…→Rollout Engine 生成，Train Engine…」。
- **证据**：R4 Fig.4 p.20 及 §6.2.2：请求经 Gateway 往返 Rollout Engine；Gateway 将数据送 Data Pool，Train Engine 从池消费并向 Rollout Engine 同步权重。没有 Data Pool→Rollout Engine 的生成链。
- **判断**：上下文可能只是列三层，N10 §3.1 已写清；但连续箭头会被自然读成执行顺序。
- **建议**：用两句区分「Agent↔Gateway↔Rollout Engine」与「Gateway→Data Pool→Train Engine；Train Engine→Rollout Engine 同步权重」，避免把分层排布误写成单条时序。

N10 未发现必须修订的事实错误。两份稿的其他未知项，经所列全文/图表范围核查，均未发现原文已披露却被写成未知的关键训练配置。此结论不等于已审计 Forge 内部实现或所有链接资产。

## 5. 主作者处理记录

主作者于 2026-09-07 收到完整审查后执行修订，交审固定副本保持不变。

| 发现 | 处理与修订证据 |
|---|---|
| F1 | 采用。R4 §3.4 的明确淘汰项移除 terminal 重试上限，另列「环境合成停止」，写明达到上限停止修复、后续处置未披露。回读 §4.1.3 p.12，未添加任何 discard/quarantine 规则。 |
| F2 | 采用。R4 §6.1 明确 R4 只使用 SampleEfficiency 名称；平均每样本表现提升的释义单独标来自 N10 §1，不计入 R4 单独披露。 |
| F3 | 采用。R4 §6.1 改为 Agent↔Gateway↔Rollout Engine 的请求流、Gateway→Data Pool→Train Engine 的训练流及 Train Engine→Rollout Engine 权重同步；与 Fig.4 p.20 分开对应。 |

N10 无必须修订的事实错误，仅补独立审查结果/身份记录。两稿仍保留未知训练配置与 MLE 图文口径、stripping 语句歧义、奖励公式缺口等，未把「审查完成」写成实验复现或来源永久无误。同一审查者的定点复核已完成，见 §6；发布验证另记于 §7。

## 6. 同一审查者定点复核

2026-09-07，审查者 `01a07831-76f5-7ae1-8211-2dc348e68bbd`（`/root/review_r4_n10`，实际 `gpt-6-astra / high`）应主作者请求复核 F1–F3。检查正式 R4 §3.4/§6.1、正式稿相对固定初稿的完整 diff，以及本报告 §5；回读 R4 §4.1.3 Stage 1、§6.2.1–6.2.2 官方 TeX、Fig.4 p.20 原页及 N10 §1 定义。

| 项目 | 复核结果 |
|---|---|
| F1 | 已准确落实：明确淘汰栏移除重试上限，另列环境合成停止；后续处置仍标未披露，没有新增 discard/quarantine 规则。 |
| F2 | 已准确落实：平均每样本提升的释义明确归属 N10 §1，并说明不是 R4 单独披露；保留概念目标而非收敛定理的限定。 |
| F3 | 已准确落实：请求、训练消费、权重同步三条方向与 Fig.4 和正文一致，已消除 Data Pool 后才生成的误读。 |

R4 相对固定初稿仅有上述三项和审查状态更新；N10 的完整 diff 仅显示末节审查状态更新，没有事实内容改动。三项发现均可关闭，本次未发现修订引入的新问题。本次是定点复核，不是第二轮全文重审；原报告的证据边界与来源未解问题继续有效。审查者仅追加本节，未改两份正文或固定初稿。


## 7. 发布与结构核验

2026-09-07，主作者在独立全文审查、F1–F3 修订及同一审查者定点复核完成后，将 `R4_minimax_m2_series.md`、`N10_minimax_forge.md`、`reviews/09_R4_N10_review.md` 及 `sources/R4`、`sources/N10` 专属附件复制到主资料库相同相对路径。来源附件共95个文件，包含原PDF/HTML/TeX、必要图表和固定初稿；没有修改共享索引、其他任务笔记或训练代码。

发布位置的两份笔记、审查和两份 SOURCE 说明共5份文档、28个本地文件链接均可解析；未含本机绝对路径，正文导航锚点有效。已逐文件比较发布副本与 worktree 专属成品及全部95个来源附件，内容一致。正文无尾随空白，限定路径的 `git diff --check` 无报错；因这些文档为新文件，另用逐行检查补足未跟踪文件的空白检查。未运行训练、下载权重、提交或推送 Git。

结构核验不验证远端链接永久可用，也不构成论文实验复现。任务09精读与独立审查/修订已完成，来源未披露和图文未解口径仍以两篇正文为准。


---

## 文档 10 / 12：10_E10_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/10_E10_review.md`

# E10 独立正确性与覆盖审查

**结论：固定初稿通过本次独立审查；未发现必须修订的技术错误、整块后训练遗漏、无依据的因果结论，或将已披露内容误记为“未披露”的实质问题。** 此结论是文献笔记审查，不是论文实验复现，也不证明配套代码完整实现了报告中的方法。作者的处理与最终状态见第5节。

## 1. 版本与独立性

- 审查日期：2026-09-07。
- 主阅读任务：`01a07827-1e43-76b3-a7b5-927d16ceab97`；派工来源：`01a077c4-9f0d-7ef0-a40a-688b42f1b294`。
- 唯一独立审查子线程：`01a0782f-d4e7-7691-ade5-f3ce907e50cb`；agent 路径：`/root/e10_independent_review`。实际模型 `gpt-6-astra`，effort `high`，干净上下文 `fork_turns="none"`；主作者另从真实 `session_meta` / `turn_context` 核对了线程关系与配置并回传。本审查者没有创建子代理。
- 来源：Intern-S2-Preview Team, Shanghai AI Laboratory，[arXiv:2608.13505v1](https://arxiv.org/abs/2608.13505v1)，指定 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E10_intern_s2_preview_2608.13505.pdf`〕。全文 35 页，正文至 p.27，参考文献 p.28–35；本版没有独立附录。页码采用该 PDF 的物理页，与印刷页一致，首页未印页码。
- 被审版本：固定初稿 E10_intern_s2_preview.initial-20260907.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E10/E10_intern_s2_preview.initial-20260907.md`〕。快照中的原有相对链接按 `reading_notes/` 根解释；当前笔记入口为 E10 正文〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E10_intern_s2_preview.md`〕。审查者仅写本文件，未修改正文或固定初稿。
- 阅读顺序：先读 `tex/main.tex` 的全部输入与结束结构，独立枚举范围，随后读全部章节源码；再检查原 PDF 分页提取与关键原页，最后打开固定初稿逐节比对。初稿一次显示发生中段截断，已补读 §5–6 的实际缺失段，不以调用成功代替全文阅读。

## 2. 从原文独立建立的覆盖检查

| 原文范围 | 独立核查内容 | 初稿对应与结论 |
| --- | --- | --- |
| Abstract、§1，p.1–2 | 科学多模态、科学生成与长程 agent 目标；397B 主对象与独立扩展 | §2–3；覆盖，没有只按 SWE 解释全文 |
| §2.1，p.2–4，Fig.1、Eq.1–4 | retrieval datastore、memory 的 KL/CE、融合 router、各阶段冻结对象 | §7.1；训练链完整，未混为会话记忆或第三个 OPD expert |
| §2.2.1–2.2.2，p.4–5，Fig.2 | encoder 的压缩和跨通道处理；数值 forecasting、horizon predictor | §7.2；架构概要足够，未擅自补专项 RL 配方 |
| §3.1–3.3，p.5–8，Fig.3–5、Eq.5–9 | VP、交错图文过滤、图像检索；冻结对象、数据单位 | §2；三条路径清楚，OCR 要求未互相混淆 |
| §4.1–4.2，p.8–9，Fig.6 | SFT 数据域、safety、CoT rejection sampling、人工与模型验证 | §3；全部主要领域及模型依赖关系覆盖 |
| §4.3.1，p.9–11，Fig.7、Eq.10–13 | 共置 pause/resume、completed-only、staleness、IS、R3、精度、BKL | §4.1/4.5；版本、概率对象与 mask 作用分开 |
| §4.3.2–4.3.3，p.10–13，Fig.8、Eq.14–24 | 长度 shaping、触发条件、35B 消融；在线 draft 的 KL/TV 与速度 | §4.3/4.6/8.3；机制、分母与实证范围覆盖 |
| §4.3.4–4.3.5，p.13–15，Eq.25–29 | GEPO、不对称 shaping、LOO、动态补采、完整 loss 与配置 | §4.2–4.4；没有把 RLOO 改写成标准化 GRPO |
| §4.4 总述及 §4.4.1，p.15–17，Fig.9 | harness × task、三 serving 协议、TITO、双视图、PrefixTree | §5.1–5.2；未从树结构推断未披露的 rewrite/分支消费规则 |
| §4.4.2，p.17–18，Table 1、Fig.10 | 七来源、任务合约、技能图、逐阶段验证、离线 skip 与反馈闭环 | §5.3–5.4；未把公开库存当最终消费量 |
| §4.4.3，p.18–20，Fig.11、Eq.30 | session outcome、过程 advantage、非可训 token、verifier 防漏、失败分类、各 harness 曲线 | §5.5–5.6/8.3；在线过程权重与离线模仿 mask 区别明确 |
| §4.5，p.20–21，Eq.31–36 | 两专家与 warmup、reverse KL、sampled-token、prox/beh/current、域与轨迹分母 | §6；理想目标与实际 surrogate 的边界保留 |
| §5.1–5.3，p.22–27，Table 2–5、Fig.12 | 所有科学、通用、多模态、agentic、Memory 和时序评测；预算、负结果、排名 | §7–8；没有遗漏非 SWE 结果，也未把总表当受控组件消融 |
| §6、作者贡献、References，p.27–35 | preview 限制；尾部检查到最后条目 [112] | §9–11；未发现额外附录或尾部技术表 |

原页目视核对覆盖全部 12 幅图、5 张表及关键公式：p.3–7、9–14、16–21、24–27 中实际含图表/公式的 21 页。其余正文通过完整源码阅读与分页提取交叉核对。参考文献只用于核对全文尾部与引用边界，未声称递归精读全部被引论文。

## 3. 关键正确性核验

1. **模型关系正确。** Fig.6 与 p.20 明示同一 SFT 初始化分别产生 reasoning / agentic experts；学生是原 SFT 模型经两专家轨迹 warmup 后进入 OPD。初稿还正确区分 397B 主评测、Fig.8 的 35B 与单独 Intern-MemDec-4B。
2. **三个概率对象与分母正确。** Eq.10/34 的比值为 current / token-specific behavior；Eq.33 为 teacher logprob 减 frozen proximal student logprob。Eq.29 先按 response 原长度平均再按组平均，Eq.36 先按 policy-token 集合长度平均再按域内轨迹平均；BKL 剔除位置没有从这些分母扣除。初稿没有用 PPO surrogate 替代 detached clipped IS。
3. **shaping 与数值 mask 正确。** Eq.25 的组熵对 token 求和，未按 response 长度归一化；Eq.28 为 GEPO 在先、长度正则在后；Eq.14/15 的触发对象是正 advantage 集合。BKL 比较 matched parameters 和 replayed routing 下两个引擎的 sampled-token Bernoulli 概率，不是全词表 KL 或跨版本策略 KL。初稿保留了 p.13 解释与 p.14 GEPO 系数串式的疑点，未自行修成配置。
4. **失败、mask 与过程反馈正确分层。** `skip` 是保留上下文但排除 imitation loss；Eq.30 的过程权重只缩放正 advantage，不更改 session reward 或 token labels。非策略上下文与数值离群 token 分属不同排除机制；初稿没有从“故障单列”推断固定 reward、重试或丢组规则。
5. **训练数量与速度范围准确。** 8,192 completed responses / batch、8 mini-batch update steps、65,536 reasoning generation tokens、OPD maximum sequence 256K、draft K=4/η=3 均与原文一致。Table 1 七行逐格一致，包括 R2E-Gym 的 7,480 tasks / 8,101 environments；未据此计算消费量或镜像复用率。2× rollout、1.7× 整体 RL 的两个测量范围没有相乘或外推硬件预算。
6. **Memory 与时序负结果保留。** Fig.12a 逐行复核并独立计算得到 14 项提高、7 项下降，均值四舍五入为 56.92/60.32；初稿的 +3.40 分是报告均值之差。Table 4 七项改善、两项下降及两个新增雷达任务正确。Table 5 的 NEG03 59.2(100) 并不优于 Moirai 59.1(100)，DeepSeek 4.3 的成功率仅 3.1%；初稿正确保留这些反例以及 MAPE 分母未知项。
7. **评测预算与因果边界正确。** Table 2–3 的所有 S2 分数、ResearchHarness v0.0.49、OpenClaw 2026.5.7、Terminus 2、Mini-SWE-Agent 及 Pro 镜像修改均已核。初稿没有把 1,865 题总库规模当 Pro 实测 split，也没有把 SCI agentic “second only to GLM”当逐行排名。Fig.8 为 35B 训练内曲线，Fig.11 为 160 步经局部平滑的代表图；没有将其认定为全部训练预算或单调提升。
8. **资产、项目映射与旧稿纠错有依据。** 另读保存的官方 HF 模型卡/metadata 与 XTuner README/revision：35B 卡、对应 revision、Apache-2.0 和 agentic Coming Soon 字样与初稿相符；没有据 README 断言实现绝对不存在。阅读指定当前简报与项目建议，并窄核 `capture_wire.py`、`canonicalize.py`、`faithful_dis_loss.py` 及集成 `fully_async_rollout.py` 的被引路径；当前 DIS 区间外置零与论文 clip 到边界确实不同。旧稿的细域多教师“否决”、白盒“自研”、标准 GRPO 和直接项目资格映射均已被正文收紧。未做全仓审计、在线训练或 GPU 验证。

## 4. 发现、残余不确定性与交付边界

**本次必须修订发现：0 项。** 没有为凑审查条数而把已正确保留的论文疑点重复列成初稿错误。以下仍应在最终正文保留，不能由“审查通过”消除：

- GEPO 两系数的排印关系与文字“较温和”的说明未统一；论文没有清晰数值配置。
- agentic 的具体 group baseline、完整 scalar loss 分母，以及故障/截断在组统计、梯度、补采中的处置未完整披露。
- compaction/rewrite 后被移除响应的覆盖、共享 prefix 计权、跨版本 matched-parameter BKL、teacher/prox 刷新均未由原文给出完整实现。
- 数据验证与消费漏斗、各阶段算力/教师成本、完整评测预算、时序专项训练配方与内部科学评测分母仍不够复现。
- 官方保存材料只支持指定版本的资产边界检查，不能由 35B 模型卡证明 397B、两个专家、warmup student 或 memory 权重均已公开；未独立下载权重或审计 XTuner 全部源码。

文件引用按主资料树与本 worktree 新增来源分别核对：初稿的既有目标均在主资料树存在；隔离 worktree 缺少这些未纳入基线的共享材料不是笔记链接拼写错误。来源快照内部链接继续按其留档说明解释，不改写固定初稿。

## 5. 作者处理与最终检查记录

主作者于 2026-09-07 收到真实审查结果并全文阅读本报告。审查发现为0项，因此没有需要逐项消除的技术问题；本文列出的原文披露边界全部保留。正文仅修改第12节：登记审查子线程与实际配置、增加本报告链接、把待审状态改为已完成。没有新增实质技术内容，也未声称进行过第二轮复核。固定初稿未修改，技术正文第1–11节保持与被审版本一致。

最终检查与发布已完成（2026-09-07）：

- 比较固定初稿与终稿，第1–11节技术正文一致；仅审查记录与最终状态更新。
- 正文、审查和E10来源说明的22个本地文件引用/导航锚点均通过检查；代码围栏闭合，无行尾空白，无本机绝对路径。原始第三方快照与初稿留档内部链接遵循来源说明，不作为当前导航入口。
- 仅发布 `E10_intern_s2_preview.md`、`reviews/10_E10_review.md` 与 `sources/E10/`；已复制回主资料 checkout 的 `docs/harness_improve/external_paper_references/reading_notes/` 相同相对位置。共58个专属文件逐字节比对一致，发布后的本地链接再次按实际目标树核验通过。
- 发布前脚本曾因E10目标子目录尚未创建而误报一个含 `..` 的链接；规范化路径后确认原链接正确，发布后直接路径检查也通过。未因此改写技术内容或已有共享文件。
- 未修改共享索引、其他任务成品、训练代码或配置；未commit/push、运行训练、租GPU或下载权重/整套数据。

本任务精读、真实独立审查、作者处置与专属成果发布完成。


---

## 文档 11 / 12：11_E5_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/11_E5_review.md`

# 任务11 · E5 SWE-smith 独立审查

审查日期：2026-09-07。结论：固定初稿已覆盖论文全部后训练内容与主要限制，没有发现改变主结论的事实错误或整段遗漏；有两处需要收紧的表述，见下文。新增 SkyRL 材料的定点核查已完成，能够支持“存在具体环境/评分接线”，不能支持 SWE-smith 专属 RL 收益。

## 1. 身份、版本与独立性

- 主任务 ID：`01a07827-1e3f-7bb0-85d6-7ac47489ae64`；主任务实际`gpt-6-astra` / `high`也已由主作者读取会话`turn_context`核实。
- 审查 agent：`/root/review_e5`；审查 thread ID：`01a0782d-eba9-79a3-81cb-51d5e1e7ace7`。
- 实际配置：`gpt-6-astra`、`high`；已从本审查会话的 `turn_context` 核对，不是仅按角色提示自称。干净上下文派工；未再派子 agent。
- 固定初稿：E5_swe_smith.draft-20260907.txt〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/E5_swe_smith.draft-20260907.txt`〕。先读任务提示、模板、项目必要背景及独立来源，再对照初稿；未修改笔记正文或固定副本。
- 主来源：[arXiv 2504.21798v2](https://arxiv.org/abs/2504.21798v2)，2025-05-21，46 页；PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/paper.pdf`〕、全文提取与 `tex/main.tex` 及其实际输入文件。PDF 物理页与印刷页一致。
- 官方代码：`SWE-bench/SWE-smith@9b74ac08118a85c39c356802f7961893af73e07f`；只核笔记引用机制。HF 三卡及其元数据 revision 与初稿所列一致。未下载完整任务/轨迹/权重/镜像，未执行训练或容器安全审计。
- 项目映射：主资料目录 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`、实际 miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6` 已核；读当前简报、2026-09-07设计建议及所引两处任务视图/评分投影职责，不扩全仓审计。

## 2. 全范围覆盖结论

独立依据 `main.tex` 确认正式阅读范围，包括摘要、§1–6、致谢、附录总览，以及 A Infrastructure、B Bug Generation Strategies、C Dataset Statistics、D Issue Generation、E Difficulty Rating、F Experiments（含实际嵌入的 Evaluation Datasets）和 G Miscellaneous。正文、附录中的后训练、数据、预算、评测、行为与负结果全部读完。仓库长表、许可表、两份组合算法、所有实际纳入的提示词和统计表均检查；目录中未纳入 `main.tex` 的旧稿/备用表不当成正式论文。

图1–27按源文件、图注及正文覆盖；关键统计图与疑点回 PDF 渲染，具体包括 p.1–2、4、7–9、16、21–22、24、26、32–33、37–38、41–46。参考文献仅作出处导航，没有扩读每一篇被引论文。

初稿对应内容完整：主 agent 的全参数 RFT/SFT、辅助难度分类器 LoRA、四种题面、五类统计口径的 bug 生成、所有消融与 SymPy 专门化、多语言弱迁移、重复动作干预负结果、在线编辑轨迹重放失败、成本与污染限制。没有把当前 RL 示例倒填进论文。未知项的查阅范围基本准确，没有发现用未读来源填补算法配置的情况。

## 3. 代表性关键核验

1. **分母链正确。** 表10的 100,074 候选→50,137 任务，与 §4 的 8,686 唯一任务、17,906 尝试、6,457 成功轨迹不是同一分母；36%是尝试级成功率。表17六项之和为5,016；每题最多三条并不等于完全去重。初稿保留了表16无法与总漏斗逐项核平的问题。
2. **模型关系正确。** F.1 为 Qwen2.5-Coder-Instruct 的全参数 SFT，torchtune、`5e-5`、最多3 epochs、32768 context、2–8 H100 80GB；E 为独立 Qwen2.5-32B-Instruct 难度分类器的 Unsloth LoRA，1699标注、80/20划分、75.3%准确率。初稿未混成同一训练链。
3. **序列化与终止限定正确。** F.1 明说 teacher function calling 需转 student XML；学生仅保留最近五条工具输出，75步/$2代理计价，不能当真实GPU费用。预算终止仍可能提交成功补丁。当前转换器不自动筛 `resolved`，初稿对此指出的复现缺口有代码依据。
4. **消融与负结果准确。** 表4统一507条、表5统一259条；图5为5/25/50/100仓而正文为4/25/50/100；难度2/4/6/8结果12.4/10.8/13.6/12.2%；图23全部五对过滤/不筛结果、图22六点pass@k均与原页一致。Multilingual 8.4/6.5/43、重复干预192/500=38.4%也准确。初稿没有把关联或匹配轨迹数夸大成独立因果/等算力结论。
5. **原文矛盾多数已妥善处理。** 安装100步/150 calls、128仓/129仓/125镜像、295/290.54GB、7B训练量、难度范围、表4/16采样数、表5/16题面行互换、模板7/9项和候选成本分母均有原文依据。初稿没有悄悄选一组数字覆盖另一组。
6. **评测与污染边界正确。** 题面生成确实使用 Verified 题面示例；难度评分器用 SWE-bench 标注与参考解；主训练仓库排除不等于所有实验/资产零暴露。C.2 明说原任务没有隐藏测试和题面泄漏/歧义检查，不宜直接用作评测。初稿保留这一点比只强调“有可执行测试”更准确。
7. **成本、代码与项目归属正确。** 表1为候选生成API成本，$1360并非端到端训练费用；Flask $2.47/402 与有效任务267分母分开。当前代码 `HEAD~1` 恢复测试、回退已识别测试文件和示例 `lr=1e-4` 均正确标为后来的实现。项目建议复用上游、只验证 rh2 接入边界，没有把论文结果冒充项目结果。

## 4. 实际发现与建议

### R1 · 明确 `f2p_only` 是按文件缩减范围，并非只判 F2P

- 位置：固定初稿 §7.1 评分行，第237行，称“另有F2P-only开关”。
- 证据：当前 `swesmith/harness/grading.py::get_eval_report` 第221–230行先取 F2P 文件，随后**同时过滤 F2P 与 P2P 列表**；`swesmith/profiles/base.py::RepoProfile.get_test_cmd` 第572行起也按 F2P 文件组装命令。随后仍调用完整 resolution 判定。
- 影响：开关名容易被理解为关闭 P2P 回归要求；实际还可能检查 F2P 所在文件内的 P2P。这会影响读者复用评分契约。
- 建议：改为“`f2p_only` 按 F2P 所在文件缩减测试范围，同时保留其中的 F2P/P2P 判定；并非一般意义上的仅检查 F2P”。这是精度补充，不推翻该行默认全评分的结论。

### R2 · 将 Flask 的证据限定到许可表与案例

- 位置：固定初稿 §6.2，第219行，“许可/仓库列表出现Flask”。
- 证据：正式表6（`tables/licenses.tex`）含 `pallets/flask`，C.2明确以 Flask 作案例；但正式仓库长表 `tables/all_repos.tex` 未列 `pallets/flask`。主训练最终123仓的表18也只展示部分仓库，不能据此确认 Flask 进入主训练。
- 影响：当前斜杠表述可能让读者误以为正式任务仓库名单也列了 Flask，略微加强了本来应保留的重叠不确定性。
- 建议：写成“许可表6出现Flask，C.2另用Flask作案例；这些不足以确定它进入主训练123仓”。保留后文“需完整血缘核查”的限制。

除此以外，没有发现应要求重写的实质性正确性或覆盖问题。主结果缺少更细的复现实验/运行账，是论文与公开版本边界，不能要求笔记凭推测补全。

## 5. 新增 SkyRL 材料的定点审查

审查对象：rl-addendum-draft.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/rl-addendum-draft.md`〕，独立于原固定初稿。核对历史 `swe-smith` 分支提交 `58cfc213c0f7b44a0b5033e68d65782d05f8a13d`（2025-06-05，`support swesmith`）的根README、SWE示例README/启动脚本及三处适配源码。

- `utils.py::get_instance_docker_image` 的 `data_source` 分支、`swesmith_utils.py::make_test_spec` 的旧版 `get_test_command`、`codeact.py` 的测试规范与评分分支均存在，足以证明具体静态接线。
- 示例确有 GRPO、OpenHands-7B初始化、16轨迹/题、15次迭代、`lr=1e-6`、KL loss 0.001、clip0.2；但路径仍是 SWE-Gym 占位，README列80/220/293训练数据。补充稿正确地未将它登记为 SWE-smith 已跑配方，也未将根README的 SkyRL-Agent 成绩归给 SWE-smith。
- 当前main的 `skyrl-agent/data/swe_data.py` 默认确为 R2E-Gym；旧分支API与此次SWE-smith当前commit不同。补充稿保留未复原依赖/未执行的限制是恰当的。

该补充可以采用。整合时同步更新 §1 阅读范围、§7.2及§8.2的“仅有限链接/实际配方未知”措辞：现在可确认静态接线，仍未确认 SWE-smith 专属数据revision、真实训练运行及受控收益。不要只替换一段而使其他位置停留在旧证据状态。

## 6. 链接与交付边界

相对路径按最终笔记目录解析：主PDF、旧稿、项目背景及 E2/N11/N13a 关联文件在主资料目录存在；新 `sources/E5` 在阅读worktree存在。没有发现这些相对路径算错。当前两个目录各自并不含全部目标，最终整合时需将本篇来源与审查记录一起带入；这是交付完整性检查，不应误报为已存在文件的链接拼写错误。

## 7. 主作者修订处理区

以下为主作者收到完整审查报告后的处理记录。固定初稿未改；正式笔记已修订。独立审查者先核原稿和单独RL补充，主作者随后验证修订落地，不冒称又做了一轮全文独立审查。

| 项目 | 处理与证据 | 日期 |
| --- | --- | --- |
| R1 | accepted：§7.1改为按F2P所在文件缩减范围，并保留其中F2P/P2P判定；回读`get_eval_report`的双列表过滤与后续resolution调用 | 2026-09-07 |
| R2 | accepted：§6.2明确只在许可表6和C.2案例见Flask，正式仓库长表未列；不据此判定进入主训练123仓 | 2026-09-07 |
| SkyRL补充与交叉引用同步 | accepted：将已由同一审查者定点核过的补充整合§7.2；同步§1来源范围和§8.2未知项，区分静态接线、通用GRPO示例与未证明的专属收益 | 2026-09-07 |
| 来源/链接整合检查 | 已完成：4份本任务撰写文档的36个本地文件引用与内部导航检查无缺失，无本机绝对路径/尾空白/未闭合围栏；已将本篇、审查与sources/E5复制至主资料reading_notes相同相对位置，并逐字节核对全部复制文件一致 | 2026-09-07 |


---

## 文档 12 / 12：12_O03_review.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/reviews/12_O03_review.md`

# 任务 12 / O03 R2E-Gym 独立审查

审查日期：2026-09-07。结论：固定初稿覆盖了正文和 A–E 全部后训练、数据、评测及负案例；主要训练关系、样本数量、公式和训练/推理收益分界正确。发现四项需修订的局部语义或精度问题，另有两项建议。以上为固定初稿的初审结论；六项随后均已修订，并由同一审查者完成定点复核，当前处理结果见文末。

## 审查身份与固定输入

- 主任务 ID：`01a07827-1e42-70f2-ac37-48ca0e1af7a7`；主任务实际配置 GPT-6 Astra / high，由主任务确认。
- 审查 agent UUID：`01a0782e-169c-7b10-939b-bff6f99d0f9a`，本环境 `CODEX_THREAD_ID` 实际返回；canonical task name：`/root/review_o03`。
- 本次调用实际配置：GPT-6 Astra / high / `fork_turns=none`，由调用配置确认；没有递归建立 agent。
- 被审固定稿：O03_r2e_gym.draft_20260907.txt〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/O03_r2e_gym.draft_20260907.txt`〕。审查者没有修改该稿或正式笔记。
- 原文：arXiv:2504.07164v1 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/2504.07164v1.pdf`〕，2025-04-09，正式标题 *R2E-Gym: Procedural Environments and Hybrid Verifiers for Scaling Open-Weights SWE Agents*，27 页。本文页码同时为 PDF 物理页和印刷页。
- 核对来源：全文〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/paper.txt`〕、实际 TeX 入口〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/tex/main-arxiv.tex`〕及其引用章节、关键页渲染〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/rendered`〕、官方代码 commit `0d94c4eb9431cd195c55a7ea3abd54006c9a1735` 的必要摘录、HF 原始元数据 JSON、来源记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/SOURCE_RECORD.md`〕。后来的代码不是论文实验版本。
- 官网 PDF 与 arXiv 文本等同性以及 p.2–27 的 60 DPI PNG 字节等同性是主任务提供并记入 SOURCE_RECORD 的来源核验证据；本审查未重新执行整套双 PDF 渲染。独立回看 arXiv p.2/3/5/6/7/8/9/15/22/23/26/27 原图，其中图中数值与公式直接核对。

## 独立覆盖检查

先读原文结构和全部附录，再打开固定稿比较；没有按几个预设问题缩小阅读范围。已读公共 TASK_PROMPT、NOTE_TEMPLATE，并以当前简报和 2026-09-07 项目一建议建立有限项目背景。

| 原文范围 | 实际检查的内容 | 对固定稿的判断 |
| --- | --- | --- |
| Abstract、§1，p.1–2 | 两项贡献、历史榜单及 test-time scaling | 摘要和历史性限定正确 |
| §2、Appendix A，p.3–4、15–18 | commit/AST 阈值、安装、原有/生成 F2P、gold-conditioned testgen、反译完整输入及模板、两个 issue 示例、patch minimization | 全覆盖；没有把合成任务说成模型注入 bug，也没有把半人工安装说成完全自动化 |
| §3/3.1、Appendix B，p.4–5、18–19 | 编辑 SFT、teacher、成功拒绝采样、四工具、采集与训练预算、数据规模/思想/真实合成消融 | 全覆盖；Table 3 数值、thought 文图矛盾均正确记录 |
| §4.1、C.1/C.2，p.5–6、19–21 | 测试 agent full SFT、含失败数据、EF LoRA 与平衡数据、Django starter | 三条模型关系和不同失败用途正确 |
| §4.2、C.3/C.4，p.6–8、21–23 | 正负候选、采样、区分率/毒性公式及分母、注意力诊断、输入消融、Pass@K 图 | 公式准确；输入消融需要补“分别训练”，见 R1 |
| §4.3/4.4，p.8–10 | hybrid、Top-n 与回归顺序、组件/rollout 消融、成本主张 | 核心正确；追加测试预算的图文差异需补，见 R2 |
| §5/6、致谢/参考文献，p.10–14 | 与 SWE-Gym/SWE-RL 和通用代码 verifier 的关系 | 没有遗漏本方法的额外 RL、OPD、数学/多模态或安全训练阶段；这些没有自身实验 |
| D.1/D.2，p.23–25 | SymPy 成功区分和 Django 异常反例、删节脚本 | 全覆盖，Django 负例及误判分支没有遗漏 |
| E，p.25–27 | PolyElement.as_expr 的题面与六步图像轨迹 | 读图与初稿相符，没有把自建复现脚本成功当成完整 grader 证据 |
| 当前代码、HF 与项目背景 | 三份 YAML、dataset_info、生成指南/仓库特例、reward、EB/EF/聚合脚本、元数据行数/修订/许可；有限 rh2 视图/评分投影/组准入模块 | 版本分层正确；不是完整仓库审计；局部精度问题见 R3/R4 |

## 关键核验

1. **三个 SFT 产物**：编辑 3,321 条成功轨迹/2,048 环境，测试 2,203 条且含正负，EF 5,700 条且类别平衡、加入已训 32B 的 on-policy 采样。后者是采样来源，不是 PPO/GRPO；编辑/测试 full SFT，EF LoRA rank 64。初稿没有混用这些样本单位。
2. **预算**：编辑采集 40 steps/32K/10 min/90 s、训练 20K；测试采集 40 steps/20K/5 min/60 s；EF 训练 32K；均 2 epochs、batch 8、LR 1e-5、warmup 0.1。当前 YAML warmup 0.05 和 instruct 初始化被单列，未补写历史未知的 mask、截断、分母、硬件或实际消费量。
3. **数据漏斗**：8,135/13 repo、4,578/10 repo 与原图相符；A 的七项过滤阈值均被记录。初稿正确保留 B 的 Lite 4,538 矛盾，没有用成功轨迹数倒推 solver pass rate；没有把生成阶段看到 gold 推广到推理测试 agent。
4. **六个公式**：EB 使用相对最高 regression 的条件和生成测试通过数；EF 是 YES/NO 相对概率；hybrid 有 EF Top-n，实践中随后回归过滤；区分率/毒性比较两类补丁的 max，分母为每问题测试数。初稿对“毒性同时可计入区分率”的推论成立。
5. **结果与归因**：Table 3 六组 baseline/SWE-Gym/ours 及误差照录正确；32B +13.8 是百分点。34.4 Pass@1、49.4 Best@16、51.0 Best@26、64.4 oracle Pass@26 分开；26 编辑加 7 测试不是 26 次总调用。历史系统之间没有被包装成等训练/等推理预算因果比较。
6. **负结果与案例**：EB 低区分/毒性、EF 对轨迹线索敏感、Django 多数测试异常、14B 数据规模平台、单独 verifier 饱和都被保留；注意力被限制为关联性诊断。图表 42.7/42.8/42.9、43.7/43.8、thought 34.2/34.4 和错误交叉引用也正确保留。
7. **当前资产**：从各 HF 原始 JSON 独立提取，确认 train 行数 8,101、4,578、3,231、2,281、5,750、200 及所列 revision；Lite 有 9 个 dev split。权重/adapter 文件列表和许可缺项支持初稿边界，没有逐行数据审计或镜像可用性证明。
8. **静态代码与项目映射**：确认 hybrid 的 floor(K/2) 和 K=1 空集路径、reproduction 结果未用候选身份作键、EF 两轮 as_completed 后 zip 原列表的错配路径；只称条件性当前代码风险，没有倒推论文受影响。rh2 的公开/私有视图、通用 pytest 控制面边界和 miles consume-time staleness 职责与所读实际文件一致。

## 强制修订

### R1：EF 输入消融要明确是分别训练 verifier

**位置**：初稿 §6.3 的“EF 全输入 vs patch-only vs 去 thoughts”，及对应解释。

**证据**：p.7 §4.2 明确说训练多个 EF verifiers，并在训练时排除不同轨迹成分；TeX sec/4_inference.tex〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/tex/sec/4_inference.tex`〕 第 258 行亦明确。Fig.7 的 71.82/68.01/68.77 和 42.8/37.6/41.4 是这些不同输入训练配置的对照。

**修订要求**：补一句“分别训练对应输入版本的 verifier”，避免读者理解为同一个冻结 verifier 在推理时删输入的干预实验。保留当前关于注意力不能证明因果的限定。现有数值本身正确。

### R2：追加五次测试采样的 49.3 与 Fig.4 对应点不一致

**位置**：初稿 §6.3 预算消融行、§8 文本矛盾汇总。

**证据**：p.9 §4.4 确实写 16→21 编辑 rollouts 为 47.6→48.4，另加五次测试到 49.3。但 Fig.4 原始图片〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/tex/figures/passrate_vs_testagentrolls.png`〕 显示 47.6/48.4 对应 **1 次测试 rollout**；固定 16 编辑、从 1 增到 6 测试的标签为 **49.4**。16 编辑/5 测试为 49.1。不能把正文 49.3 直接作为图中确认值。

**修订要求**：在该行写清共同起点为 1 次测试，并保留“正文 49.3，图中对应 6 次为 49.4”的差异；不擅自更正原论文。初稿已写“作者示例”仍不足以说明读图核验后的实际矛盾。该差异不推翻增加测试采样有帮助的方向性结论。

### R3：当前脚本是最多三次总尝试，不是额外重试三次

**位置**：初稿 §7.3 的“最多重试 3 次、默认 600 s”。

**证据**：run_reproduction_tests.py〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/official_repo/src/r2egym/agenthub/verifiers/run_reproduction_tests.py`〕 的 `process_single_task(args, timeout=600, max_retries=3)` 使用 `for attempt in range(max_retries)`。

**修订要求**：改为“每项默认最多 3 次总尝试，即首次加最多 2 次重试；每次 join 超时 600 s”。外层还能有终止清理和退避开销，因此不能暗示完整条目严格限于 600 s 或 1,800 s。现有“最终可记 0”的判断成立。

### R4：当前 reward 比较不是无条件逐键严格匹配

**位置**：初稿 §7.3 首段“比较条目数及各状态，全部匹配给 1，否则 0”。

**证据**：runtime/docker.py〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/official_repo/src/r2egym/agenthub/runtime/docker.py`〕 的 `_calculate_reward_r2e` 先比较字典长度，随后循环有 `if not k: continue`。两个字典都为空时循环不执行，也会返回 1；空字符串键的状态不会被比较。返回的 `error_code` 在该函数没有作为独立条件使用。

**修订要求**：对静态实现描述加上这些实际条件，至少避免用“全部匹配，否则 0”作绝对断言。可以简写为“长度一致且所有非空解析键的预期状态相符即给 1；函数本身未拒绝双空映射”。这只是静态条件，不表示公开数据实际出现了双空记录，也不证明论文当年误评分。

## 建议

- **S1：EF 概率缺失边界再补半句。** 初稿已记录 YES/NO 缺失填 -10000；`run_ef_verifier.py::run_model` 对两个 logprob 都直接 `np.exp`。若二者都缺失，就有 0/0 非有限分数路径，不是稳定回退到 0.5 或 0。可直接作为现有概率位置风险的一个具体后果，不扩成全仓审计，不声称实测触发。
- **S2：集中注明环境生产模型/预算未知。** 初稿清楚记录 judge 未给型号，但对 Appendix A 的 issue backtranslation 和 gold-conditioned reproduction test generation 的实际模型、每 commit 采样预算也可集中加一句未披露。不要把训练轨迹 teacher Sonnet 或当前指南的 o1-mini 默认扩展给这两个阶段。

## 残余未知与审查边界

原文没有补足：原始 commit/构建/测试生成的逐层漏斗和总成本；测试 SFT 负例类别与 minimal rejection sampling 阈值；EF 各来源精确配比；历史 SFT token mask/分母与长轨迹处理；评测重复/误差定义、精确采样分配、Top-n 实参、完整 checkpoint/框架/硬件 pin；全库稳定性、替代解、隐藏材料或评分控制面审计。初稿在已查范围内写为未知基本恰当，不能用当前 defaults 消除这些未知。

本审查没有运行模型、训练、镜像或 benchmark，没有下载权重/parquet，没有独立验证 Prime 后续 4,522/4,578 审计，也没有重新运行本项目历史三镜像 prefix 检查。主任务给定项目 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6` / miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6` 用作映射版本标识；仅检查相关模块职责，不将此记录当全仓正确性证明。

## 作者逐项处理记录

由主任务在收到本报告后追加 R1–R4、S1–S2 的处理、证据和残余不确定性。审查者提交时此处尚未填写；固定稿保持不变。


### 2026-09-07 作者修订

已收到本报告后才修订正式笔记；固定 draft_20260907.txt 未变。六项全部采纳：

| 项 | 处理与证据 | 残余边界 |
| --- | --- | --- |
| R1 | 正文 §6.3 写明分别训练各输入版本；依据 §4.2 p.7 与 Fig.7 | 未将其变成冻结模型的因果干预实验 |
| R2 | §6.3 加共同起点 1 次测试及 1→6 次；保留正文 49.3/图49.4，§8 同步 | 不擅改原文；仍无等 token/算力预算对照 |
| R3 | §7.3 改为 3 次总尝试、首次+最多2次重试、每次join 600 s，并说明清理/退避 | 不宣称整个条目有精确1800 s硬上限 |
| R4 | §7.3 改为非空解析键匹配，注明双空给1、error_code未独立参与判定 | 未证明实际任务包含该输入，未外推论文历史误奖 |
| S1 | §7.3 补 YES/NO 都缺失时指数下溢与0/0路径 | 静态说明，未运行模型触发 |
| S2 | §8 集中补反译/生成测试模型、每commit预算未披露 | 不用Sonnet或当前o1-mini示例补历史配置 |

作者还补录官网/arXiv p.2–27 的60 DPI渲染一致性（来源附件记录已有），没有修改被审固定稿。已请求同一审查者定点复核上述改动；复核结论另追加，不冒称再次全文审查。

### 2026-09-07 同一审查者定点复核

审查者仍为 `01a0782e-169c-7b10-939b-bff6f99d0f9a`（`/root/review_o03`）。已读取正式 O03_r2e_gym.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/O03_r2e_gym.md`〕 的 §6.3、§7.3、§8、§12 及上方作者处理表，逐项对照本报告保留的原文/源码证据：R1 的分别训练、R2 的共同起点与 49.3/49.4 图文差异、R3 的总尝试次数、R4 的非空键/双空及 error_code 条件、S1 的非有限概率路径和 S2 的生产模型/预算未知均已准确落地；处理表与正文一致。六项均关闭，未发现这些修订引入新问题。静态风险未被改写成实测发生或论文历史错误，原始未知项仍保留。本次仅为这六项的定点复核，没有声称再次全文审查；审查者仍只追加本报告。
