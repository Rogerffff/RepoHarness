# FrontierCode 原版：从测试正确性到可合并性，及其评分证据边界

FrontierCode 把维护者愿不愿意合并一个改动，拆成行为、回归、机械检查、测试质量、范围和代码质量六类要求，再以 blocker 决定是否通过，以加权 rubric 表达质量。它由维护者参与建设，公布 150/100/50 题的嵌套评测面，不公开完整任务集。本篇最有用的内容不是低分榜单，而是合法替代解、故意错误解、分档参考解和多轮人工审查共同校准 verifier 的流程。与此同时，公开证据有明确限制：误判图的“81%”对应特定假阳性比较；简短题面不等于全部输入缩短到三分之一；网页示例是预置播放，且其失败样本的展示 reward 与正文归零规则没有解释清楚。它是评测方法来源，不是在线 RL 配方或已可下载的训练池。

导航：[来源与覆盖](#source) · [任务与质量控制](#tasks) · [六类评分](#grading) · [完整案例](#example) · [结果与误判](#results) · [项目意义](#project)

<a id="source"></a>
## 1. 来源、版本和实际阅读范围

**正式来源：**Cognition，*Introducing FrontierCode*，2026-06-08。[官网][WEB]署名 Eric Lu、Ben Pan、Deniz Birlikci、Sam Lee、Ray Wang、Rohan Choudhury、Fermi Ma、TC Qin、Carlo Baronio、Silas Alberti，另有设计和外部贡献者致谢。发布文没有在标题写版本号；后续 1.1 文将它称为 1.0，本文沿用“原版／1.0”以区分版本。

**阅读日期：2026-09-14。** 主体证据是用户上传的 `03_FrontierCode.md/.zip`，采集于 2026-09-11；原版正文的精确采集时间为 `09:47:47.728Z`。包内包括直接提取正文、原始 SVG、截图、展开文本、官方 JavaScript 的静态数组及公开图表 JSON。2026-09-14 也成功打开官网正文并核对标题、日期、章节和关键表述，但没有独立归档实时网页的全部交互状态；下文数值和展示资产冻结在所给快照，不宣称它们是当前排行榜。

**远程基线：**`Rogerffff/RepoHarness@miles-migration`，提交 `506879e07804548ebe84bcec6f4d00fa1d36d03b`。来源材料维护在 `source_supplements/cognition_20260911/`。本稿是独立的新来源笔记，不修改此前 SWE-2/1.7 成品；项目映射为设计层分析，不代表本轮审计了 rh2 实现。

**实际已读：**全部主文、评分方法表、质量控制五阶段、唯一参考文献身份及致谢；全部五幅静态方法/统计 SVG；10 页视觉附件对应的截图与状态；三个 benchmark 的完整题面比较；两模型各八个文件的所有展示 hunk；十项 rubric 与各十项结果；93 个 model–effort–subset 聚合记录的字段与一致性检查。**没有独立技术附录。** 视觉 PDF 是采集者排版的截图集，其页码不是作者论文页码。chart-01 与 chart-02 的 PNG 相同，不能计作两次独立实验。[来源包][PACK]

| 原文结构 | 完整阅读对象 | 本笔记 |
|---|---|---|
| Raising the bar from correctness to quality | 定位、维护者、工作量、误判主张 | §2–3、§7 |
| Results | 三种子集、两种指标、重复与 effort 选择、图表 | §4、§7–8 |
| Why we built FrontierCode | 两类误判、语言、题面、补丁分布；全部展开题面 | §3、§7 |
| A Team of Open Source Maintainers | 36 仓库、维护者判断、参与者陈述 | §2–3 |
| Beyond Unit Tests / Novel Grading Methods | 六种方法、blocker、reverse-classical、scope、mutagent | §4–5 |
| Example Task | LOG_WARNING 题面、两套补丁、全部 rubric、作者解释 | §6 |
| Quality Control | Design、Hack report、Calibration、Review、Re-Review 及流程图 | §3.3 |
| Conclusion / References / Acknowledgments | 任务不公开、对模型开发者开放评测、引用及署名 | §9 |

当前不存在阻塞性读取缺口。完整任务、grader 实现、原始运行/评分日志及审计标注没有包含在这些来源中；它们与“ZIP 无法解压”不是一回事。METR 的引用身份已核，本轮没有进一步精读其独立文章，也不靠它补本篇未给出的实验信息。

## 2. 核心测量对象：maintainer mergeability，而非仅 test passing

原文问的是维护者是否会合并 PR。它将功能正确性视为必要但不足的条件，还关心测试、修改范围、可维护性与仓库惯例。维护者陈述说明了其设计意图与领域投入，不是另一次盲测或真实合并率实验。[Raising the bar；A Team of Open Source Maintainers][TEXT]

作者称这是首个测量 code mergeability 的 benchmark，并以其误判分析主张排名更准确。本文将“首个”“最强可用信号”“所有满足标准的 PR 会被批准”保留为作者定位，**没有独立核验优先权，也没有把代理标准等同于未来真实维护者合并事件**。要进一步证明预测效度，需要独立维护者判断及其与评分的对应数据；本篇未公开该层验证。

与训练的关系应单列：本篇没有提供 SFT/RL/OPD 阶段、训练样本量、loss 或模型参数更新。Devin 在这里协助寻找 rubric 漏洞；`mutagent` 是评分侧适配工具。这些角色不能被改写成训练 teacher、reward model 训练或 solver 自博弈。

<a id="tasks"></a>
## 3. 任务、分布与质量控制

### 3.1 可恢复的资产漏斗

| 对象 | 原文披露 | 尚未披露 |
|---|---|---|
| 领域人员 | 20+ 开源维护者/开发者 | 各人的题目分配、标注一致性、完整人时日志 |
| 仓库来源 | 36 个旗舰开源仓库；维护者选择多 PR 链和自由需求 | 完整仓库/PR/base commit/task manifest、时间切分 |
| 单题生产 | 每题投入超过 40 小时，多轮贡献者、pod lead、研究员修改 | setup/测试/标注各阶段耗时、失败候选数、美元成本 |
| 最终评测面 | Extended 150；Main 最难 100；Diamond 最难 50，彼此嵌套 | 难度估计使用的模型、重复数、排序方法与不确定性 |
| 单题质量校准 | 故意错误/不完整解、正确替代解、四份目标分数覆盖 0–100% 的解 | 每题实际尝试次数、各类解是否重叠、最终校准集 |
| 评测采样 | 每个可用 effort 跑 5 次，然后取该模型最优 effort 的均值成绩 | 各格有效轨迹数、缺失/超时/异常剔除与重复运行明细 |

这些是来源中不同层级的计数，不能把 36 仓库、150 题、每题四个校准解与评分图中的 45 rollouts/task 合成一个未经披露的总数据量。[Results；How we built FrontierCode][TEXT]

### 3.2 分布图：正文概括必须带对照对象和输入组成

**语言。** [原始语言 SVG][LANG]比较 FrontierCode Extended **150 题**、DeepSWE **113 题**与 SWE-bench Pro **731 题**，按任务数归一。FrontierCode 可见主要标签为 Python 13%、Go 10%、TypeScript 19%、JavaScript 15%、Java 13%、C/C++ 15%；图中还有小类别色块但没有完整可读标签。本文不由颜色猜出所有语言，也不从四舍五入比例恢复逐语言题数。原文“语言数为 SWE-bench Pro 的三倍”属于其统计主张，不能只由可见六个标签独立验证。

**题面长度。** 图显示的是中位**字符数**，不是 tokenizer token 数：[原始 SVG][PROMPT]

| 文本对象 | 中位字符数 |
|---|---:|
| SWE-bench Pro | 3,098 |
| DeepSWE | 1,975 |
| FrontierCode：任务描述 + codebase guidelines | 2,056 |
| FrontierCode：仅任务描述 | 982 |

横条是 p25–p75，不是置信区间。原文“三分之一”的解释，对应 $982/3098\approx31.7\%$；加上代码库指南后约为 $2056/3098\approx66.4\%$，且略长于此图的 DeepSWE。**不能把仅任务描述的长度，写成 agent 全部提示输入的长度。** 这是读者按图中数值计算，不是额外采样研究。

展开的三个例子也完整阅读：SWE-bench Pro 的 qutebrowser 任务详细规定 ELF/Qt 版本提取步骤、异常与精确字符串；DeepSWE 的 tomlkit 转换任务规定四个接口、原地修改、类型和注释迁移；FrontierCode 的 LOG_WARNING 任务规定目标接口与行为，同时附测试、lint、基准分支规则。三者是不同任务的展示，不是将同一道题改成长短 prompt 的控制变量实验。[完整比较状态][PROMPT-CASE]

**补丁大小。** [原始 SVG][PATCHSIZE]统计 golden patch 的 added+deleted lines 和 touched files：

| 数据集 | 行数中位数 | 文件数中位数 |
|---|---:|---:|
| SWE-bench Pro | 94 | 4 |
| DeepSWE | 642 | 6 |
| FrontierCode | 308 | 6 |

FrontierCode 的行数小于此图的 DeepSWE，但大于 SWE-bench Pro。由此不能说它“小于所有既有 benchmark”，也不能从参考补丁长度恢复 agent 的执行时间。作者选择用质量要求而非单纯补丁规模提高难度；是否确为难度的独立原因，本篇没有同题消融。

**短题面的适用边界。** 原文期望模型像人类贡献者一样从代码和指南推断维护者意图。读者分析：要求可以简洁，但必要验收依据必须可从任务、代码或约定中获取；否则隐藏偏好可能变成 false negative。这不是反对质量要求，而是要求区分合理推断和事后增加要求。

### 3.3 五阶段 QC：真正的工程资产是成组校准解

[流程图][QC]和正文一致地包含：

1. **Design**：可确定性验证的性质优先用执行测试；软质量适合明确的 prompt 评分；每条 rubric 写出理由。
2. **Hack report**：由作者扮演懒惰/对抗性程序员尝试错误高分解，同时写正确但不同于 canonical 的解查误杀；还让 Devin 寻找漏洞。
3. **Rubric calibration**：作者写四种解，目标覆盖不同分数档，而不仅验证 gold 和空补丁。
4. **Review**：先由 pod lead 与作者迭代，再由 Cognition researcher 联合审查；研究员对随机子集自己解题以检查描述和公平性。
5. **Re-review**：任何阶段可退回，多数任务多轮修改。

其思想是对一组解的相对质量排序进行校准，而非把每条解孤立地判真/假。**四份解不是统计保证，维护者专业性也不自动消除主观性。** 作者没有公布完整校准解、独立盲审和 inter-rater agreement，因此该流程是可借鉴方法，不是可直接复现的质量认证。

<a id="grading"></a>
## 4. pass、score 与六种评分方法

### 4.1 blocker 门控与质量分是两个层级

原文定义：清除所有 blocker 才 pass；通过后再对 rubric 项作加权聚合，否则 score=0。blocker 不限于功能正确性，也可能是性能或范围；non-blocker 可以包含风格、类型安全和可读性。[Results；Beyond Unit Tests][TEXT]

用读者符号表示这一文字规则：

$$
P_i=\prod_{j\in B_i}\mathbf 1[\text{criterion}_{ij}\text{ passes}],\qquad
S_i=P_i\,Q_i.
$$

其中 $Q_i$ 是该任务的 rubric 加权聚合，**原文未给完整权重、连续评分到阈值的映射及归一化公式**。以上是语义表达，不是假称作者给出的编号公式。pass rate 是 $P_i$ 的平均，score 是 $S_i$ 的平均；低 score 不等于同数值比例的任务完全没解对。用 5 次平均不是 pass@5 的“至少一次成功”。

如果后续用于训练，最终门控会使多个失败方案同为零。是否保存 diagnostic subscore、训练使用哪个目标，是新增训练设计问题；本篇没有比较不同奖励或证明该 score 是最佳 RL 目标。

### 4.2 原文评分矩阵完整整理

| 质量维度 | 方法名称 | 作者描述的执行 | 通过条件 | 阅读边界 |
|---|---|---|---|---|
| 行为正确性 | `classical` | 注入测试文件，运行，再清理 | 注入测试全通过 | 测试/辅助配置怎样保护、如何隔离，未给实现 |
| 机械整洁、回归 | `command` | 执行 shell 命令 | exit code 0 | 要知道该命令真正收集并执行了什么；不能泛化为任意命令成功都等价完成任务 |
| agent 测试质量 | `reverse-classical` | 把 agent 提交的测试运行在 base commit 上 | 测试失败 | 失败原因、collector 状态及 candidate 上的结果需要另查，见 §5.1 |
| 多种合法实现下的行为正确性 | `adaptive classical grading` | LLM 适配参考测试或应用代码 | 适配后测试通过 | 整条评分并非纯确定过程；适配是否保持语义未给公开实现 |
| 修改范围 | `scope` | 文件规则、改动量限制、可选语义局部性 | 满足约束 | 有显式规则不等于题面已充分披露，也不等于越小越好 |
| 代码质量 | `prompt` | LLM 对 diff 与自然语言标准评分 | 达到阈值 | judge 模型、prompt、重复和标定未披露 |

本篇的测试目标是评价结果，不描述训练 policy、value model、采样 logprob、IS、token mask 或梯度。上述词语不应因常用于 RL 而自动映射成作者已训练了对应组件。

## 5. 三个新增评分技术：方法与条件分开

### 5.1 Reverse-classical：base 上失败是必要线索，不是充分证明

作者将“agent 的测试在原始坏代码上失败”作为测试有效性的自动检查。这是有价值的方向，但仅凭非零退出码，不能区分真实行为断言、语法错误、找不到接口、环境启动失败或未收集到测试。原文没有逐项披露这些状态如何区分，也没有说明何种组合规则确保提交测试在候选解上通过。[Novel Grading Methods][TEXT]

**读者建议而非原文实现：**至少保存 base/candidate 上的测试收集、具体失败、退出原因和依赖条件，并要求测试确实针对需求发生变化。存在新接口时，base 的导入失败是否算有效回归测试，要按接口契约解释，不能一律接受或一律排除。恒失败的测试不能仅靠“base 失败”获得质量奖励。

示例 rubric 的 r10 写的是恢复到 base 后运行 **reference tests**，而概述说运行 **agent-submitted tests**。这两种测试来源不同，§6 单独记录；不能用一个例子证明通用 agent 测试质量检查已经完整公开。

### 5.2 Scope：files / size / semantic 分别承担不同约束

`files` 允许指定许可、拒绝或必须删除的文件；`size` 约束行改动、净增量或文件数；`semantic` 用 LLM 判断某一函数/区域内的改动性质。第三项不是纯文件系统规则，不能将全部 scope 检查称为 deterministic。

限制修改范围可以避免无关重构，但修复根因有时需要越过表面报错位置。是否把范围要求设为 blocker，是任务作者的判断而非通用常量。对于训练/评测迁移，必须说明模型能否从输入知道这些限制，以及合法扩展修复是否被误杀。

### 5.3 Mutagent：放松表面匹配，不能悄悄替 solver 修 bug

作者允许 LLM 对测试环境，甚至应用代码作精细调整，解决函数名、错误文案等表面差异，再执行测试。这与完全固定的测试 harness 不同。最终测试可以确定性运行，**不意味着适配步骤及整体评分是确定性的**。[同节][TEXT]

原文没有公开 mutagent 的模型、prompt、修改权限、补丁差异、参考解可见性、成本或独立消融。不能将其直接认定为安全的语义等价转换器。

**设计层候选：**若采用，应将 solver patch、grader adaptation patch、测试版本和前后结果分开留存，检查是否只改了表示/接口兼容，而没有补齐本该由 solver 实现的逻辑。它不是当前可信评分所必需的组件；只有固定测试的误杀确实来自实现表象时，才值得支付额外复杂度。

<a id="example"></a>
## 6. LOG_WARNING：全部展示补丁与十条 rubric 对账

### 6.1 输入与代码变化

题目来自 C++ `jsonschema` 仓库。目标是在 `src/logger.h` 实现不带参数、返回非 const `std::ostream &` 的 `LOG_WARNING()`；始终输出到 stderr，不受 `--verbose` 影响，自动输出 `warning:` 前缀，并替换代码库中的告警调用。附加指南要求相关测试、注册到 `test/CMakeLists.txt`、POSIX shell、构建/格式化检查，以及基于正确 base commit 建分支。[完整题面对象][TASK]

展示比较为 **Opus 4.8 medium** 与 **GPT-5.5 medium**。两个对象各包含八个文件，所有展示 hunk 已读取：

| 文件 | Opus +/− | GPT +/− | 共同或关键差别 |
|---|---:|---:|---|
| `src/command_bundle.cc` | +3/−2 | +13/−11 | Opus 只改首条 warning；GPT 捕获返回 stream 并将后续各行经同一引用输出 |
| `src/command_lint.cc` | +2/−2 | +2/−2 | 将 verbose-only unknown-rule warning 改用新 helper |
| `src/command_validate.cc` | +4/−3 | +4/−3 | precompiled schema 与 empty JSONL 告警改用 helper |
| `src/logger.h` | +5/−2 | +8/−2 | 两者均引入 iostream 和 helper；一行返回表达式与多行实现不同 |
| `src/resolver.h` | +1/−2 | +4/−4 | Opus 保留续行 `std::cerr`；GPT 将所有续行写入返回引用 |
| `test/CMakeLists.txt` | +1/−0 | +1/−0 | 注册新增 unknown-rule 测试 |
| `test/lint/fail_lint_disable_unknown.sh` | +36/−0 | +36/−0 | 新 POSIX shell 测试，核预期告警与其他 lint 文本 |
| `test/validate/pass_jsonl_empty.sh` | +1/−0 | +1/−0 | 增加 empty JSONL warning 期望 |
| **总计（元数据与行类型复核一致）** | **+53/−11** | **+69/−22** | 三个测试文件的展示内容相同，不据此推定它们的生成或注入来源 |

这些是官方展示 JSON 中的 patch hunks，不包含完整仓库、base hash、所有工具交互或原始测试日志。没有将它们当成可直接应用的标准 unified diff，也没有运行编译来重新判定 pass。[两模型展示对象][CASES]

### 6.2 十条 criterion 逐项保留

| ID | 简要内容 | Blocker | Opus | GPT |
|---|---|---|---|---|
| r1 | resolver 构造函数的多行 warning 均用 helper | 是 | fail | pass |
| r2 | bundle `without-id` 多行 warning 均用 helper | 是 | fail | pass |
| r3 | helper 的参数、返回 stream 与 prefix | 否 | pass | pass |
| r4 | lint 单行 warning | 否 | pass | pass |
| r5 | schema template 单行 warning | 否 | pass | pass |
| r6 | empty JSONL warning | 否 | pass | pass |
| r7 | 指定仓库构建命令成功 | 否 | pass | pass |
| r8 | clang-format 检查 | 否 | pass | pass |
| r9 | checkout reference 测试和 CMakeLists，再 make | 否 | pass | pass |
| r10 | 除 reference tests 外恢复 base 后 make 失败 | 否 | pass | pass |

这里的 blocker 只有 r1/r2；不要根据常识把 r3 或构建成功擅自改为 blocker。作者认为混用 helper 与 `std::cerr` 虽然当前外部行为一致，却泄漏了“返回的一定是 stderr”的假设；未来 helper 改动会破坏封装。GPT 的 stream reference 做法满足这一评价标准。[rubric 原数组][RUBRIC]

它展示了质量标准如何区分行为等价实现，但不意味着这种偏好对任意仓库都必须一票否决，也不证明 Opus 在此类问题上普遍不如 GPT。只有两份精选 medium 输出，没有完整重复结果。正文所谓“consistently”是作者额外陈述，本包未提供足够逐次数据检验。

### 6.3 两处必须保留的展示口径差异

**失败后的分数。** JSON 给 Opus `verdict="fail"`、`reward=0.2357`；界面取 `Math.round(100*reward)`，显示 **Fail · 24%**。它确实有两项 blocker 未过，却不是正文规定的最终 score=0。GPT 是 pass、reward=1。**原文未解释 reward 是未门控中间分、旧版本分还是其他展示值。** 本稿并列保存，不将 0.2357 改成正式成绩，也不由它反推十条 rubric 的权重。

**测试来源。** r9/r10 明确写 reference tests；通用 reverse-classical 的说明是 agent submitted tests。展示补丁又含测试文件。来源未说明这些三者怎样组合，不能在记录中消除其 provenance 差别。

### 6.4 “Run eval”不实际调用 grader

所给官方网页 chunk `af0a88ae1fd72ef7.js` 把两套文件和结果直接存入数组。按钮以 `setInterval(...,110)` 逐步展示 `files.length + rubric.length` 个单元，最后显示固定 verdict/reward；该回调没有执行测试或请求后端评分。**本轮只是静态查看代码，没有执行下载的 JavaScript。**

网页文案写“run the grading pipeline”，而实现是预置演示。它可用于理解 patch 与 rubric 的对应，但不能证明用户点击时生成了模型输出、运行了测试，或复现了 scanner/评分器。此限制不意味着作者没有真正的内部 grader，只意味着它没有通过该交互页面公开。[网页脚本][SCRIPT]

<a id="results"></a>
## 7. 结果、重复与误判证据

### 7.1 发布图表与数据快照

公开 [data.json][DATA] 有 12 个模型、31 个 model–effort 组合和 3 个 subset，共 **93 条聚合记录**。`new_score`、`correct` 分别对应页面 score、pass rate；其他字段为 tokens、cost、duration_min、tool_calls、steps、ote。图中的 Output tokens 是平均生成量，不是 trainer token，也不是 GPU 吞吐；`ote` 的定义没有在本篇正文解释，不由字段名猜测。

下表按每个 subset 的最大 `new_score` 选择 effort，数值取快照，单位为百分比；不是本轮重跑成绩。括号写 effort：

| 模型 | Diamond score | Main score | Extended score |
|---|---:|---:|---:|
| GPT-5.4-mini | 4.58 (xhigh) | 17.82 (xhigh) | 36.01 (xhigh) |
| Claude Sonnet 4.6 | 3.51 (xhigh) | 15.07 (high) | 33.56 (high) |
| GPT-5.5 | 6.31 (medium) | 25.48 (xhigh) | 44.76 (high) |
| Claude Opus 4.7 | 5.21 (medium) | 22.96 (xhigh) | 43.24 (xhigh) |
| Claude Opus 4.8 | 13.42 (xhigh) | 34.27 (xhigh) | 51.79 (xhigh) |
| Gemini 3.1 Pro | 4.67 (low) | 16.68 (high) | 34.23 (low) |
| Gemini 3.1 Flash Lite | 0.65 (low) | 4.84 (low) | 14.60 (low) |
| Kimi K2.5 | 1.00 (none) | 6.86 (none) | 22.69 (none) |
| Kimi K2.6 | 3.77 (none) | 16.04 (none) | 37.01 (none) |
| MiniMax M2.5 | 1.08 (none) | 5.34 (none) | 15.78 (none) |
| MiniMax M2.7 | 2.38 (none) | 5.98 (none) | 19.86 (none) |
| SWE-1.6 | 2.48 (none) | 5.50 (none) | 18.38 (none) |

正文的 13.4/34.3/51.8、6.3、3.8/16/37 等近似值与此相容。`none` 是源字段，不是未运行；effort 不同也不等于同推理预算。每个模型在每个 subset 可以选不同 effort，不是先选一个 effort 再对三个集统一评估。

**Harness 不是统一控制变量。** JSON 显示 OpenAI 为 Codex、Anthropic 为 Claude Code、Google 为 Gemini CLI、Kimi/MiniMax 为 mini-swe-agent、SWE-1.6 为 Devin。没有完整 harness revision、工具清单、budget、temperature、模型精确 revision 和错误重试合同，故榜单是模型与系统组合的比较，不是隔离权重能力的实验。

按各自 Diamond 最佳 score 点，Opus 4.8 约 70,008 output tokens，GPT-5.5 约 15,027，二者比约 4.66；effort 不同，不能当作同预算比较，输出 token 更少也不自动代表总费用/延迟更低。正文“up to 4x fewer”的概括不应变成普遍或精确比例。SWE-1.6 的 token/cost 等字段为 null，其他数个模型也无 cost，**不能把 null 当作 0，或用另一版本补齐**。

### 7.2 误判图：81%具体在比较什么

[原始 SVG/PNG][ERRORFIG]的图例是 **蓝色 False Positive（通过但实际错误）**、**橙色 False Negative（失败但实际正确）**。文本抽取的数值顺序先橙后蓝，不能按读取顺序互换两列。横轴是 *Share of analyzed trajectories (%)*，不是明确以所有真实错误解为分母的传统统计 FPR。

| Benchmark | rollouts/task 标注 | FP：蓝 | FN：橙 |
|---|---:|---:|---:|
| SWE-Bench Pro | 3 | 36.0% | 6.8% |
| DeepSWE | 5 | 44.9% | 1.2% |
| Terminal-Bench 2.0 | 5 | 6.8% | 5.9% |
| Terminal-Bench 2.1 | 5 | 5.6% | 2.8% |
| FrontierCode | 45 | 6.9% | 4.1% |

读者算术：相对 SWE-Bench Pro 的 FP，$1-6.9/36=80.83\%$，支持导言的约 **81% lower false positive rate**。若按图中同一“已分析轨迹份额”相加 FP+FN，再比较 11.0 与 42.8，则约为 **74.3%**，不是 81%。正文另一处写更宽泛的“81% less misclassification errors”；本稿保留这一措辞范围差别，而不静默将它解释成同一统计量。

图也显示 FrontierCode 的 FP 不低于两种 Terminal-Bench，FN 不低于 DeepSWE/Terminal-Bench 2.1。因任务、模型和抽样可能不同，这既不能推出哪个 benchmark 普遍更好，也不支持把它写成所有维度全面最优。缺失完整模型/effort、题目数、人工真值协议、抽样条件和误差区间，无法独立验证总体排名准确性。

“45 rollouts/task”是该误判审查图的口径；正文评测协议“每 effort 五次”是另一个口径，不能自行补成九个模型或其他分解。所谓误判是相对于采用的评审标准，而不是绝对程序真理。

## 8. 预算、开放性与复现程度

生产需要维护者和研究人员多轮投入；原文单题超过 40 小时，没有完整人工、模型/API、容器或评测美元账本。图表 JSON 的 cost 是每次运行费用字段，不是 benchmark 建设成本，计费服务、discount/cache 等合同也未在本篇充分说明。

论文式“训练增益”“RL sample efficiency”“GPU-hour”均不是本篇的实验证据。没有公开训练集、模型更新脚本，也没有可据此估计本项目八卡训练预算的配置。

**作者明确暂不公开任务，以降低污染，同时向模型开发者开放评测。** 公开的是方法、排行榜聚合和少量精选例子，不是完整 150 题及其镜像/测试。不能把 FrontierCode 直接列为 RepoHarness 可自行部署的 held-out 或训练题源；完整访问、可重复执行和使用条件需另行确认。[Conclusion][TEXT]

## 9. 证据边界与原文留白

| 问题 | 来源实际支持 | 仍不能推出 |
|---|---|---|
| 可合并性 | 维护者定义并校准六类标准 | 独立盲测证明所有通过解都会合并 |
| 81% | 对图示 SWE-Bench Pro 假阳性份额的相对下降 | 所有误判、所有 benchmark 均下降81% |
| 简短题面 | task-only 中位982字符 | 全部agent输入仅有前代三分之一 |
| deterministic grading | 部分执行检查可确定运行 | 含LLM适配和prompt评分的整个pipeline完全确定 |
| reverse-classical | base上测试应失败 | 任意测试失败都证明有效；示例reference等同agent测试 |
| mutagent | 允许适配测试/应用代码 | 已公开语义保持、权限边界、模型/预算和消融 |
| blocker | 定义清楚；实例给出两项 | 所有正确性项都是blocker；示例reward已按门控处理 |
| 结果 | 5次/effort的协议描述和聚合表 | 全部有效分母、误差条、未见模型调参独立性、最新榜单 |
| 运行资产 | 预置代码/结果与公开聚合 | 点击网页实际运行内部评测或可复现内部grader |

模型参与任务难度筛选、rubric打磨和最终测试的关系未充分披露。它们之间可能有合理的分工，但不能由本篇确认不存在自适应测试选择偏差。本稿不扩读引用树来替作者补齐这些字段。

<a id="project"></a>
## 10. 对 RepoHarness A/B 两线的意义

映射日期 2026-09-14；基线为 miles/SGLang、真实 coding harness 与 rh2。以下是**设计候选，不是已经批准或实现的项目功能**。

**B 线最值得先复用的是校准方法，而非整套重型 rubric。** 对现有小批任务，在 gold/no-op 之外增加少量真实替代解和故意不完整解，检查是否能区分有效修复、回归、接口表象与隐藏偏好。保留每条 criterion 的依据和失败证据，先定位测试漏洞与误杀，不必立即引入专有 mutagent 或收费人工评审规模。

| 候选 | 可复用的来源思想 | 最小验证与边界 |
|---|---|---|
| 固定测试的双向QA | 错误解、合法替代解都测试 | 原scorer与rh2同题同补丁对照；环境/collector失败不能冒充预期F2P |
| pass与质量诊断分开 | blocker门控与non-blocker | 保留原始检查事实和最终score，明确哪个值进入训练；不要从网页raw reward复制实现 |
| 测试provenance | reverse-classical与示例r10差别 | 标清reference/agent/adapted tests，记录base和candidate各自执行结果 |
| 范围与软质量 | files/size/semantic | 硬边界需有输入依据；先用作诊断，不把所有风格意见一票否决 |
| 限定的适配评分 | 接受表面不同的合法解 | 只有固定测试确实误杀时考虑；solver与grader补丁独立留痕、检查没有代修 |

**A 线的责任不是决定哪种解可合并，而是正确运输B给出的事实和分数。** 行级reward、最终门控score、状态与错误类别应能区分；某个评分中间值非零，不表示任务已经通过。是否用密集分数训练是另一个实验，不能由此评测博客自动批准。

此文也提供一个对简历有用的工程叙事：正确性不只是防作弊，还包括避免把合法答案判错。但要用本项目真实对照证明收益，不能继承作者“81%”作为自己的质量数字。

后续版本的联网规则、75项blocker降级和Diamond停止报告，见 [FrontierCode 1.1笔记](cognition_frontiercode_1_1.md)。它们是协议变化，不能当作模型训练增长。

## 11. 快速定位与关联

- 数据规模、语言、题面、补丁 → §3，[原文 Why / How][WEB]及五幅SVG。
- scoring、reverse、scope、mutagent → §4–5，[方法正文][TEXT]。
- LOG_WARNING完整展示与差异 → §6，[rubric][RUBRIC]、[patch/result][CASES]、[播放代码][SCRIPT]。
- 模型/effort/预算与误判 → §7–8，[聚合数据][DATA]、[原始误判图][ERRORFIG]。
- 关联已有来源：[SWE-2](cognition_swe2.md)、[SWE-1.7](cognition_swe1_7.md)。它们可说明训练团队怎样使用评测，不能替本篇恢复未公开trainer或grader。

## 12. 检查与状态

正文、全部已给图表和展开案例已读；作者自查完成，未做独立review、真实模型评测或沙箱执行。自查包含颜色图例、原始数值、全部展示行、评分字段、计时播放机制、JSON范围和字节级交付检查。[完整记录](reviews/cognition_frontiercode_self_check_20260914.md)

[WEB]: https://cognition.com/blog/frontier-code
[PACK]: source_supplements/cognition_20260911/README.md
[TEXT]: source_supplements/cognition_20260911/frontier-code/reading_text.md
[VIS]: source_supplements/cognition_20260911/frontier-code/VISUAL_INDEX.md
[DATA]: source_supplements/cognition_20260911/public_data/data/frontier-code/data.json
[ERRORFIG]: source_supplements/cognition_20260911/frontier-code/assets/01.svg
[LANG]: source_supplements/cognition_20260911/frontier-code/assets/02.svg
[PROMPT]: source_supplements/cognition_20260911/frontier-code/assets/03.svg
[PATCHSIZE]: source_supplements/cognition_20260911/frontier-code/assets/04.svg
[QC]: source_supplements/cognition_20260911/frontier-code/assets/05.svg
[PROMPT-CASE]: source_supplements/cognition_20260911/frontier-code/states/prompt-comparison.txt
[TASK]: source_supplements/cognition_20260911/frontier-code/embedded/array-27385.json
[RUBRIC]: source_supplements/cognition_20260911/frontier-code/embedded/array-576.json
[CASES]: source_supplements/cognition_20260911/frontier-code/embedded/array-2002.json
[SCRIPT]: source_supplements/cognition_20260911/web_scripts/af0a88ae1fd72ef7.js
