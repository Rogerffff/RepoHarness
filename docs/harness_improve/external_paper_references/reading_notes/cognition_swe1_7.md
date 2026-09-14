# SWE-1.7：采样分布重放、长程训练与模型—环境协同精读

SWE-1.7 从已经接受大量 RL 的 Kimi K2.7 / K2.7 Code 基座继续后训练，主张以采样分布重放、数值对齐、多集群容错、self-compaction 和数据质量共同延长有效训练。其 FrontierCode 1.1 Main、Terminal-Bench 2.1、SWE-Bench Multilingual 表值分别为 42.3、81.5、77.8；前一项实际是带 blocker 的加权 rubric score，不能与二元通过率混称。最有用的披露是 top-p kept-set 如何返回 trainer，以及环境、权重、缓存、轨迹和故障恢复如何协作。主要限制是没有完整优化器、组统计、轨迹 mask、数据清单及训练成本；展示结果不是各机制的独立消融。本文同时保留“语言更紧凑但探索更多”、修改范围扩大、hidden contract 案例和图文口径差异。

导航：[来源覆盖](#scope) · [采样与梯度](#sampling) · [系统与长程](#systems) · [环境与行为](#behavior) · [评测](#eval) · [演进与项目](#project)

<a id="scope"></a>
## 1. 来源、版本和阅读范围

**正式标题**：*SWE-1.7: Frontier Intelligence at a Fraction of the Cost*。机构 Cognition；网页署名 Ben Pan、Carlo Baronio（共同一作）、Rohan Choudhury、Eric Lu、Ryan Kim、Deniz Birlikci、TC Qin、Sam Lee、Fermi Ma、Allen Liu、Yang Liu、Sampriti Panda、Jacob Teo、Ray Wang、Gary Chang、Steven Cao、Silas Alberti。发布日期 **2026-07-08**，不是来源采集日期。

**主来源与快照**：[官方网页][WEB]；用户上传 `02_SWE17_16_15.zip` 的 [正文提取][TEXT]、[视觉索引][VIS]、5 个原始 SVG、5 个网页图形截图、6 个展开状态，以及 [embedded 清单][EM]、[公开图表 JSON][DATA]。采集时间为 **2026-09-11T09:47:55.261Z**；阅读日期 **2026-09-14**。本轮网页工具也返回正文和参考文献，但动态材料以已固定的来源包为准。没有声称重新独立归档了整个实时网站。

**仓库基线**：`Rogerffff/RepoHarness@miles-migration@2484c93cad304588b41abeb38b6b6b976dfbda0d`。来源包位于 `source_supplements/cognition_20260911/`；这是原始材料采集，不是另一个 agent 的科学结论。本稿与 [1.5](cognition_swe1_5.md)、[1.6 Preview](cognition_swe1_6_preview.md) 分别成文；不覆盖已完成的 [SWE-2](cognition_swe2.md)。

**已完成范围**：全部主文、评测说明、18 条参考文献身份；全部已提供技术图像；三个 CoT 展示和三个带作者注释的轨迹案例。无单列技术附录。CoT 和轨迹的 JSON / 原始脚本片段均已读，截图只核展示身份，不把滚动框可见部分当成全文。原始 SVG 使用白底渲染查看，未 OCR、未从曲线路径反推未公开训练日志。

| 原文部分 | 覆盖与来源定位 | 本笔记 |
| --- | --- | --- |
| 导言、交互排行榜、Coding benchmark results | 主文、`array-135251.json`、`data.json`、视觉附件 pp.1–2 | §2、§8 |
| Preserving Entropy and Stabilizing Training | 全部公式、`equations.tex`、entropy/mismatch 原 SVG，视觉 pp.6–7 | §3 |
| Multi-cluster Training、Fault Tolerance | 正文、地图状态与系统图，视觉 pp.3–5 | §4 |
| Intelligent Self-Compaction | 正文与 response-length SVG，视觉 p.8 | §5 |
| Data Quality | 三项质量策略及与任务学习信号的关系，全读 | §6 |
| Results: Model Behaviors | 5 段 CoT × 2 模型 × 3 任务；三份完整注释案例；行为／边界图，视觉 pp.9–16 | §7 |
| Evaluation Methodology、References | 各 benchmark 的不同 harness、effort、timeout、外部自报；18 项引用身份 | §8、§12 |

视觉 PDF 的 16 页是资料采集者编排页，不是作者论文页。chart-01/02 的 PNG 捕获了同一块双图布局；chart-03/04 是动态地图的不同状态，不计为四项独立实验。所有模型／价格／版本事实均对应该来源，而非当前榜单状态。

## 2. 训练关系与主张：不是 1.5 → 1.6 → 1.7 的逐权重续训证明

本文明确的输入是 **Kimi K2.7**，比较表称 **Kimi K2.7 Code**，已接受广泛 agentic coding RL；后续在 **Devin harness** 内继续训练得到 SWE-1.7。没有披露另一个新增 SFT 阶段、多专家合并或 OPD 阶段。不要因为其他团队或后来的 SWE-2 使用了这些技术，就补进本篇训练图。[原文导言、Self-Compaction][TEXT]

本文将基础设施、算法稳定性、任务质量和长程训练作为联合改进。作者以进一步提升反对一种普遍的 post-training ceiling 直觉；实际证据是某一强基座上还有后训练空间，不是已证明所有基座、所有任务均可无限增长，也未分离换基座与各新增机制的贡献。

产品部署通过 Cerebras，标称 **1000 TPS**；这是部署服务叙事，不是每 GPU 的 RL rollout 测量。后面的跨大陆更新例子采用 **1T 参数模型**口径；文中没有给该次训练所有模型结构、激活参数与完整资源配置，不能据示例反推出它们。

<a id="sampling"></a>
## 3. 采样分布重放：原文公式、实际分布与未知优化器

### 3.1 作者为什么认为低概率负优势 token 会压低 entropy

原文设三个 logits 满足 $x_1>x_2\gg x_3$，softmax 概率为 $p_i$。当采到低概率 token 3 时：

$$
\nabla_x\log p_3=(-p_1,-p_2,p_1+p_2)^\top.
$$

若其 advantage $\hat A<0$，按上升方向更新：

$$
\Delta x_1\propto |\hat A|p_1,\qquad
\Delta x_2\propto |\hat A|p_2,\qquad
\Delta x_3\propto-|\hat A|(p_1+p_2).
$$

于是最大 logit 比次大 logit 增得更多，极低概率选项被进一步压制。作者据此解释：某些离轨低概率 token 的负更新会使分布更尖锐，top-p 从采样端避开这部分目标可能减缓 entropy collapse。[原文 Preserving Entropy；网页 TeX][TEXT]

这是局部的三 logit 机制，不是对任意分布、任意负优势 token、共享网络参数和 optimizer 的全局定理。正文从“low reward”走到负 advantage；实际符号还取决于 baseline，本篇没有给 baseline 实现。不能从此推成“低概率探索都不好”或“top-p 越小越好”。

### 3.2 kept-set 要重放到 trainer，而不仅是记录已采样 token 的 logprob

原文的接口是：rollout 时记录**可被采样的 token 集合**，训练端用同一集合 mask 后重归一化。它试图区分两件事：模型原始全词表分布，与 rollout 实际采样的截断分布。仅用全词表 logprob 训练，而用 top-p 采样，会额外制造分布差异。[同节][TEXT]

下面是对该文字接口的数学展开，**不是作者提供的完整 PPO/GRPO loss**。令历史上下文为 $h_t$，行为时保存集合 $K_t$，训练侧使用：

$$
q_\theta(a\mid h_t,K_t)=
\frac{\exp z_\theta(a\mid h_t)}{\sum_{v\in K_t}\exp z_\theta(v\mid h_t)},\quad a\in K_t.
$$

集合外概率为零。固定 $K_t$ 后，采样动作 $a$ 的 logprob 梯度在集合内为 $\mathbf 1[v=a]-q_\theta(v)$，集合外为零。**需要复用行为时的集合，不能默认为每次用新参数重新计算 nucleus 就等价。** 温度、top-k、min-p、工具约束和 tokenizer 等若存在也需对齐；本文未交代完整顺序。

按通常最小 nucleus 约定，若最高概率 token 本身已达到 top-p 累积阈值，kept-set 只有它一个，则 $q=1$、$\log q=0$，这个局部 policy-logprob 项的梯度为零。作者说相当多 token 因而不再贡献相应梯度，但没有给比例、top-p 数值或代价消融。**这不等于删除 token 的上下文，也不证明所有 auxiliary/KL/entropy 目标对此 token 都无梯度**；这些目标是否存在和怎样计算未披露。

**读者边界**：该重放消除的是一类采样支持集失配，不会自动修复参数 stale、量化、MoE 路由、重新分词或混合版本 KV。它也不是对原全词表策略梯度的无偏性证明：截断支持集本身已经改变采样策略。引用 R3、importance sampling 与 DeepSeek-V3.2 是来源线索，不是本文交付了这些实现及其组合公式。

### 3.3 图像实际支持什么

| 原图 | 实际观察 | 不能补出的内容 |
| --- | --- | --- |
| `assets/01.svg`，policy entropy | SWE-1.7 recipe 蓝线大致稳定，baseline 橙线后期下降；起点并不重合 | 没有数值刻度、绝对 step、entropy estimator、多个 seeds 或单因素配置 |
| `assets/02.svg`，training-inference mismatch | **实际只有一条蓝色曲线**，先上升、后回落并波动 | 图片 alt 文案提到 naive top-p diverges，但图内没有另一条 naive 曲线；不能称为可直接读数的双曲线消融 |

坐标只给方向；SVG 几何坐标不是训练日志。较低／有界 KL 也不是梯度方差降低的直接测量。正文另称 Muon optimizer 与删除 trainer 非确定性操作有益，但没有给对应配置和隔离效果，不能将整套 recipe 的曲线全归于 kept-set replay。

### 3.4 未披露的优化字段

本文没有足够信息恢复每题 rollout 数、group identity、baseline/critic、reward 组合、policy ratio、clip 阈值、更新次数、学习率、mask、token/trajectory loss 分母、截断/失败补采、teacher 或参考策略。所给三 token 公式是解释机制，不是公开训练器。本轮不以框架默认值或 SWE-grep 旧文补写这些字段。

<a id="systems"></a>
## 4. 多集群与恢复：从权重到持久轨迹，分别归属

### 4.1 实际数据流

架构图为：Data buffer 提交 prompt 给 Rollout Manager；后者向 Dynamo 路由器请求 generation，回传 scored data；buffer 再将 train data 交给 trainer。trainer 写增量权重至 cloud storage，rollout engine 拉取并原地应用。图中明确标注 **XOR diff + zstd**。[Multi-cluster Training；`visuals/chart-05.svg`]

作者使用 **4 个数据中心、3 个大陆**，组合自有 GPU 与 Fireworks 等推理供应商；只有 trainer 需要位于紧密连接的高带宽集群。地图是说明性动态视图，不能凭地图像素恢复每个真实数据中心、GPU 数或地理延迟。

### 4.2 权重发布与两个不同的时间分母

每 $K$ 个 gradient steps 生成 compressed delta，报告传输量比完整权重减少 **超过 99%**；每集群的 weight controller 轮询 manifest，下载 shards，经本地 tree broadcast 分发。对象存储同时传回 routing matrices 与 top-p masks。engine 持续服务时将 delta 预取到 CPU，准备好后短暂停顿、原地应用。[Multi-cluster Training][TEXT]

**1T 模型跨大陆更新为 1–2 分钟 end-to-end，实际 inference pause 为 3–4 秒。** 这两个数字不矛盾：前者包括异步运输／暂存，后者是关键停顿。不能将跨洲带宽节约、推理停顿减少和 learner time-to-quality 写成同一加速比。$K$、绝对传输大小、压缩率分布、网络配置和 mask/routing 上行代价没有披露。

### 4.3 在途轨迹沿用旧 KV：实现选择，不是参数版本完全一致的保证

原文说 in-flight trajectory 能在新权重下继续，KV cache 保持完整。由此至少应区分：历史 token 由旧 policy 生成、历史 KV 由某版参数计算、当前 decode 使用新权重。**本篇没有证明这等价于用新权重重新 prefill 全部历史。** 同时，保留旧 KV 也不能仅凭这一句就判定实际训练错误；需要其完整概率定义、重放、routing 与优化器才能评价。

对 RepoHarness 的可迁移问题是：如何记录行为版本及缓存版本，怎样测量恢复前后的概率差异；不是自动采用相同跨版本缓存策略。

### 4.4 Fault Tolerance

| 故障位置 | 作者的恢复路径 | 未公开／不应扩大解释的部分 |
| --- | --- | --- |
| inference engine | 每个 sandbox 的 proxy 记录 tokens in/out；Dynamo 重路由；新 replica 装载最近 checkpoint 并重放后续 deltas | “engine 只持有权重”的表述不能按字面否认其在途 KV/session；缺幂等、部分响应、工具副作用与缓存恢复合同 |
| trainer | 每节点每步异步 checkpoint 到本地并向 peers 复制 shards；失败节点由 replicas 重建 | 无 checkpoint 写放大、独立 failure benchmark 和完整状态清单 |
| 暂时少节点 | 按完整 DP replica 缩容，节点恢复后扩回；rollout 保温 | 动态 batch／loss 分母调整、rank 和 optimizer 状态语义没有说明 |
| 停机期间堆积数据 | buffer policy 决定恢复后消费哪些 rollout，作者称可防止失衡引起偏差 | 没有给 sampling law、版本窗或消融，不能据该句证明无选择偏差 |

训练系统容错、agent 轨迹恢复、sandbox 外部状态和任务级重试是不同层。token proxy 保存的记录不会自动恢复任意外部副作用。这里是责任划分的阅读分析，不是对 Cognition 未公开代码的漏洞复现。

## 5. Self-compaction 与交替预算：不是简单缩短所有轨迹

**self-compaction**：接近上下文限制时，让模型总结自己的工作状态，再从自身摘要继续。训练同时学习生成信息充分而简短的摘要，以及使用这种摘要。作者追溯到 Kevin 的早期尝试，报告本次 rollout 最长达到 **6 小时**。[Self-Compaction][TEXT]

这是最长观察／运行范围，不是平均耗时，也不是所有任务的正式统一预算。没有披露触发阈值、summary prompt、summary token 的训练 mask、跨段 advantage、训练片段归属或精确上下文长度。不能将其自动视为 CompactionRL、cross-segment GAE 或任意黑盒 harness compaction 的现成实现。

**交替预算**：unconstrained 阶段仅优化 task success；budget 阶段对超出加权成本预算的解施加惩罚。成本由 **tokens、turns、tool-call time** 组成，而不是只有输出长度。作者希望压缩能力范围内任务的长度，并保留困难题的长程行为。没有给惩罚函数、权重、阈值、阶段频率或按题校准规则。[同节、`assets/03.svg`]

图中有两段 shaded budget phase 和前后 unconstrained phase。长度总体增长中伴随阶段性回落，**并非进入 budget 后立刻单调下降**；也没有各难度桶、正确性与长度联表或固定总预算消融。不能由平均曲线单独证明每种困难任务都没有受损。

后来的 SWE-2 将 cost 与 effort 联动是另一个来源的方案，不回填成本篇隐藏公式；本次也没有从相对轴推定具体切换 step。

<a id="behavior"></a>
## 6. 数据、verifier 与学习机会

原文强调三件事，均保留作者主张和披露程度：[Data Quality][TEXT]

**双向质量检查**：false positive 接受错误解，false negative 拒绝合法解；作者通过自动执行 QA 降低二者，并指向 FrontierCode 方法。主文没有公布训练任务数、repo manifest、gold/no-op/alternate-solution 结果、各关淘汰量或人时。

**难度**：排除模型总成功／总失败、认为缺学习信号的任务，选择低比例成功的任务以推动能力。这里没有重复采样数、通过率阈值、模型更新频率或在线 curriculum 算法。它描述某种训练目标下的经验选择，不是 SFT、critic、反馈蒸馏或 auxiliary objective 都无法从全错组学习的定理。

**反作弊**：限制网络、移除 git 历史和参考工件、隔离 grading path、用程序检测已知 exploit；发现任何作弊尝试，无论成功与否都赋 reward 0。**原文说零分，不是删除样本，也不是必然负 advantage**；它怎样影响组统计、梯度和重试没有展开。“尝试”判据和误杀率也未公开。

因此本篇支持把环境质量纳入训练迭代，但不提供现成可下载的 SWE task pool，也不证明低成功率 curriculum 优于合理静态混合。制作任务的模型、教师/API 成本、许可、完整时间切分和训练—评测污染审计均未给出。不要将 1.5 的手工生产描述或 1.6 的 SWE-Bench Pro 去重声明当作本篇完整数据说明。

## 7. 模型行为：读完全部展开案例后的边界

### 7.1 紧凑 CoT：短句风格不等于更少总 token

作者报告 K2.7-Code 与 SWE-1.7 的首段 CoT 在 function-word ratio 和 words per sentence 上不同，并解释可能源于 budget phases。**主文未给统计表、词性定义、测量样本数和分词工具。** 展开区是同任务每模型前五段 thinking 及中间工具名，不是整个运行。[Model Behaviors；`array-139353.json`][COT]

本轮按 Python 空白切分，得到下面的**读者计数**，不是官方 token 统计：

| 展示任务 | Kimi / SWE-1.7 thinking blocks | Kimi / SWE-1.7 空白分词数 | Kimi / SWE-1.7 tool 记录行 |
| --- | --- | --- | --- |
| protonmail/webclients-b387b241 | 5 / 5 | 85 / 241 | 19 / 12 |
| ansible/ansible-1a4644ff | 5 / 5 | 78 / 108 | 8 / 6 |
| future-architect/vuls-5af1a227 | 5 / 5 | 67 / 84 | 10 / 9 |

三个例子的 SWE-1.7 总词数反而更多；这**不反驳短句和较少功能词比例**，却说明不能将 condensed CoT 偷换为总思考量减少。比如 protonmail 的长段在追 useMyCountry 的各消费者和 loading 语义；ansible 在说明复现、非测试修改约束与调用链；vuls 在区分内核匹配及发行版相关路径。更高信息密度与更多调查内容可以同时存在。

原始脚本字段名 **`swe2` 在本篇界面显示的是 SWE-1.7**。已核对三个展开状态，不把这批示例归到 SWE-2。中间工具名重复会合并显示为 `xN`，tool 行数不等于 agent turns，更不能还原 wall-clock。

### 7.2 探索、边界分析与修改范围

行为 boxplot 对比 Kimi-K2.7-Code、SWE-1.7、Opus 4.8、GPT 5.5；SWE-1.7 的 tool calls、file reads 和 grep/search 分布更高。图有分位结构与散点，但没有可读的底层逐题表，不估读精确中位数、样本数或统计显著性。[`assets/04.svg`]

边界讨论图的纵轴原标 **Mentions per run (log scale)**，标注值如下；保留图的原尺度而不改写为任务通过率：[ `assets/05.svg` ]

| 类别 | Kimi-K2.7-Code | SWE-1.7 |
| --- | ---: | ---: |
| Edge cases | 4 | 7 |
| Hypotheticals | 21 | 21 |
| Adversarial inputs | 132 | 428 |
| Beyond the ask | 16 | 27 |

正文较广泛地描述边界和假设思考增多；图中的 **Hypotheticals 实际相等**，不是每类都增加。提及更多不等于完成更多有效验证；分类方法、聚合口径与判定者未披露。

作者认为这些行为来自降低 verifier 的假阳性与假阴性，但没有训练期 QA 开／关对照。负面结果同样明确：更多推理会写更多测试、触及更多文件，可能超出最小修改范围；作者将这是仍待优化的轴，而不是全部视为更高质量。

### 7.3 三个完整注释案例

以下覆盖 `array-151019.json` 全部内容。它们是作者选出的带解释摘录，不是原始完整轨迹、补丁、环境快照或盲审对照。[案例 JSON][TRACE]

| 任务 | 作者展示的差异 | 原文中重要细节／限制 |
| --- | --- | --- |
| `fizzy-implement-authorization` | Kimi 从常规 URL/account 假设推导权限；SWE-1.7 跟踪真实 session、先测试匿名访问漏洞，再构造匿名／有权／无权用户矩阵 | 作者称 orphaned 文件和跨 account 行为题面未规定，hidden tests 有要求；SWE 的检查顺序得到期望结果。成功至少相对于该 verifier，未提供完整依据判定所有替代行为都不合法 |
| `matplotlib-bug-stackplot` | 两者找到重复 facecolor 参数；Kimi 后来缩小范围，SWE 先实测各 style 参数和逐层语义 | 作者摘录给 Kimi 27/100、SWE 89/100，并提另一 Kimi trial 95。SWE 三次首改前脚本数为 43/30/31；不能把一次精选失败写成 Kimi 必然不会修复，也不能把写 30 个脚本视为普遍最优预算 |
| `uv-frozen-uv-lock-check-fails` | 两者都发现 env bool false 造成的冲突；Kimi 实测其他子命令也失败但选择限制 ticket 范围，SWE 动态遍历参数修整个类别 | 不是“基座从不做实验”，而是证据已有后怎样决定合法改动范围；本文未给这个任务的完整评分表或等预算多次对照 |

**读者分析**：这些案例支持“验证意图和设计假设，不只验证自己写出的代码”的研究问题。不过合理根因泛化与越权扩张之间没有一个通用规则。尤其是作者同时承认 hidden contract 未显式写入题面，并批评扩大 scope；用于 B 线时需要明确可观察需求与验收边界，不能把猜中隐藏测试当成独立能力定义。

网页明确包含三个 CoT 任务和三个长程案例，属于两套任务，不将其合并为六条独立训练样本或配方采样数。正文引用的 companion trustworthiness 博客只有链接与结论性描述，本轮不把其未读的协议／分数补入本篇。

<a id="eval"></a>
## 8. 评测：静态发布表、交互 JSON 与被测系统分开

### 8.1 主表原值

| Benchmark | SWE-1.7 | Kimi K2.7 Code | GPT-5.5 | Opus 4.8 | Opus 4.7 | GLM-5.2 | Composer 2.5 | SWE-1.6 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| FrontierCode 1.1 Main | 42.3 | 30.1 | 43.0 | 46.5 | 38.5 | 24.5 | 25.6 | 9.4 |
| Terminal-Bench 2.1 | 81.5 | 72.7 | 84.2 | 86.9 | 83.0 | 81.0 | 76.0 | 39.7 |
| SWE-Bench Multilingual | 77.8 | 73.5 | 76.8 | 84.4 | 80.5 | 74.5 | 71.6 | 58.3 |

与基座表值分别相差 **12.2、8.8、4.3 个百分点**。该对照包含重新后训练后的整个系统，不隔离 top-p、data、compaction 或 optimizer。42.3 位于 Opus 4.8 的 46.5 与 GPT-5.5 的 43.0 之下；不能将“frontier-level”写成所有指标第一。[Coding benchmark results；`array-135251.json`]

### 8.2 指标与运行协议

主表小标题写 Pass rate，但交互图明确说明 **FrontierCode Score 是 rubric 的加权汇总，未过 blocker 为零**，并有独立 Pass rate 按钮。`new_score` 与 `correct` 是不同字段。Main=100，Extended=150；Main 去掉 easy tasks。不能把其每个百分比解释为简单 solved task 个数。[导言图说明、DATA]

原文称所有模型使用 maximum reasoning effort；具体值不统一。Terminal-Bench 2.1 使用内部框架，Anthropic 为 Claude Code，OpenAI 为 Codex，其余为 Devin CLI，timeout=4h。SWE-Bench Multilingual 有官方自报时引用，无则在 Devin CLI 评测。FrontierCode 协议指向独立 1.1 博客。没有全部配对的 token budget、重复次数、方差、per-task scores 或同底座同 harness 控制变量。

因此原文长程训练上限六小时、Terminal 测试四小时、产品 1000 TPS 是三个不同口径。SWE-1.6 主表列也没有证明就是 2026-03-01 的 Preview checkpoint。

### 8.3 公开 JSON 实际增加的信息与时间边界

快照 `public_data/data/swe-1-7/data.json` 的 `v1_1` 含 8 个模型族、两种 subset、多个 effort。它还含 **Claude Fable 5**，而发布静态表和已捕获初始柱图没有这个模型。不能用后来维护的公开数据替换原始静态主表，再宣称是 7 月发布时的完整榜单。本轮不执行网页脚本，不推定每个未捕获 hover 状态。

下面只选与主表对应的 model/effort，将图表数据字段原样换为百分数展示；**这是公开展示数据，不是全量评测日志**：

| 模型／公开键 effort | Main `new_score` (%) | Main `correct` (%) | 平均 cost ($/rollout) | JSON harness |
| --- | ---: | ---: | ---: | --- |
| SWE-1.7 / none | 42.33 | 47.80 | 1.9734 | devin |
| Kimi K2.7 / none | 30.06 | 33.60 | 3.0057 | mini-swe-agent |
| GPT-5.5 / xhigh | 42.96 | 48.24 | 4.0348 | codex |
| Claude Opus 4.8 / max | 46.50 | 51.65 | 9.6225 | claude-code |
| Claude Opus 4.7 / max | 38.54 | 42.83 | 9.0876 | claude-code |
| GLM 5.2 / none | 24.50 | 27.40 | 2.4704 | mini-swe-agent |
| Composer 2.5 / none | 25.64 | 29.34 | 3.0875 | cursor-cli |

`none` 是数据键，不等于证明模型未推理；JSON 的 FrontierCode harness 也不能被 Terminal 的默认说明覆盖。token、duration、tool_calls、steps 等多项为 null，不能还原成本结构。图轴写 mean USD spend，不是训练 GPU-hour，也没有从该 JSON 得到公开报价在所有请求上的精确费用计算方法。

## 9. 成本、开放资产与复现程度

可访问的是网页、静态 SVG、脚本中的展示数组、公开图表 JSON；它们没有变成开放训练任务、权重、optimizer states 或 production runner。也没有本篇的可复现实验脚本。后续读取 Dynamo/Fireworks/其他框架公开代码可以提供比较，但不能冒充 Cognition 的实际私有实现。

| 量 | 原文给出的数字 | 正确分母／限制 |
| --- | --- | --- |
| 产品推理 | 1000 TPS | Cerebras serving；非每 GPU rollout 吞吐 |
| 多集群覆盖 | 4 DC / 3 大陆 | 布局，不是 GPU 数 |
| delta 大小 | 减少 >99% | 相对 full-weight transfer；非训练总成本 |
| 跨洲权重更新 | 1–2 min | 1T 参数例子的 end-to-end 更新 |
| 推理暂停 | 3–4 s | 应用暂存 delta 的关键暂停 |
| 长程 rollout | up to 6 h | 非平均值、非统一所有任务预算 |
| Terminal 评测 | timeout 4 h | 评测而非训练 |

环境生产、人工 QA、teacher/API、训练 GPU-hours、失败作业、checkpoint 复制、上下文压缩和系统恢复的完整费用未披露。无需再泛搜二手猜测填满这些字段。

<a id="project"></a>
## 10. 与 1.5/1.6 的演进，以及 RepoHarness 的条件化借鉴

### 10.1 三代材料真正证明了哪种演进

| 轴 | SWE-1.5（2025-10） | SWE-1.6 Preview（2026-03） | SWE-1.7（2026-07） |
| --- | --- | --- | --- |
| 模型关系 | 未命名强开放基座 | 与1.5同 pre-trained base；未证实直接续接1.5权重 | 明确 K2.7/K2.7 Code，新基座比较 |
| harness | Cascade，和工具／prompt 一起迭代 | 本系在产品 Cascade 配置评测 | 直接在 Devin 训练；外部 benchmark 各用不同协议 |
| 数据 | 人工高保真任务；tests/rubrics/browser grader；专家 hardening | 扩环境、改善质量；数量未披露 | 双向 verifier QA、低通过率任务、作弊尝试零分 |
| 性能 | Cerebras＋draft；降低工具每步开销 | NVFP4、DP亲和、NVLink；batch归一后step快6× | replay masks、跨洲delta、局部容错与buffer恢复 |
| 长度／行为 | 交互速度优先 | 更会思考，但过度验证、串行工具、人工批准负担 | 自压缩＋交替预算；语言紧凑，探索和修改范围又增大 |

这是一条**工程问题与披露的演进**，不是严格同模型、同数据、同 benchmark 的纵向消融。1.6 改善“不必要测试”、1.7 却承认更多额外测试和 scope，并非必然矛盾：底座、任务和行为定义均已变化。SWE-2 后续称进一步聚焦探索，也不证明1.7当时的全部策略错误。

### 10.2 给 A / B 的有限候选

映射基线为 miles + SGLang + 外部 coding harness / rh2，资源约8×96GB，目标30B-A3B。这是设计层映射；本轮没有重新审计 rh2 全部实现，不虚构新模块已可用。

| 候选 | 实际要解决的问题 | 最小检查／边界 |
| --- | --- | --- |
| A：实际采样分布重建 | top-p kept-set、温度、路由与训练 logprob 不一致 | 固定 token/权重，比较全词表与原 kept-set 概率；检查 singleton 局部梯度及 masks 的传输，不先发明新算法 |
| A：session/权重/KV 版本分开记录 | 长轨迹跨版本与重路由的数值差异 | 小型暂停／恢复 replay，比 token、logprob、缓存重算与成本；本篇不是直接保留旧KV的批准 |
| A：分开同步总时长与停顿 | 错把网络运输当训练关键路径 | 分阶段计时；八卡单节点通常不应复制全球对象存储方案 |
| A/B：恢复后消费分布 | 停机／陈旧样本排除是否偏向某类任务 | 固定任务身份与预算分桶，检查重试、丢弃和有效组；不能只报恢复秒数 |
| B：合法替代解与可观察需求 | 假阳性／假阴性、hidden contract 与scope冲突 | 用原始行为、gold/no-op和代表性替代解核验；不奖励无边界扩展 |
| A/B：语言、执行和成本分开 | 压缩CoT不等于少token；更多tool不等于有效验证 | 同时记录成功、token、tool time、无效重复、修改范围；只在实际画像后考虑交替预算或压缩训练 |

核心价值在于使系统和模型行为的因果链可检查，不是新增六个组件。上游已有能力准确归因；需要我方实测才可形成简历中的性能或训练成果。

## 11. 尚未回答的问题

最影响复用的缺项为：完整训练数据与split、成功及成本reward、逻辑轨迹/段/group定义、top-p阈值与mask序列化、baseline和loss分母、长程信用分配、缓存跨版本概率语义、恢复buffer采样规则、各机制独立消融和总费用。正文相关章节均已检查，不能把“未披露”误标为“附件无法解压”。

当前附件足够完成本篇已公开内容的阅读；缺的是作者没有提供的实验细节。companion trustworthiness、18项参考文献全文及私有训练实现不属于本轮完整阅读范围。官网当前页面可能继续维护，固定快照与公开JSON不一定同发布时间。

## 12. 快速定位、引用身份和检查状态

公式／采样 → §3；权重与故障 → §4；自压缩／预算 → §5；环境 → §6；六组展开 → §7；表格／价格／协议 → §8–9；版本演进 → §10。

参考文献按原顺序登记而不冒称全文阅读：1–2 FrontierCode及1.1；3 PipelineRL；4 训推差异专题；5 SWE-grep；6 R3；7 SWE-1.6；8 nucleus sampling；9 Entropy Mechanism；10 DAPO；11 DeepSeek-V3.2；12 Muon及scalable Muon；13 Fireworks权重传输；14 DeepSeek-R1；15 Kevin-32B；16 Kimi K2.5；17 Terminal-Bench；18 SWE-smith与SWE-bench Multilingual入口。参考[18]的环境论文与benchmark网站是相关而不同的来源，不能只凭前者代替全部评测协议。

**状态：全文、现有图表与展开案例阅读、作者自查完成；没有独立 reviewer，也没有训练／故障复现。** 局部公式的 NumPy 检查、样例计数和图文差异见 [检查记录](reviews/cognition_swe1_5_1_7_self_check_20260914.md)。没有给缺席审查者编造线程ID；不改共享索引或源包。

[WEB]: https://cognition.com/blog/swe-1-7
[TEXT]: source_supplements/cognition_20260911/swe-1-7/reading_text.md
[VIS]: source_supplements/cognition_20260911/swe-1-7/VISUAL_INDEX.md
[EM]: source_supplements/cognition_20260911/swe-1-7/embedded/manifest.json
[COT]: source_supplements/cognition_20260911/swe-1-7/embedded/array-139353.json
[TRACE]: source_supplements/cognition_20260911/swe-1-7/embedded/array-151019.json
[DATA]: source_supplements/cognition_20260911/public_data/data/swe-1-7/data.json
