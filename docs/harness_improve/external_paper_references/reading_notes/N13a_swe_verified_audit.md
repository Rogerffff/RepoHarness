# N13a · Why SWE-bench Verified no longer measures frontier coding capabilities

## 1. 来源、版本与全文覆盖

- 类型：官方评测审计文章；机构与署名均为 OpenAI；发布日期 **2026-02-23**；阅读日期 **2026-09-07**。
- [正式原文](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)。URL 中的旧式 slug 不是正式标题。页面没有论文版本号或独立更新时间；本笔记记录读取当日内容，不声称恢复了首发逐字版本。
- 来源记录：[web 分段抽取](sources/N13/web_text_20260907.txt)、[后半篇抽取](sources/N13/N13a_web_tail_20260907.txt)、[浏览器补充读取记录](sources/N13/browser_supplement_20260907.md)。前两者合用，仍不等于完整 HTML 存档。直接下载遭 HTTP 403，但 web 与浏览器可读全文。
- 原文为网页，**无 PDF 物理页/印刷页**；下文按正式节标题、具体任务 ID 和展示区块定位。网页引用列表、正文及末尾检查后，未见文章专属 PDF、附录、审计代码、完整标签或方法附件入口。案例代码是网页展示片段，不是训练框架源码。
- 对照旧稿：[项目一设计建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md) §3、§7；旧稿仅作项目映射线索，不作为本文事实来源。
- **后续文章不能覆盖本篇历史结论**：本文当时建议报告 SWE-Bench Pro；2026-07-08 的 [N13b](N13b_coding_eval_signal_noise.md) 撤回该建议。两篇必须分别引用。

先按原文目录及实际内容建立覆盖图，再组织主题笔记；所有正文与代码展示已精读。

| 原文单元 | 阅读深度与包含内容 | 本笔记位置 |
| --- | --- | --- |
| 导言（无独立标题） | 全读：历史进展、两项核心指控、停止报告的机构决定 | §2、§6 |
| Background | 全读：任务来源、两套测试、原 Verified 人审流程与环境噪声 | §3 |
| Too narrow and too wide tests | 全读：审计抽样/人数/结果；pylint 与 SymPy 全部题意、PR 与失败片段 | §4 |
| Contamination | 全读：Django edit_only 线索；探测者/目标模型/judge/人工复核的角色和预算 | §5 |
| GPT‑5.2 | 全读：提示、响应及 gold patch，逐项对照 | §5.2 |
| Claude Opus 4.5 | 全读：提示、prefill、响应、gold patch | §5.2 |
| Gemini 3 Flash | 全读：提示、prefill、响应、gold patch | §5.2 |
| Discussion | 全读：污染防护、自动评分两面要求、Pro 的局部观测、私有任务与人工评分 | §6 |
| Author / 附属入口 | 核署名、链接与版本；无独立附录或训练配方 | §1、§7 |

范围核对：本文没有 SFT、RL、数学/通用推理/多模态 RL、偏好优化、安全训练、蒸馏、训练稳定性或训练 infra 的专节/公式。它讨论**评测可靠性及训练数据暴露风险**，并以部署安全决策说明用途；不能据此补造任何后训练算法。

## 2. 核心问题与结论

作者要判断：高能力模型仍在 Verified 上失败，是能力不足，还是任务/评分本身不成立？第二个问题是，能通过的模型是否利用了训练中见过的任务、修复或发布说明，而不只是从当前题意和修复前仓库推导答案。

最有分量的量化结果是：对 **138 道经 o3 运行表现选出的任务**，至少六名工程师独立审查并追加复核后，作者报告 **59.4%** 存在实质题意/测试问题。另一类证据是三个目标模型在精心设计的提示下复述部分题目或修复细节。作者据此停止报告 Verified，并认为在当时前沿能力水平下，分数越来越受暴露情况影响。**这些是 OpenAI 的审计发现与判断，不是全行业撤销该基准的决定，也不是对所有模型规模的有效性定理。** [原文导言、Too narrow and too wide tests、Contamination](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)

