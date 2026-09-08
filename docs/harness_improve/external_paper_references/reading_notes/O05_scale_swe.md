# O05 ScaleSWE v4：真实 PR 任务生产、成功轨迹 SFT 与可复用资产

**主来源：** *Immersion in the GitHub Universe: Scaling Coding Agents to Mastery*，arXiv `2602.09892v4`，2026-03-24。**本次整理：2026-09-08。**

Scale-SWE 的核心是把真实 PR 转换为可执行的训练任务：交互式构建环境、补足测试、重写与测试对齐的题面，再用 DeepSeek-V3.2 的成功轨迹对 Qwen3-30B-A3B-Instruct 做 **SFT，而非在线 RL 或 OPD**。作者报告构建 100k 任务、覆盖 5.2k 仓库，选 25k 任务采样得到 71,498 条成功轨迹；Table 3 报告 SWE-bench Verified 22%→64%。本轮可读取的公开任务集实际显示 **20,181 行**，不可直接当作全部 100k。当前官方评分代码和后来的 61.4% 复跑材料提供了接入线索，也暴露出版本、测试字段、测试通过语义及运行配置需要进一步核对的地方。

**阅读状态：正文与附录 A–D 的可读文本、5 张表的 HTML 内容、官方文章／数据卡及关键代码已研读；PDF 原图页、附录 E 的生产提示词尚未取得，不能标为完整全文／图表核验通过。** PDF 获取最终明确返回文件过大（10,949,149 bytes），容器下载亦失败；HTML 的附录 E 只有标题与残留反引号。下文不编造 PDF 页码，不以现代 solver prompt 或旧摘要补缺。已完成作者自查和一个合成 pytest 小实验；没有独立审查、真实任务容器测试或模型训练复现。

