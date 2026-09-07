# R1 独立技术审查

审查日期：2026-09-07。审查对象：[R1_mai_thinking_1.md](../R1_mai_thinking_1.md)。审查员为单独委派的 GPT-6 Astra / high，使用干净上下文，未创建下级 agent，未修改正文。

**结论：未发现推翻主要训练配方、模型依赖、关键结果或项目边界的技术错误；全部后训练领域已覆盖。** 有三项低严重程度的补充/限缩建议，列于下文。这里的结论是原文与笔记的对应性判断，不是论文结果的独立复现，也不证明报告未公布的系统实现。

## 1. 审查顺序与来源

先阅读指定 L 版本目录 pp.3–4，独立列出 §3 的全部训练域和附录 A–K；随后核读训练正文、评测、红队、相关基础设施及附录，再打开待审笔记逐项对照。核验没有以笔记的“未披露”结论代替查阅原文。

- 主版本：[指定原始 PDF，L](../../../main_20260602_2.pdf)，SHA-256 `7d4f13dd88ff98d0480645e96b751f0abea00fd99122cabf7626598b29bef26f`。
- 对照版本：[官方 URL 的 2026-09-07 快照，W](../sources/R1/main_20260602_2_fetched_20260907.pdf)，SHA-256 `a267d745b1eb3792a8abf58e71e204a6f44f9c18eeb5ad8671320deae71986bd`。
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
