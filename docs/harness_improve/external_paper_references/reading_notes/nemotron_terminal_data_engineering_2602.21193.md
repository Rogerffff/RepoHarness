# Nemotron-Terminal：终端 Agent 数据工程、SFT 对照与环境复用边界

*On Data Engineering for Scaling LLM Terminal Capabilities* 研究的不是新 RL 算法，而是怎样生产终端交互数据并通过 SFT 提升 Qwen3-8B/14B/32B。Terminal-Task-Gen 将旧题适配与种子／技能合成分开，复用九个领域基础镜像，由 DeepSeek-V3.2 生成轨迹。TB2.0 的三个模型成绩分别达到 13.0、20.2、27.4；简单混合优于本文的两阶段 SFT，扩大上下文也未带来优势。最需保留的边界是：旧题适配集没有测试，合成任务不生成 oracle；“不过滤失败更好”的实验同时保留了更多数据，不能直接解释为失败内容的独立因果收益，更不能据此取消 RL 环境和 reward 的可信性检查。

导航：[来源与覆盖](#source) · [任务与环境](#data) · [训练与执行](#training) · [结果与消融](#experiments) · [开放资产与成本](#assets) · [项目映射](#project)

<a id="source"></a>
## 1. 来源、版本与阅读范围

**主来源 P。** Renjie Pi、Grace Lam、Mohammad Shoeybi、Pooya Jannaty、Bryan Catanzaro、Wei Ping，NVIDIA。正式标题 *On Data Engineering for Scaling LLM Terminal Capabilities*。arXiv **2602.21193v1**，首次提交 **2026-02-24**，PDF 首页日期 **2026-02-25**。2026-09-07 查询版本历史仅列 v1。使用 [摘要及版本历史][P-abs]、[v1 HTML][P-html]、[v1 PDF][P]；PDF 共 **24 个物理页**。本篇不是 Nemotron-Cascade 2、Nemotron 3 Ultra，也不是产生额外 6,170 个任务的 ECHO。

**实际阅读。** 阅读摘要、§1–6 全部正文、参考文献、Appendix A.1–A.3，并核查全部 **Table 1–10、Figure 1–20**。附录中的长提示词按输入、输出合同、约束和领域差别转述，不逐字搬运。原文没有展示具体 SFT loss 公式；本稿不从 veRL 的通用默认值补写。

**配套资产。** 读取 NVIDIA 官方 collection、两份数据卡及文件树、8B/32B 模型卡，核对 8B 发布文件与版本。资产 revision 与查阅边界见 §8。未下载全部任务包、Parquet 或权重，未执行容器、训练或评测。没有发现可直接对应本篇历史实验的完整生成／训练代码入口，因此本次不扩大为当前 Harbor、veRL 整库审计。

**项目读取基线。** `Rogerffff/RepoHarness@miles-migration`，读取时提交 **`9f93eb64b63f04723c62432fe18027e80b0c15b0`**。已读 [当前状态简报][RH-state]、[笔记模板][RH-template]、[O01 Codex 质量反馈][RH-review]。项目建议仅放文末。本线程只维护本篇及自查文件，不改共享 README、来源编号、批次状态或其他论文。该来源原未独立登记，暂以 arXiv 号命名，不占用并行任务的 N/R/E 编号；正式编号交汇总线程处理。

此前会话将这篇列为“简单混合／长上下文负结果”的线索，本次回原文补全两条数据路线、全部对照和附录；没有把旧会话摘要当论文证据。

### 1.1 原文覆盖与定位

| PDF 物理页 | 原文章节／图表 | 实际覆盖与本稿位置 |
| --- | --- | --- |
| 1–2 | 摘要、§1、Fig.1、Table 1 | 数据工程问题、双路线、发布主张；§2、§6 |
| 3 | §2、§3.1 | agent/harness、旧题适配及合成相关工作；TB2.0 定义；§2、§4、§6 |
| 4 | §3.2、§4、Fig.2–3 | 标准任务包与 Terminus 2 JSON 交互；§3–4 |
| 5–6 | §4.1、§4.2.1–4.2.2 | 三类 adapter、种子、技能组合和领域；§3 |
| 7 | §4.2.3、§4.3、Table 2 | 无 oracle、解法信息隔离、共享镜像、teacher 选择；§3–4 |
| 8 | §4.4、§5.1–5.2、Table 3 | 去污染、基础过滤、SFT 配置、infra、总分；§3、§5–6 |
| 9 | Table 4、§5.3–5.4 开头 | 全类别得失、数据构成、过滤；§6–7 |
| 10 | Table 5–8、§5.4–5.6 开头 | 样本规模、完成／成功过滤、上下文与 YaRN2；§7 |
| 11 | Fig.4、Table 9、§5.6–5.7、§6 | SFT 顺序、数据规模、结论与未来 RL；§2、§7 |
| 11–14 | References | 检查引用身份和正文／附录边界，不逐篇扩读引用文献 |
| 15 | Table 10、A.1、Fig.5、A.2 开头 | 九领域技能表、token 直方图、轨迹生成说明；§3、§5 |
| 16 | Fig.6、A.3 | turns 分布、模块化生成说明；§3、§5 |
| 17–18 | Fig.7–10 | Terminus system prompt 与 math/code/SWE suffix；§4 |
| 19 | Fig.11 | 合成 prompt 的结构、字段与约束；§3.3 |
| 20–24 | Fig.12–20 | 九个领域模块全部阅读，包括末页 system administration；§3.3 |

**编号以 PDF 为准。** HTML 中有几处跳转指向相邻错误编号：任务目录应为 Fig.2，不是 Fig.3；数据构成对应 Table 5，合成过滤对应 Table 7。A.3 文字称领域模块为 Fig.12–19，但实际另有 **Fig.20**。本稿保留最后一个模块，不让交叉引用错误形成漏读。

网页截图部分版本化入口失败后改用无版本 PDF；当时仍为同一 v1、24 页。完整 TeX 与容器内 PDF 下载本轮未成功，这属于获取限制，不是作者没有发布原文；PDF 文本、HTML 和关键图页已取得并阅读。自查记录见 [本篇检查文件](reviews/nemotron_terminal_self_check_20260907.md)。

## 2. 作者的问题与实际训练关系

### 2.1 核心问题是供给成本和数据选择，而不是新 scaffold 或新优化器

作者指出终端训练同时缺少题目、依赖文件和可用环境；每题重新实例化环境、多轮调用 teacher，又使轨迹生产昂贵。旧题适配容易扩量，但继承原题的静态问答结构；复杂多 agent 出题流程更灵活，却增加生产成本。本文选择简化任务生成和环境构建，并在同一个终端 scaffold 下比较数据策略。[P, §1–2, pp.1–3][P1]

§2 关于“基础模型增强后，复杂 scaffold 的边际收益可能降低”是作者展望，不是本文完成的模型规模×harness 复杂度消融。论文实际固定 Terminus 2，不能用它证明外部 harness 不重要。[P, §2–3, p.3][P3]

### 2.2 生产路线有层次，参数训练不应误画成两阶段

```text
已有 math / code / SWE prompts ──规则适配──────────┐
                                               │
种子问题（可有参考解）──LLM 生成新任务与测试───────┤
                                               ├─ DeepSeek-V3.2 + Terminus 2
领域 / primitive skills ──LLM 组合生成任务与测试─┘   在环境中生成轨迹
                                                    ↓
                                     去污染、基础质量过滤及可选筛选
                                                    ↓
                                          离线多轮 SFT 数据
                                                    ↓
                                  Qwen3-{8B,14B,32B} → Nemotron-Terminal
```

这是依据 Fig.1、§4–5 整理的流程图，不是额外算法。作者把数据生产称为 coarse-to-fine / two-stage，但推荐的参数更新方式是**把两大路线产生的轨迹混合，单阶段 SFT**。先 adapters、后 synthetic 的串行 SFT 是被比较且表现较弱的候选。[P, Fig.1；§4, p.4；§5.6–§6, pp.10–11][P11]

DeepSeek-V3.2 同时承担新任务生成和离线求解轨迹生成；目标 Qwen3 模型学习这些记录。未描述 student on-policy sampling、教师 logprob 对齐、KL 蒸馏或 RL policy update。**这是 teacher-trace SFT，而不是 OPD，也不是由测试奖励驱动的 GRPO。** §6 将 RL 明确列为未来延伸方向。原模型称谓保留 Qwen3-8B/14B/32B，不擅自改成从零预训练或声称具体 Base/Instruct checkpoint revision 已冻结。[P, §4.3、§5.1、§6][P8]

<a id="data"></a>
## 3. 两条数据路线：适配任务与可测试合成任务

### 3.1 Dataset adapters：便宜的是格式适配，不是全部数据生产

| 类型 | 原始来源与筛选层级 | 本篇的终端转写 | 必须保留的限制 |
| --- | --- | --- | --- |
| Math | Nemotron-Cascade Stage-2 math prompts；约 163K，来源 OpenMathReasoning；上游排除 DeepSeek-R1 回答少于 2K tokens 的容易题 | 原题加 suffix，在环境中工作，把答案写入 `/app/solution.txt` | 2K 是上游 R1 筛选条件，不是本篇 V3.2 轨迹长度阈值 |
| Code | Cascade Stage-2 的 79K OpenCodeReasoning prompts，再过滤／去重至约 35K | 用终端编写 Python，将答案保存 `/app/solution.py` | Table 5 最终样本为 31,960；从约 35K prompts 到这些样本的逐项损耗未披露 |
| SWE | Cascade SWE 的 127K instances，来自 SWE-Bench-Train、SWE-reBench、SWE-smith、SWE-Fixer-Train；再筛至约 32K unique prompts | 在环境中创建 prompt 给出的 buggy files；按 suffix 定位、修改并保存 `/app/solution.patch` | 给定文件内容不等于恢复完整原仓库、依赖和回归测试 |

依据 [P, §4.1, p.5；Fig.8–10, p.18][P5]。这里引用的 Cascade 是原文参考文献中的 **Nemotron-Cascade（2512.13607）**，不是以模型家族名继承 Cascade 2 的训练配置。

格式适配不需要 LLM：把原题填进 Terminus 模板，附对应指令并准备文件。但后续 teacher 在终端中生成交互轨迹仍需要 LLM、环境执行与存储。

**最关键的资产区别：§4.1.2 明说 adapters 只有 instruction 与 environment，没有配套 test cases。** 因而这类数据可以提供 SFT 行为示范，却不能因为被包装成 Terminal-Bench 风格目录，就称为已经具有可信二元 reward 的 RL 任务。后面的 adapter 实验也只比较 completion 筛选，没有 success-only 的测试筛选。[P, §4.1.2；Table 6][P10]

### 3.2 Seed-based synthesis：把原题作为灵感，重新生成可执行规格

Seed 包含问题描述、可选领域标签、可选参考解。生成模型加入具体路径、输入规模、安装要求、结果格式、数值精度和边界条件，并产生输入文件和 pytest。参考解存在时，只供生成者设计测试预期，不交给后续求解 agent。[P, §4.2.1, pp.5–6][P6]

它与 adapter 的区别不是“多一句提示”：adapter 主要保留原问题；seed route 重新构造 terminal task 和 tests。原文没有给全部 seed 来源、逐来源数量、生成重试率或人工验收漏斗，也没有证明每个新任务有独立正确解。

### 3.3 Skill-based synthesis：九个领域模块与 primitive skills 的组合

生成模型从终端技能分类中选择、组合，通常每题 **3–5 项**，避免只孤立考某条命令。正文把 primitive skills 概括为算法、系统、数据处理、数学、测试和 web/security 六类；领域 prompt 决定任务主题与约束。[P, §4.2.2, p.6][P6]

下面按实际附录 Table 10 与 Fig.12–20 整理全部领域模块，不把它们压成“合成一些 terminal 题”：[P, A.3, pp.15–16、19–24][P19]

| 附录领域 | 模块要求与技能组合的要点（转述） | 定位 |
| --- | --- | --- |
| Data Processing | 结构化格式转换、清洗与变换、聚合、时间序列／插值、可检查的数据处理链 | Table 10；Fig.12, p.20 |
| Data Querying | 理解数据关系并构造查询，连接／分组／窗口等处理、图或结构化检索、验证查询输出 | Table 10；Fig.13, p.20 |
| Data Science | 表格分析、统计和特征构造、算法与处理管线结合，要求实际结果而非只写分析说明 | Table 10；Fig.14, p.21 |
| Debugging | 从报错、日志、依赖或运行现象定位根因，再修正和测试；包含约束式依赖冲突分析 | Table 10；Fig.15, p.21 |
| File Operations | 文件 I/O、路径与目录、解析／转换、压缩归档、元信息及资源处理 | Table 10；Fig.16, p.22 |
| Scientific Computing | 数值／统计算法、科学数据处理与验证，涵盖精度、计算方法和结果一致性 | Table 10；Fig.17, p.22 |
| Security | 安全分析、密码／认证、系统与 web 安全、测试及漏洞验证；属受控任务生成范围 | Table 10；Fig.18, p.23 |
| Software Engineering | 实现／修改代码、依赖与图算法、构建、测试、接口和工程约束的组合 | Table 10；Fig.19, p.23 |
| System Administration | 文件权限、进程／服务、网络、配置、部署、自动化与 shell 脚本 | Table 10；Fig.20, p.24 |

**原文有一处领域名单不一致。** §4.2.2 列九域时写的是 **dependency management**，没有 system administration；附录九域与最终 Fig.20 则包含 **system administration**，没有单独的 dependency-management 模块。Debugging 中确有依赖冲突内容，但原文未解释两种名单是否合并或改名。本稿分别保留，不自行统一。

**通用生成合同。** Fig.11 的主模板接收领域模块、primitive skills 和 Dockerfile 上下文，要求输出任务说明、测试、权重、辅助信息、输入文件与测试依赖；对应结构标签为 `prompt / tests / weights / info / files / test_requirements`。它要求任务自包含、避免答案线索、技能非平凡组合、结果可验证，领域模块插入其第二部分。模板中的“新颖”“难解易验”是生成约束，不是已经测得的保证。[P, Fig.11, p.19][P19]

这是一套 **prompt-based、离线任务生产方法**。没有报告学习出题策略、solver-relative 难度后验、持续在线课程、生成者与求解者共同 RL，也没有按生成规则留出的组合泛化实验。

### 3.4 任务包、测试与共享镜像的责任边界

合成任务包含说明、可配置权重的 pytest、辅助输入文件和领域 Docker 环境。权重支持部分测试 credit，但本篇没有据此进行 RL，也未披露 SFT loss 随测试分数加权。测试在这里主要用于检查产物与筛选实验。[P, §4.2.3, p.7][P7]

**不生成 oracle solutions 是作者明确的设计选择。** 原因是自动生成可信 ground-truth code 而不经人工验证很困难。不要把 Fig.2 的标准 Terminal-Bench 目录里有 `solution/solve.sh`，解释成本文每个合成包都有通过验证的 oracle；也不要把原 seed 的可选 reference solution 等同于新任务的独立参考解。[P, Fig.2, p.4；§4.2.3, p.7][P4]

“Solution isolation”在本篇主要指生成上下文和 agent 可见任务说明之间分离解法信息：不给算法、实现路径或答案代码。没有完整披露 grader 主机权限、隐藏文件挂载时序、评分控制面隔离与对抗攻击实验。因此**prompt 不泄题、task 有测试、评分不可操纵**是三个不同问题。

九个预构建基础镜像避免为每题重新生成并修复 Dockerfile；环境配置与任务内容分离，agent 仍可安装额外 runtime 依赖。作者给出的收益是避免多轮 Dockerfile 修复、降低镜像与缓存负担、支持更快的单次任务生成；没有对应的构建耗时／总费用前后对照。[P, §4.2.3, p.7][P7]

**九个基础镜像不等于总共只运行九个容器，也不表示跨任务共用可变状态。** 实际 rollout 仍需要实例化隔离环境；论文没有公开每类镜像 digest、完整复用生命周期或所有成功构建数。共享镜像缩小了环境配置自由度，不能据此证明它覆盖任意真实仓库的依赖组合。

### 3.5 从 prompts 到样本：现有数字能恢复到哪一步

| 数据对象 | 已披露数量／单位 | 原文位置与限定 |
| --- | ---: | --- |
| Math 初始筛后 prompts | 约 163K unique prompts | §4.1.1；来自上游 Stage-2 |
| Code 候选 → 二次筛后 | 79K → 约 35K prompts | §4.1.1；精确逐项损耗未知 |
| SWE 候选 → 二次筛后 | 127K → 约 32K unique prompts | §4.1.1；不是 32K 独立完整仓库 |
| Adapter math/code/SWE 样本 | 162,692 / 31,960 / 31,661 | Table 5；合计 **226,313** |
| Seed-based / skill-based 样本 | 124,366 / 139,841 | Table 5；合计 **264,207** |
| 两大路线样本合计 | **490,520** | 本稿按 Table 5 加法所得，不是新增测量 |
| 基础环境 | **9 个领域基础镜像** | §4.2.3；不是 unique task 或运行容器计数 |
| 公开 Corpus rows | **366,154** | 官方数据卡／viewer，见 §8；不是完整论文混合规模 |

Table 5 的 `# Samples` 与 A.1 轨迹直方图的 N 对得上，故这里按**轨迹／训练样本**理解；不把它们自动改称去重后的任务数量、不同镜像数或有效梯度数。论文没有给“全部生成候选 → 构建成功 → 测试通过 → 去污染 → 基础过滤”的逐层数目，也没有给每题尝试次数与不同结果的对应关系。[P, Table 5, p.10；A.1, pp.15–16][P15]

### 3.6 “No filter”不等于完全不做质量处理

§4.4 先从 SFT 数据中移除与 **TB2.0 test samples 有 14-gram 重叠**的 prompt，再做基础质量过滤，包括身份泄漏以及含中文字符的响应。这里记录的是作者的英文数据取舍，不把“含中文”概括成跨语言项目的通用品质判据。[P, §4.4, p.8][P8]

其后的可选实验才是：只留 completed trajectories，或在有测试时只留通过测试的轨迹。Table 6/7 的 **No filter 应按“没有这层额外完成／成功筛选”理解**，不能用于支持取消去污染或把环境错误无条件纳入数据。

14-gram 的 tokenizer／规范化、去除量、语义改写重复、仓库及任务派生关系切分没有展开；不能称为完全无污染。complete 的精确日志字段、time/tool/context 中哪一种限制导致 incomplete、success 对部分测试分的阈值，也未给机器可重放定义。Terminus 的 `task_complete` 标记存在，不足以证明筛选只按这个字段执行。

## 4. Teacher、Terminus 2 与具体交互合同

### 4.1 Teacher 的三个验证结果不能误归到学生

DeepSeek-V3.2 负责生成新任务和执行轨迹。为了确认它在同类 terminal 接口下可用，Table 2 对其测试了适配后的数学、代码与 SWE benchmark：[P, §4.3、Table 2, p.7][P7]

| 原表 benchmark 行，pass@1（%） | DeepSeek-V3.2 |
| --- | ---: |
| AIME 2024, AIME 2025 | 93.33 |
| LiveCodeBench v6 | 67.20 |
| SWE-bench Verified | 52.40 |

AIME 在原表合为一行，本文不擅自拆成两项各 93.33，也不补计算平均方式。这些是**teacher 选择证据**，不是 Nemotron-Terminal 学生在三类外部 benchmark 上的迁移结果。Table 3 的 teacher TB2.0 为 38.2±2.9，也不表示所有自动生成轨迹都正确。

### 4.2 Terminus 2：单 tmux 工具面，JSON 可一次包含多条命令

Agent 在 Docker 沙箱中的 tmux session 收到终端输出，再返回 JSON。`analysis` 描述当前观察，`plan` 指下一步，`commands` 数组携带 `keystrokes` 与 `duration`；`task_complete` 可省略，默认 false。一次 JSON 可发送多条命令，因此 **模型 turn、命令数和工具调用数不可混算**。[P, §3.2、Fig.3, p.4；Fig.7, p.17][P17]

附录 system prompt 特别约束按键文本必须含需要的换行，说明 C-c/C-d 等特殊按键；`duration` 控制给命令的等待时间，默认约 1 秒，并提示短操作约 0.1 秒、长操作分段轮询，不应单次等待超过 60 秒。这不是每题 wall-clock 上限，也不是完整训练的超时处置合同。空命令数组可用；非 JSON 包装文字可能被容忍但产生提示，不是本轮已核验 parser 的全部行为。[P, Fig.7][P17]

`task_complete=true` 是 agent 的完成声明，不是 verifier 的成功证明。环境最终状态仍需测试判定。模型卡建议评测继续使用 Terminus 2，说明部署接口对齐是本配方的条件，尚未证明换成 Claude Code／mini-swe-agent 仍保持同等增益。[官方模型卡 M8][M8]

### 4.3 三类 suffix 的实际教学内容

Fig.8 的数学后缀将输出落到固定文件；Fig.9 的代码后缀要求生成指定 Python 工件；Fig.10 的 SWE 后缀规定检查给定代码并用 SEARCH/REPLACE 形式表达修改，最终保存 patch。它们把纯文字题变成文件操作，但没有凭空补回原题缺失的依赖、隐藏测试或真实大型仓库搜索空间。[P, Fig.8–10, p.18][P18]

本篇没有训练子 agent、GUI/VLM、跨会话记忆、偏好或安全对齐的独立阶段。与这些方向有关的技能和参考工作只出现在任务覆盖或动机中，不应额外拼出一条旗舰模型式全域训练链。

<a id="training"></a>
## 5. 参数训练、执行基础设施与轨迹预算

### 5.1 明确披露的 SFT 配置

以下来自 [P, §5.1, p.8][P8]，默认适用于未另说明的实验；不是外推到 RepoHarness 的推荐参数。

| 字段 | 原文配置 |
| --- | --- |
| 初始化 | Qwen3-8B 主消融；14B/32B 检查规模变化 |
| 学习率／weight decay | 2e-5 / 1e-4 |
| Epochs | 2 |
| 训练最大序列 | 32,768 tokens；长上下文消融另列 |
| Global batch／micro-batch | 128 / 每 GPU 1 |
| Optimizer | AdamW，β=(0.9, 0.95) |
| Schedule | cosine，10% warmup |
| Gradient clipping | 1.0 |
| 8B/14B 资源 | 4 节点×8 GPU=32 GPU，sequence parallelism=2 |
| 32B 资源 | 16 节点=128 GPU |
| Offload／框架 | 所有实验 CPU offloading；veRL SFT |

**未披露的关键训练语义**：完整 token mask、thinking／tool observation 是否进入 loss、按 token 还是 trajectory 归一化、packing／截断方向、分布式分母、checkpoint 选择、随机种子与精确 base revision。原文未明确说明 PEFT 与全参数更新范围、GPU 型号、32B 的完整并行布局或训练 dtype。模型发布为 BF16 不等于原训练各环节必然 BF16。

这里不需要强行填 PPO ratio、advantage、critic、KL reference 或 group staleness：本篇没有相应 RL 更新。测试筛选、完整性筛选和 SFT loss mask 是不同问题；缺少后两者的实现说明，不能认定所有失败轨迹每个错误动作都被相同权重强化。

### 5.2 数据生成与评测使用不同环境基础设施

Harbor 编排大规模多轮轨迹生成；作者扩展 Singularity 支持 HPC，承认 fakeroot overlay 会引入少量失败，认为用于合成数据生产时可接受。评测改用 Daytona，强调云端隔离与并行运行可靠性。[P, §5.1 Infrastructure][P8]

这是两套用途的披露，不是训练与评测环境逐字节相同的证明。“生成可以容忍少量失败”也不等于那些故障在过滤、训练或评测统计中如何处理已经清楚。本文没有报告失败率或重试成本。

论文没有详述 generation queue、backpressure、partial rollout、跨版本采样、权重发布或 MoE routing replay；不得因为 Harbor 支持并行、veRL 支持 RL，就给本篇加上 fully-async 训练配方。推理服务端版本、teacher/API 托管方式、并发度和精度同样未完整披露。

### 5.3 A.1 的轨迹分布：保留真实数量级

Fig.5/6 是已生成轨迹的直方图。下列均值／中位数来自图中直接打印的数值，不是本稿从柱高估算：[P, A.1、Fig.5–6, pp.15–16][P15]

| 路线 | N | Tokens 均值 | Tokens 中位数 | Turns 均值 | Turns 中位数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dataset adapters | 226,313 | 17,507 | 13,861 | 17.5 | 16.0 |
| Synthetic tasks | 264,207 | 17,363 | 17,836 | 16.3 | 16.0 |

Token 图横轴为长度区间，纵轴频数；adapter 分布更分散、长尾较明显，synthetic 更多集中于 15–25K。Turn 图也有 50+ 的尾桶。大部分样本可落入 32K，确有一部分在 SFT 被截断；但 30–35K 的桶跨过 32,768，不能仅凭该图给精确截断比例。

这组数据能支持“典型轨迹十几轮、总记录长度约一两万 token，并存在尾部”，不能证明任务覆盖数百轮，也不能把直方图尾桶看作配置中的最大 turn 上限。Token 的统计是否仅 action、是否含观察及重叠前缀、具体 tokenizer，原文没有足够说明；不能据此精确核算训练 token 总量和费用。

<a id="experiments"></a>
## 6. 评测协议、主要结果与类别负结果

### 6.1 成绩的对象是 TB2.0 + Terminus 2

主评测使用 **Terminal-Bench 2.0，89 个任务，Terminus 2**。这是作者为比较 checkpoint 固定的 reference harness；不是后来版本 TB 的分数，也不是对所有生产 coding agent 的统一判断。[P, §3.1、§5.2][P3]

论文及模型卡未完整给出 task／image／harness revision、采样温度、每题重复次数、通用最大 turn/wall-clock、故障重跑合同及全部闭源模型的 effort。表中的 `±` 未在方法中明确绑定统一统计定义；Fig.4 单独标了 **95% CI**，不能因此把所有表格 `±` 都改称同种置信区间。类别行呈现某种重复采样粒度，也不能据此擅自补出“每题固定五次”。

### 6.2 主模型结果与对照边界

| 模型规模 | 原始 Qwen3：TB2.0 | Nemotron-Terminal：TB2.0 | 均值差（本稿算术，百分点） |
| --- | ---: | ---: | ---: |
| 8B | 2.47±0.5 | 13.0±2.2 | +10.53 |
| 14B | 4.04±1.3 | 20.2±2.7 | +16.16 |
| 32B | 3.37±1.6 | 27.4±2.4 | +24.03 |

全部数值来自 [P, Table 3, p.8][P8]；Table 4 总行使用四舍五入的 2.5/4.0/3.4。正文把这解释为专用数据比单纯参数规模更关键；直接证据是这些 Qwen checkpoint 在该评测接口下训练前后的差距，不是“大模型规模没有作用”的受控因果结论。

Table 3 的开放模型参照为：Qwen3-Coder-480B **23.9±2.8**，GPT-OSS(high)-20B **3.10±1.5**／120B **18.7±2.7**，MiniMax M2 **30.0±2.7**、M2.1 **29.2±2.9**，Kimi K2 Thinking **35.7±2.8**，DeepSeek-V3.2 **38.2±2.9**。32B 的 27.4 高于其中一些模型的点估计，但没有配对显著性检验，也没有包含 teacher 成本的总经济性比较。

闭源参照覆盖 GPT-5 Nano/Mini/5/5.1/5.2、Grok Code Fast 1/Grok4、GLM4.6、Gemini2.5 Flash/Pro 与3 Flash/Pro、Claude Haiku/Sonnet/Opus4.5，原表从 **7.90±1.9 到57.8±2.5**；这些是历史报告坐标，不是本次重新跑出的当前排名。Table 1 另有未出现在 Table 3 的 **Qwen3-Max-Thinking 22.5**，未附误差。需要完整横向榜单时直接查 Table 3，不把两表混成新榜。

### 6.3 类别拆分：所有任务家族都保留，不能只挑改善最大的

以下对应 **Table 4**，每格为 `Qwen3 → Nemotron-Terminal`（%）。任务数是该类别的 benchmark task 数，不是重复运行数。[P, Table 4, p.9][P9]

| 类别（任务数） | 8B | 14B | 32B |
| --- | --- | --- | --- |
| Software Engineering（24） | 1.70→9.20 | 6.70→18.3 | 5.00→31.7 |
| System Administration（9） | 13.3→22.2 | 6.70→28.9 | 6.70→31.1 |
| Debugging（3） | 0→20.0 | 0→40.0 | 0→33.3 |
| Security（8） | 0→12.5 | 0→17.5 | 2.50→27.5 |
| File Operations（4） | 0→0 | 0→10.0 | 0→5.00 |
| Data Science（8） | 2.50→7.50 | 7.50→17.5 | 0→27.5 |
| Data Processing（4） | 0→35.0 | 5.00→40.0 | 5.00→50.0 |
| Data Querying（1） | 0→20.0 | 0→40.0 | 0→60.0 |
| Scientific Computing（7） | 0→0 | 0→2.90 | **2.90→0** |
| Mathematics（4） | 0→0 | 0→0 | 0→0 |
| Machine Learning（3） | 0→6.70 | 0→13.3 | 0→13.3 |
| Model Training（4） | 0→5.00 | 0→20.0 | 0→50.0 |
| Personal Assistant（1） | 0→80.0 | 0→80.0 | 0→100 |
| Games（1） | 0→0 | 0→0 | 0→0 |
| Video Processing（1） | 0→0 | 0→0 | 0→0 |
| Unknown（7） | 5.70→34.3 | 8.60→34.3 | 8.60→34.3 |

类别数合计 89。作者强调查询、模型训练等从零到非零的变化；同时应看到 scientific computing 的 32B 回退，以及数学、游戏、视频仍为零。14B 的 debugging/file operations 也高于32B，不能概括为所有子能力随模型规模单调增强。

**单题类别尤其不能过度外推。** Data Querying 的60或 Personal Assistant 的100，是一个任务上的聚合表现；不等于已全面获得数据库或个人助理能力。基础模型有限采样中得零也不能证明其解法支持集为空。本文没有大采样能力边界、retention 或未见 harness 测试。

## 7. 数据工程实验：分别说明改了什么、没控制什么

主消融模型均为 **Qwen3-8B**；默认超参数见 §5.1。表值沿用原文，`±` 的定义缺口见 §6.1。下列推论不把点估计差值自行升级为独立统计显著性。

### 7.1 数据构成（Table 5）：混合更好不等于已证明单位数据更好

| 数据子集 | #Samples | TB2.0（%） |
| --- | ---: | ---: |
| Adapter：Math | 162,692 | 5.39±1.65 |
| Adapter：Code | 31,960 | 6.29±1.65 |
| Adapter：SWE | 31,661 | 7.02±2.13 |
| Adapter：All | 226,313 | 9.66±2.11 |
| Synthetic：Seed-based | 124,366 | 6.18±1.91 |
| Synthetic：Skill-based | 139,841 | 12.4±2.38 |
| Synthetic：All | 264,207 | 12.4±2.29 |

[P, §5.3、Table 5, pp.9–10][P10]。两个 All 分别是各路线内部总和，不是都表示两路线全混合。结合 §5.6，最终混合默认结果约13.0。

Adapter 三类混合高于各单一来源，但样本数也改变。Skill-based 是 synthetic 的主要增益来源；加入 seed 后均值仍12.4，`±` 从2.38变2.29。作者称其减小方差、提升稳健性，但缺少原始重复结果与统计定义，不能据此宣称 seed 已带来可确定的独立稳健性收益。没有等样本／等 token 的 skill-only 扩采对照。

### 7.2 Adapter completion 筛选（Table 6）：各子集方向并不相同

| 子集 | Complete-only：样本；TB2.0 | No filter：样本；TB2.0 |
| --- | --- | --- |
| Math | 147,718；7.19±1.87 | 162,692；5.39±1.65 |
| Code | 20,169；6.07±1.73 | 31,960；6.29±1.65 |
| SWE | 29,053；5.39±1.68 | 31,661；7.02±2.13 |
| All | 196,940；8.09±1.84 | 226,313；9.66±2.11 |

[P, §5.4、Table 6, pp.9–10][P10]。Math 的完成筛选点估计反而更高；不能说三个子域都因为保留 incomplete 而提高。作者概括差异不显著，按合并集合点估计选择 No filter。Adapter 没有测试，**未做 success-only 对照**。

### 7.3 Synthetic 过滤（Table 7）：最有价值也最容易误读的结果

| 筛选 | #Samples | TB2.0（%） | 相对 No filter 的样本保留率（本稿计算） |
| --- | ---: | ---: | ---: |
| Complete-only | 104,603 | 6.74±2.20 | 约39.6% |
| Success-only | 83,448 | 5.06±2.11 | 约31.6% |
| No filter | 264,207 | 12.4±2.29 | 100% |

[P, §5.4、Table 7, p.10][P10]。作者的解释是：严格过滤删去过半数据，未成功轨迹也可能呈现真实错误状态及恢复行为。**直接观察是这套 no-additional-filter 配方胜出；失败片段自身的学习价值仍未独立隔离。**

No filter 的样本量约为 success-only 的3.17倍。默认同为2 epochs时，训练消费次数、token和更新步数一般也会改变；论文未给等 token、等更新步数、成功样本重采样或逐段错误监督的隔离对照。另无轨迹级统计证明所有未成功样本真的包含成功恢复行为。

因此，本实验不能推出“所有失败轨迹都应进入 policy gradient”“基础设施故障无需筛除”“任何错误动作都适合 SFT”。若用于项目设计，首先应区分完整但任务失败、有效恢复片段、截断、环境损坏，以及 reward 不可信这几类；这些是读者的应用条件，不是本篇已经实现的故障 taxonomy。

### 7.4 上下文（Table 8）：负结果不是普遍反对长程训练

| SFT 最大长度 | Eval 最大长度 | SFT YaRN2 | Eval YaRN2 | TB2.0（%） |
| ---: | ---: | :---: | :---: | ---: |
| 32,768 | 40,960 | 否 | 否 | 13.0±2.2 |
| 32,768 | 65,536 | 否 | 是 | 11.9±2.0 |
| 65,536 | 65,536 | 否 | 否 | 10.3±2.0 |
| 65,536 | 65,536 | 是 | 是 | 11.9±2.1 |

[P, §5.5、Table 8, p.10][P10]。保留原表的 **YaRN2** 写法；其参考文献指向 Peng et al. 2023 的 YaRN，本篇没有给出完整 scaling factor／实现配置，不替作者补成一种已冻结实现。

作者认为延长窗口未改善表现，并推测长尾轨迹较嘈杂、有效监督已多位于标准窗口内。本文没有逐长度质量审计来直接验证这一原因；表中训练长度、评测长度和位置扩展配置也不是全因子设计。这只能支持**本数据、本模型、本评测下，额外窗口未显出优势**，不能推出 compaction 无效或真实长程 SWE 不值得训练。32K 是训练记录截断，与 SkyRL 的在线 horizon 轨迹梯度屏蔽不是同一机制。

### 7.5 Curriculum（Table 9）：只测了一种顺序

| Qwen3-8B 训练方式 | TB2.0（%） |
| --- | ---: |
| 单阶段混合所有数据 | 13.03±2.16 |
| 先 adapters、后 synthetic 的两阶段 SFT | 10.39±1.71 |

[P, §5.6、Table 9, pp.10–11][P11]。没有分阶段学习率重启、每段 epoch／token 的完整记录，也没有反向顺序或持续动态采样实验。它支持给简单混合一个强基线地位，**不构成 solver-relative 在线 RL curriculum 的反证**，更不意味着所有预热→RL阶段设计都无效。

### 7.6 数据规模（Fig.4）：保留近似量级，不制造 scaling law

横轴是训练数据比例 **0%、1%、2%、5%、10%、100%**，这些标签在图上等距排布，不能把线段斜率当真实线性或对数比例下的边际收益。纵轴为 TB2.0 performance，阴影标 **95% CI**。图中两条曲线随数据量总体上升，14B 在各比例上更高。[P, §5.7、Fig.4, p.11][P11]

按原图目测，8B 在0/10/100%约为 **2.5/9.5/13.0**，14B约为 **4.0/16.7/20.0**。这是有限精度视觉读数，不是作者提供的完整日志；不另给高精度终值。正文称比例来自 synthetic training data，却没有完整说明每个比例对应的路线／逐条 manifest，因此不能自行将所有比例乘以490,520得精确任务数。

该实验支持继续加数据在此范围有收益。它没有等训练算力对照、幂律拟合、外推饱和点或八卡成本预测。0%是初始化参照，不表示多训练一阶段却用了零数据。

<a id="assets"></a>
## 8. 开放资产、实际访问状态与复现缺口

### 8.1 本轮实际核验的官方资产

| 资产 | 本轮访问范围与版本记录 | 已确认内容／未完成项 |
| --- | --- | --- |
| [NVIDIA collection][COL] | 页面列5项：8B/14B/32B模型、Corpus、Synthetic-Tasks | 确认入口；14B未单独深入模型文件 |
| [Corpus 数据卡][DC]与[文件树][DC-tree] | 页面显示末次提交 `a1667c4ffdadea02a89bffe4f1bb7ca2ff19f8d9`（2026-02-27），已打开对应 commit 页 | 卡片约366K；viewer显示366,154行；约226K adapters+140K skill；文件树约8.2GB。未下载Parquet逐条重算 |
| [Synthetic-Tasks 数据卡][DT]与[文件树][DT-tree] | 页面显示 `7e53648e183cee7bcb0aed623cc91a121d37fa38`（2026-02-23），已打开 commit 页 | card限定skill-based任务；skill_based/下有easy.tar.gz、medium_shard1/2.tar.gz、mixed/；树约1.03GB，未解包验证 |
| [8B 模型卡][M8]与[发布文件][M8-tree] | 固定README `bb1413579351dfada0c203699ea32d2d08f0942c`（2026-02-27）可读 | Qwen3来源、Terminus2输出约定、权重分片、tokenizer/chat template入口；未下载或运行 |
| [32B 模型卡][M32] | 读取当时main页面，未另固定权重revision | 对照主要成绩与家族说明，不作为已完成权重审计 |

Corpus/Synthetic-Tasks 的卡片与文件树以查阅时页面为依据，并通过 commit 页记录所显示 revision；指定完整 SHA 的 README blob 页面两次访问失败，因此不宣称已经重新取得两份 pinned raw bytes。8B 的固定 README 页面成功。动态页面显示的大小与行数不是本地独立统计。

两个 dataset viewer 分别出现 `TooBigContentError` 和 `SplitsNotFoundError`：前者与Parquet扫描量有关，后者与目录／tar格式识别有关。**网页预览失败不等于文件不能下载、任务不可执行或作者没有公开数据。** 本轮没有实际运行任务包，因此也不反过来声称它们已通过 RepoHarness 资格验证。

### 8.2 公开规模小于论文混合规模，并非数字互相否定

论文结论明确只释放多数数据，具体为 **adapter 与 skill-based 子集**。由 Table 5 可复算：

```text
226,313 adapters + 139,841 skill-based = 366,154 released rows
226,313 adapters + 264,207 all synthetic = 490,520 paper samples
490,520 - 366,154 = 124,366 seed-based samples
```

这与数据卡描述相符。**490,520不是已公开的完整Corpus行数，366,154也不能被写成所有带测试的可执行环境数。** 下载公开数据即可重复全部论文混合实验的主张不成立；seed-based部分缺失会影响Table 5、7及最终混合的严格复现。[P, Table 5、§6；官方DC][DC]

### 8.3 许可与源码边界

两份数据卡标 **CC-BY-4.0**；模型卡标 **NVIDIA Open Model License**。论文 arXiv 采用 non-exclusive distribution 条款，不能把数据许可证自动套用到原论文、所有上游题目、模型权重或依赖代码。此处只记录资产标注，不提供涵盖全部使用场景的许可结论。[Corpus数据卡][DC]、[任务数据卡][DT]、[模型卡][M8]。 [arXiv许可入口][P-license]

论文公开了方法、提示词、超参数和资产，但在所查原文、官方collection和卡片中，未找到与本篇原始实验绑定的完整 Terminal-Task-Gen 生成编排、过滤实现、SFT与评测脚本及依赖锁定。这个结论限定于本轮核查范围，不等于互联网上不存在任何实现。HF自动展示的 Transformers/vLLM/SGLang 通用加载片段，也不能替代复现TB2.0成绩的端到端recipe。

## 9. 成本与最影响使用的未知项

| 环节 | 已披露 | 尚不能核算／断言 |
| --- | --- | --- |
| 题目与环境生产 | 两条路线；九个领域基础镜像；避免逐题Dockerfile修复 | 候选量、构建成功率、人工工时、完整镜像大小／耗时／修复对照 |
| Teacher轨迹 | DeepSeek-V3.2；Harbor/Singularity；轨迹量与长度分布 | API总费用、teacher GPU型号与小时、请求重复、缓存收益、失败attempt成本 |
| SFT | 32或128GPU、2epochs、offload、batch与lr等 | GPU具体型号、时长、GPU-hours、能源或租赁费、有效loss token量 |
| 评测 | TB2.0、Terminus2、Daytona；部分上下文档位 | 每题CPU/RAM／网络／时限、重跑规则、各模型effort、完整总费用 |
| 结果可信性 | 14-gram去污染、基础过滤、tests、逐类别结果 | 可解性oracle、无操作检查、合法替代解、flakiness、漏洞率及隐藏grader隔离实证 |

因此，“小模型达到较大模型的某些点估计”与“总训练和使用成本更低”必须分开。九镜像是合理的成本设计，但没有量化端到端加速。原文使用“modest resources”的相对描述，不能把128GPU的32B作业直接承诺为本项目八卡可复现预算。[P, §1、§4.2.3、§5.1][P8]

三种缺口分别保留：**原文未披露**的如loss mask、统计定义；**本轮未取得**的如本机PDF、TeX、两份指定SHA数据README；**本轮未检查**的如全部tar/Parquet、镜像运行、权重加载与训练复现。前者不能从最新框架默认补齐，后两者不能写成作者不公开或材料无效。

<a id="project"></a>
## 10. 对 RepoHarness 项目一的有限映射

日期2026-09-07；依据已读取的[当前简报][RH-state]，项目是 miles + SGLang + 外部Claude Code harness，rh2自有环境、reward与轨迹消费边界。单节点8×96GB、约30B-A3B与本篇dense32B的128GPU实验不是同一资源条件。下表仅为设计层候选，不表示已审计全部当前实现，也不批准扩展任务范围。

| 可借鉴的决策 | 本篇证据 | 上游复用与必要增量 | 有限验证方式 |
| --- | --- | --- | --- |
| 将基础环境构建与任务内容拆开 | §4.2.3 九镜像 | 复用现有容器/runtime；若当前依赖可归入少量稳定模板，再做任务级文件与测试构建 | 对同一小批候选统计构建成本、存活率、资源包络；检查复用是否隐藏依赖缺失 |
| 将SFT资产与RL任务资格分开 | adapters无tests，synthetic无oracle；§4.1–4.2 | 现有可信评分边界不应放宽；SFT轨迹可另走合适的离线路径 | 分别检查“可模仿行为”“可执行”“可评分”；不把所有Corpus条目直接灌入RL |
| 先给简单混合与温和过滤一个强基线 | Tables5–7、9 | 不需新课程平台；使用已有离线分层和可审计采样 | 同底座下匹配训练token／更新；再比较成功重采样、完整失败、截断与损坏过滤 |
| 扩窗口之前先分析真正被截断的内容 | Fig5–6、Table8 | 优先利用现有harness预算与轨迹日志，不据此新增压缩策略训练 | 测被截断轨迹的原因、成功率、信息位置与成本；只改一个可解释变量 |
| 对第二域结果保持接口与能力边界 | 固定Terminus2、Table4 | Terminal可先作对照或迁移评测，不强制成为大规模第二训练线 | 原模型/训练模型固定Terminus；换原生harness另列，不混算系统与权重收益 |

**这篇对项目定位的主要贡献，是反对过早把复杂度当作价值。** 作者真正验证的是数据生产与SFT策略的组合；一些简单方案胜过更复杂的筛选、阶段顺序和窗口设置。但它没有证明RepoHarness应停止可靠性工作，也没有证明新的任务供给控制器一定值得做。

更直接的工程问题是：复用环境后，单位总预算能获得多少可信、可用的任务或轨迹？更多样本的收益是否超过生成／教师成本？筛选损耗和学习收益能否区分？答案需要本项目自己的测量，不能直接借Table7的点估计写简历成绩。

## 11. 快速检索与成文状态

| 讨论问题 | 本稿入口 | 原文定位 |
| --- | --- | --- |
| “两阶段”究竟指什么？ | §2.2、§7.5 | Fig1、§4；§5.6/Table9 |
| 现成Corpus能否直接用于RL？ | §3.1、§3.4、§8.2 | §4.1.2、§4.2.3、§6 |
| seed和skill生成有什么区别？ | §3.2–3.3 | §4.2.1–2、A.3/Fig11–20 |
| No filter是否意味着错误数据都该训练？ | §3.6、§7.2–3 | §4.4、Tables6–7 |
| 训练参数与GPU配置 | §5.1–2 | §5.1, p.8 |
| 轨迹多长，窗口为何没提升？ | §5.3、§7.4 | A.1/Fig5–6、§5.5/Table8 |
| 模型哪里改善／没有改善？ | §6 | Tables3–4 |
| 论文490,520与公开366,154如何对应？ | §3.5、§8.2 | Table5、§6及官方数据卡 |

关联已有文档：[CalibForge](E2_calibforge.md)可比较solver校准的证据类型；[SWE-smith](E5_swe_smith.md)可比较稳定仓库上的任务扩展；[SkyRL-Agent](O01_skyrl_agent_sa_swe.md)可比较SFT截断与在线RL的horizon语义。这里只提供已存在笔记的导航，不用它们补本篇未知方法。

**交付状态：全文及附录精读、作者自查完成；待独立复核；未复现训练。** 检查记录见[自查文件](reviews/nemotron_terminal_self_check_20260907.md)。本会话无独立子agent工具，未制造reviewer或thread ID；未修改训练代码、共享索引、其他阅读成品或一次性交接快照。

## 官方与项目来源

[P-abs]: https://arxiv.org/abs/2602.21193
[P-html]: https://arxiv.org/html/2602.21193v1
[P]: https://arxiv.org/pdf/2602.21193v1
[P1]: https://arxiv.org/pdf/2602.21193v1#page=1
[P3]: https://arxiv.org/pdf/2602.21193v1#page=3
[P4]: https://arxiv.org/pdf/2602.21193v1#page=4
[P5]: https://arxiv.org/pdf/2602.21193v1#page=5
[P6]: https://arxiv.org/pdf/2602.21193v1#page=6
[P7]: https://arxiv.org/pdf/2602.21193v1#page=7
[P8]: https://arxiv.org/pdf/2602.21193v1#page=8
[P9]: https://arxiv.org/pdf/2602.21193v1#page=9
[P10]: https://arxiv.org/pdf/2602.21193v1#page=10
[P11]: https://arxiv.org/pdf/2602.21193v1#page=11
[P15]: https://arxiv.org/pdf/2602.21193v1#page=15
[P17]: https://arxiv.org/pdf/2602.21193v1#page=17
[P18]: https://arxiv.org/pdf/2602.21193v1#page=18
[P19]: https://arxiv.org/pdf/2602.21193v1#page=19
[P-license]: https://arxiv.org/licenses/nonexclusive-distrib/1.0/license.html
[COL]: https://huggingface.co/collections/nvidia/nemotron-terminal
[DC]: https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus
[DC-tree]: https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Corpus/tree/main
[DT]: https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks
[DT-tree]: https://huggingface.co/datasets/nvidia/Nemotron-Terminal-Synthetic-Tasks/tree/main
[M8]: https://huggingface.co/nvidia/Nemotron-Terminal-8B/blob/bb1413579351dfada0c203699ea32d2d08f0942c/README.md
[M8-tree]: https://huggingface.co/nvidia/Nemotron-Terminal-8B/tree/main
[M32]: https://huggingface.co/nvidia/Nemotron-Terminal-32B
[RH-state]: https://github.com/Rogerffff/RepoHarness/blob/9f93eb64b63f04723c62432fe18027e80b0c15b0/docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md
[RH-template]: https://github.com/Rogerffff/RepoHarness/blob/9f93eb64b63f04723c62432fe18027e80b0c15b0/docs/harness_improve/external_paper_references/reading_notes/NOTE_TEMPLATE.md
[RH-review]: https://github.com/Rogerffff/RepoHarness/blob/9f93eb64b63f04723c62432fe18027e80b0c15b0/docs/harness_improve/external_paper_references/reading_notes/reviews/15_O01_codex_quality_review_20260907.md
