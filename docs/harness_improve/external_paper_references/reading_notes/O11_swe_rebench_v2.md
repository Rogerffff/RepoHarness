# O11 SWE-rebench V2：真实 PR 环境生产、质量诊断与开放资产精读（arXiv v2）

SWE-rebench V2 将仓库级安装合成、逐任务修复前后测试、题面审查和诊断标签连成一条多语言任务生产线，发布 **32,079 个带预构建镜像的任务**，另提供 **120K+ 个较低置信度的 PR 派生任务**。在 103 仓库的安装实验中，同为 Qwen3-Coder-480B，交互式 32K 配置的 pass@1 为 25.8%，固定流程为 12.1%；但这不是模型修复能力的训练增益。论文明确**没有端到端 RL 训练消融**。最值得借鉴的是安装复用、编译后重新构建、逐测试解析、真实数据漏斗及质量标注校准；最需保留的限制是残余题面／测试问题、PR 描述泄漏、质量标签与可学习性的区别，以及公开 builder 不等于可直接作为隔离可靠的 RL reward 服务。

导航：[来源与覆盖](#source) · [生产流水线](#pipeline) · [安装与质量实验](#experiments) · [求解诊断与统计](#diagnostics) · [成本和开放实现](#assets) · [项目判断](#mapping)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**论文 P。** Ibragim Badertdinov、Maksim Nekrashevich、Anton Shevtsov、Alexander Golubev，Nebius，*SWE-rebench V2: Language-Agnostic SWE Task Collection at Scale*。v1 提交于 **2026-02-27**，本次主读 **v2，2026-06-01**，阅读日期 **2026-09-07**。[版本入口][P-abs]、[v2 PDF][P]、[v2 HTML][PH]。这里区分作品名称的 **V2** 与 arXiv 修订号 **v2**；没有全文比较 v1，不将本次发现全部称作“v2 新增”。原文标为 CC BY 4.0；本文是注明出处的中文转述、表值整理与分析，不是原文译本或作者认可的说明。

**覆盖。** v2 PDF 共 **24 个物理页**；正文 §1–6、致谢、Impact Statement、附录 **A、B、C** 均已读。附录 A 的提示词在 HTML 中多处只剩标题，本次通过 PDF 提取文本补齐，不能用 HTML 的空白断言作者未提供提示词。参考文献检查了条目与尾部完整性，未逐篇扩读引用论文。论文没有自身的 RL/SFT 优化阶段，因此没有另造 loss、group、staleness 或 teacher–student 配方。

**原始图表核查边界。** 正文 Tables 1–7、附录 B 的 Figures 1–2、附录 C 六个结果面板均取得 PDF 截图并核对；正文数值与 v2 HTML/PDF 文本交叉核查。附录 A.1 的 v2 Tables 8–9 已逐行读取文本；其中 **Table 8 所在物理页 12 的一致 v2 图页未成功取得**。一次备用截图返回了不同分页、仅六行的旧式 repo-filter 表，本稿没有把它当成 v2 Table 8 的图像验收。此处保留图页复查项，不影响已取得的表格文本，但不声称所有 24 页都已逐页目视核完。§8 另记录真实图中可直接看到的图注与分母问题。

**配套代码 C。** 官方 [SWE-rebench/SWE-rebench-V2][C0]，固定提交 **`c71902a8cf8d2b725f63d51f199f4d3e56f68d2d`**，提交日期 **2026-03-12**，早于论文 v2。检查范围是 README、目录树、实例 Dockerfile 生成入口、模板、完整评测入口和两份相关标注模板，详见 §10。不将这个提交认作已经确认的全部实验 revision，也不因代码内容较多便替论文补写实验过程。

**数据 D。** 实际读取两份官方 Hugging Face 数据卡、文件树与页面样例：[主集][D1]、[PR 派生集][D2]。文件树给出的版本入口分别为 `475dd5e8703bb5fb22dd3c60b5d038b019eba1e0` 与 `40faf2c1bb160de625f3c3270ac9d62ea45f3f9c`；其 commit 详情/API 未成功取得，故它们只是本轮页面显示的版本定位，**不是全量 parquet 已下载核验的证据**。没有拉取 Docker 镜像、运行安装／求解或下载完整数据；没有原始 TeX 和本地 PDF 成功下载产物。

**项目与旧稿。** 项目读取基线为 `Rogerffff/RepoHarness@miles-migration` 的 **`9f93eb64b63f04723c62432fe18027e80b0c15b0`**。按 [Codex 阅读反馈](reviews/15_O01_codex_quality_review_20260907.md) 处理图表、代码范围和并行文件所有权。本篇新建 O11；目录中没有已有 O11 独立稿，旧索引仅作为来源导航，不沿用其他 SWE-rebench 访谈／旧版数据集的成本数字。对照 [E5 SWE-smith](E5_swe_smith.md) 与 [O03 R2E-Gym](O03_r2e_gym.md) 的相关段落只用于文末关系定位，不声称本次重读了那两篇完整原文。

### 1.1 按原文建立的覆盖表

下表页码采用 v2 PDF 的物理页及印刷页；无法取得一致图页的部分已单列，不能由“全文已读”替代图像核验。

| 原文范围 | 实际内容与处理 | 本笔记位置 |
| --- | --- | --- |
| 摘要、§1，pp.1–2 | 全读：训练环境短缺、交付资产、language-agnostic 定义 | §2–3 |
| §2，pp.2–3 | 全读：benchmark、setup、训练语料、自动标注与合成路线的区别 | §2、§12 |
| §3.1–3.2，pp.3–4 | 全读：PR、许可、测试拆分、repo 选择、安装代理、编译与解析 | §3–4 |
| §3.3–3.7，pp.5–6，Table 1 | 全读，Table 1 目视：双态执行、三次重跑、三 judge、PR 扩展、数据漏斗和成本 | §3、§5–6、§9 |
| §4.1，pp.6–7，Table 2 | 全读并核原表：103 仓、10 次安装、模型／上下文／交互对照 | §4 |
| §4.2，pp.6–8，Tables 3–5 | 全读并核原表：1,699 人工标注、prompt、模型、ensemble 的独立实验 | §5 |
| §4.3，pp.7–8，Tables 6–7 | 全读并核原表：300 题七模型、A/B* 诊断、三类失败与下游建议 | §6–7 |
| §5–6、致谢与 Impact，pp.8–9 | 全读：未做训练消融、依赖漂移、单容器覆盖限制、未来方向、许可及资助 | §2、§9、§11 |
| References，pp.9–11 | 检查引用身份与尾部；未逐篇扩读 | §1 |
| A.1，p.12，Tables 8–9 | 全部表值已读；Table 8 的一致 v2 图页仍待补核 | §3.2、§4.2 |
| A.2，pp.12–13，Listing 1 | 全读 Julia base Dockerfile；不把创建用户等同实际降权执行 | §4.1 |
| A.3.1–A.3.3，pp.13–17 | 全读 base/setup/parser 提示词，恢复 JSON 字段、工具预算与测试规则 | §4.1、§4.3 |
| A.3.4–A.3.5，pp.18–19，Listing 2 | 全读问题生成提示和 ExUnit parser 示例 | §4.3、§6.2 |
| A.3.6–A.3.8，pp.19–23 | 全读 A/B1–B7、难度、接口抽取、完整 clarity rubric | §5–6 |
| B，pp.23–24，Figures 1–2 | 目视完整四子图；保留近似量级和图注／统计分母问题 | §8 |
| C/C.1，p.24 | 六面板全部核查，包括 SEM、95% CI、pass@3、负下界与粗粒度总表 | §7.3 |

<a id="pipeline"></a>
## 2. 核心问题：生成可用于学习的环境，不是报告一种新的 RL 方法

作者关注三个串联条件：依赖安装正确、测试能稳定执行、自然语言要求与测试 oracle 对齐。语言无关指 **同一构建流程可以用于不同生态**，其中仍依赖少量按语言复用／生成的 base image、runner 和 parser。它不是每个语言零适配，也不是将所有工程差异交给一个完全通用 exit-code grader。[P §1–3, pp.1–4][P3]

本篇有两层证据：一层是确实生产出任务、镜像和诊断资产；另一层是安装策略、质量 judge 和现有模型求解行为的实验。**“适合作为 RL substrate”是目标和前提性验证；“用它训练出了更好的 agent”在本篇没有对应实验。** §5 明确说未进行端到端 RL 消融，只验证任务可执行、非平凡、有 pass@k 空间，且诊断标签能区分不同任务子集。[P §5–6, pp.8–9][P8]

### 2.1 两类交付不可混成同一规模

| 对象 | 原文交付 | 本轮数据卡补充 | 不能顺手推导的结论 |
| --- | --- | --- | --- |
| 主集 issue-based | 32,079 任务，3,617 仓库，20 语言；带预构建镜像 | `nebius/SWE-rebench-V2`，32,079 rows、仅 train split、文件树约 429 MB | 32,079 条训练轨迹、每题对当前策略都可学、已通过本项目安全边界 |
| PR-derived 扩展 | 120,000+ 任务，复用安装／测试 recipe、F2P 和 metadata；作者明确 lower-confidence | `nebius/SWE-rebench-V2-PRs`，126,300 rows、仅 train split、约 2.69 GB | 全部带预建实例镜像、与主集同等三次稳定性/清晰度保证、两集天然无重叠 |
| 求解诊断集 | 五语言各 60 题，共 300 题；七模型，每题三次 | 论文中的固定规模实验 | 全部 20 语言的均衡能力评测、全库逐题由七模型验收 |
| 安装对照集 | 103 个任务，各自来自不同仓库；每配置 10 次运行 | 既有 benchmark 的人工安装结果作参考 | 与上述 300 题同一集合、训练用 solver 数据集 |

主集加 PR 集的名义数量不能直接当作无泄漏、无重复、同质量的训练规模。需要实际按 instance、PR、commit 与派生关系检查；这属于后续使用条件，不是本次已做的数据审计。[P §3.6、§4.1、§4.3][P5]；[D1][D1]、[D2][D2]。

## 3. 从 GitHub 历史到冻结任务的五阶段流水线

### 3.1 来源、链接与 solution/test 拆分

从 GitHub Archive 汇总 issue/PR 描述、讨论、commit、license 和主要语言。分布式 map-reduce 克隆仓库，从本地 git 历史抽取 diff，以减少逐实例 GitHub API 请求；不是声称全流程完全不使用 API。保留 permissive-license 仓库、已合并 PR、已解决 issue，并要求 PR 新增或修改测试。通过 PR 标题／描述中的 resolving 引用建立 issue–PR 关系。[P §3.1, pp.3–4][P4]

按文件名正则 `(?i)(test(?:ing|s)?|e2e)` 将 diff 分成非测试文件的 solution patch 和测试文件的 test patch。这个机制不是 AST 级语义拆分：某些语言在生产文件内放 inline tests，作者通过后续 B7 标签提示，而不是证明该正则已经排除这类混合内容。

### 3.2 先减少需要昂贵安装的仓库数

高资源生态采用 **至少 25 stars、15 closed issues**；长尾生态放宽到 **10 stars、1 closed issue**。在前者里，少数仓库承载大多数候选任务，因此用大约 20% 的仓库保留约 80% 的任务。这个比例描述 repo-based 筛选，**不是环境安装率，也不是全部语言的最终存活率**。[P §3.1；A.1 Table 8, p.12][P12]

Table 8 的严格筛选部分如下；括号中比例为原表四舍五入值：

| 语言 | 原始候选任务/仓库 | 保留任务/仓库 | 任务保留/仓库保留 |
| --- | ---: | ---: | ---: |
| Python | 184,558 / 10,548 | 152,161 / 2,144 | 0.82 / 0.20 |
| Go | 123,424 / 6,168 | 104,115 / 1,345 | 0.84 / 0.22 |
| TypeScript | 114,164 / 7,356 | 92,292 / 1,300 | 0.81 / 0.18 |
| JavaScript | 80,262 / 7,650 | 58,349 / 915 | 0.73 / 0.12 |
| Java | 75,114 / 3,574 | 64,805 / 795 | 0.86 / 0.22 |
| Rust | 49,703 / 3,325 | 39,397 / 530 | 0.79 / 0.16 |
| C++ | 41,905 / 2,425 | 35,099 / 478 | 0.84 / 0.20 |
| PHP | 29,130 / 2,607 | 23,181 / 492 | 0.80 / 0.19 |

该表另列 Scala 23,248/913、Julia 14,347/922、C 13,608/1,193、Kotlin 13,003/913、R 9,368/619、Dart 8,792/579、Swift 7,457/809、Elixir 6,621/563、Clojure 4,815/189、OCaml 3,089/201、Lua 2,990/243；这些行的任务与仓库保留比均为 1.00。表共 19 行，不能把它补写成最终 20 语言的完整数量表；最终数据卡包含 C#。Table 8 数值已按 v2 HTML/PDF 文本核对，图页限制见 §1。

### 3.3 全流程漏斗：哪些分母对应什么问题

下表完整保留原文 Table 1。PR 列在末段表示已形成的任务实例，不能与实际 agent rollout 数混用。[P Table 1, p.5][P5]

| 阶段 | PR/任务数 | 仓库数 | 主要含义 |
| --- | ---: | ---: | --- |
| 原始 PR | 29,511,758 | 145,306 | GitHub 历史候选，不是全部尝试过构建 |
| 有测试变更 | 8,593,722 | 101,958 | 具备抽取测试 oracle 的线索 |
| 同时链接 issue 且有测试 | 805,598 | 50,797 | 题面来源约束显著缩小池子 |
| Repo-based filtering | 583,809 | 21,692 | 进入本轮 setup/验证范围 |
| 成功且具有 F2P | 41,349 | 4,006 | 安装、执行、解析与非空 F2P 的组合结果 |
| Issue text filtering | 33,049 | 3,701 | 三 judge 清晰度筛选后 |
| 三次验证稳定 | 32,079 | 3,617 | 最终主集 |

本文算术：41,349/583,809 ≈ **7.08%**，32,079/583,809 ≈ **5.49%**；33,049→32,079 的最后一步保留约 **97.06%**。它们分别以进入 repo-filter 后的任务候选、或前一阶段存活任务为分母，不能称作从任意新仓库开始的一次安装成功率。4,006/21,692 ≈18.47% 与作者“单次 setup 大约 20% 仓库成功”的描述相容，但它也包含后续 F2P 要求，不能据此恢复纯安装失败分解。

§3.3 在执行验证段介绍三次重跑，Table 1 将稳定性行放在 issue-text 筛选之后。本稿按表记录统计顺序，不额外推定每个原始候选具体跑了几次、每次是否独立重建整个镜像。

## 4. Setup、编译、测试与 parser 的实际关系

### 4.1 仓库级合成复用，任务级执行重新验证

先用 **Qwen3-Coder-480B-A35B-Instruct** 生成按语言划分的 base Dockerfile。大型生态提供多个主版本，如 Java JDK 11/17/21。随后在每仓“本次采集到的 PR 中 merge time 最新的任务快照”上合成一份安装与测试 procedure，复用于该仓其他历史任务。**这个快照不是无条件的当前 default-branch HEAD。** 历史 toolchain 差异是作者明确承认的失败源及多快照重试方向。[P §3.2、§3.7, pp.4–6][P4]

安装 agent 使用 **mini-SWE-agent v1.14.4 + Qwen3-Coder-480B-A35B-Instruct**。它查看代码/README/CI、尝试安装、观察错误、迭代修正。成功是测试能够运行且没有依赖／基础设施错误；测试在未修复版本失败可以是正常情况，不要求初始全部通过。

附录的 setup prompt 虽称执行器 non-interactive，指的是**终端命令不应等待交互输入**，不是否认模型能根据执行反馈继续调用工具。最终 `install_config.json` 主要提交 `install` 与 `test_cmd` 两项；后续流水线再附加 base image/parser。提示中出现“three fields above”的措辞，但示例只展示两项，不能因此发明第三字段。[P A.3.2, pp.14–16][P14]

附录还给出具体执行约束：优先 lockfile 和标准包管理器、选择正确 monorepo root、关闭颜色而保留逐测试 verbose 输出、构建日志尽量安静、单次工具显示上限 64 行／每行 500 字符、依赖和缓存准备完整、缺少私有凭据时报告不能完成、只将最终必要命令留在配置中。允许为测试环境修订配置，但这不自动证明对测试 oracle 的完整性无影响。

Julia 示例使用 `julia:1.10-bookworm`、linux/amd64、基础编译工具和 `/workspace/.julia` 缓存。示例创建 nonroot 用户却没有展示 `USER nonroot`；不能将其当作实际执行已降权的证明。它是 base image 示例，不是论文的完整沙箱安全配置。[P A.2、Listing 1, pp.12–13][P12]

### 4.2 安装消融：测的是能否复现参考 F2P 集

103 个任务分别来自 103 个唯一仓库，来源为 SWE-bench、SWE-bench-multilingual、Multi-SWE-Bench。作者将人工安装说明转成同一 pipeline 格式，在同一 base images 上验证参考 F2P；自动 setup 的**成功标准为产生的 F2P 集与参考集完全一致**，不是仅编译成功或 exit code 为零。每配置进行 10 次独立运行，Table 2 报告 pass@k。[P §4.1, pp.6–7][P7]

A.1 Table 9 的类别分布为 Python55、JS11、JS/TS6、Ruby6、Go5、C5、Rust5、Java4、PHP4、C++2，共103。作者称十种语言；其表中 JS 与 JS/TS 分列，且 Python 占过半，不能称为十语言等权或全部二十生态的无偏验证。

| 安装策略/模型 | context | pass@1 | pass@3 | pass@5 | pass@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| Non-interactive，Qwen3-Coder-480B | 未另列 | 12.1 | 14.2 | 14.9 | 15.7 |
| mini-SWE，Qwen3-Coder-30B-A3B | 32K | 17.4 | 30.5 | 36.9 | 46.1 |
| mini-SWE，DeepSeek-V3.2 | 32K | 20.3 | 37.3 | 46.6 | 59.8 |
| mini-SWE，Qwen3-Coder-480B-A35B | 32K | 25.8 | 42.4 | 50.0 | 58.8 |
| 同上 | 64K | 26.8 | 43.1 | 49.2 | 55.9 |
| 同上 | 128K | 27.1 | 44.4 | 52.2 | 62.7 |

单位均为 %。Non-interactive 基线也有**固定三阶段**：读指定文件列表、生成命令、按错误日志修订；不是完全没有反馈的单次 prompt。交互式 30B 超过固定流程480B，是这一特定环境准备实验的结果，不等于30B软件修复全面更强。480B 32K 的25.8%对12.1%是在相同模型、任务和base images下的比较，但总token与工具调用未等成本锁定。

更长 context 的收益不单调：64K 的 pass@10 55.9 低于32K的58.8，128K则62.7；不能简化成“长上下文没用”或“越长越好”。作者认为32K足以处理多数安装任务，并列出循环、无关细节、toolchain版本、native依赖、monorepo路径、凭据、异构日志、过早收敛等失败。本次主生产仅每仓一次setup，是作者选择的成本—产出折中，**不是论文证明一次尝试普遍最优**。

### 4.3 测试必须跑新二进制，解析必须识别具体测试

在 base_commit 上应用 test patch 并跑**完整项目测试套件**，再加 solution patch 重跑。至少一个测试从失败变为通过才保留；重复三次结构化结果不变，降低 flaky 噪声。编译语言需要在应用补丁后显式 rebuild，避免执行旧二进制造成假的F2P。JVM生态优先JUnit XML，因为stdout中的测试顺序、名字可漂移。[P §3.2–3.3, pp.4–5][P5]

Qwen3-Coder-480B 还承担仓库级 **log parser 生成**：从没有基础设施错误的测试日志生成解析器，再用于同仓其他任务；不适用时用新日志最多迭代五次。多数生态一到两个parser够用，CTest/GoogleTest/Catch2等更异质。提示要求标准库实现、稳定且可区分参数化实例的test ID、返回每测试状态、剥离ANSI等；同名多次结果按提示采用最后出现状态。提示只列 `PASSED/FAILED/SKIPPED`，不能从正文泛称“error”推定发布schema一定另有第四状态。[P A.3.3, pp.16–17][P16]

Listing 2 的 ExUnit 示例先将普通执行行暂记PASSED，再以failure header覆盖；后续普通pass使用 `setdefault`，不会反过来覆盖已知失败。**示例的失败优先行为与通用提示的last-occurrence规则需要按具体runner核验**，不能把提示等同可执行保证。该例调用 `re` 和 `TestStatus`，不是一个包含所有依赖声明的自足程序。[P A.3.5, pp.18–19][P18]

完整套件和非空F2P提高了可验证性，但不证明测试覆盖全部需求、合法替代解必被接受、评分资产不可见或oracle不能被干预。三次稳定也只是有限运行中的稳定性观测，不能保证新硬件、新并发和未来依赖条件下一直确定。

<a id="experiments"></a>
## 5. Issue clarity：标注基准、ensemble 与部署决策应分别记录

### 5.1 标注来源与实际输入

校准数据来自 SWE-bench 的 **1,699 个实例，每题三名人工标注者**。其中 well-specified 评分为0–3：0/1认为足够明确，2/3认为信息不足；最终人工标签取三人分数的**最大值**，不是多数票。该人工集还含测试有效性和难度标注，但本文这组实验使用的是issue clarity，不能把结果扩写成已同时校准测试覆盖和所有语言质量。[P §4.2, pp.6–7][P7]

主生产的三judge为 **gpt-oss-120b、GLM-4.7、DeepSeek-V3.2**，仅在三者都认为描述足够时保留。Verified-E 将原始gold patch和test patch也给评审器，用来检查“只给issue和代码库的工程师是否能理解任务”。这是**生产标注端的特权信息**，不等于应把这些字段交给policy。[P §3.4、§4.2；A.3.8][P22]

### 5.2 Prompt 消融（Table 3）

| Prompt | Accuracy | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| Rebench V1 | 0.67 | 0.76 | 0.22 | 0.34 |
| SPICE | 0.66 | 0.59 | 0.34 | 0.43 |
| Verified | 0.68 | 0.75 | 0.24 | 0.36 |
| Verified+ | 0.69 | 0.66 | 0.40 | 0.50 |
| Verified-E | 0.65 | 0.83 | 0.10 | 0.17 |

Verified+ 是用GPT-5.2改写原rubric、增加提示；不是用GPT-5.2作为该行独立新solver。Verified-E增加patch上下文。作者因为重视precision，选择Verified-E用于流水线；**它不是F1最佳项**，其recall仅0.10。原文表格未显式写二值化实现的positive label及完整混淆矩阵，本文保留指标名称，不擅将0.83改写成“保留集83%无问题”或“全部坏题检测准确率83%”。[P Table 3及邻文, p.7][P7]

### 5.3 Judge 模型消融（Table 4，全用 Verified prompt）

| Judge | Accuracy | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| gpt-oss-120b | 0.68 | 0.75 | 0.24 | 0.36 |
| gpt-oss-120b high | 0.66 | 0.81 | 0.16 | 0.26 |
| DeepSeek-V3.2 | 0.66 | 0.76 | 0.18 | 0.29 |
| GLM-4.7 | 0.64 | 0.81 | 0.10 | 0.18 |
| MiniMax-M2.1 | 0.59 | 0.59 | 0.16 | 0.25 |
| GPT-5.2 | 0.67 | 0.80 | 0.18 | 0.30 |
| Gemini 3 Pro | 0.57 | 0.92 | 0.05 | 0.10 |
| Claude Opus-4.5 | 0.67 | 0.83 | 0.16 | 0.27 |

作者使用各模型默认参数，high为单列条件。最高precision对应极低recall，不能拿一个指标直接决定模型适合所有过滤任务；也不能把这里的GPT-5.2、Gemini 3 Pro与§7求解实验的GPT-5.2 medium、Gemini 3 Flash当成完全相同配置。[P Table 4, p.7][P7]

### 5.4 Ensemble 消融（Table 5，全用 Rebench V1 prompt）

| 设置 | Accuracy | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| Single model | 0.67 | 0.76 | 0.22 | 0.34 |
| Mixed average | 0.69 | 0.73 | 0.31 | 0.43 |
| Mixed consensus | 0.64 | 0.88 | 0.06 | 0.11 |

混合模型为gpt-oss-120b、GLM-4.7、DeepSeek-V3.2；作者结论是平均聚合更均衡，一致同意适用于优先precision的目标。**Table 3的Verified-E、Table 4的Verified、Table 5的Rebench V1不是同一个实验条件**。论文没有给出可直接读取的“最终Verified-E + 三judge一致同意”联合混淆矩阵，不能乘加这些数字预测最终数据质量。[P Table 5, p.8][P8]

完整rubric在A.3.8，仍写“open-source Python repositories”；四档示例是 `examples[0..3]` 模板占位，PDF没有展开实际few-shot题目。本文未找到该标注系统在全部20语言上的分语言人工校准，也没有逐实例敏感信息筛除的完整审计结果；不以“language-agnostic”补齐这些证据。

## 6. Metadata 与 PR 派生：诊断信息不等于训练收益

### 6.1 A/B1–B7 的用途与限制

作者分析七模型求解轨迹后，用 **gpt-oss-120b** 对任务赋予诊断metadata。A.3.6输入包括repo、issue、test patch和golden patch；输出含意图完整度、错配说明、多个布尔flag、一个primary code、confidence、external URLs、PR categories和difficulty。不是每个任务都由七模型重新求解后才产生标签。[P §3.5、§4.3、A.3.6][P19]

| Code | 原文名称 | 含义与容易误解的边界 |
| --- | --- | --- |
| A | SOLVABLE | 题面与测试看起来对齐；不是对某个策略必能解出的证明 |
| B1 | TEST_SUITE_COUPLING | 修复目标却导致其他路径回归；原文明确这可能是**合法P2P要求**，并非一定是坏测试 |
| B2 | IMPLICIT_NAMING | 测试依赖题面未说明的具体名称、签名等 |
| B3 | EXTERNAL_DEPENDENCY | 关键信息在未引用正文的外部URL，可能缺失、变动或需认证 |
| B4 | AMBIGUOUS_SPEC | 缺少预期行为、复现步骤或验收条件 |
| B5 | PATCH_ARTIFACTS | 参考修复含无关变动，而测试可能连带依赖 |
| B6 | IMPLICIT_KNOWLEDGE | 所需领域知识未在题面说明且无法从仓库推得 |
| B7 | INLINE_TEST | 普通solution文件中包含测试逻辑，文件级patch拆分不足 |

difficulty按预计人工实现时间：easy<15分钟、medium15分钟–1小时、hard>1小时。它不是经过当前30B模型采样估计的pass probability。12类PR标签为critical/major/minor/regression/edge_case/performance/security bug，integration/core/ui_ux feature，dev_ops/documentation enhancement；可多选，不能默认各类构成严格互斥划分。

作者提出先用A类作SFT/RL warm-up、后加B类训练鲁棒性、部分任务用partial credit、B3可配浏览工具。这些是**用途建议和未来训练设想**；本篇没有训练这套curriculum，没有证明简单排除所有B标签能最大化泛化收益。特别不能为了提高通过率删除正确的P2P回归约束。[P §4.3–5, pp.8–9][P8]

**接口补充。** A.3.7仅抽取新建/签名变化且被新测试明确调用的函数或类，包含名称、signature、location、输入/输出要求和简述；排除未被测试调用的内部helper、type alias、enum、常量等。它意在补足隐含命名要求，但利用了测试与参考patch。将生成interface加入agent输入，会改变题面信息条件，应与原始issue-only运行分开；不能称为不影响难度的纯格式修复。[P §3.5、A.3.7, pp.21–22][P21]

### 6.2 PR 派生任务怎样扩容，泄漏审计究竟测了什么

主集生产成功后，回到这些仓库的普通PR，复用安装／测试recipe以摆脱必须链接issue的限制。§3.6明确：**合成题面条件是原PR描述加对应patch**，不是只复制PR原文。摘要与相关工作有较简略的“from PR description”表述，本稿保留更具体的方法描述，不把两种输入当成两项已验证方案。[P §3.6, p.5][P5]

A.3.4要求用用户可观察的行为描述问题、期望与验收标准，禁止代码、文件/符号/行号/commit定位、具体算法/控制流程/数据结构等实现线索；允许概念性根因假说。还使用额外post-processing筛可疑题目，但完整规则、成本和逐阶段拒绝率未披露。这些要求只能降低泄漏风险，不证明题面无答案。

在 **509 个从SWE-bench Pro PR构建的任务**上，用LLM judge比较生成题面与原参考problem statement、requirements、interfaces：

| 判断 | 数量/分母 | 原文比例 |
| --- | ---: | ---: |
| Clean | 392/509 | 77.0% |
| 某种程度泄漏 | 117/509 | 23.0% |
| 其中明确solution leakage | 12/509 | 2.4% |

12例是泄漏集合中的更严重子类，不应将三个比例相加。此审计的judge身份、判级细则、样本如何代表完整126,300条以及人工复核没有充分披露。它说明PR-derived是**更大但lower-confidence的训练资源**，不是所有发布PR任务都经过同一独立人审，更不是2.4%泄漏率适用于所有新合成器的保证。[P §3.6][P5]

<a id="diagnostics"></a>
## 7. 现成模型求解诊断：原模型不更新权重

### 7.1 设置与 Table 6

从Python、JavaScript、Go、Rust、Scala各随机取60题，共300题，七模型每题三次独立运行，名义上为6,300次求解尝试；不等于收集出6,300条合格训练轨迹。harness为mini-SWE-agent、各模型默认generation参数，GPT-5.2单列medium。§3.2明确setup用v1.14.4，但求解评测没有完整另给scaffold revision、context/turn/wall-clock、网络规则、失败重跑和全部模型服务revision。[P §4.3, pp.7–8][P7]

| 模型 | Python | JS | Go | Rust | Scala | pass@1 | pass@3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Claude Opus-4.5 | 36.1 | 26.7 | 15.0 | 28.9 | 19.4 | 25.2 | 32.7 |
| GLM-4.7 | 27.2 | 26.1 | 17.2 | 24.4 | 11.7 | 21.3 | 26.7 |
| MiniMax-M2.1 | 26.1 | 26.1 | 15.6 | 20.6 | 7.8 | 19.2 | 27.0 |
| Gemini 3 Flash | 25.6 | 25.0 | 11.7 | 21.1 | 7.2 | 18.1 | 27.7 |
| DeepSeek-V3.2 | 23.3 | 24.4 | 12.2 | 21.7 | 5.6 | 17.4 | 25.0 |
| GPT-5.2 medium | 20.6 | 24.4 | 11.1 | 21.7 | 7.2 | 17.0 | 25.0 |
| gpt-oss-120b | 8.9 | 13.3 | 9.4 | 9.4 | 2.8 | 8.8 | 14.3 |

均为百分比，来源[P Table 6, p.8][P8]。这是五语言等题量子集，不按全库语言比例加权，也不是当前2026-09最新模型榜。pass@3表示多次尝试至少一次成功，不是三次全成功率。作者看到可提升空间及跨语言差异，不能据此证明“这些任务对所有学生都提供良好GRPO组方差”。

### 7.2 A 与 B* 子集（Table 7）

作者在语言、改动文件数和行数分布相似的A/B*任务上比较，原文说“sampled 60 tasks from Code A and B* categories”。**没有清楚说明60是两组合计还是每组，本文不写成60+60=120，也不从百分比倒推另一种样本量。**[P §4.3、Table 7, p.8][P8]

| 模型 | A pass@1 | A pass@3 | B* pass@1 | B* pass@3 |
| --- | ---: | ---: | ---: | ---: |
| DeepSeek-V3.2 | 22.0 | 26.0 | 4.0 | 4.0 |
| Gemini | 26.0 | 34.0 | 0.0 | 4.0 |
| GLM-4.7 | 28.0 | 34.0 | 4.0 | 6.0 |
| GPT-5.2 | 14.0 | 26.0 | 4.0 | 6.0 |
| Opus-4.5 | 22.0 | 28.0 | 6.0 | 8.0 |

观察支持这些标签在该样本中区分不同求解成功率；它不是随机修改同一道题后的因果实验，也不是A类训练优于B类训练的证据。A也可能与未完全匹配的难度相关；B1又包含真实回归要求，因此不能直接将全部A/B分差归为“环境坏了”。

### 7.3 附录 C：不能用总榜掩盖误差

C.1的分语言面板每组60题，报告pass@1、SEM、95% CI和pass@3。下面完整保存所有模型的 **SEM / CI / pass@3**，pass@1的精细值在原面板与§7.1四舍五入值对应。所有数字均为百分比，方括号为原文区间；并非本文重算。[P C.1, p.24][P24]

| 语言 | 模型 | pass@1 | SEM | 95% CI | pass@3 |
| --- | --- | ---: | ---: | --- | ---: |
| Go | GLM-4.7 | 17.22 | 4.38 | [8.65,25.80] | 23.33 |
| Go | MiniMax-M2.1 | 15.56 | 4.15 | [7.42,23.69] | 23.33 |
| Go | Opus-4.5 | 15.00 | 3.92 | [7.33,22.67] | 25.00 |
| Go | DeepSeek-V3.2 | 12.22 | 3.88 | [4.62,19.82] | 16.67 |
| Go | Gemini | 11.67 | 3.25 | [5.30,18.04] | 21.67 |
| Go | GPT-5.2 | 11.11 | 3.23 | [4.77,17.45] | 20.00 |
| Go | gpt-oss-120b | 9.44 | 3.55 | [2.48,16.41] | 11.67 |
| JS | Opus-4.5 | 26.67 | 5.42 | [16.04,37.29] | 31.67 |
| JS | MiniMax-M2.1 | 26.11 | 5.14 | [16.04,36.19] | 35.00 |
| JS | GLM-4.7 | 26.11 | 5.44 | [15.45,36.77] | 30.00 |
| JS | Gemini | 25.00 | 4.99 | [15.22,34.78] | 33.33 |
| JS | DeepSeek-V3.2 | 24.44 | 5.13 | [14.40,34.49] | 31.67 |
| JS | GPT-5.2 | 24.44 | 5.00 | [14.64,34.25] | 33.33 |
| JS | gpt-oss-120b | 13.33 | 3.65 | [6.18,20.48] | 21.67 |
| Python | Opus-4.5 | 36.11 | 6.20 | [23.95,48.27] | 36.67 |
| Python | GLM-4.7 | 27.22 | 5.46 | [16.52,37.92] | 31.67 |
| Python | MiniMax-M2.1 | 26.11 | 5.32 | [15.68,36.54] | 31.67 |
| Python | Gemini | 25.56 | 5.16 | [15.45,35.66] | 33.33 |
| Python | DeepSeek-V3.2 | 23.33 | 4.97 | [13.60,33.07] | 31.67 |
| Python | GPT-5.2 | 20.56 | 4.95 | [10.85,30.26] | 23.33 |
| Python | gpt-oss-120b | 8.89 | 2.84 | [3.32,14.46] | 16.67 |
| Rust | Opus-4.5 | 28.89 | 5.34 | [18.42,39.36] | 38.33 |
| Rust | GLM-4.7 | 24.44 | 5.25 | [14.16,34.73] | 30.00 |
| Rust | GPT-5.2 | 21.67 | 4.61 | [12.64,30.70] | 33.33 |
| Rust | DeepSeek-V3.2 | 21.67 | 4.47 | [12.91,30.43] | 33.33 |
| Rust | Gemini | 21.11 | 4.41 | [12.47,29.75] | 33.33 |
| Rust | MiniMax-M2.1 | 20.56 | 4.56 | [11.62,29.49] | 30.00 |
| Rust | gpt-oss-120b | 9.44 | 3.08 | [3.41,15.48] | 16.67 |
| Scala | Opus-4.5 | 19.44 | 4.29 | [11.04,27.85] | 31.67 |
| Scala | GLM-4.7 | 11.67 | 3.62 | [4.58,18.75] | 18.33 |
| Scala | MiniMax-M2.1 | 7.78 | 2.55 | [2.78,12.78] | 15.00 |
| Scala | GPT-5.2 | 7.22 | 2.52 | [2.29,12.16] | 15.00 |
| Scala | Gemini | 7.22 | 2.25 | [2.80,11.64] | 16.67 |
| Scala | DeepSeek-V3.2 | 5.56 | 2.26 | [1.12,9.99] | 11.67 |
| Scala | gpt-oss-120b | 2.78 | 1.64 | [-0.44,5.99] | 5.00 |

附录All面板的精度明显更粗：Opus **25/2/[21,30]/33**，GLM **21/2/[17,26]/27**，M2.1 **19/2/[15,23]/27**，Gemini **18/2/[14,22]/28**，DeepSeek **17/2/[14,21]/25**，GPT **17/2/[13,21]/25**，gpt-oss **9/1/[6,11]/14**（依次pass@1/SEM/CI/pass@3，单位%）。主表Opus25.2/32.7不应被这个粗粒度25/33无声替换。

原表Scala的gpt-oss区间下界为负，本稿照录并注明这是报告的统计区间，不是可能出现负成功概率；没有改成截断区间。论文未详述SEM/CI的构造和按任务／按重复如何聚合，也没有模型间配对显著性检验。分语言误差很大，不能把1–2个百分点差值直接写成稳定模型排序。

## 8. 附录图像检查：保留数量级，也保留图注问题

Figures 1–2均位于附录，不是正文方法架构图。[P B, pp.23–24][P23]

**Figure 1(a)** 横轴2014–2025、纵轴count。图内标题是“PRs by year”，子图说明是“Issue years”；目视2020/2021约4.1–4.2K，2022约5.2K，2023约6.2K，2024约7.1K，2025约3.9K。它提供采集年代结构，不能据2025较少就推断全年PR活动下降，也不能擅自认定字段一定是issue创建时间而非PR时间。

**Figure 1(b)** Python和Go最高，目视约8.0K、7.6K，随后JS/TS/Rust约4.6/4.3/3.8K，长尾显著。这里有分母缺口：正文称最终32,079题中Python21.6%，相乘约6.93K，并不等于图中约8K。本稿不把图反算成最终精确语言数量，也不猜它来自哪个更早筛选阶段；保留“图表统计cohort未解释”的问题。

**Figure 2(a)** 纵轴share，core_feat约41–42%、minor_bug约28%、major_bug/regression_bug各约10%，其余较小。metadata允许类别多选，图的归一化分母未进一步交代，不能当成严格互斥比例来重建任务数量。

**Figure 2(b) 的实际图是 Difficulty distribution**，横轴medium/easy/hard，纵轴share，目视约68–69%/26%/5%。但子图caption写“Diff sizes”，总图caption写“patch-size distribution”。这是原始PDF中可见的图内容—图注不一致；**图不能证明代码diff长度分布**。正文的median3files/34lines、p90 9files/181lines仍按正文保留，而不是从这张难度图推出。

这些近似量级来自原图目视，不是日志重算或精确数字化；正文有明确数值的地方仍以其原始口径单独记录。

<a id="assets"></a>
## 9. 成本：$1.9K 不是整个数据集的造价

原文§3.7的成本对象如下。[P §3.7, p.6][P6]

| 成本项 | 报告值及分母 | 应保留的限制 |
| --- | --- | --- |
| Setup agent覆盖 | 21,692仓，平均24.67个交互turn/仓，总约535K API calls | 不是agent训练rollout计数 |
| Setup token | **每仓轨迹**平均约214K input、966 output tokens | 原文就这样报告；不能擅改为每次API调用或966K；未拆缓存与完整计价细节 |
| Setup推理费用 | 代表性商业价格下约$0.0873/仓，合计约$1.9K | 仅setup inference；致谢列Nebius Token Factory credits，不等同实际现金账单 |
| 任务验证构建 | 583,809次Docker builds，均值2.71min，约26,400 **job-hours** | 不是CPU-core-hours、GPU-hours，也不是端到端墙钟时间 |
| 最终环境存储 | 32,079环境的Docker artifacts合计26.36TiB | 未给本地去重层口径、全库下载／缓存部署的确定成本 |
| 其他生产与评测 | 未完整披露 | PR/题面生成、三judge、metadata、parser迭代、七模型评测、人工、网络、存储服务及失败尝试不能遗漏 |

独立算术核对：21,692×24.67≈535,142turn，×$0.0873≈$1,893.71；583,809×2.71/60≈26,368.71job-hours，与原文近似值相容。26.36TiB/32,079≈0.841GiB/保留任务，只是把聚合存储平均分摊，不是每个镜像独占大小或每题边际存储需求。

相比SWE-smith的仓库固定版本合成，这里的历史任务环境包占用、toolchain变化与生产成功率是不同成本结构，不能只比“任务数/GB”而忽略任务定义、镜像共享与验证方式。论文没有给8×96GB训练预算，也没有目标模型训练时长，不能以setup代理的MoE激活参数估算本项目learner成本。

## 10. 开放代码和数据：能直接复用哪些环节

### 10.1 版本化实现范围

配套仓库明确自述builder：**标注模板、base/instance Docker生成、已有镜像上的任务评测**。它有复用价值，但不是包含GitHub Archive分布式采集、全流程自动安装代理服务、三judge聚合、三次稳定性重跑和RL trainer的完整一键生产平台。本文只将实际检查到的入口作为实现事实；没有据目录缺少某文件判断作者内部系统不存在。[C0][C0]

| 固定路径 | 本次检查的职责 |
| --- | --- |
| `README.md` | 输入、构建/评测命令、公开资产边界；例子的gpt-4.1-mini不是论文judge配置 |
| `scripts/build_instance_images.py` | 从JSON逐题渲染Dockerfile与build、tag构造、dry-run |
| `combine.Dockerfile.j2` | base image字段、clone/reset、安装命令、source与权限边界 |
| `scripts/eval.py`（全文） | JSON/HF读入、patch选择、镜像解析、容器执行、parser消费、结果与错误汇总 |
| `prompts/annotations/meta_info.j2` | 当前B1–B11及interface输入，与论文B1–B7的范围差异 |
| `prompts/issue_clarity_ablation/verified_extra.j2` | patch/test-aware rubric、0–3标签与占位示例，与A.3.8对应 |

未逐个审核全部语言parser、所有base image和每个task样例；重要逻辑以固定提交、完整路径和符号定位，不扩成通用整库审计。

### 10.2 Builder 成功与可训练环境成功不是同一件事

[C1 `build_instance_images.py`][C1] 使用Jinja渲染 [C2 `combine.Dockerfile.j2`][C2]，其输入base字段为 `spec.install_config.image_name`。模板clone仓库、reset到base_commit、移除origin，再对每条install执行 `(cmd) || true`。因此 **Docker build退出成功不能单独证明所有安装命令成功**；仍要以有效测试执行验证环境。模板有两段FROM并复用base层，但不自动意味着所有安装中间产物已被最小化。

模板移除remote，不等于清理了未来git对象、其他refs或reflog；它没有展示完整history sanitization。`chmod -R 777`也不是隔离保证。这些是固定模板可见的边界，不是本次已证明发布镜像存在某项可被利用的漏洞。要把它用于真实agent，需要自己的runtime/grade隔离配置，而不是修改论文来声称作者已经做了这些防护。

### 10.3 评测入口的三个易误用语义

[C3 `scripts/eval.py`][C3] 的`main → evaluate_task → evaluate_instance → run_in_container → parser → build_report_item`是实际消费路径。它在fresh容器内reset HEAD，先应用候选patch再应用test_patch，执行`install_config.test_cmd`，解析逐测试状态。**它是已有oracle下的候选/黄金补丁评测，不是重新跑双态基线、抽取F2P再三次验真的完整采集流程。**

**一，缺失预测时可能回退gold。** `evaluate_instance`先取`spec['patch']`，仅在有override时替换；`evaluate_task`在非golden模式下用`patch_overrides.get(instance_id)`。所以没有`--patches`、缺少某instance预测，或override缺patch字段时，可能仍使用数据集gold。显式空patch会因缺patch检查报错，但**缺失预测不自动报错**。它服务golden环境验收是合理用途；直接拿不完整预测文件算模型成功率则有风险。此结论来自静态字段流，不声称论文模型结果使用了缺失预测。

**二，`passed_match`是严格集合/列表匹配，不只是所有目标测试通过。** parser的PASSED结果经计时字符串归一后排序，与`PASS_TO_PASS + FAIL_TO_PASS`排序列表完全相等才记ok。额外出现的passed测试也可能使其False。报告另列F2P通过交集、P2P缺失及exit_code；`main`的ok计数使用`passed_match`，没有另将exit_code直接作为必要条件。这个检查适合特定golden一致性用途，却不能未经定义就当成对所有合法模型修复都适用的唯一binary reward。

**三，公开CLI不是资源/网络安全规范。** `docker run --network host`，read-only挂载patch目录，但没有在该调用给出CPU/RAM/总timeout；`subprocess.run`也未设置timeout。HF加载路径尝试pull镜像、失败后继续尝试本地cache，完成后删除镜像。host网络、重复pull/rmi与无限等待不是论文RL配方；需要使用者按执行场景处理。结果保留error，但后续如何将环境error与模型失败分开，应由调用端明确，不能自动都写成reward=0。

### 10.4 论文、代码与数据字段并不完全同步

固定代码的metadata模板是 **B1–B11**：比v2正文多B8视觉上下文、B9非英文、B10文本fixture测试、B11多issue PR，且把生成interface拼入ISSUE_TEXT；论文A.3.6仅列B1–B7。代码日期更早也不能据此推定这些额外标签用于v2全部实验。非英文、视觉需求不天然等于坏任务，标签需要结合目标能力解释。[C4][C4]

本轮主集页面样例的`meta.llm_metadata.detected_issues`常只显示B1–B6，不能假定缺B7–B11就等于False或已检查。数据样例用 `install_config.base_image_name`，而模板读取`install_config.image_name`；**直接将当前HF row传给该builder需要字段适配验证**。主集顶层`image_name`则是实例镜像，与base字段不是同一项。[D1][D1]；[C2][C2]

`resolve_task_image`在HF路径要求顶层`image_name`；当前PR数据卡/预览没有此列。因此主集现成镜像评测入口不能无改动地套到PR派生集。需构建相应实例并提供正确image identity；不能仅凭都有install_config就称作开箱即用。[C3][C3]；[D2][D2]

### 10.5 数据卡的可见内容与许可

主集提供repo、base_commit、gold patch、test patch、issue、原PR描述、interface、image_name、F2P/P2P、install_config、metadata。PR集额外有pull_number、hints_text。**整行公开数据不是policy应该看到的任务面**：gold/test、原PR讨论、实现线索应与执行指令分开。数据卡标“train”仅是文件split，不等于作者替使用者完成了与所有外部评测的去重和时间切分。

原文说执行整项目suite，当前PR页面的若干monorepo样例却提供子包test_cmd；这至少要求明确“项目”的粒度。本次没有执行它们，也未据样例判断全部任务覆盖不足。主集页面还可见P2P空集合及个别占位式test ID；这些是复用前检查parser与oracle字段的线索，不是从十条预览估计全库错误率。

论文/数据卡为CC BY4.0，代码仓库为MIT；数据卡要求同时尊重每个原仓库在该commit的许可。部分预览license字段为`custom-check-github`而非明确SPDX，因此不能笼统称“每条都已由本次审核为可商用”。本文记录发布许可而不提供法律判定。预建镜像tag、代码commit、数据revision分别需要管理；tag包含commit缩写不等同内容digest固定。[D1][D1]、[D2][D2]、[C0][C0]

## 11. 最影响结论的未知与版本问题

| 问题 | 原文/资产状态 | 本次处理 |
| --- | --- | --- |
| 使用该语料训练后的收益、filtered/unfiltered curriculum消融 | §5明确未做 | 标记不适用，不补PPO/GRPO/OPD配方 |
| 最终过滤组合的positive class、联合混淆矩阵 | Tables 3–5条件不同，未充分披露 | 不把precision换成保留集纯度 |
| metadata校准到20语言、B类比例和人工误判 | 部分诊断与prompt，缺全量审计 | 不把A/B当真值或当前policy的difficulty |
| A/B诊断60题的分组分母 | 表文未清楚拆分 | 保留原文，不推120题或另猜样本量 |
| PR生成泄漏审计可迁移性 | 509题的特定LLM比较，未详述全部judge与样本协议 | 2.4%不推广到完整PR集或其他生成器 |
| PR集是否全部同主集三次稳定、镜像可用 | 交付等级不同，未完整披露 | 两类资产分开，不合并保证 |
| 全部训练/测试去重、污染和后续维护 | 作者承认公开历史可能被训练见过；时间过滤仅降低风险 | 不声称污染已消除 |
| $1.9K与26,400 job-hours | 两种局部成本，缺全流程账单 | 明确分母，不外推八卡训练 |
| Figure2(b)与caption、Figure1与最终比例 | 已目视确认存在不一致/未解释 | 图按实际轴说明，正文数值另存 |
| Table8完整v2图页 | 文本已读、稳定图页未取得 | 作者自查保留非阻塞复查项 |
| 数据完整revision下载、image digest、实际可重建性 | 文件树/卡片可访问，未全量下载或运行 | 不标独立复现或逐题验收 |
| 代码是否等同论文内部生产系统 | builder公开范围有限，commit未绑定实验 | 只按当前固定路径说明 |

§5明确列出三项限制：**没有端到端RL训练消融；Docker不能消除外部包源、系统包和网络资源的漂移；单容器设计限制了需要数据库、队列及分布式组件的真实多服务项目。** filtered/unfiltered curricula的直接训练比较仍待开展，周期性重建、环境更新和metadata修订也属于维护计划。§6提出增加setup重试、策展子集、长尾语言及多服务长程任务，并探索性能、latency、memory等非功能性目标；均不是已完成实验。Impact Statement另说明公开宽松许可仓库、凭据泄漏扫描及源仓库偏差的处理原则，不增加一项模型安全训练证据。[P §5–6及Impact Statement, pp.8–9][P9]

<a id="mapping"></a>
## 12. 对 RepoHarness 项目一的有限判断

映射日期2026-09-07，项目snapshot为`9f93eb64…`。依据[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)，当前为miles/SGLang+外部coding harness，rh2拥有可信输入、评分与训练消费边界；216题SWE-Gym Lite是候选资产，不是已经冻结的首训集合。本次只作设计层映射，未重新审计这些模块。

**本篇支持优先考虑复用已有生产资产，而不是为了简历规模立即自建二十语言工厂。** 与E5的“固定仓库状态后注入bug”、O03的“真实commit构环境并训练SFT模型”相比，O11的独立贡献是多语言真实历史生产、setup与质量校准实验、以及明确分级的任务资产。已有SFT结果属于E5/O03，不应转移到O11名下。

| 少量候选借鉴 | 条件与职责 | 最小辨识验证 |
| --- | --- | --- |
| 从主集抽小批真实仓库任务，复用镜像/recipe | 数据入口及fresh grading适配；不重写miles训练核心 | gold/no-op、三次重放、parser ID、资源/网络、历史与评分可见性逐项检查；记录有效题数和导入成本 |
| 对确实需要新增的仓库，复用repo-level setup并按失败类别重试 | 先有缺口；一次setup不能覆盖所有历史toolchain | 小规模固定预算比较一次尝试、重试、多快照；指标是新增可信任务/成本，而非API成功响应率 |
| 将A/B标签用于诊断采样，而非直接硬拒全部B | A不是训练收益证明，B1可能合法回归；已有强简单采样作为基线 | 先比较分层solve curve和审计误判，再决定是否做静态筛选/标签分层的训练对照 |

此时不需要把多语言、自动curriculum或新的reward列为完成项目一的前置条件。论文最能支持的个人工程叙事，是**把外部历史任务转换成可复现的本项目训练经验，并测清有效产出、评分语义与成本**。独立学习增益仍必须来自我们的实验，不能由32K任务规模或A/B成功率差代替。

## 13. 快速定位与作者自查状态

数据规模与筛选分母→§3/Table1；安装模型与重试→§4/Table2；三组judge实验→§5/Tables3–5；metadata与题面泄漏→§6/A.3.4–8；求解能力与统计→§7/Tables6–7/C.1；图形数量级与caption冲突→§8；生产成本→§9；实际构建/评测字段消费→§10。

本篇覆盖正文及全部附录文本，完成主要图表目视核对和有边界的官方代码检查。**状态：作者自查完成，待独立复查；Table8图页另待补核。** 没有独立sub-agent、没有训练/环境复现，也没有用代码静态阅读宣称实际触发gold fallback或误判频率。详见[O11作者自查记录](reviews/O11_self_check_20260907.md)。

本线程只维护这份O11笔记与其自查记录；共享README/catalog/批次状态由汇总线程登记。没有修改O01、其历史审查记录、训练代码或实施定案。

## 原始链接

[P-abs]: https://arxiv.org/abs/2602.23866v2
[P]: https://arxiv.org/pdf/2602.23866v2
[PH]: https://arxiv.org/html/2602.23866v2
[P3]: https://arxiv.org/pdf/2602.23866v2#page=3
[P4]: https://arxiv.org/pdf/2602.23866v2#page=4
[P5]: https://arxiv.org/pdf/2602.23866v2#page=5
[P6]: https://arxiv.org/pdf/2602.23866v2#page=6
[P7]: https://arxiv.org/pdf/2602.23866v2#page=7
[P8]: https://arxiv.org/pdf/2602.23866v2#page=8
[P9]: https://arxiv.org/pdf/2602.23866v2#page=9
[P12]: https://arxiv.org/pdf/2602.23866v2#page=12
[P14]: https://arxiv.org/pdf/2602.23866v2#page=14
[P16]: https://arxiv.org/pdf/2602.23866v2#page=16
[P18]: https://arxiv.org/pdf/2602.23866v2#page=18
[P19]: https://arxiv.org/pdf/2602.23866v2#page=19
[P21]: https://arxiv.org/pdf/2602.23866v2#page=21
[P22]: https://arxiv.org/pdf/2602.23866v2#page=22
[P23]: https://arxiv.org/pdf/2602.23866v2#page=23
[P24]: https://arxiv.org/pdf/2602.23866v2#page=24
[D1]: https://huggingface.co/datasets/nebius/SWE-rebench-V2
[D2]: https://huggingface.co/datasets/nebius/SWE-rebench-V2-PRs
[C0]: https://github.com/SWE-rebench/SWE-rebench-V2/tree/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d
[C1]: https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/scripts/build_instance_images.py
[C2]: https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/combine.Dockerfile.j2
[C3]: https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/scripts/eval.py
[C4]: https://github.com/SWE-rebench/SWE-rebench-V2/blob/c71902a8cf8d2b725f63d51f199f4d3e56f68d2d/prompts/annotations/meta_info.j2
