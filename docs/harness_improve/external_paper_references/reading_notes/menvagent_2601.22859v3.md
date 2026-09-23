# MEnvAgent v3：可验证 SWE 环境的构建、增量复用与下游 SFT

MEnvAgent 将环境生产分成规划、执行、验证，并在已有同仓环境上用增量安装命令适配新任务。MEnvBench 的 1,000 题实验中，作者报告相对 SWE-Factory 的平均 F2P 提高 8.6 个百分点、平均构建时间减少约 43%；这不是 RL 吞吐或全流程费用的改善。下游证据是 3,872 条成功教师轨迹的 SFT，不是在线 RL。对 RepoHarness 最有用的是“复用依赖修复，但仍验证当前任务”的分工。重要边界包括：较新环境向后兼容只是检索假设；F2P 不证明题意与测试完整；当前官方核心构建代码尚未发布；数据卡、文件树和论文计数存在需版本化核对的差异。

导航：[范围与版本](#scope) · [方法与验证语义](#method) · [数据与构建实验](#build) · [SFT 与成本](#training) · [公开代码／资产](#assets) · [项目意义与检查](#project)

<a id="scope"></a>
## 1. 来源、版本和实际完成范围

**主来源 P：** *MEnvAgent: Scalable Polyglot Environment Construction for Verifiable Software Engineering*。作者为 Chuanzhe Guo、Jingjing Wu、Sijun He、Yang Chen、Zhaoqi Kuang、Shilong Fan、Bingjin Chen、Siqi Bao、Jing Liu、Hua Wu、Qingfu Zhu、Wanxiang Che、Haifeng Wang；机构为哈尔滨工业大学和百度。以 [arXiv v3 HTML][PH]、[PDF 原文入口][P] 为主；[版本历史][PA]列 v1 为 2026-01-30、v2 为 2026-02-02、**v3 为 2026-06-06**。本次阅读日期 **2026-09-24**。原文许可 CC BY 4.0；下文是注明来源的中文释读、选取的实验数据和独立分析，不是作者中文稿。

**完成状态：正文 §1–8、Impact Statement、参考文献及附录 A–I 的可取得原文文本已精读，关键代码／数据入口已定点核查，作者自查完成。部分 PDF 原图的 v3 版本一致性尚未闭合；无独立 reviewer、无环境／SFT 复现。** 不能简写成“全文全部图页独立核验通过”。

**来源取得的特殊限制。** v3 HTML 显示完整目录、v3 标识与公式；无版本 PDF 入口的解析文本共 25 页，与该目录一致。已取得多张 PDF 图页，但无版本入口部分截图返回旧排版：例如返回的 p.22–24 把数据集附录标为 G，v3 文本中相应部分是 I，且 v3 新增的 G/H 不在这些截图中。本文拒绝用这种截图证明 v3 位置或缺失内容，章节／表号统一以 v3 HTML 和 25 页解析文本为准。未取得可在本地打开的完整 PDF bytes 或 TeX；没有以重绘图替代原图核验。具体已核与缺口见检查记录。

**公开代码 C：** `ernie-research/MEnvAgent@d9e63881f7c4a4670bb536c89add24573459bbee`，提交日期 2026-02-03。它早于 v3 约四个月。递归目录完整取得；实际检查范围见 §8。**源码存在与论文所述全部实现开放是不同结论。**

**项目基线：** `Rogerffff/RepoHarness@0554dafd633cd982288bd60a54f75da65e5c54d4`，`codex/project-status-20260923`。本任务独立写入 `pro/menvagent-reading-20260924`，不合并前三个阅读分支，不改实施代码或共享索引。

**复用旧稿：**[环境专题 05 的 MEnvAgent 段](../environment_processing_survey_20260915/05_new_environment_builders.md)已经正确定位 PEV、同仓复用、pyrainbird 案例与 F2P 的有限含义。本稿保留这些定位，补齐 benchmark、消融、全部下游 SFT、成本、公开资产和代码；不把旧专题当作独立原文证据。

### 1.1 原文覆盖表

页码按 v3 的 25 页解析文本，表／图编号按 v3；视觉状态另列，避免跨缓存版本混合。

| 原文范围 | 内容与处理 | 本稿位置 |
| --- | --- | --- |
| 摘要、§1，pp.1–2，Fig.1 | 问题、三类贡献、人工与自动构建；全读 | 摘要、§2 |
| §2，pp.2–3，Eq.1–2 | 环境三元组、PASS 与 F2P；逐式核对 | §2.2 |
| §3，pp.3–4，Fig.2，Eq.3–4 | 六角色、检索、增量适配、回退；全读 | §3 |
| §4–5，pp.4–6，Table 1–2，Fig.3 | 数据构建、指标、模型／基线、主要构建结果；全读 | §4–5 |
| §6.1–6.2，pp.6–7，Table 3，Fig.4–6 | 复用消融、历史密度、仓库规模与失败；全读 | §5.2–5.4 |
| §6.3，pp.7–8，Table 4 | 教师、五个学生、OpenHands 与 SWE 评测；全读 | §6 |
| §7–8、Impact Statement，pp.8–9 | 与前作分工、总结及执行风险；全读 | §2.1、§9 |
| References，pp.9–11 | 检查引用身份与全文结束位置；未全文重读所有引文 | §2.1、§9 |
| A，p.12 | 可验证 benchmark、真实／合成训练数据的分类；全读 | §2.1、§6.4 |
| B，pp.12–13，Eq.5–8 | 状态转移、基础镜像与二元结果形式化；全读 | §2.2 |
| C，pp.13–16，Table 5、Alg.1、Fig.7 | I/O、控制流程、home-assistant 复用例；全读 | §3 |
| D，pp.14–20，Table 6–7、Fig.8–10、Listing 1–2 | 过滤、judge 提示、原始漏斗、领域／规模、样例；全读文本 | §4 |
| E，p.20，Table 8 | 并发、温度、超时、迭代配置；全读 | §5.1 |
| F，pp.20–21，Table 9–10 | 全语言结果、token 和 API 成本；全读并对读原表图页 | §5.1、§7 |
| G，p.22，Table 11 | 200 题跨语言复用消融；全读文本，v3 表页目视待补 | §5.3 |
| H，pp.22–23 | C++ 五种失败及比例；全读 | §5.4 |
| I，pp.23–25，Table 12–13 | 生产、验证、语言分布、比较、SFT 配置；全读 | §6–7 |

Fig.7–9 的案例和提示词内容可从 PDF 文本恢复；Fig.10 的部分条形数据只能从提取内容看到，本文不将未闭合的原图读数写成精确分布。主文图表与返回的共同版本内容已经目视检查；不能因此声称整份 v3 PDF 已逐页一致。

<a id="method"></a>
## 2. 核心问题：生产可执行任务，不是提出新的 RL 优化器

### 2.1 三项贡献与两条实验线

作者将 agent 训练的数据瓶颈定位于：真实仓库的依赖、构建和测试方式各异，安装／编译昂贵，失败后从头重建浪费。MEnvAgent 用专门角色形成 Planning–Execution–Verification（PEV）循环，并尝试复用历史环境。三个产物是构建方法、用于评估构建能力的 **MEnvBench**、以及带环境和解题轨迹的 **MEnvData-SWE**。[P, §1、§7–8；A][PH]

要分开两条证据链：

```text
固定 LLM 作为构建代理 → MEnvBench → 构建 PASS/F2P、时间、API 成本

构建 MEnvData-SWE → Claude 教师在 OpenHands 中求解 → 保留成功轨迹
→ 学生 SFT → SWE-bench Verified / Multilingual 的 Resolved Rate
```

第一条不更新环境构建模型；第二条是拒绝采样后的监督微调。文中提到 RLVR 的动机，**没有报告在线 RL、GRPO、critic、OPD 或训练出一个 EnvPatch policy**。不能把可用于 RL 的环境与已验证 RL 训练收益合并。

§7/A 将前作分为静态依赖推断、LLM 安装／执行代理、构建 benchmark、真实或合成 SWE 数据。作者认为自己的构建器可与 SWE-smith 等任务生成器互补；这只是方法关系，不是已经实测了与所有生成器组合的收益。Table 1 对 INSTALLAMATIC、ExecutionAgent、EnvBench、Repo2Run-bench、SweSetupBench-lite 的比较是作者当时的范围划分，不是本次审计各框架现状。其数据规模例子分别是 40、50、994、420、671 个任务；MEnvBench 为 1,000 题、200 仓、10 语言。[P, Table 1；§7；A][PH]

### 2.2 精确恢复验证语义

任务包含目标仓库快照 $R$、issue，以及从关联 PR 拆出的 fix patch 和 test patch。$R_{fix}$ 表示应用修复后的代码状态。构建输出 $(B,\mathcal P,T)$：基础镜像 $B$、安装命令序列 $\mathcal P$、测试配置 $T$。$T$ 包含应用 test patch 和执行测试命令。构建状态 $S=\delta(B,\mathcal P)$。[P, §2][PH]

原文 Eq.1 的 **PASS**：

$$
\varepsilon(R_{fix},S,T)=0.
$$

原文 Eq.2 的 **F2P**：

$$
\varepsilon(R,S,T)=1\quad\land\quad\varepsilon(R_{fix},S,T)=0.
$$

这测的是环境与选定测试是否能区分 buggy/fixed 两个状态。**它不是 actor 的任务解决率，也不是 SWE-bench 逐测试 ID 的 F2P/P2P 列表。** 特别是 Fig.6 的 P2P 指两种代码状态都通过、未复现缺陷；不是一般评分中的“保留原有通过测试”回归集合。

附录 B 将 $\delta(S,c)$ 定义为命令执行后的状态，序列通过逐项复合；$B=\delta(S_{empty},C_B)$，随后 $S=\delta(B,\mathcal P)$。Eq.8 将全部测试通过编码为 0，其他结果编码为 1。**形式化中把状态转移写成确定性，不是联网安装、镜像标签和 shell 状态已经可重现的实验证明。** B.3 结尾又写验证目标为 $\varepsilon(R,\delta(B,\mathcal P),T)=0$，未显式写 $R_{fix}$；本文保留这一记号边界，主要 PASS/F2P 以 §2 和 I.3 的双态操作说明为准。

作者称 F2P 保证可复现 issue，但本篇没有完整证明非零结果必然是目标断言失败，而不是收集、导入、资源或包装脚本错误；没有提供所有合法替代修复、负例、测试修改攻击或重复稳定性审计。因此更保守的可复用事实是：**特定脚本在两个参考状态上给出了期望差异**。这足以做构建有效性检查，不等于需求完整性和训练 reward 的全部可信性已闭合。

## 3. PEV 与增量复用：具体哪些东西能改

### 3.1 六个角色及其职责

| 角色 | 主要输入 | 产物／工作；不是模型训练阶段 |
| --- | --- | --- |
| Repository Analysis Agent | 目标快照、文件树、配置、文档 | 项目类型、构建入口、依赖摘要 |
| Environment Setup Agent | 摘要、上一轮诊断 | 基础镜像和完整安装脚本 |
| Test Configuration Agent | 摘要、安装脚本、反馈 | 与已装工具匹配的测试命令、所需环境变量 |
| Environment Execution Agent | 基础镜像、命令序列 | 实际执行、观察终端、修缺包／版本冲突；多次失败后回规划 |
| Verification Agent | 环境、测试脚本 | 成功标志、环境或测试命令的错误归因；反馈规划角色 |
| EnvPatchAgent | 目标仓库、候选历史环境、失败诊断 | 增量安装命令 $\Delta\mathcal P$，适配该目标 |

[P, §3.1；Table 5, p.14][PH]

验证阶段先让 fixed 状态跑通，再按正文/I.3 补做 F2P。构建器能够修改安装和测试配置，不意味着 solver 被允许修改最终 evaluator，更不意味着可以为通过而删掉行为要求。论文没有给这些权限边界完整的沙箱实现；不能把其多角色图当成代码层已验证的能力隔离。

### 3.2 检索规则比“相似环境检索”更具体

原文用下式表达理想检索目标：

$$
S_{sim}=\arg\min_{S\in\mathcal S_{pool}}\mathcal C_{adapt}(S,R). \tag{3}
$$

实际没有训练一个 adaptation-cost 网络，而是采用同仓历史规则：优先**同仓同版本**；没有精确版本则扩到同仓；选择**比目标快照更新、时间上最近**的环境。前提是较新环境通常向后兼容，不是只检索时间更早的状态，也不是任意跨仓向量检索。[P, §3.2][PH]

适配为：

$$
S_{new}=\delta(S_{sim},\Delta\mathcal P),\qquad
\varepsilon(R,S_{new},T)=1\land\varepsilon(R_{fix},S_{new},T)=0. \tag{4}
$$

流程先生成当前测试配置，尝试历史环境；已满足则直接复用，失败才诊断并生成增量命令，仍失败则从基础镜像重建。它复用的是环境状态／构建积累，**不是重放教师解题动作，也不是复用上一轮候选补丁**。

版本字段怎样定义、没有较新候选时如何选、同时间排序、池初始化／淘汰／并发写入，在论文中没有完整规定。较新的依赖环境可用，不等于可以把未来仓库修复、测试或 git 对象一起交给求解 agent。对这类残留的保证不能仅从 Eq.4 推出来。

### 3.3 Alg.1 与正文不能无条件合并成更完善的实现

Alg.1（p.15）先检索、测试，失败后显示**一次** EnvPatch，再失败进入 `MaxRetries` 的从头构建；正文称 EnvPatch 可循环。算法中早返回的 `VerificationAgent` 是布尔检查，没有显式逐次列出 buggy/fixed 双态，也只在 scratch 成功分支明确向池中添加状态。正文和 I.3 则说明最终 F2P 过滤。[P, Alg.1；§3.1–3.2；I.3][PH]

可理解为高层伪代码省略，但不能因此声称已核查每个复用早返回都执行同一完整 F2P 事务，或所有成功 patch 都自动更新池。核心源码尚未公开，无法在本轮通过实际调用链消除这些缺项。

### 3.4 home-assistant 案例：补依赖，不是放宽验收

Fig.7（p.16）的例子在旧环境执行 `bash eval.sh`，rainbird 的 `conftest.py` 导入 `pyrainbird` 失败，退出码 4。验证代理诊断缺包；EnvPatch 的动作是初始化 conda、激活 `testbed`，然后 `pip install pyrainbird`。再次执行得到 **11 passed in 0.65s** 和退出码 0。[P, C.2；Fig.7][PH]

0.65 秒是末次测试耗时，不是整次修复、模型 API 或镜像构建耗时。图中展示最后 PASS，没有展开 buggy 状态复验；也没有给 pyrainbird 的固定版本。它支持“已有底座加有限依赖修订”的具体可行性，不能据一例证明所有同仓任务都能稳定共享环境。这个 rainbird 例子与 D.5 的 home-assistant remote 功能样例不是同一道题。

<a id="build"></a>
## 4. 数据生产与 benchmark：把候选、成功环境、轨迹分开

### 4.1 原始漏斗与质量筛选

仓库筛选关注 stars、forks、issues、PR 数和主语言比例。正文使用严格大于，Table 6 使用不小于（1,000 stars；其余各 200；主语言 60%）；实现的实际阈值需按固定代码核查，本文不将这两种符号默认为一致。候选 Issue-PR 来自 2018–2025，保留 closed issue、关联 PR、非空 fix/test patch、代码改动，表中规模上限是 1,000 行、10 文件。[P, §4.1；D.1；Table 6–7][PH]

| 语言 | 原始仓库 | 保留仓库 | 原始实例 | 筛后候选实例 |
| --- | ---: | ---: | ---: | ---: |
| Python | 9,515 | 1,722 | 91,072 | 60,872 |
| Java | 3,743 | 692 | 33,164 | 21,379 |
| Go | 3,563 | 771 | 61,216 | 41,113 |
| JavaScript | 7,388 | 1,128 | 18,952 | 13,864 |
| TypeScript | 4,839 | 1,295 | 58,637 | 41,753 |
| Rust | 1,743 | 467 | 20,106 | 13,500 |
| C | 2,273 | 443 | 2,965 | 2,057 |
| C++ | 3,061 | 672 | 11,283 | 7,227 |
| PHP | 1,962 | 427 | 14,129 | 8,376 |
| Ruby | 1,638 | 383 | 5,759 | 3,625 |
| **合计** | **39,725** | **8,000** | **317,283** | **213,766** |

这些是候选来源，不是 213,766 个已构建环境。论文没有给从这个候选池到最后 3,005 个成功任务的完整“实际尝试构建数、构建成功数、F2P 成功数、排除原因与成本”漏斗。**不能据 3,005/213,766 计算环境构建成功率。** MEnvBench 1,000 题是另一个评估抽样，不是 3,005 题生产路径中的中间过滤阶段。[P, D.3；I.1–I.4][PH]

### 4.2 LLM 质量分不等于可执行性审计

DeepSeek-V3.2 按 Fig.8 的扣分提示判断 issue 描述信息是否充分，分数低于 5 被删除。重大扣分包括缺预期输出、复现、版本、完整报错，以及非问题类提交；一般扣分含多目标冲突、模糊约束、外部链接和测试信息不足。输入模板只有 **issue 文本**，不能将其表述为已执行测试并审查覆盖率的 verifier。[P, D.2；Fig.8, p.17][PH]

两处边界值得保留：提示说不可实现时分数不应超过 5，但过滤又允许等于 5；提示包含“已解决或 closed”扣分，数据筛选却要求 closed issue。是否指题目文本而非 GitHub 状态，需要进一步语义说明。本文不把这种张力推成所有任务被误删，也不把阈值当成题意充分性的证明。

### 4.3 MEnvBench 的组成与适用范围

MEnvBench = **10 语言 × 20 仓库 × 5 个不同历史实例 = 1,000 题**。采样兼顾领域和五档仓库大小：<10MB、10–50MB、50–100MB、100–500MB、>500MB。领域分类使用仓库名、description、topics、语言等 metadata，Fig.9 包含应用开发、数据库、数据工程、ML/AI、基础设施、专业领域、安全、UI/UX、QA/测试、嵌入式/IoT 等十类。[P, §4.2；D.4；Fig.9–10][PH]

这增加生态覆盖，但各领域和大小区间不是严格均匀。仓库大小可以影响构建复杂性，却不是独立控制后的因果变量或模型认知难度。Fig.10 原图版本未闭合，本稿不补精确条形读数。

D.5 给出 Python 的 `home-assistant__core-104627`（remote significant-change）和 Java 的 `keycloak__keycloak-39637_test`（secret entropy）示例。字段含 base commit、版本、日期、问题、patch/test_patch、hints/all_hints 和 commit URL；长文本本来就被作者截断。它们展示跨语言 schema，不是可以单凭论文 Listing 运行的完整任务。[P, Listing 1–2, pp.18–20][PH]

这些参考解、评论和修复链接是数据资产，不自动意味着求解模型应能看到。论文没有披露完整训练／评测可见字段表。

## 5. 构建实验：主结果、消融、资源失败与不利结果

### 5.1 基线配置和总体结果

构建代理骨干为 **Kimi-K2 (`kimi-k2-0905-preview`)** 与 **Gemini-3-Flash**。Repo2Run 只在 Python 评测；SWE-Bench-Live 在本实验覆盖六语言；SWE-Factory 在本实验覆盖十语言，不能由此否认其原论文不同的支持范围。[P, §5][PH]

Table 8 固定 temperature=0.5、每任务 3 小时超时、并发 15。Repo2Run 最大 50 迭代；Live 安装和验证分别 20；Factory/MEnvAgent 各 5。**统一超时不等于统一 LLM call 数、token 或工具计算**；这些不同控制单位需保留。未充分披露逐容器 CPU/RAM、镜像缓存条件、全部 per-call token 上限和失败任务时间归入方式。

| 骨干 | 方法 | F2P % | PASS % | 平均时间 秒/题 |
| --- | --- | ---: | ---: | ---: |
| Kimi-K2 | SWE-Factory | 26.2 | 34.5 | 6,356 |
| Kimi-K2 | MEnvAgent | 35.7 | 45.9 | 3,339 |
| Gemini-3-Flash | SWE-Factory | 33.3 | 41.5 | 6,175 |
| Gemini-3-Flash | MEnvAgent | 41.1 | 52.0 | 3,808 |
| 作者跨模型平均 | SWE-Factory | 29.8 | 38.0 | 6,266 |
| 作者跨模型平均 | MEnvAgent | 38.4 | 49.0 | 3,574 |

[P, Table 2；Table 9；Fig.3][PH]

headline 的 **8.6 是百分点**；43% 是这里的平均构建 wall-clock 降幅，不是在线 RL 吞吐、GPU-hour 或总经济成本。平均行是作者四舍五入值，不能为对齐精度暗改其他行。没有多随机种子／置信区间，也没有完全等 token 的角色拆分消融。

Table 9 的全语言主对照如下；每格依次为 **F2P/PASS/秒每题**：

| 语言 | Kimi Factory | Kimi MEnv | Gemini Factory | Gemini MEnv |
| --- | --- | --- | --- | --- |
| Python | 31/37/5512 | 53/60/2311 | 44/51/5529 | 61/66/2530 |
| Go | 50/57/5742 | 61/70/3171 | 53/61/5193 | 61/66/3173 |
| Java | 13/16/6182 | 28/33/4909 | 18/24/6582 | 37/43/4797 |
| JavaScript | 37/40/5650 | 44/51/3210 | 39/41/5690 | 48/63/3715 |
| C | 13/35/5777 | 13/39/3364 | 18/37/5482 | 20/46/4598 |
| C++ | 7/21/5832 | 7/23/5254 | 6/24/5361 | 7/26/5995 |
| Rust | 19/32/7773 | 33/42/4662 | 37/42/7311 | 43/57/4828 |
| TypeScript | 23/27/8962 | 32/43/2330 | 24/28/8050 | 35/43/3632 |
| PHP | 30/34/5759 | 37/40/2394 | 39/45/5969 | 40/47/2415 |
| Ruby | 39/46/6368 | 49/58/1782 | 55/62/6582 | 59/63/2399 |

这张表限制了“全部语言所有指标都更好”的表述：Kimi 的 C/C++ **F2P 持平**；Gemini 的 C++ MEnv **更慢**（5,995 对 5,361）。Python 的 Repo2Run 两骨干分别 24/26/3112、27/32/3769；Live 分别 13/15/2589、21/23/2547。Live 某些语言速度更快但 F2P 较低，所以结论应围绕成功率—时间取舍，不应把任何更快的 baseline 隐去。[P, Table 9, p.21][PH]

### 5.2 Python 复用消融：历史密度是关键条件

正文消融使用 Kimi-K2，Python 子集扩到每仓最多 10 实例。与无复用或直接复用相比：

| 方法 | RSR % | PASS % | TIME 秒 |
| --- | ---: | ---: | ---: |
| 完整：检索＋增量适配 | 39.0 | 59.0 | 2,314 |
| 无 EnvPatch，只直接复用 | 25.0 | 52.0 | 2,777 |
| 无复用，从头构建 | 0.0 | 40.5 | 4,283 |

RSR 在 §6.1 定义为通过复用路径完成、无需回退 scratch 的**任务比例**。这里衡量 PASS，而不是 F2P。完整方案相对 scratch 时间减少约 46%、PASS +18.5pp；移除 EnvPatch 相对完整方案时间增加约 20%。后者不等于加入 EnvPatch 相对直接复用减少 20%，分母不同。[P, Table 3；§6.1][PH]

Fig.4 按每仓历史实例数 1→10 展示复用概率、时间和 PASS。只有一个实例时复用近零，和从头构建表现接近。**这不是只加一个缓存就保证获得 46% 的证据**：历史池密度和可用性必须足够。完整 pool 建立成本、实例执行顺序、warm/cold 计费和跨仓持久化寿命未完整披露；不能把按每题均值降低写成整个扩容流程总计算也同比下降。

### 5.3 v3 跨语言补充消融：另一批 200 题，不套用 46%

附录 G 采用 **10 语言 × 4 仓 × 5 题 = 200 题**，不是主 benchmark 的全部 1,000 题，也不是 Python 的 10 题/仓设置。

| 语言 | RSR % | MEnv PASS % | 无复用 PASS % | MEnv 时间 | 无复用时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Python | 30.0 | 70.0 | 60.0 | 2861 | 3994 |
| Ruby | 30.0 | 65.0 | 50.0 | 2364 | 3776 |
| TypeScript | 25.0 | 60.0 | 55.0 | 3826 | 4850 |
| Go | 25.0 | 55.0 | 45.0 | 4309 | 5117 |
| Rust | 25.0 | 55.0 | 50.0 | 4698 | 5639 |
| Java | 20.0 | 45.0 | 40.0 | 4322 | 5141 |
| JavaScript | 20.0 | 45.0 | 30.0 | 3916 | 5275 |
| PHP | 15.0 | 30.0 | 25.0 | 3212 | 3764 |
| C++ | 15.0 | 20.0 | 10.0 | 5377 | 6238 |
| C | 10.0 | 20.0 | 15.0 | 5804 | 6455 |
| **作者平均** | **21.5** | **46.5** | **38.0** | **4069** | **5025** |

[P, G；Table 11, p.22；数值来自 v3 HTML/PDF 解析，原版表页视觉核验待补][PH]

这一批显示 PASS +8.5pp、时间约 -19%，不能把 Python 的 -46% 外推为全语言结果。还有源文口径冲突：Table 11 caption 将 RSR 写成 **Repository-level Success Rate**，正文仍是 **Reuse Success Rate**；caption 把 TIME 写 Total Execution Time，邻文说 average time。本文按原值转录，不自行确定另一套分母。G 未单独清楚给骨干名称，也不能仅凭 §6.1 的 Python 配置自动补上。

### 5.4 失败与规模结果：不是“多 agent 就能解决构建”

Fig.5 给出 F2P 随仓库大小增加而下降的关联；作者归因于依赖图与构建负担。语言、工具链、资源需求可能同时变化，不能当作控制变量后的因果证明。Fig.6 把结果分为环境安装失败、测试执行失败、P2P、F2P；这有助于区分“装好但没有复现问题”和“根本未形成有效运行”。[P, §6.2；Fig.5–6][PH]

v3 附录 H 的 C++ 分析列出：编译 OOM 22%、非标准构建系统 20%、大型依赖安装失败 18%、缺系统开发库 8%、网络下载超时 5%。这些数字合计 73%，原文未给完整剩余类别、绝对样本数、互斥性或按哪一骨干汇总；不能拿它们当作全部任务的失败概率。

例子包括 Godot 的编译内存、Drake 的定制构建、ROS2 大依赖、Qt 等系统库与 submodule 下载。作者将资源可分配 sandbox 和专门工具列为未来工作。**这说明失败可能来自环境基础设施，不证明加 token 或换一个规划提示就能解决，也不要求本项目立刻支持所有语言。**[P, H, pp.22–23][PH]

<a id="training"></a>
## 6. MEnvData-SWE 与学生训练：成功轨迹 SFT 的证据

### 6.1 数据不是 benchmark 子集的同义词

构建候选池经过 MEnvAgent 生产和双态验证，形成 3,005 个任务、942 个仓库、10 种语言。教师用 OpenHands 工具 `str-replace-editor`、`execute-bash`、`finish` 求解，保留 resolved 实例的 **3,872 条轨迹**。[P, §6.3；I.1–I.4][PH]

| 语言 | 仓库数 | 任务数 | 成功轨迹数 |
| --- | ---: | ---: | ---: |
| Go | 169 | 502 | 502 |
| Java | 14 | 33 | 47 |
| JavaScript | 119 | 578 | 694 |
| PHP | 21 | 159 | 395 |
| Python | 192 | 477 | 543 |
| Ruby | 79 | 283 | 749 |
| Rust | 249 | 769 | 769 |
| TypeScript | 76 | 157 | 157 |
| C | 9 | 16 | 16 |
| C++ | 14 | 31 | **0** |
| **合计** | **942** | **3,005** | **3,872** |

[P, Table 12, p.24][PH]

这是重要的覆盖边界：**环境覆盖十种语言，但表中只有九种语言有非零教师轨迹，C++ 为 0**。同一题可能产生多条轨迹，Ruby/PHP 等轨迹与任务比例不同；不能认为按轨迹均匀采样就是按任务或仓库均匀采样。教师每题尝试数、总失败数、token/turn 上限、成功轨迹去重和精确重采样规则没有完整给出。

### 6.2 教师、构建模型和学生各自是谁

构建代理使用 Kimi/Gemini，issue judge 使用 DeepSeek-V3.2；解题轨迹教师是 **Claude-4.5-Sonnet**。学生是 Qwen2.5-Coder-Instruct 的 7B/14B/32B、Qwen3-Coder-30B-A3B-Instruct 和 GLM-4.5-Air。教师提供离线成功对话，而不是对学生访问前缀在线返回分布的 OPD；五个学生是独立微调，不是串联专家。[P, §5；§6.3；D.2][PH]

原文没有预训练、独立安全／偏好对齐或新的多教师阶段。没有给 SFT 的 assistant/thinking/tool mask、tokenizer/template、packed loss 分母、是否只微调部分参数等完整定义。不能从 Megatron-LM 或模型家族默认值补写。

### 6.3 全部已披露训练配置和一个原文冲突

| 字段 | I.6 披露 | 解释边界 |
| --- | --- | --- |
| 框架／目标 | Megatron-LM 的统一 SFT | 非 GRPO；未公开该实验训练脚本 |
| 序列长度 | 128K = 131,072 tokens | 不等于每条样本都达到上限 |
| 数据／epoch | 约 4k “instances”，3 epochs | 邻近统计是 3,872 trajectories，别改成约4k独立SWE题 |
| global batch | 8 | 不是八张 GPU |
| optimizer | AdamW | betas/epsilon 等未给 |
| 学习率 | peak 1e-5，minimum 1e-9，无 warmup | 同句又称 constant strategy，但又写 decays；具体 scheduler **不清楚** |
| clip／weight decay | 1.0／0.1 | 按原文保留 |
| MoE aux loss | 1e-3 | 不据此声称 trainer/rollout routing 已对齐 |
| 硬件／并行 | H800；TP=8、PP=8、EP=8；Sequence Parallelism | 全局 GPU 数、DP 与 EP 映射未给，不能乘成512卡，也不能说8卡可复现 |
| 效率配置 | Flash Attention 2、full activation checkpointing | 无该配置的独立速度或显存消融 |

[P, I.6, pp.24–25；包含超参的 p.25 截图与文本一致][PH]

原文没有训练 GPU-hour、总 token、学生吞吐或全成本。它支持同量级 MoE 的成功轨迹 SFT 可有收益，**不支持直接预测 RepoHarness 8×96GB PCIe 的时长、显存或收益**。

### 6.4 下游成绩与评测边界

| 模型 | SWE-bench Verified 基线→SFT | SWE-bench Multilingual 基线→SFT |
| --- | --- | --- |
| Qwen2.5-Coder-7B-Instruct | 0.0 → 21.8 | 0.0 → 12.3 |
| Qwen2.5-Coder-14B-Instruct | 5.8 → 39.8 | 0.0 → 31.2 |
| Qwen2.5-Coder-32B-Instruct | 7.5 → 54.6 | 0.0 → 38.3 |
| Qwen3-Coder-30B-A3B-Instruct | 45.2 → 53.4 | 34.7 → 38.0 |
| GLM-4.5-Air | 58.0 → 62.8 | 42.3 → 47.7 |
| GPT-4.1 参考行 | 54.6 | 31.5 |
| Claude-4.5-Sonnet 参考行 | 77.2 | 68.0 |

单位为 **Resolved Rate %**。Verified 为 500 题；Multilingual 为九语言，Table 13 列 300 题。使用 OpenHands，作者说明修正了 git log 可泄漏问题（链接 SWE-bench issue #465）。没有给精确 OpenHands commit、模型 revision、逐题 manifest、重复次数、置信区间、完整推理预算或全部 git 对象清理步骤。[P, Table 4；§6.3；Table 13][PH]

Qwen3-Coder 的 +8.2pp / +3.3pp、GLM 的 +4.8pp / +5.4pp 是同表训练前后差值；对本项目应当作为有价值的 SFT 参照，不是在线 RL 已成功的证据。大幅改善的弱 Qwen2.5 起点可能同时涉及工具行为和任务能力；没有相同教师/数据量/预算的多种数据质量路线对照，因此不能把增益全部归因于 EnvPatch 或某个过滤器。

训练集与另一个 benchmark 名称不同，不充分证明仓库、PR、派生内容或预训练的全部不重叠。文中只明确了独立 benchmark 和一项 git log 防护，不能扩写为全面去污染已验证。

A/Table 13 对 SWE-gym、SWE-smith、SWE-Flow、SWE-Synth、SWE-Mirror 及多个 benchmark 的关系作讨论。其“最大真实多语言环境集”是作者当时的组合口径；SWE-smith 表里有 50k 任务，因此不能删去 polyglot/realistic 限定后声称 MEnv 数量最大。表中 real/synthetic 分类也不是独立质量分数。

## 7. 时间、API 与集群开销：不能用一个“43%更省”概括

### 7.1 Table 10 给的是按当时价格估算的模型调用费用

Input/Output 单位是 **千 token**，价格采用 Kimi $0.6/M input、$2.5/M output；Gemini $0.5/M input、$1.5/M output。这是论文计算口径，不是本次实时报价。[P, Table 10, p.21][PH]

| 语言 | Kimi Factory $/题 | Kimi MEnv $/题 | Gemini Factory $/题 | Gemini MEnv $/题 |
| --- | ---: | ---: | ---: | ---: |
| Python | .08 | .11 | .11 | .26 |
| Go | .06 | .09 | .10 | .24 |
| Java | .09 | .10 | .14 | .40 |
| JavaScript | .06 | .12 | .09 | .42 |
| C | .10 | .15 | .27 | .48 |
| C++ | .10 | .15 | .23 | .57 |
| Rust | .09 | .07 | .10 | .18 |
| TypeScript | .06 | .08 | .10 | .28 |
| PHP | .07 | .09 | .11 | .36 |
| Ruby | .05 | .07 | .14 | .33 |

例如 Kimi Python：Factory 90k in/12k out，MEnv 141k/9k；Gemini JavaScript：65k/41k 对 166k/224k。**时间更短不意味着 API 更少**。作者认为这些绝对费用低、增加可忽略；这是作者的经济判断，不作为本项目结论。JavaScript 的 Gemini 费用按表约4.67倍；应同时衡量成功任务产出和完整成本。

本稿按十语言四舍五入费用作简单平均，Kimi 为 .076→.103，Gemini 为 .139→.352 美元/题；这是读者算术，不是新增官方总费用，也不能代替按实际次数、失败与缓存折扣重新计费。CPU/内存、镜像仓储／网络、池预热、教师解题与 SFT 成本不包含在这个 API 表中。

### 7.2 K8s 的作用与披露限制

附录 I.2 报告作者本地 Docker 构建并发约10–15，转向 K8s 后可运行1,000+并发构建。前者是其具体基础设施的初步观测，不是 Docker 的通用硬上限；后者是作者工程规模描述，未给全资源配置、负载分布、缓存冷热和等资源对照。当前核心代码与 K8s 实现不在公开固定树中。[P, I.2；C0/C1][PH]

它表明构建需要独立管理环境资源，但不要求本项目先引入 K8s。对小型任务池，复用可验证的依赖层、控制实际并发和保留失败原因，可能比复制千路平台更直接；这属于项目候选推论，不是本篇对八卡系统的实验结果。

<a id="assets"></a>
## 8. 官方实现与开放资产：实际能用什么

### 8.1 固定树的最重要事实：核心构建代理还不是可读代码

官方树 `d9e63881…` 的 `menvagent/README.md` 直接标注核心代码仍在整理、等待公开。完整递归树中有 README、图示、requirements 和 **curation**，没有 EnvPatchAgent、环境检索、PEV runtime、K8s 构建或 Megatron SFT 的实际实现。[C0: README][C0]、[C1: core 状态][C1]、[C-tree][CT]

因此，本任务不能声称已从代码验证伪代码全部早返回、F2P 隔离、历史池更新或并发故障处理。论文的开放承诺、README 的 feature 列表与可取得实现是三种证据。README 安装示例仍使用 `your-org/MEnvAgent` 占位地址，也不能称一键复现。

### 8.2 可读的真实路径：候选数据生产

实际读取路径为：

```text
curation/curation.sh
→ 仓库抓取／筛选调用
→ swe_task_crawling/run_get_tasks_pipeline.sh（入口引用）
→ get_tasks_pipeline.py::construct_data_files
→ build_dataset.py::create_instance / main
→ filter_instances.py
→ issue_filter/issue_eval.py
```

本轮读取 curation.sh、get_tasks_pipeline.py、build_dataset.py、filter_instances.py、issue_eval.py 和两级 README；**没有审计全部抓取函数、版本提取实现和 GitHub API 历史**。以下结论仅针对这些文件。[C2–C7]

`curation.sh` 当前默认 **PHP**，不是 Python，调用 min_stars=1000、PR/issues/forks=200、40 workers、cutoff_date=20180101。它还带需替换的代理占位配置。不能将这一示例视为论文所有实验的冻结 manifest。

`get_tasks_pipeline.py` 走 issue-first 抓取、关联 PR，再按 repo 对应语言调用 `build_dataset()`。`create_instance()` 拆 patch、题面和 hints，记录 base commit、created_at、关联 issue；版本从 `get_version_at_commit()` 获取，失败退到 `0.0`。本文未核该版本提取方法，不把 `version` 当作可靠 semver。缓存存在时会跳过部分采集／实例，不代表每次重跑都重新验证远端状态。[C4–C5]

### 8.3 过滤实现不是环境验证

`filter_instances.py` 的 base 条件要求合并 PR 和关联 issue、非空 fix/test/problem，以及两份 patch 都包含目标语言后缀文件。medium 条件以 **fix patch 字符串的换行数≤1000、`diff --git a/` 数≤10** 筛选；high 使用500/5。它不在这一步限制 test patch 同样的规模，更不是精确 added/deleted LOC 统计。`build_dataset.main` 依次写 base/medium/high 输出。[C5–C6]

这些检查有明确用途，但既没有运行测试，也没有证明 test patch 覆盖 issue。原文 Table 6 的“Lines of Code”与实现的字符串行计数需分开记录。

### 8.4 issue judge 的输入、失败与解析边界

`issue_eval.py` 仅把 `problem_statement` 填入与 Fig.8 相应的提示，调用 `deepseek-v3.2`；最多3次重试，32进程。失败最终记 score=-1，同时保留错误记录；保留阈值是≥5。[C7]

当前分数正则为 `issue score:(\d+)`。本轮只在 CPU 上对该**原样正则**做了四个合成字符串检查：`issue score:5` 解析为5；`issue score: 5` 不匹配；`issue score:12` 解析为12；`issue score:5.9` 解析为5。函数没有随后强制0–10范围。**这不是运行了整条数据生产，更没有测出历史误删率**；但说明响应格式失败、模型判断低分和真实任务质量必须分别记账，不能把score=-1都叫无效题。

独立执行 `build_dataset.py` 的 CLI 没有提供 `main` 所需的 language，但上层 pipeline 调用确实传入了语言。这是示例入口可用性差异，不能把它夸大为 pipeline 必然不能运行。[C4–C5]

### 8.5 数据资产的实际可取得性和版本冲突

| 资产 | 本轮直接看到什么 | 尚未验证什么 |
| --- | --- | --- |
| MEnvBench | 官方数据卡和文件树；`MEnvBench.jsonl` 约35.2MB，树显示提交短号 `4e312f1` | 未整库下载、重算1000行／split、运行构建 |
| MEnvData-SWE | 官方卡、schema、样例、文件树；树显示 `edfaa7bf15ada849c3bd63f55a5e3ab9e85359c2` 与单个约62.8MB `swe-images.jsonl` | 未读取该revision全部行，未拉Docker镜像 |
| MEnvData-SWE-Trajectory | 官方卡与viewer，字段 `tools/messages/docker_image`；viewer显示**3,918行** | 未固定原始数据文件revision、去重或解释与论文3,872的差值 |
| Docker镜像 | 数据记录含 image_name/docker_image，作者声称3005镜像 | 未验证registry、digest、CPU架构、拉取权限与镜像内容 |
| SFT模型／训练脚本 | 原文报告5个学生结果 | 本轮未确认官方逐模型checkpoint与完整训练入口 |

[MEnvBench][DB]、[MEnvData-SWE][DD]、[Trajectory][DT] 均为作者官方 HF 入口。这里记录的是阅读时页面响应，不保证不同缓存视图属于同一即时快照。

两个具体差异不能忽略：第一，MEnvData 的 viewer 返回一个指向 **`2f2c5efe0ddcfbf54f3c35740e154949ac7a5802`** 的旧生成错误：混合文件多出 `docker_image/swe_type`，导致 schema cast 失败；文件树又指向上面的 `edfaa7…`。不能把旧 viewer 错误归到未实测的新revision，也不能据此声称数据集整体不可用。第二，trajectory 卡仍写3,872，但viewer计数3,918；不要自动合并成论文用了3,918条，或假定差值都是新样本。

面向使用的下一步是固定 revision 和具体 data_files，再核schema、行数、重复与任务映射；这是尚未执行的检查，不是本文已经测试通过的加载 recipe。

### 8.6 环境脚本字段：复用脚本不能脱离父环境

官方 schema 区分 `env_setup_script`（增量命令）、`original_env_setup_script`（原始／被复用底座安装）、`eval_script`（应用测试补丁并执行）、`image_name`。因此不能从任一增量脚本独立推导完整依赖，也不能在不知镜像已包含什么的情况下无条件重跑全部安装。[C0；DD]

原始任务同时含 fix patch、test patch、hints/all_hints、修复 commit URLs。它们方便生产、验证与教学，但本篇没有证明全部已从 solver 可见环境中剥离。`docker_image` 标签本身也不等于不可变digest或可以公开pull的完整registry地址。未确认前不把官方“verified”标签直接升级为 rh2 已合格。

代码和HF卡标注 Apache-2.0，论文为 CC BY 4.0。**这些许可声明不替代源仓库、镜像内依赖、教师轨迹使用条件的逐资产核对**；本轮没有进行法律合规审查。

## 9. 证据限制与不能自动推出的结论

| 项目 | 已取得的证据 | 不补写／仍待核的部分 |
| --- | --- | --- |
| 复用是否有效 | Python和200题跨语言消融 | 全流程冷启动成本、pool顺序/污染、目标八卡收益 |
| 新环境选择 | 同仓同版本优先，较新且时间接近 | 未来源码残留、wheel缓存与历史正确性的实现隔离 |
| 评分含义 | fixed PASS与buggy/fixed差异 | 重复flakiness、所有替代解、自然部分修复与反作弊覆盖 |
| 当前源码 | curation完整相关路径；core明确待公开 | 不编造EnvPatch、K8s或verifier代码审计 |
| 模型收益 | 成功教师轨迹SFT前后表 | 在线RL、动态课程、拆分质量机制的等预算因果收益 |
| 训练配方 | I.6部分超参 | scheduler冲突、token mask、总GPU和总token、checkpoint选择 |
| 当前数据 | 卡、树、viewer及差异 | 全量文件、镜像可拉取和论文数据revision一致 |
| 版本视觉核验 | 部分共同图表与p.25可对读 | v3原图全部页、Fig.10精确分布、Table11原版图 |

Impact Statement 明确提醒生成安装命令与执行不可信代码的风险，并推荐 Docker 隔离；这不是已经证明容器能处理任意敌对代码的安全审计。该节又笼统写所用模型皆开源，与 §5 明确将 Gemini 称为闭源及 §6.3 的 Claude 教师不一致；本文保留模型角色，不沿用这一笼统许可／开放性结论。[P, Impact Statement；§5；§6.3][PH]

A.2 对 SWE-Mirror 的“真实问题复现”讨论，与 Table13 用真实/合成二分的方式也不是完全相同的质量判断。本文只用它解释路线差异，不按一个勾叉排列数据质量。

<a id="project"></a>
## 10. 对 RepoHarness 的有限映射：复用修复，不复用未验证结论

映射日期2026-09-24，项目以[9月23日同步包][PR]为基线。该包记录166题环境修复范围、164题修订对照与真实求解中的开发入口问题，同时明确环境证据不等于可训练资格。本稿不重跑或重新批准这些结果。

### 10.1 值得保留的复用边界

| 对象 | 可考虑复用什么 | 每个目标任务仍需确认什么 |
| --- | --- | --- |
| 基础OS／工具链／公共依赖层 | 固定底座、下载缓存和安装成果 | 架构、目标版本、资源条件是否兼容 |
| 同仓依赖修订 | 有原始日志依据的增量安装命令 | 目标snapshot实际import／build、激活是否送达actor |
| 通用测试运行适配 | 真实测试框架、命令包装、结果解释工具 | 这题的测试选择、收集结果、buggy/fixed含义 |
| 题目测试／reference／hints | 作为有身份的评分和教学资产保存 | 可见性、题意范围、合法替代解与非目标回归；不自动给solver |
| agent工作目录与构建后状态 | 不自动作为跨任务可信模板 | 必须排除候选残留、未来修复、私有测试、历史解法与缓存状态影响 |

前三行是 MEnv 的复用思想结合当前项目事实提出的候选分工；后两行是基于本项目风险的设计推论，**不是作者已经实施并验证的同一套隔离协议**。较新第三方依赖与较新被测项目代码是两种风险，不应一律禁用新包，也不能一律认为有PASS就安全。

### 10.2 一个有辨识力、可负担的最小实验

从已经修订过、同仓有多个历史实例的少量任务中，对比三条受同一资源和超时约束的构建路径：**固定底座从头构建、复用同仓环境而不增量修、复用加有限增量修**。新仓或只有一个历史实例的任务作为“复用机会不足”的对照，不为制造收益只选最适合复用的题。

固定目标base commit、任务材料和评分规则；每条路径除gold/noop之外，还核actor能否按正式交付方式导入项目、运行公共开发测试。若自然候选存在明确回归证据，可以在对应任务做已有的质量复核，不要求所有题新增完整仓库回归平台。

测量从空池到产出合格任务的总成本，以及warm复用阶段的成本；分别记录安装、模型调用、验证、失败回退、镜像存储／传输。**不以wall-clock缩短直接宣称API费减少，也不以更多构建PASS宣布模型训练提升。** 可先用固定规则增量修订作为简单基线；没有必要为了贴近论文就先实现六个LLM角色。

### 10.3 当前不值得直接复制的部分

不因1000+并发描述就先迁移K8s；不为参数相近照搬128K、TP/PP/EP配置；不把DeepSeek质量分接成新的强制准入门；不把缺包错误与模型修复失败都转成相同reward；不把未发布EnvPatch源码用自己猜测实现后称为复现。

本篇为“环境修复能够跨任务积累并降低重复构建成本”提供直接方法和消融支持，但**没有解决当前 Conan/Moto/mypy 的所有题意与验收争议，也没有证明现有全零组应当换哪种训练目标**。它的项目价值主要在B线环境资产复用与构建成本；学习策略仍需本项目独立数据与训练证据。

## 11. 快速查阅与旧稿增量

| 要查什么 | 本稿 | 一手位置 |
| --- | --- | --- |
| PASS、F2P、Fig6 P2P分别是什么 | §2.2 | §2，Eq1–2；B，Eq5–8；Fig6 |
| 怎样选历史环境、何时回退 | §3.2–3.3 | §3.2；Alg1，p.15 |
| 同仓修复的真实例子 | §3.4 | C.2，Fig7，p.16 |
| 8.6pp、43%、46%、19%分别来自哪里 | §5、§7 | Table2/3/11，条件不同 |
| 为什么不能说整体更便宜 | §7.1 | Table10，p.21 |
| 十语言任务是否有十语言SFT轨迹 | §6.1 | Table12，C++为0 |
| 30B-A3B真实训练与结果 | §6.2–6.4 | §6.3/Table4；I.6 |
| 哪些代码现在能读 | §8.1–8.4 | 固定C0–C7与完整树 |
| 官方资产能否立即使用 | §8.5–8.6 | HF卡/文件树/日志revision分别核对 |
| 当前项目先试什么 | §10 | 仅候选设计，不是实施批准 |

旧专题的关键机制没有被推翻；新增事实包括跨语言与API成本的非一致收益、全量SFT和无C++成功轨迹、core未开放、judge解析边界、数据revision差异、伪代码与最终F2P合同的未闭合部分。新文成为本来源完整维护入口；旧专题保留，不回写为它当时已经做完这些检查。

## 12. 自查与交付状态

已完成源文文本范围检查、主要表值对读、版本差异识别、固定官方代码路径核查、资产入口核对及少量算术／正则检查。详见[作者自查记录](reviews/menvagent_self_check_20260924.md)。无独立子agent、无模型／环境／GPU复现，不编造线程ID或review通过状态。图页缓存错版导致的剩余核验列在该记录，可在取得本地v3 PDF后定点补齐，无需从头重写笔记。

早期会话附件过期不影响本稿已取得的公开原文；本次没有调用这些附件。后续如需补齐v3原图，可使用本地原件或重新上传该PDF。提交只包含本稿与检查记录，不上传原文PDF、第三方代码副本、数据集、凭据或训练产物。

## 一手来源链接

[PA]: https://arxiv.org/abs/2601.22859
[P]: https://arxiv.org/pdf/2601.22859v3
[PH]: https://arxiv.org/html/2601.22859v3
[C0]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/README.md
[C1]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/menvagent/README.md
[CT]: https://api.github.com/repos/ernie-research/MEnvAgent/git/trees/e3e0e72eeec94789091f18ea9cf66f2083588840?recursive=1
[C2]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/curation/README.md
[C3]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/curation/curation.sh
[C4]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/curation/swe_task_crawling/get_tasks_pipeline.py
[C5]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/curation/swe_task_crawling/build_dataset.py
[C6]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/curation/swe_task_crawling/filter_instances.py
[C7]: https://github.com/ernie-research/MEnvAgent/blob/d9e63881f7c4a4670bb536c89add24573459bbee/curation/issue_filter/issue_eval.py
[DB]: https://huggingface.co/datasets/ernie-research/MEnvBench
[DD]: https://huggingface.co/datasets/ernie-research/MEnvData-SWE
[DT]: https://huggingface.co/datasets/ernie-research/MEnvData-SWE-Trajectory
[DD-tree]: https://huggingface.co/datasets/ernie-research/MEnvData-SWE/tree/edfaa7bf15ada849c3bd63f55a5e3ab9e85359c2
[PR]: https://github.com/Rogerffff/RepoHarness/blob/0554dafd633cd982288bd60a54f75da65e5c54d4/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/external_sync_20260923/README.md
