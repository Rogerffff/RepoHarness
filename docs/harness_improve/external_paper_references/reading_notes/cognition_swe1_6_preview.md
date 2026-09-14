# SWE-1.6 Preview：异步资源配置、训练加速与 Model UX 的未完成取舍

SWE-1.6 Preview 仍在训练中，沿用 SWE-1.5 的同一 pre-trained base，在产品 Cascade 配置下将 SWE-Bench Pro 图示分数从 40.1 提至 51.7，同时报告 batch-size 归一后的 step 比三个月前快 6 倍。其最有价值的披露不是一个新 loss，而是低精度、KV 亲和、训推资源分配与用户体验之间的取舍。正文给了一个忽略 staleness 和权重发布成本的平衡模型；其中输入／输出比率定义前后相反，且 GPU 数与 engine 并发的单位需谨慎区分。作者完整报告过度思考、自我验证过多、串行工具和长命令同步执行等未解决行为，不能把 benchmark 提升描述为产品体验全面改善。

导航：[来源覆盖](#scope) · [模型与评测](#eval) · [性能](#speed) · [资源公式](#allocation) · [行为与项目](#ux)

<a id="scope"></a>
## 1. 来源与完整阅读范围

正式来源：Cognition，*An Early Preview of SWE-1.6 and Research Update*，[网页][WEB]，**2026-03-01**。署名 Carlo Baronio、Ben Pan、Sam Lee、Eric Lu、Steven Cao、Rohan Choudhury、Adam Zweiger、Ray Wang、Gary Chang、Silas Alberti。

本轮以用户 `02_SWE17_16_15.zip` 中的[正文][TEXT]与原图为主要冻结材料；采集于 **2026-09-11T09:42:40.145Z**，阅读日期 **2026-09-14**。网页工具另取得全文，核对标题、日期和关键段。项目快照为 `miles-migration@2484c93cad304588b41abeb38b6b6b976dfbda0d`。本文是独立维护入口，与 [1.5](cognition_swe1_5.md)、[1.7](cognition_swe1_7.md) 相互引用，不用后来博客的配方补写本篇。

| 原文部分 | 读取材料 | 本稿 |
| --- | --- | --- |
| 导言与 Evaluation Details | 全文、9模型对照加本模型的10柱图 | §2–3 |
| Scaling RL | 内部 solve-rate 和 hard-query thinking 曲线 | §4 |
| How we made our training 6x faster | NVFP4、DP亲和、Multi-Node NVLink 全文 | §5 |
| GPUs Allocation and Staleness | 全文、staleness双面板、4张原始公式图 | §6 |
| The missing axis: Model UX | 全文、Arena图、改善／恶化清单 | §7 |
| 结尾与链接 | 数据/工具承包团队署名及引用身份；排除网页全站推荐卡片 | §8 |

[视觉索引][VIS] 共9页：1主评测，2 solve rate，3 thinking，4 staleness，5–8公式，9 Arena。页码是采集者的截图PDF，不是作者发表的论文页。全部原图已目视核验；透明公式PNG以白底合成后查看，未OCR。无单列附录，没有把页尾其他博客推荐当正文。

## 2. 模型、阶段与数据：哪些关系是真的

作者明确说本次与1.5使用同一个 pre-trained model，部署速度同为950 tok/s；**并未说直接从1.5最终checkpoint续训**，也没有披露基座名称、确切参数量、SFT阶段或教师。不要从1.7的K2.7基座倒推1.5/1.6。[导言][TEXT]

训练改进包括稳定性算法、更多RL环境和更好数据。所谓解锁两个数量级更多compute，是作者对训练能力扩展的描述；没有公开GPU-hours、训练步数、数据token或总费用，不能据此算这次正好耗资100倍。Preview是正在训练的一个checkpoint，不代表后来所有标注SWE-1.6的结果。

训练环境完整数量、repo/语言分布、generator/solver/grader、reward组合、组采样、baseline/critic、clip、token mask、loss分母、模型超参数均未披露。文中引用Kevin/SWE-grep作为方法演进，不等于交付了它们在本次训练中的确切版本。硬件为数千GB200 NVL72，不能迁移成8张PCIe卡上的已验证配方。

<a id="eval"></a>
## 3. SWE-Bench Pro：完整原图与异构评测协议

图标注 **731项agentic coding tasks、41个repo**。这是该图的自述口径，本文未独立下载manifest确认是哪一个公开／内部split。

| 模型（图中标注） | Score (%) | 文中评测来源／harness |
| --- | ---: | --- |
| GPT-5.3-Codex，xhigh | 56.8 | OpenAI自报；作者自己尝试Codex CLI、Cascade、Devin，最佳仅54.0，保留自报值 |
| Claude Opus 4.6，high | 53.6 | Claude Code、Cascade、Devin三harness中的最好结果 |
| SWE-1.6 Preview | 51.7 | Cascade，产品相同system prompt和设置 |
| Claude Opus 4.5，64k thinking | 51.6 | Anthropic自报 |
| Claude Sonnet 4.6，high | 51.4 | Claude Code、Cascade、Devin中最好 |
| Composer-1.5，Cursor CLI | 50.8 | Cursor CLI，多轮spot-check和重跑 |
| GPT-5.3-Codex-Spark，high | 50.5 | OpenAI自报 |
| GLM-5 | 48.7 | Cascade、Devin中最好 |
| Kimi K2.5 | 48.2 | Cascade、Devin中最好 |
| SWE-1.5 | 40.1 | Cascade，产品相同system prompt和设置 |

来源：Evaluation Details 与 `original_assets/image-01.png`。**不是统一harness或统一effort/预算下的纯模型对照**。best-of-harness与单harness自报的选择过程也不同。未给完整重复次数、置信区间和所有失败处置；不把0.1/0.3点差当显著胜出。

导言称“11% higher”。按图中51.7与40.1计算，差为 **11.6个百分点**，相对提升约 **28.93%**。两种口径明确分开，不把正文近似措辞静默改成精确相对增长。1.5旧文40.08与此40.1可由显示精度解释，但仍按各来源分别保存。

### 3.1 环境与评分调试是真实工作的组成部分

作者说人工阅读数百条轨迹，并与Scale发布轨迹交叉核对；处理过依赖、agent/grading环境设置、各harness不一致timeout、patch收集/应用边界和grading OOM，同时检查训练repo与SWE-Bench Pro任务repo不重叠。[Evaluation Details][TEXT]

这支持B线完整记录评分的中间事实，而非只保存pass/fail。repo不重叠是其中一种审计，不是所有数据污染风险已经排除；原文也没有提供完整去重manifest。**评分环境失败与候选补丁造成的失败，应保留各自归因**；本文没有替作者补统一重试策略。

## 4. 训练曲线：正结果与解释边界

`image-02.png` 标题为内部可验证SWE任务的训练表现，solve rate使用EMA，从标注 **52.4%到68.7%**。横轴写Training Step但没有数字刻度；未标明这条曲线对应训练池、另一个holdout还是动态任务集合，不将其认作SWE-Bench Pro最终验证曲线。

`image-03.png` 的thinking token曲线来自一部分较难SWE-Bench Pro题，EMA从 **4,245到7,958**；精确比约 **1.875×**，图标题概括为2×。题量、选择方式和重复数未知。它测的是thinking tokens，不是工具总轮次、总输出或总成本。

两条曲线和作者观察支持训练期间解题与思考行为发生变化；没有单独证明“因为思考更长所以更聪明”，也没有固定质量下的token效率对照。作者自己把更长思考与过度验证的用户代价并列讨论。

<a id="speed"></a>
## 5. 训练快6×：分母、组件与拓扑不能合并

| 披露 | 原始比较 | 不应外推 |
| --- | --- | --- |
| 训练step快6× | 与三个月前，normalizing for batch size | 非达到同分所需总GPU-hour降低6×，没有严格同任务长度与硬件控制 |
| NVFP4 throughput高2–3× | 相对BF16或FP8 rollout配置，配合算法改善以处理logprob差异 | 无完整采样/并发矩阵；非只改dtype就有相同收益 |
| Multi-Node NVLink加速1.5× | 数千GB200 NVL72的训练系统 | 不等于单节点PCIe拓扑可获同样加速 |
| 950 tok/s | 与1.5同量级的产品部署速度 | 非每GPU训练采样吞吐 |

来源：How we made our training 6x faster；原文没有把这些项组织为可相乘的独立消融。因此不计算 $2\text{–}3\times1.5$ 来“解释”6×，也不补未报告的余下倍率。

多轮请求有共享前缀。作者给每条rollout标DP rank ID，使后续请求回到该rank，保留KV并减少重复prefill。其目标同时包含cache命中和负载平衡，但没有给调度算法、热缓存迁移、长尾分布或对应消融。**稳定亲和与动态负载均衡是需要权衡的目标，不由一个ID自动同时保证。**

<a id="allocation"></a>
## 6. GPU分配公式：原图恢复、符号冲突与适用条件

### 6.1 原文假设

将系统近似为两阶段：inference生成trajectory，trainer每取得 $B$ 个sample更新一次。稳态重叠，step time由较慢阶段决定。作者认为由于其算法改进，选择分卡时可以暂时忽略staleness；权重刷新／广播也忽略，或视为已经异步摊销。这是**其系统用于初猜的假设**，不是不需要记录陈旧度的结论。[GPUs Allocation and Staleness][TEXT]

总GPU数 $N=n_i+n_t$；$s_{roll}$ 是饱和时包含prefill代价的**输出tokens/sec/GPU**，$L_{out}$ 为平均每trajectory生成token；$s_{train}$ 为对应更新工作负载的有效tokens/sec/GPU。

**符号冲突必须保留**：前面的列表把 $r$ 称作 output-to-input，随后又明确写 $r=\text{in/out}$，并使用 $L_{tot}=L_{out}(1+r)$。下文为复核公式而采用后者，即 $r=L_{in}/L_{out}$；这是选择与图和代数一致的解释，不声称原文从来没有前一种定义。

文中把 $L_{in}$ 解释为cache保留下新增prefill，而非每轮完整历史。$s_{roll}$ 已测入prefill成本，所以 rollout 分子仍是输出token，不再乘一次 $(1+r)$。

### 6.2 四张图片公式

从原始透明PNG目视转写，不靠正文提取猜分母：

$$
t_{roll}\approx\frac{B L_{out}}{n_i s_{roll}}.\tag{图5}
$$

$$
t_{train}\approx\frac{B L_{tot}}{n_t s_{train}}
=\frac{B L_{out}(1+r)}{n_t s_{train}}.\tag{图6}
$$

取 $t_{step}\approx\max(t_{roll},t_{train})$，令两阶段相等，得到：

$$
n_t\approx\frac{N}{1+\dfrac{s_{train}}{s_{roll}(1+r)}},\qquad n_i=N-n_t.\tag{图7}
$$

每inference rank并发 $c$ 条轨迹，原文估计step-based陈旧度为 $c n_i/B$，代入得：

$$
\operatorname{avg\ staleness}\approx
\frac{c}{B}\frac{N}{1+\dfrac{s_{roll}}{s_{train}}(1+r)}.\tag{图8}
$$

图号为附件视觉顺序，不是原文编号公式。前3式维度在上述定义下自洽；本轮用独立算术验证平衡恒等式，没有据此推荐实际训推卡数。

### 6.3 GPU与engine、唯一token与计算token的边界

原文先定义 $n_i$ 为GPU数，后用每engine并发 $c$ 乘 $n_i$。若每engine横跨多个GPU，就需明确engine数与GPU数之间的映射。**读者扩展**：若一个engine用 $p$ 张GPU，则在途数更自然是 $cE_i$，$E_i=n_i/p$；不能在多卡TP/EP设置下直接按单GPU一个engine代入原陈旧度式。原文没有给这个换算。

此外，实际trainer可能为多次模型调用重复处理历史、计算old/ref logprob或critic、经历padding/packing/CP不平衡。此时training physical-token work未必等于唯一追加输入加输出。需要使用对应实际布局测 $s_{train}$ 或另外建成本变量，不能仅靠rollout端cache账单推定训练工作量。

$cn_i/B$ 是稳态并发量与吞吐量的近似，不涵盖ready queue等待、长尾、批形成、丢弃补采、不同policy版本及请求重试。它不是p95 staleness上界。$B$ 与 $L_{out}$ 在简化平衡解中消去，也不意味着改变batch或长轨迹对真实系统没有影响：它们会改变吞吐、内存、排队和优化质量。

最后，$n_t$、$n_i$ 必须满足整数、模型显存、TP/EP/DP拓扑与共置约束。连续最优解只是参考点，不能用数学分卡替代实际可运行的并行配置。

### 6.4 Staleness图实际说明什么

图4左侧标Average Staleness of Trajectories / Average Lag (Steps)，右侧标题为Utilization of Inference Engines，**纵轴实际写Concurrent Requests**。较高staleness条件维持较稳定的请求并发，baseline明显回落波动；坐标无绝对刻度。

因此它说明某种控制方式能减少推理供给中断，但不能从右图读取GPU利用率百分比，也不能推出更陈旧不伤害学习。作者的分卡假设与后来1.7强调限制staleness以支持激进学习率，应当理解为不同系统条件，不是“一次解决陈旧度就可永久忽略”。

<a id="ux"></a>
## 7. Model UX：原文主动报告的负面结果

作者认为难度更高的SWE benchmark仍不能充分测用户体验；Windsurf Arena的盲选偏好只提供另一个观察面。所列重要维度为：从不完整上下文推断意图、让用户看见推理/命令/计划、工具效率与非侵入性、自适应思考、跨多轮遵循指令。[The missing axis][TEXT]

**改善**：减少不必要单测和文档；长任务用todo跟踪；专业且简洁的回答；先获取上下文、思考再改代码。

**尚未解决**：过度思考和循环验证；轮次过多；长命令同步而非后台执行；本可并行的工具调用却串行。文中还举出模型偏好表达能力更强的bash搜索，但复杂命令降低可见性，并可能使用户每10–20秒都要人工批准。这里是dogfooding观察，没有量化频率与因果消融，不把这种时间范围当整个系统的统一批准协议。

### 7.1 Arena图：偏好不是正确性

图9的Elo值为：Opus4.6 1075、Opus4.5 1062、Sonnet4.5 1050、SWE1.5 1016、Haiku4.5 1000、GPT5.2 992、KimiK2.5 986、Gemini3 Flash Low 943、Grok Code Fast1 938、Gemini3 Pro 913。它没有1.6 Preview一列。图有误差线，但本文没有获取对局数、采样规则、区间方法和价格条件，因此不作显著排名结论。

作者将1.5较好的偏好表现主要归因速度，这是其解释，不是只改速度的随机实验。快、正确、少打断用户和有充分证据应分别测量，不能用一个Elo或一条solve-rate曲线全部代替。

## 8. 开放性、成本与对项目的作用

原文公开的是博客、图片、方法解释和外部评测来源。没有配套完整训练代码、环境包、权重、检查点或总成本；不因文中提到开源基座就称本项目可复现。本文不深入展开Kevin、SWE-grep、Blackwell、排行榜等引用全文，也不把网页推荐卡片加入科研覆盖计数。

| 对RepoHarness的候选启示 | 先验证什么 | 不应直接采用什么 |
| --- | --- | --- |
| 用实测吞吐提出训推分卡初猜 | 同一工作负载、精度、cache条件下测推理输出吞吐与真实训练工作量 | 本篇数千GB200拓扑与6×数字 |
| session affinity | cache命中、prefill重算、engine尾部负载 | 不经量测假定粘住一个rank始终最好 |
| 学习质量与系统速度一起看 | time-to-quality、失败/过滤分布和staleness尾部 | 单独最大化Concurrent Requests |
| 评分链完整性 | 相同补丁经原scorer与本项目scorer的事实对照 | 把评分OOM/依赖错误当模型错误 |
| 过程与体验诊断 | 有效工具调用、重复验证、人工交互、范围控制 | 直接奖励少轮次或少测试而不管任务结果 |

映射日期2026-09-14，基线是miles + SGLang + 外部harness/rh2，约8×96GB。以上是设计层候选；本轮没有审查这些候选是否已在A/B代码中实现，不新增训练配置或批准新数据集。

与[1.5](cognition_swe1_5.md)相比，本篇把资源调度与Model UX代价说得更具体；与[1.7](cognition_swe1_7.md)相比，它还没有披露kept-set replay、自压缩和跨洲版本管理的完整叙述。后来的SWE-2说长度baseline自1.6起使用，是后来源的回溯陈述，不能将公式悄悄写成这篇Preview已公开。

## 9. 检查状态和关键缺项

已全文读取，9张原始图全部检查，4个图片公式人工转写并验证代数；r方向冲突、11%措辞、2×标题、推理利用率图的真实纵轴均显式保留。没有训练复现、独立reviewer或算法实现审计；作者自查记录见[检查文档](reviews/cognition_swe1_5_1_7_self_check_20260914.md)。

最重要未知项：pre-trained base身份、实际RL目标及超参数、环境规模和split、GPU实际分配、每engine占卡数、完整算力/费用、曲线横轴与样本身份、各性能项独立消融、UX量化和评测重复数。当前不是材料访问失败，而是博客未披露；不向用户索要不存在的字段。

[WEB]: https://cognition.com/blog/swe-1-6-preview
[TEXT]: source_supplements/cognition_20260911/swe-1-6-preview/reading_text.md
[VIS]: source_supplements/cognition_20260911/swe-1-6-preview/VISUAL_INDEX.md
