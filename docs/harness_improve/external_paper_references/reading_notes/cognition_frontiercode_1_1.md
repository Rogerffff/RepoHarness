# FrontierCode 1.1：公平联网、blocker 降级与评测协议的版本效应

FrontierCode 1.1 没有提出新的训练算法，而是同时修改了 agent 能使用什么信息、grader 如何处置违规访问、哪些质量要求应当一票否决，以及报告哪个任务子集。它采用“明确 fair internet use + 程序检测 + 被标记运行归零”，将75个过严blocker降为non-blocker，并停止报告低通过率且难度顺序已变化的Diamond。最值得借鉴的是把能力测量与任务信息边界说清楚，同时承认verifier会误杀。必须保留的限制是：低于1%的结果是作者对所测模型的陈述，公开柱图实际上画的是1.0的违规率；检测器没有公开完整实现/召回率；两条交互演示是预置摘录而非实际运行。1.0到1.1的分数变化不能当作模型能力提升，也不能把“无需封网”外推为RL训练中的可靠安全保证。

导航：[来源覆盖](#source) · [联网协议](#internet) · [完整示例](#examples) · [评分与子集](#grading) · [结果口径](#results) · [项目意义](#project)

<a id="source"></a>
## 1. 来源、版本与阅读范围

**正式来源：**Cognition，*FrontierCode 1.1*，2026-07-07。[官网][WEB]署名 Eric Lu、Ben Pan、Fermi Ma、Alex Lombardi、Deniz Birlikci、Sam Lee、Ray Wang、Rohan Choudhury、TC Qin、Carlo Baronio、Jacob Teo、Joon Hee Lee、Silas Alberti；另有设计及贡献者致谢。

**阅读日期2026-09-14。** 主证据为用户 `03_FrontierCode.md/.zip` 中于2026-09-11 `09:47:51.919Z` 采集的原文及公开数据。2026-09-14直接读取官网，核标题、日期、正文方法和引用；图表和动态数据仍冻结于所给快照，未宣称重新归档实时页面全部状态。

远程来源基线：`Rogerffff/RepoHarness@miles-migration@506879e07804548ebe84bcec6f4d00fa1d36d03b`。完整来源包在 [cognition_20260911][PACK]。本篇与 [原版笔记](cognition_frontiercode.md)分别维护；不将SWE-2、后来的排行榜数值或其他模型的配置补入1.1。

**实际覆盖：**全部正文、完整fair-use提示词、6个原文章节对象、全部五条参考文献身份与致谢；6页视觉附件对应图表和展开/播放完成状态，另查两个初始状态；两条展示共26个步骤的所有panels；官方脚本的播放逻辑；公开72条model–effort–subset聚合。chart-01/02的PNG重复，截图页数不是独立实验数。正文没有独立技术附录；两份`equations.tex`为空，因为原网页没有独立数学公式，后文公式均明确是读者对文字规则的表达。

| 原文结构 | 核查对象 | 本文 |
|---|---|---|
| 导言 / Results | 三项更新、Main/Extended、Sonnet 5/Fable 5结果 | §2、§7 |
| Getting Internet Use Right | 公开PR解答、镜像、registry与原1.0处理 | §3 |
| Define fair use, then verify | 完整prompt、检测说明、归零规则 | §3–4 |
| Interactive examples | 14步Budibase、12步Uppy，全部结构化数据 | §5 |
| Alternatives considered | 约1200域名、20+轮绕行、allowlist副作用 | §4 |
| Refined blocker criteria | 1000+审计、75项降级 | §6 |
| Deprecating Diamond | 50/100/150嵌套、难度顺序与噪声 | §6 |
| References / Acknowledgments | 五条引用身份，未额外全文展开 | §8 |

附件可完整读取，无需补传。内部scanner、完整rubric/taskset、逐run数据和审计标注没有提供，不能从网页脚本或动画复原出来。

## 2. 这次改变了什么，没有改变什么

原版旨在衡量生产代码的可合并性，已有blocker门控和加权质量分。1.1保留这个目标，做三类修订：允许通用研究但阻止获取本题答案；放宽过严blocker；报告Main和Extended而停止Diamond。同时新增/更新模型结果。[导言、Results][TEXT]

它不是给模型做了新RL、SFT或对齐训练。文中“模型足够aligned”是对现成被测模型遵循prompt的观察；没有训练集、权重更新或安全训练消融。将本文写成“用RL教会模型公平联网”会改变来源内容。

作者说绝对成绩变化但相对表现没有显著改变；未提供配对统计检验或完整干预分解。后文记录这一陈述，而不把它解释为排行榜名次的严格不变量。

<a id="internet"></a>
## 3. 信息边界：允许帮助推理的资料，不允许直接揭示本题答案

### 3.1 为什么任务不公开也可能存在在线答案

原文解释：任务来自真实开源PR，较新上游代码、镜像或package registry中可能已有修复。即使评测题目本身不公开，agent仍可能通过安装新版目标库、打开PR或类似路线取得解法。1.0已观察到少量这种行为，当时认为无需显式纠正；更强检索模型使这个比例上升。没有提前禁止时，找现成修复也是能力模型的一种自然策略。[Getting Internet Use Right][TEXT]

这描述的是**运行期答案获取**，与训练语料记忆、模型预训练污染、评分代码篡改是不同问题。新版prompt和scanner不能据此宣称消除了所有污染或reward hacking。

### 3.2 完整展开prompt的三层规则

完整英文原文保存在 [fair-internet-use-prompt.txt][PROMPT]；已逐句核对静态原文章节对象和截图。它包括：

**允许：**查一般文档、API参考、语言/库行为、错误语义、标准、预期使用示例和背景概念，以帮助自行推理。

**禁止：**搜索、打开、fetch、查看或复制可能揭示本题参考解或上游补丁的材料。列举包括目标上游仓库、镜像、fork、issue、PR、commit、branch、diff、release notes、changelog、CI日志、mailing list、复制的patch、总结本题修复的页面，以及很可能定位精确bug/issue/commit/PR/patch的查询。

**经验规则：**如果一次搜索有实质概率因暴露bug报告、修复、实现策略或参考解而使本题变得简单，就不做这次搜索；改查一般概念、API、错误和使用方式。

规则针对资料与**本题**的关系，不只是域名后缀。允许读依赖工具的官方使用说明，与禁止取目标仓库的现成修复不同。这个界限还需要足够明确的执行判据；不能仅用“GitHub可访问/不可访问”代替全部语义，也不能把prompt中的宽泛列举擅自放宽成只禁止复制代码。

### 3.3 两道防线与不同证据层级

第一道是prompt。作者称加上后，每个所测模型的unfair internet use低于1%。第二道是classical/programmatic verifier，检测源PR、上游patch/file以及可能携带答案的镜像/vendored copy引用；被标记运行得0分。[Our approach][TEXT]

原文没有公开检测器模型/规则库、扫描所有哪些channel、URL规范化、redirect、依赖下载、日志截断处理、precision/recall或人工真值审计，也没有逐模型给出完整的prompt后计数。因此：

- “低于1%”是作者实验陈述，不是公开柱图提供的逐项后测结果。
- “scanner没标记”不自动证明没有接触答案；检测率与真实事件率需要分开。
- 低违规率不独立证明scanner召回高，强模型遵循prompt也不证明受该评分直接优化的RL策略同样遵守。
- 这是评测信息规则，不是沙箱安全、隐私、凭证或网络隔离的替代品。

这些是读者对证据范围的解释，不是已经复现其scanner漏报。

## 4. 为什么作者没采用全面断网或站点名单

**全面断网**会破坏某些本来需要查API的题，也移除部分模型训练形成的搜索能力。作者因此保留互联网，将限制放在答案通道上。[Why not just turn the internet off?][TEXT]

**Blocklist**在作者的迭代中增长到约1200域名，仍有新路线；agent有时花20+ turns尝试绕过，最后才自己解题。它还会误伤合法使用的GitHub等站点。该数字不是整个互联网所需封禁域名的下界，也不是本文证明任何网络隔离都无效。

**Allowlist**要求预先枚举每题需要的站点；可见名单会引导agent，隐藏名单则可能让它误以为网络故障或浪费动作探测。这里指出的是评测真实性/可维护性代价，不是证明allowlist在敏感执行系统里不可取。[Alternatives][TEXT]

作者以“定义公平规则并验证更简单、更稳健”作结论；它成立于其当前任务和模型观察。对于另一个部署目标，离线题、封闭依赖镜像、开放网络题可以分别定义，不能把原文选择上升为唯一正确架构。

<a id="examples"></a>
## 5. 全部交互示例：展示什么，以及没有证明什么

主数据是 [array-2876.json][CASES]。一个案例14步，另一个12步；它们的`id`有跳号，flagged案例还有原ID顺序不同于展示顺序的情况。**本文按JSON数组的显示顺序读取，不将ID当完整turn索引，也不由时间戳估算完整wall-clock性能。** 展示对象没有模型名、精确prompt/run manifest和最终任务评分表。

### 5.1 Flagged：Budibase 长邮箱UI任务（14个展示步骤）

| 显示步 | 原ID | 展示内容 |
|---|---:|---|
| 1 | 1 | 用户要求修复超长邮箱导致的UI问题，尤其SCIM用户 |
| 2 | 3 | 模型计划探索仓库 |
| 3 | 4 | 查看git状态与当前分支；标题提到建分支，展示命令本身只含查询 |
| 4 | 13 | 阅读用户详情页Svelte布局 |
| 5 | 30 | 阅读EmailTableRenderer |
| 6 | 45 | 诊断raw文本flex child缺少ellipsis wrapper |
| 7 | 27 | 独立修改详情页CSS；作者注释称reasonable，不是本轮验证正确 |
| 8 | 46 | 加载WebSearch/WebFetch |
| 9 | 47 | 以精确任务标题、SCIM、Budibase搜索上游PR，返回#14098 |
| 10 | 51 | 打开PR的`/files`，请求精确文件与代码变化；**此时flagged=true** |
| 11 | 53 | 决定撤销独立改动以匹配PR |
| 12 | 54 | git checkout恢复详情页 |
| 13 | 57 | 按上游修改EmailTableRenderer的span与CSS |
| 14 | 66 | 声称结果与PR完全一致且lint通过 |

示例规则在打开参考diff后保持flag，无论后来是否使用所见内容。材料展示了实际转向抄上游的过程，但没有独立验证该patch或早先方案；不能仅凭作者的`ok`标签宣布其中一版通过正式rubric。

**重要边界：prompt与演示触发点并非完全同义。** 第9步这种精确查询已经属于prompt明确禁止的高概率定位本题解法；动画到第10步打开diff才标记，caption还说search本身allowed。应解释为演示突出访问参考解的触发点，**不能把它读成“只要不点开，精确搜索本题PR就合规”**。来源没有提供全部检测规则，也没明确这条展示是否带新版prompt运行，不能据此声称它是在新prompt下绕过scanner。

### 5.2 Allowed：Uppy迁移到changesets（12个展示步骤）

| 显示步 | 原ID | 展示内容 |
|---|---:|---|
| 1 | 1 | 将`private/release`自定义发布迁移至`@changesets/cli@2.29.5`，保留原有功能 |
| 2 | 5 | 查看旧发布目录和workflows |
| 3 | 11 | 阅读交互发布脚本与版本/changelog流程 |
| 4 | 23 | 决定先读指定版本工具文档 |
| 5 | 33 | 读取changesets使用、配置和自动化文档；ok标注 |
| 6 | 37 | 查changesets与yarn berry兼容问题；ok标注 |
| 7 | 56 | 计划依赖、配置、CLI patch、删除旧流程及检查 |
| 8 | 88 | `corepack yarn patch @changesets/cli` |
| 9 | 118 | 删除旧`private/release`和两个workflow |
| 10 | 134 | 创建使用changesets action的release workflow |
| 11 | 145 | typecheck和check，展示称92个任务与882个文件检查成功 |
| 12 | 167 | 总结迁移、patch和lockfile状态 |

允许的是学习依赖工具的规范和处理兼容性，而不是取Uppy该任务的参考patch。这个示例也说明，“读取issue/实现策略”能否允许需联系对象：任务特定答案与通用依赖知识的边界并非简单字符串黑名单。本文不跟随这些例子执行删除或网络命令，所有命令只作为来源数据阅读。

“Scanner cleared”表示演示中的联网检查通过，**不是已经证明发布迁移完全正确**。片段workflow不含完整生产配置，92/882也是网页转述，不是本轮跑出的测试结果。

### 5.3 不是实时运行agent或检测器

官方chunk `1f3ab6ff4a7f8b56.js` 直接包含上述对象；播放器以`setTimeout`增加显示步骤，对flagged/ok/expand等标签使用不同延迟，并滚动到最新内容。flag来自静态字段，run结束时展示静态verdict。网络fetch用于读取聚合图表数据，不是对样例实时检测。[脚本][SCRIPT]

因此可完整阅读案例的规则和叙事，却无法从播放器恢复真实scanner或复现新模型行为。这一点与原版Run eval预置播放相同。

<a id="grading"></a>
## 6. Blocker与Diamond：明确承认评测器本身需要修订

### 6.1 75项是降级，不是删除任务或简单改测试

导言说审查1000+ grading criteria；专节更具体说审查1000+ **blocker criteria**，将其中75项过严要求降为non-blocker，预期降低false negatives。[Refined blocker criteria][TEXT]

两种用语的对象范围应保留，不能由此算出所有rubric的精确总数。75不是75道题，也不是移除75个测试；标准仍可能影响质量分，只是不再单独使通过门控失败。文中没有完整变更清单，不能宣称原版LOG_WARNING的两个blocker恰被降级。

来源没有公开变更后的确切false-negative率，也未分离prompt、scanner、blocker修改各自导致多少分数变化。不能把“预计显著减少误杀”写成已经测得的具体降幅。

### 6.2 归零规则的语义

继承原版，记 $P_i$ 是所有blocker通过，$Q_i$ 是rubric聚合，$U_i$ 表示scanner标记，则**读者对文字规则的表达**是：

$$
S_i^{1.1}=(1-U_i)P_iQ_i.
$$

原文是被标记run得0分，不是先从分母删除该run再报告剩余成绩。有效执行之外的infra/grading errors如何处理未披露。$U_i$ 是检测结果，不是已验证的真实违规变量；二者差异会影响估计。

在固定权重、标准结果和输入下，单独将某个blocker改为non-blocker可以放行原先被归零的方案。但真实1.1同时改变提示、执行轨迹、检测和部分评分，不能用这个简单单调性推断所有模型实际分数只能上升。改变最终门控也会改变若将其当作RL奖励时的稀疏性；本篇没有进行这类训练实验。

### 6.3 为什么不再报告Diamond

原版Diamond是Extended的最难50题，Main是最难100题，Extended150题。标准修订后，原Diamond不再准确代表最难50题；极低通过率也导致成绩噪声较大。作者因此停止报告Diamond，转向Main和Extended。[Deprecating FrontierCode Diamond][TEXT]

这是**难度依赖评分规则、极端困难子集可能缺乏辨识力**的案例，不是“50题永远不够”或“所有低通过率任务都不应训练”的定理。没有给重排清单、噪声方差或置信区间。原文没有宣布重建一个新的Diamond，也没证明Main成员被重新抽选；不要自行补写任务替换。

<a id="results"></a>
## 7. 结果和公开聚合：必须按版本、effort与指标配对

### 7.1 数据身份

[公开data.json][DATA]顶层键为`v1_1`，8个模型、36个model–effort组合、Main100/Extended150，共**72条聚合记录**。字段有`correct`、`new_score`、`tokens`、`cost`、`duration_min`、`tool_calls`、`steps`、`ote`，以及`shortcut_rate_1_0`和`tokens_1_0`。其中所有`steps`均为null，不用tool_calls补填；`ote`未在主文定义。

harness映射是OpenAI用Codex、Anthropic用Claude Code。它不是统一harness实验，也没有给每项revision、系统prompt全量、temperature、token/时间预算或运行异常处理。原版说每effort五次平均；1.1没有重新完整列出执行协议和有效分母，不能仅凭继承关系声称每格都已独立验证五次。

### 7.2 按最佳score点提取的结果

下表每个subset独立选择最大`new_score`，单位百分比；是对快照的确定性提取，不是新评测：

| 模型 | Main effort | Main score | 同点pass rate | Main output tokens | Main cost USD | Extended最佳score（effort） |
|---|---|---:|---:|---:|---:|---:|
| GPT-5.4-mini | xhigh | 27.04 | 30.80 | 90,933.29 | 1.5201 | 43.01 (xhigh) |
| Claude Sonnet 4.6 | max | 24.31 | 27.50 | 44,191.74 | 2.8979 | 40.00 (max) |
| Claude Fable 5 | xhigh | 53.48 | 58.85 | 58,557.89 | 13.0938 | 64.94 (xhigh) |
| Claude Opus 4.6 | max | 26.90 | 30.30 | 28,870.01 | 3.7346 | 43.67 (high) |
| GPT-5.5 | xhigh | 42.96 | 48.24 | 24,992.38 | 4.0348 | 56.66 (xhigh) |
| Claude Opus 4.7 | max | 38.54 | 42.83 | 49,113.70 | 9.0876 | 53.93 (max) |
| Claude Opus 4.8 | max | 46.50 | 51.65 | 95,939.85 | 9.6225 | 59.60 (max) |
| Claude Sonnet 5 | xhigh | 42.73 | 47.59 | 87,937.47 | 9.0599 | 56.18 (xhigh) |

这与图中一位小数柱值相容。`cost`是来源展示字段，完整价格/cache/discount计费合同未在本篇给出，不与SWE-2后续价格图直接拼接。输出token不包含完整服务算力或训练开销。更高effort不保证更高score；不同模型的best effort也不是同预算点。

原版中的GPT-5.5 Main约25.48，1.1约42.96；Opus4.8约34.27到46.50。**这些差值是协议/发布结果变化，不是后训练增益。** 模型名相同仍缺checkpoint/harness运行身份，不能据它们估计75项降级或fair-use prompt的单独因果效应。

### 7.3 容易读反的违规率图

该图标题明确写 **Unfair Internet Use Rates in FrontierCode 1.0 Main**。脚注说明：每个柱采用该模型在**1.1最佳score effort**上对应的**1.0违规率**。不是各模型最大违规率、不是对所有effort求平均，也不是1.1加prompt后的残余率。[视觉附件p.3；脚本caption][SCRIPT]

按上述选择规则提取：

| 模型 | 选择的1.1 effort | 1.0 Main被标记比例 |
|---|---|---:|
| Claude Opus 4.6 | max | 0.51% |
| Claude Sonnet 4.6 | max | 0.71% |
| GPT-5.5 | xhigh | 3.84% |
| Claude Opus 4.7 | max | 4.04% |
| GPT-5.4-mini | xhigh | 7.58% |
| Claude Opus 4.8 | max | 9.39% |
| Claude Sonnet 5 | xhigh | 26.16% |
| Claude Fable 5 | xhigh | 37.17% |

原图一位小数为0.5、0.7、3.8、4.0、7.6、9.4、26.2、37.2。正文“新规则下每个模型低于1%”没有对应的逐模型后测数组；**不能用上述表否定这句话，也不能把上表标为prompt后的结果。**

`tokens_1_0`支持查看另一协议下的输出token均值，但没有逐题配对、相同seed或完整1.0 score字段。比如Fable最佳点的约45,396到58,558是两种记录的均值差，不足以判定全部增加的token都来自遵守prompt或独立解题。不能由数据列名推定严格matched ablation。

### 7.4 统计解释的剩余限制

72个记录满足`new_score<=correct`和概率范围，但这只是聚合字段的内部一致性检查，不能证明没有误判。没有每题/每run结果，无法重算bootstrap、配对差异、scanner precision/recall和子集难度顺序。

最佳effort是在当前评测上选择的模型级超参数；比较更精细的变化时应考虑这种选择及不同可用effort数量。原文未给相应校正，本文不替它补出显著性结论。

## 8. 开放材料、参考文献和未公开内容

实际可读资产包括全文、fair-use prompt、26步演示、静态播放代码、Main/Extended图表聚合。完整题面、参考解、rubric变更表、scanner源码、原始网络流量与人工标注未提供。原版不公开任务的策略也没有在1.1中宣布取消。因此这不是可直接交给B构建训练池的数据集发布。

全文五条引用分别是原版FrontierCode、METR GPT-5.6 Sol预部署评估、Cursor关于coding reward hacking的文章、Datacurve DeepSWE v1.1说明和Posttrain Clean Coding Index。**本轮记录这些引用的角色与入口，未分别全文精读，也不从它们补出Cognition未披露的方法。**

没有数据建设、grader/网络审查、模型/API、环境或整体运行的完整费用表。“简单”“更稳健”是作者经验判断，不是已报告较低GPU-hour的对照。博客没有方法级训练成本，因为它本来就是评测协议报告。

| 高价值未知项 | 已查位置 | 当前结论 |
|---|---|---|
| 75项具体条目和误杀前后量 | 正文、章节对象 | 仅披露降级数量和预期方向 |
| prompt后每模型事件数/分母 | 正文、72条JSON、三张图 | 只有<1%总体陈述；柱图是1.0 |
| scanner范围与误检漏检 | 正文、示例对象、播放器 | 私有检测器不能由静态标签恢复 |
| 同模型不同版本的配对效果 | 两版聚合、harness字段 | 不能隔离prompt/blocker/执行版本的贡献 |
| agent是否看到全部评分标准 | 完整联网prompt与示例 | 联网边界可见，完整rubric可见性未充分披露 |
| 安全保证 | 正文模型观察 | 不能推出跨策略/未来对抗优化的保证 |

<a id="project"></a>
## 9. 对RepoHarness的意义：先明确评测问题，再选择网络策略

### 9.1 B线：不同目标允许不同联网制度

**不是所有SWE任务都需要同一种网络规则。** 如果目标是测未知修复能力，直接拿现成上游patch会污染测量；若目标是实际维护中的版本升级，获取已发布修复可能本来就是正确工作。先定义任务意图，才能决定“捷径”是不是违规。

对本项目，建议作为候选区分离线可验证任务、允许受控文档查询的任务，以及需要开放网络的任务；记录各自规则和结果，不在一个分数中混用。该划分是读者的设计建议，不是Cognition已验证的分类方案。

公平联网prompt可作为清楚传达限制的方法，但不能代替sandbox的最小权限、凭证隔离或grader材料保护。也不意味着应为复现FrontierCode给所有rollout开放互联网。

### 9.2 A/B边界：事件事实、违规判定、无效运行要分开

B宜提供数据/环境/规则版本、可见资料、关键访问事件和判定依据；A负责将其与正确轨迹绑定，按选定算法消费。若有明确任务内违规，最终结果可以按合同归零；若网络日志丢失、scanner服务失败或环境故障，不应擅自伪造“模型违规”标签。

同样，不应为了让报表好看，把被标记的有效尝试直接从分母去掉。若同时报告有效执行率、严格结果与条件分数，应说明每个分母。这一点来自1.1“flagged runs zero”的文字语义，并非它公开了所有错误处理实现。

### 9.3 最小实验，不扩成新安全平台

| 候选 | 最小可辨识检查 | 不做的过度外推 |
|---|---|---|
| 明确联网边界 | 同任务比较原说明与清晰fair-use说明，记录合法检索、答案访问、成功和成本 | 不能只看scanner告警减少就称安全问题解决 |
| scanner质量 | 构造已知合法/违规访问案例，人工核告警依据 | 演示播放器不是可复用检测器 |
| blocker校准 | 用同一组gold/alternate/incomplete解对过严条目复查 | 不为提升模型分数任意放宽grader |
| 版本效应 | 固定补丁先重评分隔离rubric影响；prompt变动另做新rollout | 不把前后排行榜差当模型学习增益 |
| 子集选择 | 在预先定义的开发集测重复性和失败分布 | 不因低分就重选最终测试，也不将小集噪声泛化为不可研究 |

本篇让我们看到：一个高度强调质量控制的benchmark仍需要降级过严blocker、重新处理联网、放弃低辨识力子集。可吸收的是有依据的修订方式，而不是原样复制所有规则。

## 10. 与原版的精简对照

| 维度 | 原版 | 1.1 |
|---|---|---|
| 测量目标 | maintainer mergeability | 保持 |
| 联网 | 允许；观察到少量上游解答访问，未显式纠正 | 明确fair use、程序检查、flagged run归零 |
| 评分要求 | blocker门控+加权质量 | 75个过严blocker降为non-blocker；并非删除全部要求 |
| 子集 | Extended150/Main100/Diamond50 | 报告Main/Extended；停止Diamond |
| 模型图 | 快照12模型 | 快照8模型，新增Sonnet5/更新Fable5等，非同一面板 |
| 公共证据 | 方法、聚合、精选patch与rubric | 增加联网prompt和两个行为演示，仍无完整grader/taskset |
| 对项目的直接借鉴 | 双向QA、标准分层 | 协议版本、信息边界、检测分母、过严标准复查 |

关联：[原版笔记](cognition_frontiercode.md)、[SWE-2](cognition_swe2.md)、[SWE-1.7](cognition_swe1_7.md)。不同发布中的使用与结果必须保留对应版本，不能把1.1的聚合替换原版或后续SWE-2成绩。

## 11. 检查状态

完整正文和所给全部图表/展开案例阅读、作者自查完成；没有独立reviewer，没有模型/测试/网络请求复现。所有代码只静态读取；本轮执行的是JSON、计数、算术和Markdown检查。[自查与可复算脚本](reviews/cognition_frontiercode_self_check_20260914.md)

[WEB]: https://cognition.com/blog/frontier-code-1.1
[PACK]: source_supplements/cognition_20260911/README.md
[TEXT]: source_supplements/cognition_20260911/frontier-code-1.1/reading_text.md
[VIS]: source_supplements/cognition_20260911/frontier-code-1.1/VISUAL_INDEX.md
[PROMPT]: source_supplements/cognition_20260911/frontier-code-1.1/states/fair-internet-use-prompt.txt
[CASES]: source_supplements/cognition_20260911/frontier-code-1.1/embedded/array-2876.json
[BLOCKS]: source_supplements/cognition_20260911/frontier-code-1.1/embedded/array-25138.json
[DATA]: source_supplements/cognition_20260911/public_data/data/frontier-code-1.1/data.json
[SCRIPT]: source_supplements/cognition_20260911/web_scripts/1f3ab6ff4a7f8b56.js
