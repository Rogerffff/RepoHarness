# CodeMidas：从已有实现构造可执行 Coding RL 任务

CodeMidas 的核心不是新的 RL loss，而是以源代码为任务特定输入，将已有功能转换为“行为规格＋待实现仓库＋隐藏执行验证器”，再做执行与求解轨迹筛选。作者用最终 5,545 题训练 MiMo-V2.5，报告五类外部评测均有提升；较小的清洗任务池也优于较大的未清洗池。最值得本项目借鉴的是：**原始实现用于产生可观察行为证据，但不应把偶然实现细节变成唯一正确答案；环境稳定性、自然候选的评分一致性和模型相关难度是不同检查。** 本文分别恢复这些机制、训练配置、消融与行为统计，并标明它们尚不能证明的事项。

**阅读状态（2026-09-23）：正文 §1–6、附录 A/B 的可取得原文文本已逐节读完，Table 1–3/A1 已按解析文本核对，作者自查已完成；PDF 原件及九幅图的实际图像未取得，完整参考文献条目未取得，故尚未达到本库“全文＋原图目视核验”的完整交付标准。不是仅摘要预读，也不是独立审查通过或运行复现。** 仅图中存在的数据不从二手解读补入。续读缺口集中在 §1.3 和 §12。

导航：[来源与覆盖](#source) · [任务与环境生产](#environment) · [训练语义](#training) · [结果与消融](#evaluation) · [行为分析](#behavior) · [复现边界](#limits) · [项目映射](#project)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

### 1.1 主来源及取得方式

正式标题：**CodeMidas: Scaling Agentic Coding RL Environments from Code Itself**。作者为 Bowen Ye、Lei Li、Shicheng Li、Zihao Yue、Linghao Zhang、Hanglong Lv、Yuanxin Liu、Wenhan Ma、Hao Tian、Rang Li、Jinhao Dong、Yikai Zhao、Xiangwei Deng、Hailin Zhang、Liang Zhao、Qi Liu、Lingpeng Kong、Tong Yang、Fuli Luo。机构为 LLM Core, Xiaomi；Peking University；University of Hong Kong；Renmin University of China。原文标记 Tong Yang、Fuli Luo 为通讯作者，并注明部分工作在小米实习期间完成。[P，标题与作者区]

arXiv 编号 **2609.22068**，目标版本 **v1**；学术索引给出的首次提交时间为 **2026-09-18 17:55:17 UTC**。检索／阅读日期为 2026-09-23。没有取得完整 submission-history 页面和 PDF 水印，故不声称已独立证明“至今只有 v1”。

一手入口：[论文页][P]、[指定 v1 HTML][P-html]、[指定 v1 PDF][P-pdf]。本轮普通 URL 访问多次返回 cache miss；通过关联该 arXiv 条目的学术检索结果展开，取得了原文 §1–6、Table 1–3、Fig.1–9 图注、附录 A 的 Table A1 及附录 B 全部定义。实际依据是这份**关联 arXiv 原文的解析文本**，不是搜索摘要、MiMo-V2.6 笔记或第三方综述。文本中的参考文献引用 key 未全部展开，References 仅出现标题。

正文证据用 `[P，§x / Table / Figure caption / Appendix]` 标注。因为没有取得 PDF，不虚构物理页码、总页数或完整图页覆盖。本文保存原创阅读笔记，不上传第三方论文全文、图像或模型文件。

### 1.2 与仓库、MiMo-V2.6 的关系

项目映射固定到 `Rogerffff/RepoHarness@0554dafd633cd982288bd60a54f75da65e5c54d4`，即 `codex/project-status-20260923` 同步快照。本稿写入独立分支 **`pro/codemidas-reading-20260923`**；不改训练实现、题目、reward 或共享索引，不合并其他阅读线程的分支。

使用 [NOTE_TEMPLATE.md](NOTE_TEMPLATE.md) 的覆盖与证据规则。项目事实来自 [9月23日同步入口][project-sync] 和 [AGENTS.md][project-agents]；本轮不重复审计全部 A/B 源码及运行账本。

新增 [MiMo-V2.6 笔记][mimo-note] 位于另一固定提交 `aa423327b76c541e744f2f0fb7ad3c9ceea8d32d`。本轮只读取其来源与阶段总览作为关系校对，**不以其 44 页报告里的 GRS/GAR、mini-harness、MOPD2、优化器或硬件补写 CodeMidas 的未披露项**。CodeMidas 本文训练对象是 MiMo-V2.5，而不是 V2.6 或开放的 9B SFT 模型。

### 1.3 覆盖表：哪些已经读完，哪些明确没有

| 原文单元 | 实际阅读与处理 | 笔记位置／剩余缺口 |
| --- | --- | --- |
| 标题、作者、摘要 | 取得并读完 | §1–2 |
| §1 Introduction | 逐段读完 | §2、§7–9 |
| §2.1 Building coding RL environments；Table 1 | 正文和整张表的解析文本已读；表格原图未核 | §2.2 |
| §2.2 Rewards and verification for coding agents | 逐段读完 | §2.3；引用工作不逐篇扩读 |
| §3.1 Task Design and Codebase Adaptation | 逐段读完 | §3 |
| §3.2 Execution-grounded Test Construction | 逐段读完 | §3.3 |
| §3.3 Environment Preparation | 逐段读完 | §4.1–4.2 |
| §3.4 Post-rollout Environment Filtering | 三项过滤逐段读完 | §4.3–4.5 |
| §3.5 Dataset Overview | 正文及 Fig.2–4 图注已读 | §5；完整图中标签、分布尚未核 |
| §4.1 Experimental Setup | 正文读完并与 A1 对照 | §6–7 |
| §4.2 Results；Fig.5–6 | 正文、图注已读 | §7；Fig.5 两项只在图中的分数、Fig.6 完整 token 曲线待核 |
| §5.1 Task Scale and Quality；Fig.7–8 | 正文、图注已读 | §8；不据文字重画全曲线或填全图值 |
| §5.2 Behavioral Changes and Generalization；Table 2–3 | 全部正文与表格解析文本已读 | §9；Fig.9 案例图像未核 |
| §6 Conclusion | 读完 | §10–11 的证据判断 |
| References | 仅取得标题与正文引用 key | 未取得完整条目，不能标参考文献全文读完 |
| Appendix A Training and Evaluation Configuration；Table A1 | 全部可见行已读 | §6；表格物理页目视待核 |
| Appendix B Behavioral Metric Definitions | 三个定义全部读完 | §9.1 |
| Fig.1–9 | 九个图注均已读；九幅原图均未取得 | §12 列逐图续读清单；不称目视完成 |

<a id="environment"></a>
## 2. 核心命题与相关工作的准确位置

### 2.1 “只用代码”指任务特定输入，不是整个流水线没有其他依赖

作者针对的限制是：issue、PR、commit、已有测试或文档只覆盖项目中部分已实现功能。CodeMidas 从已经工作的功能出发，产生要实现什么的说明、保留真实依赖的开发起点和独立可执行验证器，扩展任务来源。[P，§1]

“source code as its only task-specific input”不等于不需要预训练 agent、通用提示词、包依赖、容器基础镜像或环境计算；也不表示源代码中的功能一定符合外部用户真实需求。原始实现同时提供功能候选和参考解，测试仍需要对规格与可观察行为进行审查。[P，§1、§3]

本文没有开展基座预训练，也没有给出从预训练、SFT、RL 到蒸馏的一整条模型开发线。可确认的专项关系为：

```text
已有源代码 → agent 构造规格、开发起点与测试 → 执行／求解筛选 → 冻结训练任务池
已有 MiMo-V2.5 → 在该池上进行 GRPO → RL checkpoints → 内部验证与五个外部评测
```

不能将“本篇未增加 SFT 阶段”改写成“输入模型从未经过 SFT”；也没有证据表明 CodeMidas 的出题 agent 通过自博弈共同更新权重。

### 2.2 Table 1 是任务来源要求比较，不是质量或成本排名

为避免把表中符号误读，以下将原表的否定式列标题换成正向中文：

| 方法 | 需要 issue | 需要 PR | 需要 commit | 需要已有 tests | 需要预先写好的说明 | 表中语言数 |
| --- | --- | --- | --- | --- | --- | ---: |
| SWE-rebench V2 | 部分步骤需要 | 是 | 是 | 是 | 否 | 20 |
| daVinci-Env | 是 | 是 | 是 | 是 | 否 | 1 |
| R2E-Gym | 否 | 否 | 是 | 部分步骤需要 | 否 | 1 |
| SWE-smith | 否 | 部分步骤需要 | 部分步骤需要 | 是 | 否 | 1 |
| SWE-Flow | 否 | 否 | 否 | 是 | 否 | 1 |
| SWE-Hub | 否 | 否 | 否 | 是 | 部分步骤需要 | 11 |
| R2E | 否 | 否 | 否 | 否 | 是 | 1 |
| MindForge | 否 | 否 | 否 | 否 | 是 | 15 |
| CodeMidas | 否 | 否 | 否 | 否 | 否 | 23 |

这是作者在 Table 1 的归纳，本文没有重审所有被比较代码库。语言数不等于任务难度、环境有效率或多语言泛化优劣；“不要求已有测试”也不表示最终评分不需要测试。原文还分别解释了 issue/commit 路线、已有测试驱动变异路线和文档驱动规格路线。[P，§2.1、Table 1]

### 2.3 学习型审查 agent 与 RL reward model 是不同角色

§2.2 将 learned critic、patch similarity、过程 reward、rubric 与执行测试区分。CodeMidas 的训练奖励来自生成测试的**二元执行结果**，没有另外训练一个 reward model 或 learned verifier。§3 中确实使用 agent 审查环境与候选，但这些模型用于任务生产／筛选，不意味着它们的自然语言判断直接成为训练时的逐轨迹奖励。[P，§2.2、§3.4、A1]

## 3. 任务设计、代码改造与行为规格

### 3.1 先识别外部可调用行为，再划定移除范围

构造 agent 检查仓库结构及 build metadata，寻找有公开入口、结果可观察的已有功能。作者优先选择需要跨代码理解的任务，支持三类接口：CLI、纯库函数、有状态 API。其结果分别通过进程输出、函数返回值、跨调用状态变化观察。[P，§3.1]

agent 沿公开入口和共享依赖确定范围，移除核心实现，调整剩余代码使之成为连贯开发起点；题面与代码边界共同修订，并保留共享模块和项目上下文。原实现独立保留为 reference solution，而不是交给 solver 作为答案。[P，§3.1]

这不是从 issue 中猜测应改哪些文件，也不是随机注入一个故障；起点是已知实现的功能。不过原文没有给删除大小／函数选择算法、精确提示词或候选去重实现，不能据此复刻一个完全相同的生成器。

### 3.2 题面约束公开行为，不把内部实现当评分规范

题面说明输入、可观察行为与必须满足的公开接口。solver 可以选择自己的内部 helper 和算法。对“可观察”与“公开接口”的强调，是原文关于接受合法替代解的核心，而不是要求与 reference diff 相似。[P，§1、§3.1]

**读者判断：**原代码中存在某种异常措辞、对象遍历顺序或私有 helper，不足以独立证明题目必须要求它。反过来，题面明确约定的行为也不能为了容纳某个候选而删除。原文的做法是审查规格—断言对应关系，不是普遍放宽测试。

### 3.3 执行驱动的测试构建

对每项规格，构造 agent 选择输入和边界情况，在 reference copy 上运行公开入口并记录结果。CLI 测试运行命令，纯函数使用输入输出案例，有状态 API 使用调用序列；涉及顺序、清理等要求时检查跨调用依赖。**每个 test 记录它所覆盖的具体要求。**[P，§3.2]

规格固定了某个输出时，reference execution 提供期望值；规格没固定的部分只检查已经声明的约束。例如要求异常类型，但不钉死未声明的消息文字。不同输入应能产生有区分力的输出，不能只测一个常数返回也能满足的案例。[P，§3.2]

接着逐断言审查过度限制：精确措辞、偶然顺序、内部结构。能替换成行为检查则替换；依赖私有符号且找不到行为替代的任务被拒绝。修订后重新在 reference 上执行；最后固定输入与断言用于正式评分。[P，§3.2]

注意这里审查的是**生成的任务规格与测试**，不意味着可以不看真实 API 合约、版本文档和用户要求，就把现有 SWE 任务中的某条断言删掉。CodeMidas 自己构造题面，和维护外部真实 issue 数据的责任不同。

## 4. 环境准备与三项 post-rollout 筛选

### 4.1 环境里的答案清理与开发支持须同时保留

从统一 base container 出发，agent 按项目声明安装依赖并准备 build/runtime 资源。清理可能暴露被删实现的编译产物、cache、构造 agent 遗留文件；**与目标功能相关的原始测试也移除**。原文不是说删除全部仓库测试。必要包、fixtures、build wrappers 留下，使 solver 能构建和运行新实现。[P，§3.3]

solver 收到题面与改造后代码库及依赖，解题期间 verifier 在其环境之外，只在评分时注入并给二元结果。[P，§3 开头]

这一文字支持“解题期隐藏评分材料”，**不直接支持 fresh grader、不同 UID、网络隔离或对恶意持久进程的完整控制**；评分究竟在原容器、重置容器还是独立新容器内执行，未在取得文本中讲清。不能把 MiMo 的另一个实现或 RH2 的评分路径填到这里。

### 4.2 六个 fresh container 的执行一致性检查

每题按训练 runtime 条件启动六个新容器：两个保留待实现起点，四个放入 reference。前两个必须失败，后四个必须全部通过，检查预期的 fail-to-pass 转换并筛掉不稳定执行。[P，§3.3]

这是有限次数检查，而不是数学上证明没有 flakiness；“起点失败”也未逐层说明如何排除 setup/parser 异常。本项目需要自己的错误归因，不能把测试未运行与目标断言失败混为一类。

执行检查也没有覆盖全部替代实现。作者因此继续使用自然求解轨迹审查；不能把六次运行视为完整任务质量认证。

### 4.3 Leakage filtering：攻击尝试后还要检查证据

adversarial agent 在完整 solver-visible 环境里寻找残余实现，包括编译输出、cache、构造文件，以及已安装的被测项目副本，记录命令和输出。随后独立 review 对照 reference 与 verifier 检查利用证据；确认可以绕过目标开发工作才拒绝该任务。[P，§3.4]

这里的泄漏主要是**运行时答案通道**。它不等于预训练污染检测，也不意味着作者有权读取所有开源项目的历史训练来源。被拒绝的是任务，不是描述了一套每次 rollout 都自动清理攻击痕迹的生产安全机制。

### 4.4 Agreement on agent solutions：每题四次自然求解

coding agent 每题做四次求解。reviewer 可见题面、verifier、reference、候选代码、执行输出及轨迹，评估候选是否满足题面，并核对测试判定。如果 reviewer 认为错误实现通过，或认为正确实现被拒，则记录 false positive / false negative；识别出 verifier defect 的任务被拒绝。[P，§3.4]

重要限制：这些“正确／错误”在本篇是 agent 审查决定，未给 reviewer 身份、人工校准、盲审或与独立专家的一致性数据。reviewer 又看得到 reference，存在偏好参考实现的可能性；这是待验证风险，不是本文已证明发生的错误。

§3.2 的断言改写与此处的后置审查拒绝不是同一动作。**原文没有描述对所有被拒任务继续自动修题并循环重试的完整闭环。** 因此不能把 CodeMidas 归纳成“边训练、边修 grader”的在线系统。

### 4.5 Rollout outcome filtering：另一轮筛选，不是上一轮“四次”的别名

另一个 frontier model 对每题进行若干尝试，verifier 评分；只保留既有成功又有失败的任务。文本没有给这一步的精确尝试次数或模型名，不能沿用上一节的四次，也不能直接假定用 MiMo-V2.5 或计划训练的 Qwen。[P，§3.4]

原文主动指出：全对／全错可能是难度，也可能是弱测试、题面缺要求等残留缺陷，单看结果分布无法识别原因。这一步服务于**该筛选模型及预算下的训练适用性**，不是逻辑上认定全错题坏、全对题无价值。[P，§3.4]

筛选发生在正式 RL 之前；本文没有报告按持续更新的 learner 重新估计难度和实时生成题目的 curriculum。

## 5. 数据资产、漏斗与覆盖

| 对象／步骤 | 能确认的数量与单位 | 尚未确认 |
| --- | --- | --- |
| 原始可选代码库 | 未在可读正文给出 | 采样母体、时间、许可证、去重规则 |
| 设计、测试构造、中间过滤节点 | Fig.1 图注说明存在 retained-task pyramid | 原图未取回，全部中间数量与阶段对应暂空缺；不采用二手抄录 |
| 一致性检查 | 每题 2 个起点＋4 个 reference fresh containers | 覆盖候选总数、平均重试、完整运行成本 |
| 自然候选审查 | 每题四次 coding-agent 求解 | 模型、预算、人工审计与判定误差 |
| outcome 筛选 | frontier model 若干次尝试 | 次数、模型、预算、是否与上一轮复用轨迹 |
| 最终训练集 | **5,545 tasks / 3,185 codebases / 23 languages / 15 domains** | 公开 task manifest、镜像与参考补丁下载情况 |
| 内部验证集 | **200 tasks，每题 3 次评测**，与 5,545 题分开 | 仓库级／代码级切分和抽样 seed |
| 规模消融 | 随机 1k、3k、完整 5,545；另有约 8k 未清洗样本 | 子集是否嵌套、完整抽样规则与跨 seed 重复 |

[P，§3.3–3.5、§4.1、§5.1、Fig.1 caption、A1]

语言标签继承仓库主语言；正文给 Python 21.4%、TypeScript 18.3%、Go 16.2%、C++ 12.5%、JavaScript 11.3%。Fig.2 图注给出前十种语言覆盖 **5,445/5,545（98.2%）**。不能仅据覆盖 23 种语言，就认为任务分布均衡，或每道题只含其标签语言。[P，§3.5、Fig.2 caption]

领域标签也来自代码库：systems software 17.4%、web 14.6%、developer tools 13.6%，作者报告前三合计45.6%；Fig.3 另外标注18个未标注任务属于 Other（0.32%）。图中使用半径与占比平方根成比例的显示方式，不能把未见图的条长当线性占比。[P，§3.5、Fig.3 caption]

reference patch 的规模按**增加或删除的全部 source lines**计数，包含注释和空行；中位142行，IQR 66–305行，65.9%的任务涉及至少两个源文件。Fig.4 采用分段 log 横轴，1–10 区间缩为后续 decade 的五分之一宽。[P，§3.5、Fig.4 caption]

这些是任务范围的代理描述，不是人时难度、最优补丁长度或相对 SWE-bench 更困难的直接测量。原实现复杂也不排除存在更短的正确实现。

<a id="training"></a>
## 6. 实际训练语义：恢复已披露配置，不补一份通用 GRPO 教科书

### 6.1 Appendix A 的完整配置

| 字段 | 原文数值／含义 |
| --- | --- |
| 初始策略 | MiMo-V2.5 |
| 完整训练池 | 5,545 CodeMidas 任务 |
| 算法 | GRPO |
| reward | 二元 verifier 结果，0 或 1 |
| 按标准差归一化 advantage | **关闭** |
| batch size | 32 |
| 每题 rollouts | 32 |
| maximum prompt length | 8,192 tokens |
| maximum response length | **516,096 tokens** |
| maximum turns per rollout | 500 |
| maximum staleness | 8 |
| optimizer | **Adam** |
| learning rate | 5 × 10^-6 |
| warmup steps | 0 |
| Adam β1 / β2 | **0.95 / 0.95** |
| Adam ε | **10^-15** |
| gradient clipping threshold | 1 |
| weight decay | 0 |
| CodeMidas Val | 200 题；每题 3 次尝试 |

[P，§4.1、Appendix A / Table A1；数值按解析文本记录，PDF 原表目视仍待核]

这里的 response 上限很大、Adam 参数也并非常见默认值；本稿忠实保留，不擅改成 512K、不改用 AdamW/Muon、不替作者调整 ε。最大 prompt 加最大 response 在算术上为524,288，但**这不是证明模型单次真实上下文窗口、有效轨迹长度或样本打包规则**。文本没有把 observation、thinking、工具调用串及压缩后片段各自的长度口径展开。

同样，32×32 在名义配置下对应每批1,024条 rollout；不能由此推断 trainer 永远消费1,024行或完全不丢弃样本，更不能用配置上限算实际 GPU-hour。

### 6.2 论文给的是方法名与若干配置，不是完整 loss 公式

可确认：使用执行 reward，GRPO，关闭 advantage 的标准差归一化。**没有取得明确的 GRPO 目标函数、baseline 定义、likelihood ratio、clip 参数、KL／entropy 系数或 loss 分母。** 不把减组均值、leave-one-out、token mean、sequence mean 等任何一种默认值当成已披露事实。[P，§2.2、§4.1、A1]

同一原因，不能将本项目的 faithful DIS、SAO、MiMo-V2.6 的 GAR/GRS 公式或某个框架代码拼进此篇。原文也没有说明 teacher/student logit 蒸馏、learned critic 或过程 reward；离线任务审查并不构成这些训练机制。

### 6.3 staleness=8 不能展开成未经披露的完全异步实现

A1 明确给最大 staleness=8，但没有定义单位是 optimizer step、模型版本还是其他量，没有解释记录／检查点、逐 token／逐段关系或部分轨迹恢复规则。可以说作者限制了陈旧度，不能据此宣称采用 miles、slime、某个队列算法、同步间隔或断点语义。[P，A1]

原文也没有给 GPU 型号数量、训练/推理分卡、TP/EP/CP、权重同步、MoE routing、精度、trainer backend、batch packing、harness 名称或准确版本。代码中出现 Read/Search/Write/Edit 只是动作类型，不足以确定 Claude Code 或 mimoagent。

### 6.4 终止、错误与可学习性的缺口

文本没有给预算截断、工具错误、transport failure、环境崩溃、parser 失败如何影响 reward、组统计和梯度，也没有说明训练中是否再次过滤全零／全一组。任务筛选阶段的 outcome filtering 不能自动视为 learner 的动态过滤代码。

本项目应从自己的执行合同出发，不将二元评分中的0分一律解释成基础设施健康的正常失败；反过来，也不能因为轨迹无效，就认为该题永远不可用。

<a id="evaluation"></a>
## 7. 评测范围、指标与主要结果

### 7.1 固定评测设置的意义与不足

作者称初始策略与各 RL checkpoint 使用相同评测设置，并采用五项评测的官方任务集：SWE-bench Pro、DeepSWE v1.1、ProgramBench、RepoZero C2Rust、Terminal-Bench v2.1。CodeMidas Val 是另取的200题，每题3次评测。[P，§4.1]

作者检查训练任务集合与内部 Val、五个外部任务集互不重叠。这支持**任务集合级 disjoint**，不自动证明无共同仓库、代码克隆、预训练污染或公开答案渠道。构建源代码和 reference 本来可能公开；原文没有提供更强去污染的审计过程。

ProgramBench 指标为 **Almost Solved：至少通过95%测试的任务占比**。其余报告 pass rate。原文没有把所有评测正式定义为 pass@1、best-of-k 或 avg@k；尤其不能因为 Val 每题做3次，就称为 pass@3。[P，§4.1、A1]

### 7.2 结果表：只填当前原文文本给出的值

| 评测 | 初始 MiMo-V2.5 | CodeMidas RL | 本文算术差值 | 原始证据／限制 |
| --- | ---: | ---: | ---: | --- |
| SWE-bench Pro | 待原图 | 待原图 | 待原图 | §4.2称提升；Fig.5 数字未取回 |
| DeepSWE v1.1 | 10.0 | 21.7 | +11.7 pp | §1、§4.2明确给值 |
| ProgramBench / Almost Solved | 4.5 | 21.5 | +17.0 pp | 非严格全部测试通过率 |
| RepoZero C2Rust | 待原图 | 待原图 | 待原图 | §4.2称提升；Fig.5 数字未取回 |
| Terminal-Bench v2.1 | 63.7 | 72.2 | +8.5 pp | §4.2明确给值 |
| CodeMidas Val | 35.0 | 44.7 | +9.7 pp | §4.2；规模分析用44.73的更细精度 |

[P，§1、§4.1–4.2、Fig.5–6 caption]

摘要里的“+11.7%”在正文已明确为**百分点差值**，不是相对提高11.7%。所有数字是作者报告，不是本项目复测。没有取得完整的外部任务数、sampling 参数、turn/token/wall-clock 预算、harness 配置、seed 或每项重复次数；A1虽标题为训练与评测配置，也没有补足这些行。

### 7.3 内部学习曲线伴随更长交互

Val 在step40之后的观测 checkpoint 大致维持高于初始8–10个百分点；平均总 token 长度增加，作者解释为更多使用可用交互预算。Fig.6 使用通过率与千 token 单位的双轴。[P，§4.2、Fig.6 caption]

这是固定名义评测条件下的观察，不是等实际 token 消耗的成本比较。更长交互可能提供更多有效检查，也可能增加费用；论文没有通过删去／强制某种行为隔离因果贡献。完整长度曲线只存在图中，本稿不报目视未见的具体起终点。

## 8. 任务规模与质量消融：结论有效，但不是每个过滤器都有独立收益证据

### 8.1 四个任务池究竟怎么不同

| 设置 | 构造方式 | 与完整池共享什么 | 关键差异 |
| --- | --- | --- | --- |
| 高质量1k | 最终池随机子集 | 相同训练配置与观测checkpoint范围 | 题目数量与重复利用程度变化 |
| 高质量3k | 最终池随机子集 | 同上 | 不知道是否与1k严格嵌套 |
| 高质量5k | 完整5,545题；图中简称5k | 同上 | 最终全池 |
| vanilla约8k | 过滤前抽样，仍有题面、开发环境和verifier | 同上 | **不做环境cleaning、一致性检查和三项post-rollout过滤** |

[P，§5.1]

这里的 vanilla 不是只少了某个难度筛选器，而是整组处理共同移除。因而结果支持清理、执行验证、审查和训练适用性选择的**合并价值**，不能分摊成“六容器检查值多少分”“反作弊贡献多少分”或“MILP curriculum 有效”；本文没有后者。

### 8.2 原文报告的规模结果

Fig.7 每五步记录一次、范围step0–70、不平滑。正文记录：1k 在step30达到41.30；3k 在step65达到43.22；完整池从step40到70的每个已评测checkpoint均领先，到step70为44.73。[P，§5.1、Fig.7 caption]

| 高质量池 | DeepSWE | CodeMidas Val |
| --- | ---: | ---: |
| 1k | 17.57 | 41.30 |
| 3k | 19.05 | 43.22 |
| 5k（5,545） | 21.70 | 44.73 |

完整池相对 vanilla8k 的优势在 SWE-bench Pro、DeepSWE、Val 分别为 **0.59、4.59、4.49 pp**；3k 也在三项评测上超过 vanilla8k。[P，§5.1]

不把上述 Val 汇总值全部解释为同一步结果：正文已经给1k/3k对应的不同step，Fig.8的checkpoint选择政策还需要结合原图及后续资产核查。也不由“相同训练配置”推出相同实际GPU时间、token数、成功执行数和环境生产成本。

### 8.3 适合提炼的结论与不能提炼的结论

**原文支持：**这套筛选后的数据，增加任务规模在作者设置下带来更好的结果；较少的处理后任务可以优于较多未处理任务。

**不支持直接泛化为：**所有更难任务更好、原始失败数据都应删除、动态课程必要、前沿模型筛出的混合任务一定适合30B学生、任何cleaning组合都值得其总费用。缺少多随机种子、生成／筛选token成本、等规模清洗开关和逐过滤器控制实验，限制了组件归因。

<a id="behavior"></a>
## 9. 行为分析：完整恢复指标，保留相关性与测量口径

### 9.1 Appendix B 的三个定义

**Codebase exploration。** 首次代码库编辑前的不同 read/search 请求数。同文件且同行范围的读取、同query/scope/options的搜索去重；专用工具与等价shell请求也算重复。[P，Appendix B]

**Code drafting。** 对每个 Write/Edit payload，以4个字符为stride抽取不同的16字符片段，检查该片段是否出现在此次写操作之前的任意reasoning中。分子、分母分别跨写操作汇总，得到比值。单位是**字符片段，不是token，也不是AST语义相似度**。[P，Appendix B]

**Self-verification。** 最后一次代码库编辑之后执行的不同验证命令数，包含项目测试、内联检查、临时测试程序和本地运行；重复命令只计一次。[P，Appendix B]

原文没有给shell等价识别器、验证命令分类器、文本清洗与所有undefined条件的实现。没发生编辑或没有相应payload时的缺失值不能擅自填0。代码草稿比值只测字面重合，不证明模型形成了正确规划。

### 9.2 训练早期到后期的变化

| 行为 | Early | Late | 原表Change |
| --- | ---: | ---: | ---: |
| 首次编辑前读取／搜索 | 27.2 | 40.1 | +12.9 |
| drafting ratio | 0.358 | 0.629 | +0.271 |
| 最终编辑后不同验证命令 | 2.03 | 2.53 | +0.50 |

Table 2 的均值只使用各指标有定义的rollout，变化基于未舍入均值。正文有0.36/0.63的摘要表达，并不与三位小数冲突。训练Early/Late具体窗口在取得文本中未充分定义，不能套用Table 3的“前后三个checkpoint”。[P，§5.2、Table 2]

Fig.9 提供一个 .secret.csv／flag 行为的示例，展示阅读、草稿、编辑和检查。当前只读到图注，没有取得代码与reasoning原图，不从二手截图或图注重构该完整case。[P，Fig.9 caption]

### 9.3 与成功相关的分析及不显著结果

作者在 CodeMidas Val 的相同任务、相同checkpoint内比较：有agent自己编写并执行检查的rollout，相比没有此行为的rollout，通过率平均高 **4.2 pp，95% CI [1.8, 6.6]**。

以各checkpoint中位数分组，排除无定义测量后：探索量差异为 **+0.7 pp，CI [-1.9, 3.7]**；drafting差异为 **+1.95 pp，CI [-0.04, 3.96]**。置信区间通过整题重采样，同一题所有已观察checkpoint一起保留。[P，§5.2]

必须保留后两项区间含零的事实，而不是只写三个行为都增加、所以三个都显著提高成功率。前一个有正相关也不证明强制多写测试能导致同等增益；同题同checkpoint控制降低了部分混杂，但没有随机分配行为。

**读者推断：**统计窗口依赖“第一次／最后一次编辑”，任务完成方式本身会影响测量；能力更强、进展更顺利或愿意分配更多时间的轨迹也可能更常自测。这些是因果解释的限制，不是原文已经量化的偏差。不要把这些指标直接做成训练奖励。

### 9.4 外部行为迁移与交互长度的方向并不一致

Table 3 比较每个benchmark**最先与最后三个已观察checkpoint的均值**，不是简单的未训练模型与最终模型。行为指标各用有定义的子集，assistant turns使用全部已评分rollout；各checkpoint子集可以不同。[P，§5.2、Table 3]

| 评测 | 探索read/search | drafting ratio | 不同验证命令 | assistant turns |
| --- | --- | --- | --- | --- |
| SWE-bench Pro | 23.1 → 35.5 | 0.304 → 0.653 | 0.80 → 0.96 | 37.3 → 50.1 |
| ProgramBench | 55.7 → 83.6 | 0.106 → 0.361 | 0.93 → 0.99 | 155.1 → 122.8 |
| Terminal-Bench v2.1 | 11.9 → 16.8 | N/A | 2.01 → 2.61 | 59.2 → 69.5 |

程序构建上的探索增多伴随总交互减少，因此不能概括成“RL 只学会输出更长”；另两项又没有支持全局交互成本下降。Terminal drafting 的 N/A 不是0，也不是“没有思考”。各子集变化、行为定义和真实token费用都需要保留。

<a id="limits"></a>
## 10. 开放资产、运行成本与证据分层

### 10.1 本轮真正核到的外部入口

[HF 论文页][HF-paper] 的检索结果显示作者 Lei Li 于2026-09-21提交该论文，并指向 [MiMo RL 项目入口][project-page]。这是可追查的一手发布线索，不是数据集已经全部可下载的证明。项目页本轮没有取到正文。

GitHub 仓库名检索没有返回可明确归属于作者的 CodeMidas 专属仓库；出现的无关近似名称未采用。对 XiaomiMiMo 的定向检索未定位到本篇完整task manifest、Docker镜像、生成prompt、过滤脚本或训练checkpoint。**这只表示本次未确认公开资产，不写成“作者肯定没有公开”。** 不假定 mimoagent、V2.6 开放的coding任务或别的MiMo模型就是CodeMidas全部产物。

关联 MiMo-V2.6 的代码／资产是另一个已安排专题，本篇不越界审查整个mimoagent或verl fork。没有实际下载模型、构建环境、跑verifier或训练。

### 10.2 四类成本都没有足够分母

| 成本 | 能从原文看见的工作 | 尚缺的关键量 |
| --- | --- | --- |
| 任务生产 | 探索代码、规格、改造、测试构造与断言审查 | 各agent型号、token、工具次数、失败重做、API费用 |
| 资格检查 | 六容器执行、攻击与审查、四次求解、另一轮frontier筛选 | 每阶段候选数、成功率、时长、硬件／并发及轨迹复用 |
| RL | 5,545题，32 batch、32 rollouts，长预算与staleness限制 | GPU型号数量、训练步总量、有效token、失效工作和总费用 |
| 评测 | 200题Val每题3次，五外部任务集 | 外部重复、预算、资源、checkpoint选择与总执行成本 |

这些缺失使“代码来源可扩展”不能被量化为“在我们的八卡预算内廉价扩容”。最终题数不等于全流程尝试数；也不能只计算5,545×6当作实际资格检查总成本。

### 10.3 三种未知不得混写

**可读文本没有给：**生成／审查模型、若干采样次数、完整算法和系统协议、精确资源成本等。本稿只说“已取得正文与附录文本未给”，不排除未取到的图像／未来资产另有信息。

**明确只在图中、目前没取得：**Fig.1中间漏斗值、Fig.5两项benchmark数值、部分学习曲线／领域标签／示例。这些不归类成作者未披露。

**需要本项目自己验证：**小模型任务适用性、真实CC与不同预算、RH2评分边界、可复用资产和端到端学习成本。别的论文和模型卡不能补成CodeMidas实验事实。

<a id="project"></a>
## 11. 对 RepoHarness 的条件化意义

### 11.1 当前项目前提

本项目是 miles + SGLang + Claude Code + RH2，A负责训练消费与链路，B负责环境、数据、评测与基座诊断。9月23日同步包记录了已发生的候选覆盖缺口、验收范围争议、同题信号不足，以及诊断预算与正式默认条件的差异；这些事实是项目记录，不是CodeMidas论文结果。[项目同步入口][project-sync]

本稿不批准改题、引入新grader、扩大任务生成器或更换训练算法。当前值得借鉴的是将实际问题拆开，而不是把论文的整条大规模生产线搬进现有系统。

### 11.2 最直接的候选映射

| 候选借鉴 | 原文依据 | 与当前工作的关系 | 小规模辨识方式 |
| --- | --- | --- | --- |
| 每条断言对齐到具体公开要求 | §3.2 | B已有争议题和部分修复；可增加可追溯依据，而非新审批平台 | 对固定候选集分别检查规范、行为、断言；保留原题版本和原始分数 |
| 自然候选审查补足reference对照 | §3.4 agreement | 当前Conan等自然候选比只跑gold更有信息 | 在不同实现路线的候选上比较原grader与补充行为检查；盲化reference偏好并保留人工裁定 |
| 按功能改造稳定仓库生成新题 | §3.1 | 是未来扩容备选，不替代修复当前actor开发条件 | 先在一个已能稳定运行的仓库形成少量功能任务，测有效产出、替代解接受率及成本 |
| 搜索安装副本、编译产物、cache等答案通道 | §3.3–3.4 | 不仅检查仓库目录，和当前日志／可见性问题相邻 | 用solver权限审计可见资产；不从别处抄一份通用删除清单损坏开发依赖 |
| 将环境有效性与模型相关难度分开 | §3.4 outcome | 当前全零格子不能直接当环境坏，也不能证明新目标必要 | 在固定模型/harness/预算下逐题记录结果，先分辨环境故障、题意问题与能力不足 |
| 保留行为分析但不直接塑形reward | §5.2、Appendix B | 有助于比较轨迹变化；不保证这些行为是因果驱动 | 同题同checkpoint分析，并检查额外token成本；先不奖励“更多搜索／更多测试” |

所有实验是本稿的设计建议，未执行，也未被论文证明在本项目上有收益。

### 11.3 这篇新增的证据与没有解决的争论

**新增支持：**代码本身可以成为不依赖历史issue/PR的任务特定来源；在该模型和配置下，清洗与筛选后的任务能够提供外部迁移的RL信号。这使“稳定仓库上的功能任务”成为有实证动机的候选。

**对早期直觉的约束：**“多读多测导致更好”在本文是行为变化和相关性，非因果消融；“所有全对／全错题都坏”与作者文字不符；“既然通过gold/noop就可靠”也被后置自然候选审查否定；“3k优于8k，所以某一个过滤器必做”则超出了实验隔离能力。

**仍未解决：**源代码参考行为怎样与真实需求分歧裁定；学生换成30B-A3B后是否仍有混合结果；更小预算是否保留求解空间；已有SWE任务与功能合成题相比哪种每单位总成本更有效。它没有直接给出动态curriculum、多harness混训、OPD或新loss的必要性证据。

如果将来以这条路线形成个人成果，较有说服力的证据是：在同样可执行与评分可靠的基础上，以受控代价增加了当前模型真正可学习的任务，并在独立任务和固定评测协议上验证收益。**原论文数字不能作为我们的预期增益或八卡预算。**

## 12. 作者自查、剩余图页与接续位置

作者自查记录见 [reviews/codemidas_self_check_20260923.md](reviews/codemidas_self_check_20260923.md)。没有工具可创建实际独立审查子agent，本稿不伪造线程ID、模型effort或“独立审查通过”。正文与附录文本完成不代表PDF视觉检查完成。

取得PDF后按以下次序补读，不重写已经核清的文本：

| 图／材料 | 需要核查与补入的具体内容 |
| --- | --- |
| PDF首页与版本 | 标题、机构、版本、水印、总页数、页节映射；是否与本轮解析文本一致 |
| Fig.1 | 完整四模块结构、六类检查与节点对应、每一步retained-task数；不沿用二手漏斗 |
| Fig.2–3 | 完整语言／领域label、计数、占比与图形尺度；确认重复或Other口径 |
| Fig.4 | bins、非标准log段宽和中位数线；不从patch规模推断难度 |
| Fig.5 | SWE-bench Pro、RepoZero C2Rust缺失成绩；五项全部图值、初始/终点和pp标签 |
| Fig.6 | 通过率与实际token长度曲线，双轴、checkpoint与单位 |
| Fig.7–8 | 全部曲线点、评测checkpoint、各面板尺度与消融表值；是否补足选择政策 |
| Fig.9 | 原始case代码、reasoning与工具动作；区分示例和系统性统计 |
| Table 1–3/A1 | 特别目视核A1的516,096、Adam β/ε、staleness及表格脚注 |
| References与可能遗漏页 | 恢复关键benchmark、MiMo版本和代码／数据链接；检查是否存在解析漏掉的附录或说明 |

早期会话上传附件目前未自动出现在本运行环境。若CodeMidas PDF保存在本地或其他未发布资料中，需重新上传或发布可读原件；本稿不虚构该文件已经在仓库。补齐上述内容后再更新阅读状态，不先增加阅读库“全文完成”计数。

## 13. 快速定位与现有笔记

- 规格、reference和替代解：§3；P §3.1–3.2。
- 隐藏verifier、答案清理、六容器与两类solver过滤：§4；P §3.3–3.4。
- 数据规模、质量消融与成本限制：§5、§8、§10；P §3.5、§5.1。
- 实际GRPO配置：§6；P Appendix A，不由框架默认补公式。
- benchmark口径与图中缺失值：§7、§12；P §4、Fig.5–8。
- 行为定义、置信区间与负结果：§9；P §5.2、Appendix B。
- 项目候选：§11；只作设计层映射。

关联已有来源：[SWE-smith](E5_swe_smith.md)、[R2E-Gym](O03_r2e_gym.md)、[CalibForge](E2_calibforge.md)、[MiMo-V2.6 独立分支笔记][mimo-note]。它们用于比较来源路线，不替CodeMidas补模型、预算、算法或开放资产事实。

[P]: https://arxiv.org/abs/2609.22068
[P-html]: https://arxiv.org/html/2609.22068v1
[P-pdf]: https://arxiv.org/pdf/2609.22068v1
[HF-paper]: https://huggingface.co/papers/2609.22068
[project-page]: https://mimo.xiaomi.com/rl/
[project-sync]: https://github.com/Rogerffff/RepoHarness/blob/0554dafd633cd982288bd60a54f75da65e5c54d4/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/external_sync_20260923/README.md
[project-agents]: https://github.com/Rogerffff/RepoHarness/blob/0554dafd633cd982288bd60a54f75da65e5c54d4/AGENTS.md
[mimo-note]: https://github.com/Rogerffff/RepoHarness/blob/aa423327b76c541e744f2f0fb7ad3c9ceea8d32d/docs/harness_improve/external_paper_references/reading_notes/mimo_v2_6_technical_report.md