导航：[来源与覆盖](#sources) · [流程与数量](#pipeline) · [三类生产 Agent](#agents) · [质量与泄漏](#quality) · [SFT 与评测](#training) · [可消费资产](#assets) · [评分代码](#implementation) · [成本和未知项](#limits) · [B 侧适用性](#mapping)

<a id="sources"></a>
## 1. 来源身份与范围

### 1.1 一手来源及版本

主论文作者为 Jiale Zhao、Guoxin Chen、Fanzhe Meng、Minghao Li、Jie Chen、Hui Xu、Yongshuai Sun、Wayne Xin Zhao、Ruihua Song、Yuan Zhang、Peng Wang、Cheng Chen、Ji-Rong Wen、Kai Jia。首次提交 2026-02-10；本任务固定 **v4，2026-03-24**，不把之后的模型、轨迹或代码变更倒填到该版本。[P0][P0]

| 标记 | 来源 | 本轮身份与用途 |
| --- | --- | --- |
| P | [v4 HTML][P]；[v4 PDF 入口][PDF] | 论文为主要依据；PDF 本轮未成功读取 |
| W | [作者项目文章][W] | 页面标注 2026-02-10；未有可固定的文章 revision。只作作者额外经验，不与论文消融混用 |
| G | [ScaleSWE 官方仓库][G] | 固定 `b531926bf4fc069451eca390587a4e30c1b1bb21`，2026-07-21；README、目录和资产导航 |
| D1 | [Scale-SWE 任务集][D1] | 可读 [Files 页][D1pin]对应 `d8db20390a936bbda9c96d88b97cc4778dff1481`；3 月 5 日 README 更新。检查 schema、预览行和页面统计，未全量下载 |
| D2 | [Scale-SWE-Distilled][D2] | [Files 页][D2pin]指向 `c14ce2130f494812fef907f4afc81d8e33990805`；commit 正文未取回。检查 schema、预览和统计，不称全量审计 |
| M | [Scale-SWE-Agent 模型卡][M] | 页面与开放权重入口可读；未下载权重或固定 checkpoint 文件摘要 |
| C | [AweAgent 代码][C] | 固定 `b38414e5dc9c7c51f2ec48318b718af0c8852060`，2026-08-18；只追 §8 所列路径 |
| B | [本项目 B 侧阅读请求][B] | 项目读取基线 `bbce8683b025077ac1bed5da7d7587a6f1ec8dcb`，`miles-migration`；只决定文末映射问题 |

HF 页面与 viewer 是本轮可取得的前端内容，可能有缓存；本稿记录页面显示和可取得的版本线索，不声称实时遍历了整个仓库或 registry。论文在 arXiv 标注 CC BY 4.0；官方仓库和数据卡也声明 CC BY 4.0。各源代码仓库及其依赖的原许可证仍须分别保留，不能将任务集合的许可证解释为替所有上游软件重新授权。

### 1.2 原文覆盖表

本稿采用 **v4 章节／表／公式／图号**定位。PDF 物理页数与页码待原文件取得后补充；不伪造“第几页已目视检查”。

| 原文范围 | 实际读取内容 | 状态／本稿位置 |
| --- | --- | --- |
| Abstract、§1 Introduction | 动机、规模、训练路线与 60/64 数值差异 | 文本已读，§2、§6 |
| §2.1.1–2.1.4 | EBA/UCA/PSWA、Eq.(1)–(3)、交互构建与复用 | 文本和公式已读，§3 |
| §2.2 | 仓库与 PR 筛选、反泄漏 | 文本已读，§2、§4 |
| §2.3 | golden/base 测试与人工抽审 | 文本已读，§4 |
| §2.4 | 统计、教师采样、数据集对比、bug 分类 | 文本及 Table 1–2 已读，§2、§5 |
| §3.1–3.2 | OpenHands、SFT、评测协议、Table 3–4 | 文本与完整表项已读，§6 |
| §4 Related Work、§5 Conclusion | 作者的真实／合成分类、范围与多语言未来计划 | 文本已读，不逐篇扩读所有引用 |
| References | 核对主要依赖身份 | 已读；SWE-rebench 是原版，不是后来 V2 |
| Appendix A.1 | 候选→筛选→生成流程和 1M 中间量 | 图注已读；Fig.5 原图未读 |
| Appendix B | 16 个任务字段及合成 F2P 描述 | 全部字段已读，§7 |
| Appendix C | Table 5 的 SFT 超参数 | 表项已读，§6 |
| Appendix D | Git 清理脚本文本 | 全部可读脚本已读，§4；未在真实镜像执行 |
| Appendix E | 生产流程 prompts | **未取得正文，不是“作者未披露”** |
| Figure 1–5 | 图注和正文解释 | 原图未取得；不据图估精确密度、百分比或流程支路 |

HTML Table 1–5 能恢复明确行列，但仍未经 PDF 版面复核。Fig.1 是分数与激活参数；Fig.2 是三 agent 架构；Fig.3 是 bug 类别分布；Fig.4 是 token/turn 密度；Fig.5 是数据生产漏斗。原图及作者网页的相应 PNG 均访问失败，不将文字解读表述成亲眼确认图中全部细节。

<a id="pipeline"></a>
## 2. 研究对象与完整生产／训练流程

### 2.1 三个不同产物

**Scale-SWE** 是数据构建流程；**Scale-SWE-Data** 是带环境与测试的任务集合；**Scale-SWE-Agent** 是在教师成功轨迹上微调后的模型。多 agent 是生产侧的职责拆分，非多智能体 RL 优化；这里的 distillation 是教师轨迹 SFT，非学生在自身采样 prefix 上请求教师概率的 OPD。[P, §1–3][P]

按原文恢复的流程为：

```text
PyPI / GitHub 仓库候选
  → 仓库、许可与 PR 质量筛选
  → SWE-agent 驱动的 EBA 环境构建与复用
  → UCA 从真实 diff / 仓库生成或补足测试并执行验证
  → PSWA 根据 PR 与测试重写题面
  → base / golden 的 F2P + P2P 检查
  → 100k 任务
  → 选取 25k 任务，DeepSeek-V3.2 每题采样 5 次
  → 只保留通过全部测试的成功轨迹
  → Qwen3-30B-A3B-Instruct SFT
  → SWE-bench Verified 评测
```

**真实来源不等于全部组件由人类编写。** PR 的代码变化来自真实软件演进，但题面被重写，部分测试由模型合成，环境也由 agent 构建。因此更准确的是“真实 PR 来源＋生成式任务重构”，不是“未经加工的天然真实任务”。这保留作者的 Real/Synthetic 分类，同时避免把字段来源混为一谈。

### 2.2 数量漏斗及正确分母

| 阶段 | v4 披露 | 应怎样解释 |
| --- | --- | --- |
| PyPI 来源 | 下载量 Top 15,000 包所对应仓库 | 包数量不是独立仓库数量 |
| SEART 来源 | 9,062 仓库 | Python 为主语言；≥5 contributors；≥500 stars；创建日期 2015-01-01 至 2025-10-29 |
| 来源并集 | 约 23k 候选仓库 | 去重后的近似量；后续逐关仓库数未给 |
| 仓库过滤 | 排除 SWE-bench Verified 仓库；仅 permissive licenses；LLM 根据 README 排除不适合对象 | GPU-dependent、教程型、缺少有效源码是文中例子；不是完整可执行规则清单 |
| 已合并 PR | 约 6M | 从过滤后仓库的 main/master 分支采集；judge 读取 diff、PR 描述、merge message |
| 质量筛选后 | 约 1M PR | 附录 A 的 Fig.5 图注明确给出；正文未列每个子过滤的数量 |
| 环境、测试、题面生成后 | 100k 验证任务；5.2k 仓库 | **构建成果，不是本轮确认全量公开** |
| 专家求解池 | 25k 任务子集 | 如何选择、各仓库配额和完整 manifest 未在可读部分给出 |
| 专家采样计划 | 每题 5 次；temperature=0.95；最多 100 interaction turns | 名义最多 125k 次初始采样；实际失败、重试和未完成尝试未逐项披露 |
| 成功轨迹 | 精确 71,498；文中简写 71k；约 3.5B tokens | 多条轨迹可以对应同一任务；不能称 71,498 个独立任务 |
| 本轮公开任务页面 | **20,181 行**；发布说明写 20k | 与全部100k、教师池25k分别记录 |
| 本轮公开蒸馏页面 | **71,498 行** | schema 为 messages/data_source/system，不自动证明全部轨迹可由公开任务集重跑 |

原文定位：§2.1.2、§2.2–2.4、Appendix A；公开数见 [D1][D1]、[D2][D2]。摘要把 6M 与 5.2k 并列，§2.2 与附录则区分较大的候选池和最终覆盖；本表按阶段记录，不擅自假设全部 6M PR 都来自最终这 5.2k 个仓库。

粗略算术：100k/6M≈1.67%，100k/1M≈10%。这只能称相应阶段口径下的最终产出比例，**不是 EBA 成功率**。同理，71,498/(25k×5)≈57.2% 是相对名义采样计划的成功轨迹比例，不是目标学生通过率；未核清实际完成和重试数前，不作为精确执行成功率。

### 2.3 源仓库排除与剩余泛化问题

排除 SWE-bench Verified 所在仓库，是文中明确的防训练—评测交叉措施，强于只排除相同 issue ID。[P, §2.2][P]

但正文没有给出实际排除 manifest、fork/mirror 检查、重复 patch/近似题面匹配或教师训练污染核验。仓库排除不自动排除基座／教师既有知识、运行时在线取答案等风险。这里是防污染措施的覆盖边界，不是本稿发现了实际泄漏。

对用户自建 held-out，也不能沿用“作者排除了 SWE-bench Verified，所以与我方所有评测都不重叠”的推断。发布任务与轨迹之间的 `data_source ↔ instance_id` join 同样要实测：20,181 小于25k，**不证明必然缺少成功轨迹对应任务**，但不能仅凭数字保证全部可回放。

<a id="agents"></a>
## 3. 三类生产 Agent：职责、可见信息和复用机制

### 3.1 执行基础与模型角色

生成流程建立在 **SWE-agent** 上，使用 DeepSeek v3.1 或 v3.2 生成任务，PSWA 例外采用 **Gemini3-Pro**。主文没给 v3.1/v3.2 的精确实例配比、API revision 和每角色采样参数。后续求解教师明确为 **DeepSeek-V3.2**；模型训练／实验框架则是 **OpenHands**。这三个角色层不能合写成“一直在 OpenHands 里跑三个训练 agent”。[P, §2.1.1、§2.4、§3.1][P]

### 3.2 EBA：交互搭环境，再从执行轨迹提炼 Dockerfile

原文 Eq.(1)：

\[
\mathcal D_{final}=EBA(\mathcal R,\mathcal D_{init}).
\]

输入是源码仓库与通用 Docker 基础环境；输出是仓库可执行环境。agent 读取 `setup.py`、`pyproject.toml`、README 等，执行安装、观察依赖冲突、修改并再次测试。随后提取轨迹中的命令，由 LLM 整理成可复现 Dockerfile。[P, §2.1.2][P]

这里的机制与静态生成 requirements 有实质区别：**依赖解析由实际终端反馈约束**。但从“交互容器成功”到“提炼后的 Dockerfile 可从干净基础镜像重建”仍是两个检查点；可读论文未独立披露后一个检查的成功率、重复重建及镜像 digest 记录。

**环境复用策略。** 每仓库最多选择10个 PR 进行完整 EBA 构建；其余 PR 按 PR ID 距离匹配最近的已建环境。PR ID 被用作时间线代理，不是语义依赖距离。若在最近环境中测试失败，就从最终集合丢弃；成功则保留任务及环境。平均每仓库约19个实例。十个 PR 不等于每仓库只有十个任务，更不等于作者实际建成恰好52k镜像。[P, §2.1.2、Table 2][P]

**解释边界。** 环境复用降低成本是合理设计动机，但没有“每题单独构建 vs ≤10锚点”的同成本消融，也没有错配环境导致的丢弃率。按现有描述，它可能更偏好依赖稳定时期；这是待测选择效应，不是作者报告的缺陷。

### 3.3 UCA：测试是交互产生的，仍须区分来源与验证力度

Eq.(2)：

\[
\mathcal U=UCA(\mathcal M,\mathcal R,\mathcal D_{final}).
\]

`M` 包含标题、说明、diff；UCA 能读仓库、理解跨文件调用、编写断言和 fixture，在容器中执行并根据结果迭代。F2P 要在原始版本失败、gold 修复后通过；P2P 在两个版本都通过，检查回归。[P, §2.1.3][P]

文中一方面把 P2P 定义为已有 passing tests，另一方面明确生产流程可构建两类测试。这两种表述不应被压成“所有 P2P 都是开发者原始测试”；实际每条来源需要资产或构建日志确认。

Appendix B 将 `f2p_script` 解释为原开发者 F2P 不存在时的补充。但当前数据实例和 evaluator 显示 **`f2p_patch` 与 `f2p_script` 可以同时存在、同时布置**，最终执行集合由 F2P/P2P ID 指定。文档概念、字段实值和代码消费的差异详见 §7–8，不私自修改任何一方来使它们看似一致。

### 3.4 PSWA：通过测试定义需求，而不是泄漏修复

Eq.(3)：

\[
\mathcal S=PSWA(\mathcal M,\mathcal U,\mathcal R,\mathcal D_{final}).
\]

PSWA 同时看到 PR 元数据、实现 diff、测试、仓库与环境。因为 PR 常在解决问题之后撰写，直接改写描述容易泄漏位置或方案；另一方面，F2P 可能调用 base 中尚不存在的新函数／类，题面必须说明这些必要接口，否则正确实现也可能因未猜到测试假设而失败。作者因此要求输出完整行为需求，却不泄漏实现。[P, §2.1.4][P]

**“说明必要接口”与“给出解法”不可一律等同。** 原文的处理目标是可解性与泄漏控制同时满足，不是把所有函数名都从题面删除。现代 solver prompt 只定义求解行为，不能替代本次未取得的 Appendix E 生产提示词。

作者网页补充说，内部轻量题面消融并不严格，SFT 后的差距接近10%；没有明确这一10%是相对百分比还是百分点，也没有提供完整对照。网页还把更长求解轨迹看作更少泄漏的线索。这些保留为作者经验，**不能当作严格因果效应或无泄漏证明**。[W, §3 PSWA][W]

三个公式都是组件输入—输出定义，**不是优化损失，也不代表 EBA/UCA/PSWA 的参数经过多 agent RL 共同训练**。

<a id="quality"></a>
## 4. 质量保证、测试污染与反泄漏边界

### 4.1 两个代码状态、四项必要测试条件

§2.3 保留任务的规则是：base 上所有 P2P 通过、F2P 失败；gold 上所有 F2P/P2P 通过。可作为直观参考的状态表如下：

| 代码状态 | F2P | P2P |
| --- | --- | --- |
| base / 未修复 | 应失败 | 应通过 |
| base + golden patch | 应通过 | 应通过 |

关键是**测试真的执行到预期断言**。环境没装好、测试没收集到、parser 不识别，不等于合法的 F2P 失败。该表是对论文规则的恢复，不表示本轮替作者所有100k实例重新运行过这些状态。

作者强调固定 P2P/F2P 执行顺序以减少测试污染，但没有在可读文本写出生产验证中完整的命令、是否分进程／分容器、前后状态清理及多次重跑分布。固定顺序提高同条件可重复性，不等于证明所有顺序都无污染。[P, §2.3][P]

### 4.2 人工质量核查的实际证据

四名资深博士生按作者称为 cross-validation 的协议审核随机100题，其中94题被判断为环境、测试、题面均有效。正文没有公开这100题清单、每题由几人审、分歧裁定、各缺陷类别数量或置信区间。[P, §2.3][P]

因此可写“作者随机抽审100题，94题有效”；不能写成“全量数据已证明94%有效”或“四人独立逐题一致通过”。这也不是独立团队复现。

**缺少的质量实验**包括：对多种合法替代解的接受率、在与教师不同的 solver 上核验、对修改测试／控制面行为的压力检查、失败重试后稳定性，以及在未参与生产的仓库类型上的误差。它们未在可读部分形成独立实验，不能因有200余P2P就认为都覆盖了。

### 4.3 Appendix D 的 Git 清理做了什么

脚本将工作区切到 `parent_commit`，处理未跟踪内容和 stash，生成 pre-agent commit；删除 remote refs、tags、packed refs、ORIG_HEAD/FETCH_HEAD 等与 reflog；将 HEAD 指向保留分支，删除其他 heads，再执行 aggressive GC。目标是去掉 parent 之后可恢复的 gold 解答历史。[P, §2.2、Appendix D][P]

必须保留四个限制：

1. 它没有创建独立 orphan root；保留 base 的合法祖先不等于反泄漏失败。不能将作者目标扩写为“删除全部 Git 历史”。
2. 清理本地 Git 元数据不自动关闭网络、删除远程地址、依赖缓存、镜像中的其他副本或预存测试。原文未给完整网络及文件可见性策略。
3. 可读脚本中 `stash pop || echo ...` 会容忍失败；整体没有明确的统一 fail-fast 包装。是否有外部 runner 检查各步退出码未披露，不能由片段断言生产系统一定忽略失败。
4. dataset 的 `pre_commands`、论文 D 和现今 AweAgent `PreAgentSetup` 并不是逐字相同的脚本；接入时必须执行并记录选定版本，不以“都有 anti-hack”视为等价。

这些是覆盖边界和静态解释，本轮没有构造真实数据集攻击，也没有复现 reward hacking。

## 5. 任务分布与数据比较：作者测了什么

### 5.1 Table 1 的全部统计（按 HTML 表项）

| 指标 | Mean | P50 | P75 | P95 |
| --- | ---: | ---: | ---: | ---: |
| Modified Files | 6.4 | 3.0 | 6.0 | 18.0 |
| Deleted Lines | 54.9 | 1.0 | 10.0 | 119.0 |
| Added Lines | 220.8 | 43.0 | 120.0 | 595.0 |
| Edited Lines | 37.0 | 6.0 | 20.0 | 108.0 |
| Total Changes | 312.7 | 63.0 | 167.0 | 867.0 |
| Fail-to-Pass | 5.7 | 2.0 | 5.0 | 15.0 |
| Pass-to-Pass | 209.0 | 68.0 | 178.0 | 793.0 |
| Total tests | 214.7 | 72.0 | 185.0 | 801.7 |

这是作者构建集合的统计，不是本轮对20,181公开行的复算。正文使用 F2P 平均5.69，表中四舍五入5.7。分位数不要求逐列可加，P95 的801.7也不应被“修正”为整数。修改行数和测试数只能说明工作量的一部分，不能独自衡量语义难度、覆盖率或无泄漏。

### 5.2 Table 2 的来源比较（保留作者分类）

| Dataset | 可执行实例 | Primary Source | 仓库数 | Traj. |
| --- | ---: | --- | ---: | ---: |
| R2E-Gym | 4.6k | Synthetic | 10 | 3.3k |
| SWE-Gym | 2.4k | Real | 11 | 491 |
| SWE-smith | 50k | Synthetic | 128 | 5k |
| SWE-Mirror | 60k | Synthetic | 40 | 12k |
| SWE-rebench | 7.5k | Real | 3.5k | N/A |
| Scale-SWE | 100k | Real | 5.2k | 71k |

这是 **v4 作者选定的历史资产对照**。SWE-rebench 行引用 `2505.20411` 原版，不能替换为我们已经阅读的 SWE-rebench V2。这里的 Traj. 也不是 Table 4 为每个来源重新蒸馏后实际用于训练的统一数量。[P, Table 2、References][P]

### 5.3 Fig.3 与 Fig.4 的证据力度

作者采用 BugPilot 的十类 taxonomy，并用 **DeepSeek v3.2 自动标注**：API Mismatch、Logic Error、Input/Boundary、Constructor、Import Error、State Sync、Mutability、Spec Violation、I/O Resource、Security。Fig.3 被作者解释为 Scale-SWE 分布更均衡，SWE-smith 更集中于 Logic Error。[P, §2.4、Fig.3][P]

没有公开这一分类器的准确率、逐题标注、置信区间或同 taxonomy 的人工复核，因此不能将它当作与任务难度完全独立的客观测量。论文说 SWE-Gym 仓库多样性较低，作者网页又说其 bug 类别相对均衡；仓库数量与缺陷类别分布不是同一维度，两句话不能直接合并成冲突。

Fig.4 描绘成功蒸馏轨迹的总 token 数与工具调用轮数密度，作者解释为 Scale-SWE 需要更长探索与调试。原图本轮未读，不估曲线峰值、尾部或均值。即使观察到更长轨迹，也可能同时包含教师风格、harness、环境效率等因素；它不是“无泄漏”的充分证明，也不是学生训练后效率提升的证据。

<a id="training"></a>
## 6. 后训练、评测、对照与结果限制

### 6.1 教师轨迹与学生优化是两个阶段

| 阶段 | 模型／方法 | 数据与预算 | 输出与未知项 |
| --- | --- | --- | --- |
| 数据生产 | DeepSeek v3.1/v3.2；PSWA 为 Gemini3-Pro；SWE-agent | 真实 PR、源码、gold diff、测试和交互环境 | 未给完整版本、重试次数和构建 API 成本 |
| 轨迹采样 | DeepSeek-V3.2；OpenHands 实验框架 | 25k任务；每题5次；temperature0.95；100 turns上限 | 通过全部测试的71,498条；无失败轨迹训练对照 |
| 学生训练 | Qwen3-30B-A3B-Instruct；SFT | 教师成功轨迹，约3.5B序列tokens | Scale-SWE-Agent；不是从零预训练，也不是Qwen3-Coder起点 |
| 推理评测 | Scale-SWE-Agent；论文称OpenHands | SWE-bench Verified500题；最大context262,144 | resolved rate；详细attempt/retry/seed协议缺失 |

Appendix C / Table 5：

| 超参数 | v4 披露 |
| --- | --- |
| Learning rate | 1e-5 |
| Base model | Table5简写Qwen3-30B-A3B；正文为-Instruct |
| Batch size | 128 |
| Maximum context length | 131,072 |
| Warmup ratio | 0.05 |
| Scheduler | Cosine |
| Epoch | 3 |

论文没有完整 SFT objective、assistant/tool/thinking mask、token/sequence 分母、截断样本处理、packing、optimizer/betas、precision、全参或PEFT细节、并行布局、gradient checkpointing 或硬件清单。**未说明PEFT不等于已经证明全参数训练；模型卡展示BF16不等于训练计算全程BF16。** 不用常见框架默认值补齐。

约3.5B是数据token规模，不等于产生梯度的assistant token规模；3个epoch也不能不考虑截断/packing便写成实测10.5B有效训练token。平均约49k序列token/成功轨迹只是由两个汇总量相除的估算，不替代长度分布。

未见 RL reward优化、PPO/GRPO、critic、KL、OPD教师概率、staleness、权重同步等训练阶段。二元测试用来筛选教师成功轨迹，不能据此把方法描述为RLVR。题库适合RL是复用方向，尚非本篇实验证明。

### 6.2 评测协议应随数字一起保存

作者称所有实验采用 OpenHands，支持文件编辑、shell和网络浏览；训练context131,072，推理放宽到262,144。评测是500题的SWE-bench Verified，指标为解决题数占总题数的比例。[P, §3.1][P]

正文没有钉死OpenHands commit、提示词、评分器revision、全部模型的effort/turn/token预算、每题重复次数、随机种子、失败重试和样本级列表。Table3中不少外部结果带原工作引用，未逐行说明哪些本地重跑、哪些引自发布；**“统一框架”一句不足以证明整张异质模型表是完全匹配的同平台实验。**

没有第二个公开benchmark、跨harness迁移或无关能力保持结果。Figure1按激活参数表达效率，不能替代同硬件吞吐、GPUh或每次成功成本。

### 6.3 Table 3：完整保留历史比较，不加工成当前排行榜

| 原表组别 | 模型 | Base Model（沿用原表） | Resolved Rate % |
| --- | --- | --- | ---: |
| Proprietary Models | GPT-5.2 Thinking | — | 80.0 |
| 同上 | Claude Sonnet 4.5 | — | 77.2 |
| 同上 | Gemini 3 Pro | — | 76.2 |
| 同上 | MiniMax-M2.1 | — | 74.0 |
| 同上 | GLM-4.7 | — | 73.8 |
| 同上 | DeepSeek-V3.2 | — | 73.1 |
| 同上 | Kimi K2 Thinking | — | 71.3 |
| Open Source Methods | SWE-Gym-32B | Qwen-2.5 coder | 20.6 |
| 同上 | SWE-Fixer-72B | Qwen2.5-72B | 32.8 |
| 同上 | R2E-Gym-32B | Qwen-2.5-Coder | 34.4 |
| 同上 | SWE-rebench-72B | Qwen2.5-72B-Instruct | 39.0 |
| 同上 | SWE-smith-32B | Qwen2.5-32B | 40.2 |
| 同上 | SWE-RL | Llama3-70B | 41.0 |
| 同上 | Skywork-SWE-32B | Qwen2.5-Coder-32B-Instruct | 47.9 |
| 同上 | SWE-Mirror-LM-32B | Qwen2.5-Coder-32B-Instruct | 52.2 |
| 同上 | SWE-Lego-32B | Qwen3-32B | 52.6 |
| 同上 | KAT-Dev-32B | — | 62.4 |
| Models of the same size | Qwen3-30B-A3B-Instruct | — | 22.0 |
| 同上 | Qwen3-Coder-30B-A3B-Instruct | — | 51.6 |
| 同上 | GLM-4.7-Flash-30A3B | — | 59.2 |
| Our Model | Scale-SWE-Agent | Qwen3-30B-A3B-Instruct | 64.0 |

“Proprietary Models”是作者原分组名，不表示本稿重新判定每项模型的权重开放状况。不同底座、规模与训练历史不可合并为一个单变量比较。[P, Table3][P]

按表直接算：相对起点 **+42.0个百分点**；相对Qwen3-Coder **+12.4pp**；相对GLM-4.7-Flash **+4.8pp**；相对KAT-Dev **+1.6pp**。64/22≈2.91指解决率之比，不代表单位计算效率近三倍；单次小分差未报告置信区间，不能认定稳健显著胜出。

### 6.4 Table 4：统一蒸馏管线的对照，不是所有变量都匹配

| 教师轨迹来源 | SWE-bench Verified % |
| --- | ---: |
| SWE-Gym | 54.8 |
| SWE-smith | 54.6 |
| Scale-SWE | 64.0 |

这是本文最接近数据路线对照的实验。作者明确说三者采用相同distillation/SFT pipeline，所以其证据强于仅拼接三个模型发布分数。但**没有给三条分支最终成功轨迹数、实际训练token、仓库覆盖、每题重复量、总教师采样与完整费用的对齐表**。[P, §2.4、§3.2、Table4][P]

因此支持的结论是：在作者实施的管线下，Scale-SWE分支优于两个数据分支，分别高9.2和9.4pp。作者进一步认为真实数据天然优于大规模合成，本稿保留这一解释，但不将其升级为普遍因果定律。SWE-smith与SWE-Gym差0.2pp，在500题单次口径下相当于一题，没有重复统计支持“合成训练已饱和”。Table2里原资产的Traj.不能拿来填这里未披露的新蒸馏量。

### 6.5 60%、64%及后来61.4%必须分开

v4内部：§1训练段写 **22%→60%**；同版Abstract、贡献列表、§3/Table3与Conclusion写 **64%**。本文主要结果按明确Table3记录64，同时保留引言60的差异。**没有原作者勘误，不能自称已证实60就是旧版残留。**

当前AweAgent另有[官方收录的复跑说明][C7]：500题提交，498 completed，307 resolved、191 unresolved，2 empty patches，0 error，采用500为分母得到 **61.4%**。它说明作者完整setup可稳定到64，而所给参考材料略低；该解释是说明中的主张，非本文复现。

更重要的是，该说明主动列出依赖：`swebench==4.1.0`的两项兼容补丁、prediction cleanup、以及**没有一并发布的runtime/prompt/tool-call改动**；完整轨迹、预测与运行日志不在该目录。故不是“运行未改动的main即可得到61.4%”，也不是完整独立复现64%。

复跑配置还包含temperature1、200 turns、模型服务262,144 context、agent max_context220,000及每次response16,384等不同层级预算。它们不能反填为v4历史实验的完整参数。声明中的清理修改了491/500行预测，去除.gitignore和临时脚本等；没有前后分数对照，不能认定它无影响，也不能凭数量指控作弊。正确处理是把补丁投影、parser和资源设置都作为评测协议记录。

<a id="assets"></a>
## 7. 实际可消费的开放资产

### 7.1 任务包字段：名称相似不代表与SWE-bench直接同schema

| 字段 | 本文／公开资产含义 | 接入注意 |
| --- | --- | --- |
| instance_id | `{user}_{repo}_pr{id}` | 与轨迹data_source进行实际关联 |
| user、repo | 仓库所有者和名称 | 两字段组成完整repo；owner数不是repo数 |
| language | 当前Python | Java/C/C++/Rust是未来计划 |
| workdir | 容器工作目录 | 不固定为`/testbed`，预览常为`/workspace/<repo>` |
| image_url | 预构建镜像引用 | 预览如`aweaiteam/scaleswe:<instance_id>`；tag不是内容digest |
| patch | 真实PR的gold diff | 只能进入可信构建/验证侧，不作为policy输入 |
| pr_commit、parent_commit | 修复与base提交 | 作者loader将parent_commit映射到base_commit |
| problem_statement | PSWA重写题面 | 不能当作原issue全文 |
| f2p_patch | 开发者测试补丁（如有） | 非gold修复patch；不与f2p_script互斥 |
| f2p_script | 合成测试Python代码 | 官方说明要求评分前写到仓库根`test_fail_to_pass.py`，不是拿字符串当shell执行 |
| FAIL_TO_PASS、PASS_TO_PASS | 指定测试ID | viewer显示为JSON编码字符串；loader/evaluator还允许list，不能假定已解析 |
| github_url | 原始仓库地址 | 存在字段不代表求解时允许访问完整在线历史 |
| pre_commands | 初始环境与Git清理命令 | 会修改状态；须作为可信setup执行并检查结果，不能忽略失败 |

来源：Appendix B；[HF任务卡][D1]；[固定task loader][C1]。这16个原字段是任务资产，不构成完整训练轨迹schema。原始镜像Dockerfile、所有构建失败轨迹、完整筛选与生产编排未在主仓库检查范围内取得。

### 7.2 公开样本揭示的三种测试组合

本轮只检查HF viewer的若干可见行，**不是随机质量审计，也没有真实执行这些题**：

| 示例 | 可见字段形态 | 对接入的实际启示 |
| --- | --- | --- |
| `auth0_auth0-python_pr671` | f2p_patch为空；f2p_script非空；F2P指向test_fail_to_pass.py | 合成脚本必须落为文件后按ID调用 |
| `beetbox_beets_pr3661` | 两个测试字段都非空；F2P指向生成文件 | 两个字段同时布置，不由是否存在patch决定忽略script |
| `adamtheturtle_doccmd_pr42` | 两字段非空；F2P指向原`tests/test_doccmd.py` | script存在不代表它的全部函数实际在本题评分集合中 |
| `andialbrecht_sqlparse_pr330` | f2p_patch非空；f2p_script为空 | 必须保留原测试patch支持路径 |

题面可能是feature request或迁移，不全是狭义bug修复。仓库、代码修改与测试种类的实际范围，应在选择子集时保留，不能仅按“都来自PR”视为同质。

### 7.3 蒸馏资产不是已带TITO信息的RL轨迹

[D2][D2]实际viewer schema为`messages`、`data_source`、`system`；预览中有OpenHands角色和多轮交互。[文件目录][D2files]为8个parquet shard，总大小约4.72GB，页面精确计数71,498。数据卡却复用任务集字段说明，**数据卡表格不等于实际parquet schema**。

这些字段支持离线SFT候选。预览没有原始token IDs、行为logprob、权重version、路由或loss mask字段，不能直接当作可作importance correction的历史on-policy样本；是否在别的附件补充这些内容本轮未确认。导入时还需处理system字段与messages中system消息的关系，避免重复注入；具体训练时的rendering和mask不能由这份卡片倒推出。

公开成功轨迹的长度与当时目标学生在rh2中的成功分布是两件事。没有目标模型的真实采样，不能用教师通过比例判断这批任务适合直接GRPO。

### 7.4 发布范围与后续版本

[G README][G]写明2026-02-26只发布一部分：20k任务和71k轨迹；HF实际当前可读统计分别为20,181和71,498。2026-06-11的41k条 **DeepSeek-v4-Pro-High** 新轨迹、以及新数据集 **DeNovoSWE** 是后续资产，不属于v4的DeepSeek-V3.2配方。

主仓库固定版本根目录包含README、LICENSE、figures及SWE-bench Verified评测轨迹目录；本轮未看到完整EBA/UCA/PSWA生产程序或SFT训练脚本。AweAgent提供后来接入与运行代码，但不因此成为原始生产或训练管线的完全开放实现。

| 资产 | 本轮取到什么 | 尚未验证 |
| --- | --- | --- |
| 20,181任务 | 数据卡、schema、预览、数据文件入口，约984MB | 全量去重、仓库数、gold/no-op、20k与25k任务关联 |
| 71,498轨迹 | schema、预览、精确行数、8shard入口 | 全量内容和token统计、成功重跑、完整与超长样本处理 |
| Docker镜像 | 每题image_url示例 | registry可拉取、体系结构、digest、重建和运行成本 |
| 学生模型 | 模型卡与权重入口 | 原始base精确revision、权重摘要、硬件执行与评测 |
| 评测轨迹目录 | 固定官方仓库中确实存在 | 未逐条审阅，不用目录名推定它等于320题成功的完整可复核证据 |
| 当前评分代码 | 实际调用链定点静态阅读 | 未在ScaleSWE真实容器复现正确／错误patch |

<a id="implementation"></a>
## 8. 当前评分实现：实际控制流与语义边界

这里所有代码固定AweAgent `b38414e5...`，晚于2026-03-24论文；静态发现不倒推作者历史数据或分数一定有同样问题。

### 8.1 从task loader到评分

```text
ScaleSWETask._to_instance
  parent_commit→base_commit；image_url→image；user/repo拼接
  pre_commands→setup_commands；F2P/P2P与两种测试字段保留在metadata
    ↓ default_evaluator() 返回 ScaleSWEEvaluator
调用继承的 PatchTestEvaluator.evaluate
  fresh runtime.session(image)
  → checkout base → pre_patch_setup/PreAgentSetup
  → 应用候选patch → restore_test_files
  → ScaleSWEEvaluator.run_tests
      → BeyondSWEEvaluator._eval_beyondswe
          → 布置f2p_patch和test_fail_to_pass.py
          → F2P IDs + P2P IDs 合并运行
          → run_tests_with_runner → EvalResult
```

来源：[task.py][C1]、[ScaleSWE evaluator][C2]、[共享BeyondSWE evaluator][C3]、[base evaluator][C4]、[setup][C5]、[test runner][C6]。

旧README链接的`awe_agent/tasks/beyond_swe/evaluator.py`在当前版本404；真实包名已是`aweagent/`。这是版本化入口变化，不能据死链接认定代码从未开放。

### 8.2 F2P/P2P执行与错误返回

`_eval_beyondswe`先应用f2p_patch，失败返回`accepted=False, score=0`且附`f2p_patch_failed`；接着将script作为文件上传；调用`parse_test_ids`支持JSON字符串或list，构造 **f2p_ids+p2p_ids**。两者都空时返回`no_test_ids`，测试时间上限取配置与1800秒的较小值。末端给二元0/1，没有按部分测试通过率给ScaleSWE部分reward。[C3][C3]

这只描述当前实现的顺序和错误分类。论文质量验证称固定执行顺序，却没有证明历史上就是当前“F2P在前、一次pytest”的方式。

基类为评分创建新的session，并恢复若干test目录、test命名文件和conftest以减少测试篡改。这不代表所有构建配置、pytest插件、源代码导入副作用都被隔离；同时，真实任务若确实要求修改测试相关工件，恢复规则可能改变提交含义，需要按实际任务核对。[C4][C4]

### 8.3 强检查存在，但不保证每次都执行到

`run_tests_with_runner`上传pytest runner与config，runner调用：

```text
pytest -vv --junitxml=... -o addopts= --rootdir=. <test_ids>
```

然后根据pytest返回值打印`<pytest>true</pytest>`或false。外层第一条分支只要在输出中发现true标记，便直接返回成功；没有先验证每个expected ID。若没有true标记才读JUnit XML；再不行就退回summary。[C6, PYTEST_RUNNER_SCRIPT、run_tests_with_runner][C6]

XML路径的检查更严格：多种ID归一化／匹配后，要求至少一个expected被找到、所有匹配均通过、无缺失expected；被skip的case被忽略，因此仍留在缺失集合。summary路径则只检查至少一个passed且无failed/errors，不要求所有预期ID执行。**三条路径的接受条件不等价。**

本轮做了一个最小、无网络的合成实验：Python3.13.5、pytest9.0.2，一个通过用例加一个skip用例，使用与源码runner相同参数。结果pytest返回0并生成true标记，但JUnit中仍有一个skipped expected。它证实“pytest整体成功”弱于“所有指定测试实际通过”。结合当前fast path，可提出应核对的条件性评分风险；**没有执行完整AweAgent，也未证明哪一道真实ScaleSWE题受影响，更未证明论文64%被高估**。复现代码和输出记在[自查记录][Review]。

代码还允许某些setup命令失败后仅记录warning继续，基类捕获异常后也会返回0分。因此使用这套输出做RL时，至少要保留details，区分agent的合法任务失败与环境／评分失败；不能把全部0分当成同类学习信号。[C4][C4] [C5][C5]

### 8.4 本轮没有审计的代码范围

没有展开完整runtime实现、镜像拉取、网络策略、候选patch提取、所有repo-specific兼容补丁、模型服务和分布式训练。复跑README里的prediction cleanup和parser/resource补丁只确认其声明与文件存在，未逐个执行，不将它们自动判为“无语义影响”。

<a id="limits"></a>
## 9. 成本、可复现性与证据等级

### 9.1 成本表

| 阶段 | 披露的规模／机制 | 可读来源未给出的成本 |
| --- | --- | --- |
| 仓库/PR采集筛选 | 23k候选、6M PR、1M入选；LLM judge | API tokens/费用、爬取时长、重试、人工修复 |
| 环境构建 | 每仓库≤10个PR锚点；邻近PR复用 | 实际构建数、镜像总大小、CPUh、build/cache失败率 |
| 测试与题面 | 三角色、反复执行、100题人工抽审 | 每关token、执行次数、人工人时、无效任务成本 |
| 教师轨迹 | 25k×5计划、100turns、71,498成功、约3.5B tokens | 总输出/输入缓存收费、失败轨迹tokens、墙钟、超时重试 |
| SFT | batch128、131k、3epochs | GPU型号/数量、GPUh、并行策略、精度、有效loss token |
| 论文评测 | 500题、262kcontext | 全部调用预算、总tokens/API/GPU/CPU费用、重复次数 |
| 后来61.4复跑 | 8GPU服务命令、TP8、并发等示例 | GPU型号和全流程GPUh；未发布的runtime改变成本 |

“论文称效率更好”主要基于参数规模与分数，不足以估算本项目8×96GB的全流程成本。不能拿激活3B当成3B dense训练，也不能将后来的TP8推理命令当成原论文SFT硬件。

### 9.2 它已经证明与尚未证明什么

**训练证据：**作者确实报告了成功轨迹SFT和模型结果，非只有框架想法。**对照证据：**Table4统一蒸馏管线有参考价值，但未充分隔离数据量、成功率、token和仓库覆盖。**代码／资产证据：**有部分任务、轨迹、模型及可读的当前评分实现，不等于全量生产／训练复现。**独立复现：**本轮未确认；作者repo中的61.4材料也不能自动标成独立完整复现。

没有直接证据支持：Scale-SWE对任意目标模型优于其他RL题源；更多P2P就无错误评分；长轨迹就没有题面泄漏；多agent生产优于每种简单builder；当前打包任务可直接成为rh2正式训练集；方法在第二harness、第二语言或其他能力域上稳定泛化。

### 9.3 未知与访问缺口分开记录

| 项目 | 类型 | 已查范围／后续所需证据 |
| --- | --- | --- |
| 生产prompts全文 | 本轮未取得，不是未披露 | AppendixE渲染失败；需要v4 PDF或TeX |
| Fig1–5精确图形及PDF页码 | 本轮未取得 | 文本/图注可读；需原图页补核表格和图中文字 |
| EBA/UCA重试、采样、停止规则 | 可读正文未完整披露；可能受E缺口影响 | 不在读完E之前断言整篇无这些细节 |
| 历史完整训练脚本和mask | 可读正文/C未披露，当前主repo未发现 | 不以其他框架默认值补齐 |
| 25k选样与全部评测排除manifest | 可读正文未披露 | 需实际资产与作者说明 |
| 每个Table4分支的成功轨迹/token总量 | 可读正文未披露 | “identical pipeline”不等于全部预算相同 |
| 94题有效的人工协议细节 | 可读正文未披露 | 抽审清单、分歧和缺陷统计未取得 |
| HF全量、镜像拉取和gold/no-op | 本轮未执行 | 页面可读不能代替真实验证 |
| 跨harness/RL/多语言效果 | 本篇未报告 | 不能用后续资产／无关论文补成本篇结果 |
| 60与64的原因 | 原文存在差异，原因未确认 | 无勘误不静默统一 |

<a id="mapping"></a>
## 10. 对B侧数据／环境决策的分析

以下是**2026-09-08的项目推论**，不是论文已经在RepoHarness证明的结论。项目基线是miles/SGLang、真实coding harness和rh2；硬件约8×96GB，模型目标约30B总参数／3B激活。[B][B]

### 10.1 推荐定位

Scale-SWE值得作为 **真实PR来源的第二候选池、完整轨迹SFT候选及环境复用设计参考**，但不宜现在直接替换现有题源、照搬100k生产线或宣布选定为正式GRPO数据。

对环境侧，最可复用的是“少量锚点环境＋大量邻近PR复核”，以及“PSWA必须知道测试需要哪些新接口”。对学习侧，强证据是与目标量级接近的模型在成功轨迹SFT后改善；直接RL可学习性仍需目标模型采样。对infra侧，当前评分链的字段类型、测试布置和成功条件很具体，适合做adapter与参考scorer对照。

### 10.2 四个有限、能决定是否接入的检查

| 检查 | 冻结／比较什么 | 决策用途 |
| --- | --- | --- |
| **资产与谱系** | 固定D1/D2 revision；统计repo/base/PR/task去重；data_source关联；标注本项目train/dev/test重叠 | 判断有多少可重放任务与可用SFT轨迹，不用100k做可取得资产预算 |
| **原评分路径与rh2等义** | 选覆盖script-only、patch-only、两者并存和特殊测试的代表题；同base与gold/empty/普通失败候选；比较逐测试事实及终局判定 | 先解释差异，再决定修接入还是淘汰题；不要只比较一位reward |
| **环境可复用性与成本** | 拉取固定digest，在干净session运行setup/gold/no-op；少量代表重复，记录CPU/内存/执行时间和状态差异 | 判断是否值得使用现成镜像，哪些兼容问题是系统而非学生能力 |
| **目标模型学习机会** | 固定模型具体variant、harness、context/turn/time预算，对环境合格小池采样；同时记录组内信号和失败类型 | 判断先做小型静态RL、补SFT，还是换任务；不拿DeepSeek教师成功率代替 |

这些是诊断而非新通用平台。跳过/未收集测试、测试补丁冲突、setup失败应保留为独立事实；可判分的模型失败也不能被环境层统一过滤，具体梯度与组统计处理留给A侧算法合同。

### 10.3 不能机械搬来的三条结论

**真实比合成好。** 可作为待检验假设；Table4没有隔离所有重要因素。不要因此放弃SWE-smith等低成本来源。

**长轨迹意味着值得训练。** 它也可能是环境低效、教师风格或无效循环。需要终局成功、成本和目标模型分布共同判断。

**评分代码公开就能直接上线。** 当前runner的fast path与完整ID检查语义不同；先在小规模参考用例证明符合我们的声明，再决定复用或窄修正。这里没有批准改上游或发PR。

### 10.4 B可以先定什么，不必等什么

可以先定这条来源进入**小批候选比较**，先消费明确可取得的20,181任务或71,498成功轨迹中的合适子集。可以按原始三种测试字段组合准备adapter检查，也可以先比较SFT初始化需求。

尚不能据本篇定正式taskset大小、永久train/test分割、在线课程、完整环境合成平台或八卡训练时长。PDF/E缺口应补齐以完成文献核验，但本地数据读取、schema对账与环境探针不必因此停住。

## 11. 结论与后续维护

Scale-SWE提供一条具有实际训练结果的路线：**真实PR多样性＋交互构建环境与测试＋需求重写＋成功轨迹SFT**。它最值得借鉴的不是“再多20k题”，而是将题面、测试和可执行环境共同生产，并将环境建设成本与PR实例数量分离。

本轮也说明三类东西需要分别维护：论文的100k构建与64%结果；当前公开的20,181任务和71,498轨迹；晚于论文的AweAgent实现与61.4%复跑材料。它们互相关联，却不是同一个冻结实验。

**文档交付状态：主体精读与资产/代码核查稿已形成，作者自查完成；附录E、原图和PDF页码待补，独立复查未进行。** 本稿是O05的后续维护入口，不因一次提交就在共享索引登记为完整精读通过。补读只需回到明确缺口，不从零重写。

[自查与合成探针记录][Review]保存实际范围、算术和后续核查项。其他已读数据论文可用于之后的跨来源比较，本稿未借用其结论替Scale-SWE补历史实验。

## 来源链接

[P0]: https://arxiv.org/abs/2602.09892v4
[P]: https://arxiv.org/html/2602.09892v4
[PDF]: https://arxiv.org/pdf/2602.09892v4
[W]: https://aweai-team.github.io/projects/scaleswe/
[G]: https://github.com/AweAI-Team/ScaleSWE/tree/b531926bf4fc069451eca390587a4e30c1b1bb21
[D1]: https://huggingface.co/datasets/AweAI-Team/Scale-SWE
[D2]: https://huggingface.co/datasets/AweAI-Team/Scale-SWE-Distilled
[D1pin]: https://huggingface.co/datasets/AweAI-Team/Scale-SWE/tree/d8db20390a936bbda9c96d88b97cc4778dff1481
[D2pin]: https://huggingface.co/datasets/AweAI-Team/Scale-SWE-Distilled/tree/c14ce2130f494812fef907f4afc81d8e33990805
[D2files]: https://huggingface.co/datasets/AweAI-Team/Scale-SWE-Distilled/tree/main/data
[M]: https://huggingface.co/AweAI-Team/Scale-SWE-Agent
[C]: https://github.com/AweAI-Team/AweAgent/tree/b38414e5dc9c7c51f2ec48318b718af0c8852060
[C1]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/tasks/scale_swe/task.py
[C2]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/tasks/scale_swe/evaluator.py
[C3]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/tasks/beyond_swe/evaluator.py
[C4]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/core/eval/base.py
[C5]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/core/eval/setup.py
[C6]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/aweagent/core/eval/utils.py
[C7]: https://github.com/AweAI-Team/AweAgent/blob/b38414e5dc9c7c51f2ec48318b718af0c8852060/recipes/scale_swe/swebench_verified/README.md
[B]: https://github.com/Rogerffff/RepoHarness/blob/bbce8683b025077ac1bed5da7d7587a6f1ec8dcb/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/b_external_reading_requests_20260908.md
[Review]: reviews/O05_scale_swe_self_check_20260908.md