本笔记的证据判断：测试缺陷案例直接说明“测试失败”可能误杀合法解；复述案例支持存在数据暴露风险。文章没有披露完整训练数据或去污染对照实验，因而不能据此估算任一模型有多少分来自污染，亦不能把所有后续分数增益判成记忆增益。

## 3. 数据来源、评测任务与历史构建

原始 SWE-bench 于 2023 年发布，从 **12 个开源 Python 仓库**的已解决 issue 及对应 PR 构建。模型收到原始 issue 文本和修复前仓库状态；文中所说模型看不到的 tests 是评分用测试材料，不能扩大成“模型不能运行仓库中任何测试”。模型代码需让两类测试全部通过：修复前失败、修复后应通过的目标测试，以及修复前后均应通过的回归测试。原文没有在此给某一实现版本的 F2P/P2P 文件清单、Docker 镜像或 harness commit。[原文 Background](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/#background)

| 阶段 | 数量与单位 | 方法/排除理由 | 不可混用的口径 |
| --- | --- | --- | --- |
| 2024 年 Verified 构建人审 | 1,699 道 SWE-bench 题；每题 3 名独立专家 | 排查过度具体/错配测试、题意不足、环境导致的假失败 | 不是本次 2026 审计样本 |
| Verified 发布集 | 500 道题 | 从上述审核产生的精选集合 | 不是 500 个镜像或训练轨迹 |
| 2026 本次深入审计 | 138 道题，占 500 的 27.6% | o3 在 64 次独立运行中未稳定解决；每题至少 6 名工程师独立复核，任何专家标记后另团队再核 | 不等于随机抽样，也不等于全部 64 次均失败 |

原文说明 Linux/Windows、Python 版本等差异曾导致假失败，故原始任务的有效性依赖执行环境。但本文没有新的 flakiness 率、环境构建漏斗、timeout/解析错误统计，也没有说明这些错误如何转成训练 reward。任务数据、仓库代码、release notes 及公开讨论都可能成为暴露渠道；没有给训练数据来源占比、许可审计、去重算法或 train/dev/test 训练切分。

## 4. 测试与题意错配的审计

### 4.1 数字及抽样边界

| 作者报告结果 | 分母 | 解释 | 原文定位 |
| --- | --- | --- | --- |
| 59.4%（导言表述为至少） | 138 道被审任务 | 测试设计或题意中的实质问题 | Too narrow and too wide tests，首两段 |
| 35.5% narrow tests | 同上 138 | 将特定实现细节强制为唯一合法解 | 同节项目符号 1 |
| 18.8% wide tests | 同上 138 | 强测题目没要求的额外功能 | 同节项目符号 2 |
| 5.1% miscellaneous | 同上 138 | 不能良好归入前两类的其他问题 | 同节项目符号 3 |

这几个百分比是任务占比，不是失败轨迹占比、测试断言占比或全库坏题率。原文未给计数明细，不能用四舍五入值制造精确标签清单。最初按 o3 表现选题存在选择偏差：59.4% 不能推广为全部 500 道的比例；64 次也不是 64 个独立新任务。作者没有披露“未稳定解决”的具体阈值、置信区间、标注一致性统计或盲审细则。按原文范围，可报告已检查集合存在大量问题；不宜据此计算“干净集分数上限”。

### 4.2 两个完整案例

**pylint-dev__pylint-4551（narrow）**：题目要让 pyreverse 利用 Python type hints 生成 UML；PR 新增 `get_annotation`，隐藏测试直接 import 此名字。合法实现可以把逻辑放在别处，仍满足业务需求，但收集测试时即发生 ImportError。作者展示题意、测试 import 和失败堆栈。这是对私有实现结构的依赖，不是测试函数数量不够。定位：原文同节的 Problem description / PR test snippet / PR test failures；[原 PR](https://github.com/pylint-dev/pylint/pull/4551) 为作者链接，本文未另运行该仓库。

**sympy__sympy-18199（wide）**：对应 PR 同时处理 `nthroot_mod` 的 #17373、#17377、#18212，而任务题意只取 #18212（特定模条件下遗漏 0 根）。模型补好描述中的问题后，仍可能被覆盖另两项改动的 PR 测试拒绝。定位：原文同节 Original PR description 及随后两个 Problem Description 区块。尝试打开[原 PR](https://github.com/sympy/sympy/pull/18199)时 web 抓取超时，本文案例依据是官方文章展示的三组原始材料，未声称重跑核实测试全量。

二者的共同机制是 **PR 的真实协作范围不等于抽出的单题契约**。Gold patch 能过，仅说明参考实现与测试一致；不能证明其他正确实现也能过，更不能证明题目提供了所有必要要求。此最后两句为本笔记对案例的归纳。

## 5. 污染探测的模型关系、协议与证据

### 5.1 角色与预算

这里的模型关系是“探测者—受测模型—判定者”，不是 teacher/student 训练。文中首先给 GPT‑5.2 解决 **31 道作者认为几乎不可能的任务**作为动机，没有给该 31 的全部题单或可用于重算的分母。Django #14725 要求隐藏参数 `edit_only`，题意没有明说；展示的推理文字提及 4.1 或 4.2，而作者结合 release notes 解释为知道 4.1 的改动。不能把推理文字的自述当作训练数据来源审计。[原文 Contamination](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/#contamination)

| 角色/步骤 | 文章明确披露 | 未披露或边界 |
| --- | --- | --- |
| 探测者 | GPT‑5；拿到任务 ID、description、gold patch、PR tests | 这些是探测者特权材料，不是保证全部送给受测模型 |
| 目标模型 | GPT‑5.2‑Chat、Claude Opus 4.5、Gemini 3 Flash Preview；作者意图排除 reasoning models | 作者承认三者有不可忽略的能力差异；未给 API snapshot 和完整推理参数 |
| 自适应探测 | 对每个 Verified question，在 15 轮中尝试改变 system/developer、user prompt、assistant prefill 及诱导策略 | 15 轮是每题探测预算，不是修复任务的 agent 轮数或 15 份训练样本 |
| 第一 judge | 每轮判新颖的任务专有信息，污染严重度从 none 到 strong | judge 型号、全量 rubric/阈值未给 |
| 泄漏控制 | 对 strong 案例另用 judge 检查 GPT‑5 没向目标泄漏过多信息 | “too much”的可复现阈值未给 |
| 人工核查 | 人工复核本文展示的 strong transcripts | 不能扩大成全部强污染判定均经人工复核 |

### 5.2 三个目标模型的展示与原文内部边界

| 原文节 / 任务 ID | 输入与恢复内容 | 证据强度的实际边界 |
| --- | --- | --- |
| GPT‑5.2 / django__django-11451 | 提供 ID 与短题意片段，要求回忆题目和 diff；响应给出文件、方法及 username/password 为空的提前返回条件 | **作者称 exact gold patch；展示并非整份逐字相同**：模型把 guard 放在 `UserModel` 赋值及 kwargs 回退之前，gold 放在 kwargs 回退之后；hunk header 也不同。应表述为恢复关键修复细节，而非本笔记已证整份精确复制 |
| Claude Opus 4.5 / astropy__astropy-13236 | 提供题意概要、ID、prefill；能恢复文件/方法、四行功能代码及对应注释，涉及取消 structured ndarray 自动转 mixin | 恢复的是原代码/改动信息及注释；响应描述 removed/changed，不是完整统一 diff。不能说完全无题意输入 |
| Gemini 3 Flash / django__django-11099 | 用户提示仅以 ID 定位并要求题目和 patch，另给通用 prefill；输出 username validator 的正则修改、文件路径和 hunk 信息 | 正则终止符由 `$` 改为 `\Z`，ASCII/Unicode 两处均出现。恢复非常具体，但不由此估算全模型污染率 |

定位为[原文三个同名模型节](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)。Django 原 PR 页面另核为 2019-06-10 合并、提交短号 `3ee0834`，但本文关于展示差异的证据直接来自文章 Model response 与 Gold patch，未把 PR 短号误作该审计代码版本。

上述差异不会自动推翻“存在暴露风险”，但会限制“逐字复现”的措辞。探测经过多轮自适应搜索并挑选 strong 展示，不能用三个例子比较提供商污染严重度；没被诱导出来也不等于没暴露。原文没有提供泄漏率全表、假阳性/假阴性率、去污染模型对照或训练数据命中记录。

## 6. 作者的建议、性能背景与适用性

导言给前沿榜单分数在前六个月从 **74.9% 到 80.9%** 的背景，并链接第三方榜单。本笔记仅记录作者当时引用的历史数字；没有把它们当作同模型、同 harness、同推理预算的消融，亦未拿当前排行榜覆盖历史数据。文章没有把 64 次 o3 运行定义成某个 pass@k 报告协议。[原文导言](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)

Discussion 的建议有两条独立责任：公开数据要额外查污染，发布方式可采用密码保护、训练过滤严格遵循 canary strings（用于识别不应混入训练的数据标记）；自动评分既要接受无关实现细节不同的合法解，也要能拒绝捷径解。Canary 和保护发布是作者建议，本文没有给其覆盖率或零泄漏保证。

当时作者在 Pro 上也发现少量污染案例，但称更少、更弱，且没有模型产出完整逐字 gold patch；这不是“Pro 零污染”。其没有给该 Pro 探测的题数、完整设置或统计量。文末以 GDPVal 的私下原创任务、专业人员整体评分说明另一思路，承认资源密集；它是跨领域评测背景，不是本文训练算法或 SWE 专用实证。作者的 Pro 替代建议已于 7 月撤回，详见 [N13b §6](N13b_coding_eval_signal_noise.md)。[原文 Discussion](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/#discussion)

## 7. 后训练、运行预算、开放资产与未知项

没有可复原的 base→SFT→RL→distillation 流程；所有被提到的模型均用作解题/探测/判定对象。本文没有 reward 合成、advantage、KL、mask、loss 分母、OPD 目标、teacher logprob、异步更新、staleness、权重发布等训练语义。不适用不代表作者实际训练时没有这些机制，只代表这篇审计不提供依据。

| 待核字段 | 本次查阅范围 | 结论/影响 |
| --- | --- | --- |
| 全量 138 审计题及逐人标签、分歧处理规则 | 测试审计节、全部案例、Discussion、页面附件入口 | 未披露；不能复算分类、构造去坏题后的新排行榜 |
| o3 64 次运行参数、筛选阈值、模型/harness 版本 | 测试审计节、导言及 Background | 未披露；无法复现实验选择函数 |
| 污染 judge、15 轮模板、完整结果/准确率 | Contamination 与三组 transcript | 仅局部协议和精选例子；不能估计污染总率 |
| 各模型训练阶段、数据、算力与算法 | 全文、案例、末尾入口 | 没有训练披露；禁止从模型家族补齐 |
| token、wall-clock、API、人工与 GPU 成本 | 全文方法与 Discussion | 仅有人数、轮次和“资源密集”的定性说明；无货币/GPU-hour 预算 |
| sandbox、网络、重试、取消、解析和超时评分 | Background、审计及案例 | 没有运行协议；文章案例不证明 rh2 现有隔离正确 |
| 原始资产的许可与版本 | 文章链接及署名 | 文章可公开读；不等于授予所有关联仓库/基准统一训练许可 |

本篇公开资产是文章、局部 transcript/patch/测试展示及原 PR 链接。没有审计实现可 pin 的 commit；没有完整审计数据下载或可重放 entrypoint。该限制来自本次所查文章与配套入口，不代表作者在所有其他渠道从未发布。

## 8. 对 RepoHarness 项目一的意义（设计层候选）

映射日期 2026-09-07。基线据 [CURRENT-STATE-BRIEF](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)（2026-09-05）：miles + SGLang + 外部 Claude Code harness；rh2 负责环境/评分与轨迹入训边界，首训 taskset/C 包尚未定。检查所指 spike-log 顶部未见更近的 09-06/07 决策条目；09-07 设计建议较新但不是批准，本文不把它升级为既定实现。未审全仓代码，以下不是模块验收结论。

主目录 HEAD 已只读核对为 `ce2009f879cf38071d7898a1387e01d4e27741d6`；状态入口包含未提交文档，本映射依据实际读取的文档日期与内容，不能只靠该 commit 复原全部背景。

| 候选借鉴 | 来源依据 | 职责与成本边界 | 最小可验证证据 |
| --- | --- | --- | --- |
| 区分环境完整性与评分语义有效性 | narrow/wide 两案例 | rh2 现有任务/评分入口上增加离线审查案例；fresh grader 与权限隔离不保证需求完整，不增 runtime 平台 | 在小批任务比较 gold、合法替代解、满足题意的局部解被接受/拒绝的具体证据 |
| 污染说明与内部 held-out 分开 | 公开仓库/release notes 暴露 | 上游承担模型训练和数据知识；rh2 能记录自己的切分/派生关系，但不能证明基座未见过 | 按任务/仓库/PR 家族冻结切分并记录污染探针覆盖、未覆盖部分 |
| 给公共 benchmark 降低结论权重 | OpenAI 停报决定有模型与时点边界 | 项目选择对 30B 有区分力的外部坐标，同时用独立 held-out 证明学习；不以公司建议代替本地有效性实验 | 固定协议比较 checkpoint，披露坏题与排除规则；不只筛掉当前模型难题 |
| 不因本文改造 RL/OPD infra | 文章没有训练实验 | fully-async、推理、训练内核继续复用 miles/SGLang；本文不支持新 loss 或 curriculum | 无需为该文章新增训练组件 |

本篇能支持“评分测试与题意错配是工程上的真实问题”的项目动机；不能支持“rh2 已降低误奖励率/已提高能力”的简历结果。误判率、效率和学习增益均需自己的受控测量。置信区间、任务级配对及统一重跑是项目设计建议，**不是本篇已实施的统计方法**。

## 9. 旧稿更正、快速定位与独立审查

指定旧稿 §3.3、§7 已明确测试不等于需求、公共坐标不等于零污染，未发现可归于它的 N13 数字错误；本次补足原始来源与审计分母，不虚构“旧稿曾说 59.4% 全库坏题”。需要防止沿用的过时结论是“OpenAI 当前推荐 Pro”：2 月确曾如此，7 月已撤回。本文还对原文“exact gold patch”与实际展示差异作了明示，保留旧稿不改删。

- 审计样本/人数/缺陷比例 → §3–4；原文 Too narrow and too wide tests。
- 模型关系、特权材料、15 轮预算 → §5.1；原文 Contamination。
- 三组污染展示与逐字复制边界 → §5.2；三个模型同名节。
- 训练算法/成本不可复现项 → §7；全文查阅范围。
- Pro 后续审计与建议撤回 → [N13b](N13b_coding_eval_signal_noise.md)。

独立审查已于 **2026-09-07** 完成：本线程唯一审查 subagent 使用 **GPT-6 Astra / high、干净上下文**，先从官方原文独立建立覆盖清单，再逐项对照两篇初稿。审查文件：[06_N13_review](reviews/06_N13_review.md)。审查者亲自核对全部正文、案例、图表与方法内容；两篇均未发现必须修订的问题，P0–P3 均为 0。

主审已读完审查报告，确认覆盖与证据，完成版本记录和审查状态更新；无技术纠错项需要回改。原文内部措辞/聚合缺口保留为未知，不冒充独立实验复现；最终主目录链接与副本一致性核验见审查文件末尾。**本任务精读完成**，不表示基准审计本身已被本项目重跑复现。
