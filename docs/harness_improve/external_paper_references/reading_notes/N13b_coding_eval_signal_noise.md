# N13b · Separating signal from noise in coding evaluations

## 1. 来源、版本与全文覆盖

- 类型：官方评测质量审计文章；机构/署名 OpenAI；发布日期 **2026-07-08**；阅读日期 **2026-09-07**。
- [正式原文](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)。网页无独立修订号、更新时间或版本历史；以下对应读取当日可见英文内容，不将抓取日期称为发布版本。
- [web 抽取记录](sources/N13/web_text_20260907.txt)、[浏览器交互内容与图表读数](sources/N13/browser_supplement_20260907.md)、[原方法图 SVG](sources/N13/N13b_quality_assurance.svg)。直接下载正文返回 HTTP 403，web 与浏览器成功读取；浏览器先自动显示中文，随后切到英文核对正文、图与全部案例。静态抽取只显示默认案例，不能独自支持全文覆盖。
- 原文是网页，**没有 PDF 页码**，故以节标题、图题、标签名和案例 ID 定位。全文及末尾链接检查后，未见独立技术附录、审计代码、全量人审标签或方法附件下载入口。Methodology 及两个人/agent 审查节、方法图本身就是配套方法说明。
- 旧稿为 [项目一设计建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md) §3 与 §7，仅作项目背景。此文与 [N13a](N13a_swe_verified_audit.md) 是两篇独立文章，不能合并为一个无日期的“OpenAI 建议”。

按原文结构建立覆盖图后，已精读全部正文与交互案例，没有以项目问题筛掉内容。

| 原文单元 | 阅读深度/内容 | 本笔记位置 |
| --- | --- | --- |
| 导言（无独立标题） | 全读：安全/部署用途、Pro 设计、731 题、进展背景、两条审计结果 | §2–3 |
| Share of Dataset Flagged by Issue Type 图 | 浏览器读取一位小数标签及图例/分母，补静态抽取缺口 | §4 |
| Methodology | 全读；目视方法图：筛选后分成两条独立深入审查路径 | §3 |
| Human-supervised agent review | 全读：repo/environment 访问、独立重复、研究员终判 | §3 |
| Human annotation campaign | 全读：5 人独立初判、培训、标签/严重性/升级处理、74%及多标签 | §3–4 |
| Failure modes → Misleading prompt | 全读下拉菜单两例 OpenLibrary-77c16d5、Qutebrowser-e34dfc6，含代码 | §5.1 |
| Failure modes → Overly strict tests | 全读单例 Navidrome-b65e762，含测试代码 | §5.2 |
| Failure modes → Underspecified prompt | 全读下拉菜单两例 Flipt-86906cb、Flipt-af7a0be，含代码 | §5.3 |
| Failure modes → Low-coverage tests | 全读单例 OpenLibrary-d109cc7，含构造测试 | §5.4 |
| Discussion | 全读：人类 PR 协作的任务边界、agent 审查价值、撤回 Pro 推荐、原创 benchmark | §6 |
| Footnotes / Author | 全读两条旧新术语对应、署名与入口 | §1、§4 |

全文没有 SFT、RL、通用推理/数学/多模态训练、偏好优化、reward 学习、蒸馏或训练稳定性/infra 章节，也无此类附录。安全/对齐在这里是评测结果的使用场景，不能硬写成安全训练配方；Codex 是审计工具，不是本文训练产物。

## 2. 核心问题与结论

本文要同时检查两种错误：任务失败是否真反映模型做不到，任务通过是否真代表模型完整满足要求。前一篇 Verified 审计主要强调误杀与污染，本篇增加了**低覆盖测试导致不完整实现通过**这一明确方向，并把题意误导与不可合理推断的缺失要求分开。

OpenAI 在 **731 题 public split** 上先自动筛出 **286 道可疑题**，随后用人类监督的调查 agent 审查与五名工程师/题的人工标注两条路径深入检查。其报告前者认定 **200 道（27.4%）**、后者 **249 道（34.1%）**有问题；作者将整体概括为约 30% 的任务 broken，并撤回自己先前采用 Pro 的推荐。[原文导言、Methodology、Discussion](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)

这不是随机抽 286 题调查全库，也不是对全部 private/commercial split 的结论。两条审查路径都依赖同一个自动筛选入口，不能用相近比例证明不存在共同漏检。文章没有估计由坏题造成的净分数偏差，更没有新的 Pro 污染率结果。判断主体为 OpenAI；没有证据表明整个社区或基准发布方据此撤销基准。

## 3. 任务来源、审计流程、模型角色与运行协议

### 3.1 原任务与审计对象

文章称 Pro 旨在用更长时间尺度、更真实的 coding 任务改进 Verified：从公共/私有仓库的功能变更历史程序化取题，模型应实现新功能并保持既有行为。当前审计量化对象是 **731 道公开题**。文中“前沿模型八个月从 23.3% 提高到 80.3%”是历史进展背景，未给对应模型对、推理预算或同 harness 证明，不能当本文受控实验。[原文导言](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)

这里的题意、gold patch、评分测试和模型 attempts 是**评测审查输入**，不是训练样本漏斗。原文没有新的训练任务生成器、生产成本、去重/仓库切分算法、统一许可或镜像统计。原始 Pro 发布入口由文章链接至 [Scale 官方介绍](https://scale.com/blog/swe-bench-pro)；本任务不把 Pro 基准完整论文/实现展开成第三篇独立精读，也不从其默认设置补充 OpenAI 未披露的审计配置。

### 3.2 两条深入审查不是串联两次过滤

| 阶段 | 输入与操作 | 数量、预算、输出 | 原文定位 |
| --- | --- | --- | --- |
| 初始自动筛选 | 模型指令、attempts、评分测试；方法图补充 rollouts、patches/diffs、task metadata | public split 731 → flagged 286；未标记不进入图示深入路径 | Methodology + Quality assurance pipeline 图 |
| 人类监督 agent 审查 | Codex-based investigator 可访问任务 repo/environment，读文件、跑测试、分析尝试/共同失败 | 若干独立重复深入审计后，researcher 查摘要并终判、分类；结果 200 broken | Human-supervised agent review；导言图注 |
| 人工标注（同一 flagged 子集的并行分支） | 工程师先受 benchmark 目标、分类与边缘案例培训；先根据题意、tests、gold 独立判断，再看 pipeline/transcript 辅助材料 | 每题 5 名；标签与严重性；分歧/低置信升级；结果 249 broken | Human annotation campaign；导言图注 |

见[原图](sources/N13/N13b_quality_assurance.svg)：初筛输出 flagged/not flagged；flagged 分成两个分支，每个分支输出自己的 broken/not broken 与类别。不能写成“先 200 题再交人审扩成 249”，也不能写“5 名工程师独立审完 731 题”。

调查 agent 的环境权限具有方法意义：合理歧义可以通过邻近代码和仓库约定解决；真正缺失是既没写出、也无法合理推断的隐藏要求。因此审题不能只做 prompt—test 关键词对比。人工先形成独立判断再看 agent 解释，有助于减少先入为主；但整批人工样本仍由同一初筛选出，不能称整体与 agent 完全独立。[原文 Human-supervised agent review / Human annotation campaign](https://openai.com/index/separating-signal-from-noise-coding-evaluations/#human-supervised-agent-review)

没有 teacher/student、参数冻结/更新或训练阶段关系。初筛模型身份、Codex 模型 snapshot、独立重复数、采样温度、token/上下文、工具轮次/超时、网络和 sandbox 约束、错误重试及运行总成本都未在这几个方法节和案例中披露。模型可以跑测试，不意味着每例都经过完整测试重放；本笔记也没有运行仓库测试。

## 4. 数字、类别与统计解释

### 4.1 分母表

| 原文数字 | 正确分母/单位 | 不可误读成 |
| --- | --- | --- |
| 286 flagged | 731 道 public 题中的初筛集合；39.1% 为本笔记计算 `286/731` | 286 道最终确认坏题或随机样本 |
| 200 / 27.4% | agent+researcher 终判的任务数 / 731 | 纯自动分类器精确率、或 `200/286=27.4%` |
| 249 / 34.1% | 人工分支报告任务数 / 731 | 249 道 agent 结果之外新增坏题 |
| 约 30% | 作者对审计发现的约略概括 | 27.4–34.1% 的统计置信区间 |
| 74% overlap | 作者说人工与 agent 已标类别在案例层面重合 | 完整 binary accuracy、五人一致率或 Cohen's κ |
| 9.4% vs 4.1% | low-coverage 类别占 benchmark 的比率，人工 vs agent | 在 249/200 中的条件比例 |

来源：[导言图注、Methodology、Human annotation campaign](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)。原文未定义 74% 的精确集合运算、是否允许部分多标签重合、分母计数或 severity 聚合，因此不能自行算其错误率。

### 4.2 图中所有类别与数值

下表来自浏览器显示的一位小数标签，图题为 **Share of Dataset Flagged by Issue Type**，纵轴明确 **Percent of total dataset**。静态 web 抓取没有图值；原始读数保存在[浏览器补充记录](sources/N13/browser_supplement_20260907.md)。

| 类别 | 人类监督 agent | 人工标注 | 类别意义及旧术语 |
| --- | --- | --- | --- |
| Overly strict tests | 14.4% | 17.8% | 把未规定且不可合理推断的具体实现强制成唯一实现；脚注 1 对应旧 narrow tests |
| Low-coverage tests | 4.1% | 9.4% | 没检查全需求，不完整修复可通过 |
| Misleading prompt | 6.3% | 7.5% | 题意引向与测试相反的行为 |
| Miscellaneous issues | 1.9% | 1.2% | 图中存在的第五类；正文未细分解释或提供专例 |
| Underspecified prompt | 0.6% | 0.8% | 隐藏测试要求题意以外且不可合理推断的功能；脚注 2 对应旧 wide tests |

**分类图不是互斥完备饼图**：作者明确人工更常多选标签；人工列相加 36.7%，高于任务总数占比 34.1%。不能按总和替换去重任务比例。agent 列相加 27.3% 与 27.4% 有舍入差，不能反算逐题标签。图题和正文关于人工“最常见问题”的口径也未给完整聚合公式，本笔记保留原始数值而不重建未公开聚合方式。

正文另称在所有 flagged 题中，“not broken”都不是最常见人工标签，同时又只报告 249 道 broken，少于初筛 286。文章未解释 **286、249 与最常见标签**之间的 severity/终判映射，也没给逐题投票；不能自行补成“剩余 37 题均无问题”，或把该句当成“286 题全部最终判坏”的证据。这个缺口需要原始标注规约才能消除。

### 4.3 可信范围与未做的统计

确认坏题占全库的计数比与随机抽样估计不同。未标记的 445 题没有按文中协议深入人审，故初筛漏检未知；作者认为 agent 分支相对保守，依据是人工发现更多重叠/附加问题，不能据此量化初筛 recall。人审也不等于无误的地面真值，尤其在需求是否可合理推断方面需要判断。

文章没有报告坏题剔除前后模型分数、排名反转、配对置信区间、bootstrap、重复运行方差、显著性或纠偏模型。低覆盖可抬高分，严格/矛盾测试可压低分，因此净偏差不能只按一个方向纠正。这里关于偏差方向与统计可识别性的解释为本笔记推论，不冒充作者测出的模型分数变化。

## 5. 六个完整案例：题意、参考实现与测试怎样脱节

以下均定位于[原文 Failure modes](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)，需按标签并展开相应下拉菜单。案例 ID 是文章显示的短 ID；未披露完整任务版本/修订，不把后缀直接宣称为已经核验的 Git commit。没有公开全量环境重跑证据可据此复算所有判定。

### 5.1 Misleading prompt：不只是信息少，而是要求冲突

- **OpenLibrary-77c16d5**：任务规定 `TocEntry.to_markdown()` 的字符级输出。提示例子在管道前给一个空格，隐藏 `test_to_markdown` 要两个。文章内普通内联代码显示可能让空格不明显，应看明确写出的 `[space]` 与 `[space][space]` 代码区块。严格遵循题意会被判失败，不能把这一字符差单独归为模型没完成要求。
- **Qutebrowser-e34dfc6**：清理 URL/搜索词判断，题意明确要求特定 SharePoint 地址不被识别为有效 URL，隐藏 `test_is_url` 却对同一字符串给 True。文章展示的参数化测试直接与提示相反；不存在同时满足这两个要求的实现。

### 5.2 Overly strict tests：合法结构不同也会失败

**Navidrome-b65e762**：要求同一用户其他 session 收到 server-sent event，而发起客户端不回收自己的事件。公开要求包括每客户端 UUID、request context 及 `Broker.SendMessage(ctx, event)`。隐藏测试却调用私有 helper `shouldSend`，并构造含私有字段 `senderCtx` 的 message；gold 使用这些名称，但题意、requirements 与可见 tests 均未要求。逻辑放在既有函数里、使用不同字段同样可实现行为，却会被隐藏结构依赖拒绝。正文还提到未规定的 literal error string 也是该类问题可能的表现，不能将类别限缩成私有函数名问题。

### 5.3 Underspecified prompt：评分范围超出给定任务

- **Flipt-86906cb**：题目要求修存储子系统的 snapshot cache 引用删除；隐藏 tests 检查认证 session 配置、schema 和 HTTP CSRF 行为，要求新 `AuthenticationSessionCSRF` 配置。满足缓存任务仍可能完全没有碰到这些无关要求。
- **Flipt-af7a0be**：题目要从废弃 `tracing.jaeger.enabled` 迁移到新 tracing 配置并兼容旧行为；隐藏 tests 还改变缓存弃用警告的精确文本，把 `cache.backend` 和 `cache.enabled` 的先后顺序调换。与 tracing 问题无关且无法从所给上下文推断。虽然也有“字符串过严”的表现，**文章把此例放在 underspecified**；本笔记保留来源分类，不擅自移类改图。

### 5.4 Low-coverage tests：通过不表示功能完整

**OpenLibrary-d109cc7**：任务是条目专属的公开 Markdown notes，要求覆盖数据模型、列表操作、输入规范化、编辑/显示模板、前端/API JSON、Solr 索引和导出。展示的 tests 只检查 `List`/`Seed` 构造及字段，没测 notes 如何渲染、编辑、序列化、索引、导出或保持原结构兼容。补丁可以通过这些构造测试而漏掉大部分功能。

这项证据不是“模型已经主动作弊”的证明，而是 verifier 覆盖不足，允许不完整提交被打为正确。它与只看失败 trace 的审查存在互补：成功任务也需要查需求覆盖。该最后一句是本笔记的方法归纳。

## 6. 讨论、污染与建议变更

作者解释根因：开源 issue/PR 是为人类长期往返协作写的，问题描述、合并代码、unit tests 未必自然形成孤立且一致的单题；PR 测试常用于验证某个具体实现，而非定义对所有合法实现公允的验收规则。更强 agent 能检查提示、patch、trace、测试和边界案例，因此作者认为可扩展的数据质量检查比过去更可行。这是方法价值的解释，没有吞吐、人力节省或因果消融数字。[原文 Discussion](https://openai.com/index/separating-signal-from-noise-coding-evaluations/#discussion)

作者建议由有经验的软件开发者专门构建评测任务，保留工程真实性与难度，并增强全流程人类监督。最终目标包括不易投机、可信、能反映能力/对齐；评测对部署与 Preparedness Framework 安全判断有影响，故错误指标不是纯 leaderboard 问题。这里没有设计新的对齐训练或发现某种模型已更不安全。

**版本时间线必须同时保留**：2026-02-23 的 N13a 在承认 Pro 并不完美的情况下建议暂用它；2026-07-08 本文 Discussion 明确撤回这一推荐。撤回理由是本次任务质量审计；本篇没有新公布 Pro 的污染探测协议或污染率，不能把约 30% broken 误写成约 30% contaminated，也不能据它否定前篇所述当时 Pro 污染“较少”的局部观测。更不能宣称 Pro 在任何模型/用途上已经完全无效。[N13a 原文](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/#discussion)、[N13b Discussion](https://openai.com/index/separating-signal-from-noise-coding-evaluations/#discussion)

## 7. 开放资产、预算与证据缺口

| 字段 | 已检查的位置 | 实际披露与缺口 |
| --- | --- | --- |
| 公开审计材料 | 全文、图表、四标签六案例、Footnotes 与页面链接 | 文章及代表性代码展示、方法图；未给逐题完整审计数据和人工标签下载 |
| 审计版本/实现 | Methodology、两审查节、末尾入口 | 没有审计 repo/commit、模型 snapshot、完整模板或运行命令 |
| 731 public split 的冻结版本 | 导言、方法与案例 ID | 有任务数，无数据 revision、任务列表/hash、镜像/harness pin；不能用最新 Pro 默认配置填补 |
| 初筛/人审漏斗的聚合 | Methodology、图、Human annotation campaign | 286/200/249、5 人与74%；缺 severity→broken 规则、tie/重叠计算与未筛中题复审 |
| 环境与运行协议 | agent review、方法图、案例 | repo/environment 可访问、能跑 tests；资源、重试、随机性、解析/timeout 的处理未披露 |
| 成本与效率 | 全文 | 无 token/API/CPU/GPU-hour、人小时或单题美元成本；无法声称 agent 审查便宜多少倍 |
| 训练语义 | 全文、脚注、所有附属入口 | 无训练数据、loss、reward、KL、mask、OPD、staleness 等；不适用 |
| 因果效果与污染 | 全文，尤其 Discussion | 无清理后模型分数对照、审计器消融或新污染率；不可给出净分数修正 |

“未披露”限定于本次文章和其配套方法内容，不声称作者在全部其他渠道从未公开；公开可读也不等于所有关联任务资产有相同训练许可。本文未下载全部 benchmark、未运行训练或测试、未租用算力。

## 8. 对 RepoHarness 项目一的意义（最后才作设计映射）

映射日期 2026-09-07；据 [当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md) 2026-09-05 版本与 [设计建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md) §3/§7。后者较新但非实施批准；所查 spike-log 顶部没有更近的 09-06/07 决策。miles/SGLang 与外部 coding harness 承担训练/推理/agent 基础能力，rh2 的增量围绕环境、评分和训练消费边界；以下只作设计候选，不声称代码已具备或改变 C 包。

主目录 HEAD 已只读核对为 `ce2009f879cf38071d7898a1387e01d4e27741d6`；状态入口包含未提交文档，本映射依据实际读取的文档日期与内容，不能只靠该 commit 复原全部背景。

| 候选借鉴 | 原文依据 | 上游/我方边界与成本 | 最小验证 |
| --- | --- | --- | --- |
| 对现成任务离线查四类缺陷，保留其他类 | 六个案例、分类图 | rh2 可在现有任务入口补审查记录；上游任务不因开源就自动有效，不建新的通用审核平台 | 小批题逐项需求—测试映射；检查 gold、合法替代、不完整解；报告审计分母 |
| 先独立判断，再看 agent 摘要 | 五人工程师流程 | 少量高风险任务用人审；agent 做线索和测试调查，最终判定有具体证据；不能直接以 agent 标签作新 reward | 比较独立判断与看摘要后的改变，保留分歧、不确定及人工成本 |
| 成功与失败都抽查 | low-coverage 反例 | 现有可信评分保证执行边界；还需证明评分与需求对应。自动过滤仅帮助排序，不把未标记题都称已验证 | 在 flagged 与未 flagged、成功与失败中按预定规则抽查，分列误杀/误奖励 |
| 固定公共坐标的解释范围 | Pro 撤回与 public 分母 | rh2 报告版本/题单/harness/预算、统一坏题处理；目标 30B 是否有区分力由实测决定，不盲换更昂贵基准 | 同题同预算配对 checkpoint，报告排除与费用；必要时把公共坐标降为辅助证据 |
| 训练算法和 infra 保持上游复用 | 本文没有训练实验 | 不据此要求自建 verifier 生成器、后训练平台或新蒸馏目标 | 先验证任务/评分，训练候选仍由既定流程决定 |

冻结 held-out、按模型无关规则排除无效环境、固定重试、任务级配对区间等来自当前项目建议及统计推理，**不是 OpenAI 本文已运行的协议**。这些文章支持任务有效性的重要性；不证明 rh2 已实现低误奖励率、训练能力增长或节省 GPU。简历里的量化结果必须另有本项目实测。

## 9. 旧稿更正、快速定位与独立审查

指定旧稿已经将合法替代解、描述遗漏、覆盖不足、污染、固定协议及不确定性列为注意点；本次未发现可直接归于它的 N13 错数。补充的实质是完整 731→286→两分支漏斗、所有六个案例、原图五类别、以及 2 月推荐到 7 月撤回的时间线。旧稿及其他模型对话不改删；不能把“建议改报 Pro”的历史说法当成 09-07 的机构现状。

- 全流程、角色、运行披露 → §3；原文 Methodology 与两审查节。
- 数字、分母、多标签、聚合缺口 → §4；原图及 Human annotation campaign。
- 四类六例及短 ID → §5；原文 Failure modes 交互区。
- 污染与建议时间变化 → §6；两篇 Discussion。
- 无训练算法/预算/公开实现 → §7；全文与附件入口。
- 前篇 Verified 审计 → [N13a](N13a_swe_verified_audit.md)。

独立审查已于 **2026-09-07** 完成：本线程唯一审查 subagent 使用 **GPT-6 Astra / high、干净上下文**，先从官方原文独立建立覆盖清单，再逐项对照两篇初稿。审查文件：[06_N13_review](reviews/06_N13_review.md)。审查者亲自核对全部正文、案例、图表与方法内容；两篇均未发现必须修订的问题，P0–P3 均为 0。

主审已读完审查报告，确认覆盖与证据，完成版本记录和审查状态更新；无技术纠错项需要回改。原文内部措辞/聚合缺口保留为未知，不冒充独立实验复现；最终主目录链接与副本一致性核验见审查文件末尾。**本任务精读完成**，不表示基准审计本身已被本项目重跑复现。
