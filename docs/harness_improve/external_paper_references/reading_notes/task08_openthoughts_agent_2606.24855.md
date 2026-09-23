# Task08 · OpenThoughts-Agent：数据配方、SFT–RL 分工与收益边界

**精读日期：2026-09-08。** 本文主读 *OpenThoughts-Agent: Data Recipes for Agentic Models*，而不是更早的 OpenThinker-Agent-v1 发布。论文最强的证据是针对数据来源、混合、教师、过滤及扩容方式的实验比较；32B 主模型只做 SFT，RL 则是另一条 8B 冷启动分支。两条路线不能合并成“32B SFT 后继续 RL”。最值得保留的结果是：SFT 与 RL 的好数据排序不同；较长多轮示范在近似等 token 对照中仍有效；任务改写在不同规模下效果不同；最强 RL 运行后期会崩溃。七项均分最高也不代表每项能力都更好。本次还核对了公开数据实际行数、三处论文固定代码版本及部分实现差异。

导航：[来源与覆盖](#scope) · [实验协议](#protocol) · [六阶段 SFT](#sft) · [数据扩容](#scaling) · [RL 配方与行为](#rl) · [评测与成本](#evaluation) · [开放资产和代码](#assets) · [项目意义](#project)

<a id="scope"></a>
## 1. 来源、版本与阅读边界

### 1.1 主来源和配套来源

**P：论文。** Negin Raoof、Richard Zhuang、Marianna Nezhurina、Etash Guha 等，末位联合贡献作者 Benjamin Feuer、Ludwig Schmidt；参与机构包括 UC Berkeley、Stanford、JSC、LAION 等。主读 [arXiv 2606.24855v1 PDF][P]，首次提交 **2026-06-23**；本轮查询版本历史仅列 v1。PDF **36 个物理页**，正文 §1–6，技术附录 **A–G**。文中 OpenThoughts-Agent 指项目／数据体系，OpenThinkerAgent 指训练后的模型；OpenThoughts-Agent-v2 是最终数据配方名称，不是本文的 arXiv v2。

**W：官方发布文章。** [2026-06-10 官方博客][W]，时间早于 arXiv。它是发布级概括，不用于补足论文未披露的算法、消融或预算。

**M/D：模型卡与数据卡。** 实际打开 32B SFT、8B RL 模型卡，SFT-100K 数据查看器与数据卡，以及 RL-5K 的 README。HF 页面按 2026-09-08 的本次访问记录，未冻结全部权重／数据 revision，未下载全量 parquet 或权重。页面存在、卡片声明、实际 viewer 行数分开记录。

**C：配套代码定点阅读。** 论文 D.8 的三个短 SHA 均解析到完整提交：

| 原文来源 | 解析到的固定提交 | 本轮实际检查范围 |
| --- | --- | --- |
| open-thoughts/OpenThoughts-Agent | `4e2b8422b7ee5ca4af3566df603c1ca58d576238`，2026-02-27 | commit diff、`rl/README.md`、`hpc/skyrl_yaml/jupiter/24GPU_base.yaml`；thinking 模板修改 |
| penfever/SkyRL | `ada3bd4f952ef5ff59134389e5577f54530d29f6`，2026-02-27 | commit diff、`skyrl-train/examples/terminal_bench/entrypoints/main_tbench.py` 全文 |
| laude-institute/harbor → harbor-framework/harbor | `94f358bc51fb214d8089f098c746ef6f3f66e9a3`，2026-02-27 | `src/harbor/utils/traces_utils.py` 的该提交 diff：trial-level 结果回退 |
| OT-Agent 当前 main，单列 | `3bd1917e62c9d03d73063b433f5c442c279c0563`，2026-09-02 | README 的安装／数据／SFT／评测入口区段；`data/README.md` 全文 |

固定历史代码与当前 main 不混用；读到某项配置不证明完整论文运行没有额外 CLI overrides。没有整仓审计，也没有执行上游训练、sandbox、checkpoint 或 GPU 测试。

**RepoHarness 映射基线。** `research/nemo-rl-packing-loss-20260908@827dcdf2f113b745e2c3901e58c38bb12e634131`。本轮读取该分支的阅读模板及 CURRENT-STATE-BRIEF；它继承的项目快照仍为 miles/SGLang/Claude Code/rh2，简报更新于 2026-09-05。只在文末作设计层映射，不以本次阅读批准任务集或算法改动。交付单独分支为 `research/openthoughts-agent-20260908`，不向 NeMo 或其他阅读任务分支写入。

### 1.2 完整覆盖表

正文和全部技术附录均已读；不以“取得 HTML”代替完成阅读。以下页码一律是 **PDF 物理页**。

| 原文范围 | 实际内容／阅读深度 | 本文对应 |
| --- | --- | --- |
| pp.1–4，摘要、§1–2、Fig.1–2、Table 1 | 全读；动机、模型关系、既有工作、六阶段图；Table 1 文本与 Table 23／模型卡交叉核数 | §1–3、§7 |
| pp.4–7，§3.1–3.6，Table 2–7 | 六个数据决策及所有表格逐项阅读 | §3 |
| pp.8–9，§4，Fig.3–4、Table 8 | 四类扩容方式、100K 配方、数据漏斗 | §4 |
| pp.9–11，§5.1–5.3，Table 9–11 | RL 数据源、冷启动、训练协议与结果 | §5、§7 |
| pp.11–12，§6、Limitations、Broader Impacts、致谢 | 全读；规模边界、底座限制、开放性的正反影响、研究计算支持 | §9–10 |
| pp.12–19，References | 阅读引用结构与本研究直接依赖的来源身份；不扩读全部被引论文 | §1、§8 |
| pp.20–24，A.1–A.3，Table 12–15 | 95 个来源策略完整排名、两种 presentation、等 token 过滤实验 | §3 |
| p.25，B，Fig.5 | 8B 数据规模曲线 | §4 |
| pp.25–26，C.1–C.2，Table 16–19 | 32B／8B SFT 通用和规模特定配置，含成本与冲突 | §6 |
| pp.26–28，D.1–D.8 | 硬件、优化、异步、服务、错误处理、step 48 指标及复现 pin | §5–6、§8 |
| pp.28–29，E，Table 20 | 近重复运行、评测噪声、误差估计披露及未闭合项 | §7.4、§9 |
| pp.29–33，F.1–F.3，Table 21–22、Fig.6–8 | 行为统计、judge、两个相反学习方向、后期崩溃、条件均值与全尝试均值 | §5.4 |
| pp.31–36，G，Table 23–24 | 全 benchmark、harness、超时、复现缺口、版本变化 | §7 |

**视觉核查范围。** 已目视 Fig.1–8、Table 2–24；PDF p.3 的截图反复失败，因此 Table 1 单页未完成目视检查，使用其 PDF 提取文本、Table 23 原图和官方模型卡核对重叠数字，不标成“全部表图已目视完成”。HTML 缺失大量表格和整个附录 C 的具体配置，且表号重排／部分链接显示 `LABEL:`；全部技术定位以 PDF 为准。没有使用 OCR，也没有取得完整 TeX 或可在本机打开的 PDF。

<a id="protocol"></a>
## 2. 实验先读口径：不是把 100 多次实验当成一个严格全因子设计

### 2.1 三条训练分支

```text
Qwen3-8B ── 各种 10K 轨迹集全参 SFT ── 六阶段数据决策与消融
       ├── 最终数据配方、不同规模 SFT ── 8B SFT scaling
       └── GLM-4.7-AWQ 的 SWE-Smith thinking 轨迹冷启动
              └── 8 类来源分别 async RL ── pymethods2test 为主要结果

Qwen3-32B ── 最终数据配方、不同规模全参 SFT ── OpenThinkerAgent-32B
```

32B 主模型没有在本篇中继续做 RL。8B 的 ColdSFT 与最强 100K SFT 不是同一个初始化。数据卡给出的 ColdSFT 实际规模为 **9,437 对**，名称用 10K；RL 集为 **5,000 个可执行任务**，不是 5,000 条教师答案。最终 RL 权重标记 **step 45**，附录 D 的运行诊断则是 **step 48**。[P §3、§5；D8][P4] [M8][D-RL]

教师生成离线示范再 SFT 是蒸馏式数据生产，但不是 OPD：没有学生在线采样、教师对学生 token 给 logprob 的训练目标。RL 分支采用学生自身交互与 verifier feedback，而非继续模仿保存的教师轨迹。本文没有多教师 OPD、DPO、专门安全 RL、VLM 或独立预训练阶段。文中的医疗、金融、搜索能力主要作为下游评测，不能倒推相应领域均参与训练。

### 2.2 数据配方由三个开发指标选择

SFT 消融默认：**Qwen3-8B、每策略 10K 轨迹、full-parameter SFT、lr=4e-5 cosine、global batch=96、7 epochs、32,768 context**。默认教师是 **GLM-4.7-AWQ**，harness 是 **Terminus-2**，隔离执行用 **Daytona**。[P §3, p.4][P4]

三个 core 指标：SWE-bench Verified 的 **100 题仓库分层子集**、OpenThoughts-TBLite **100 题**、Terminal-Bench **2.0 的 89 题**。它们参与多轮策略挑选，属于开发坐标。五个 OOD 集——Aider、BFCL、MedAgentBench、GAIA、FinanceAgent——按作者描述在 pipeline 实验完成后才测。[P §3 Evaluation, p.4；G][P4]

作者使用每个阶段候选集内的平均 z-score 选策略。用本文符号重述为：

$$
 z_{s,b}=\frac{a_{s,b}-\mu_b}{\sigma_b},\qquad Z_s=\frac{1}{3}\sum_b z_{s,b}.
$$

其中 $a_{s,b}$ 是策略 $s$ 在 benchmark $b$ 的准确率，$\mu_b,\sigma_b$ 来自**该阶段全部候选**。不是训练 reward 归一化。各阶段候选集不同，其 $Z_s$ 不能直接跨表比较；平均 raw accuracy 与平均 z-score 也可能选出不同教师或来源。论文未给候选方差为零时的处理。

**解释边界。** 三次 stochastic eval rerun 不等于三个独立训练种子；“>100 ablations”不等于所有因素的全因子交叉，也不等于独立团队复现。逐阶段选择提供可操作配方，但无法排除阶段间交互及长期使用三个开发集的选择效应。作者将 benchmark 标准化称为平衡权重；它并不使三个 benchmark 的任务数、方差或现实重要性相同。

<a id="sft"></a>
## 3. 六阶段 SFT：做了什么、证据是什么、不能推出什么

以下三项小表数字顺序固定为 **SWE-Verified-100 / OT-TBLite / TB2.0**，单位都是百分比；保留的 Raw 是三者算术平均，不是七项 headline 均分。完整排名回原文 Table 12–13，不将 95 行全文复制为第二份数据表。

### 3.1 任务来源：好来源呈现能力侧重

作者考察 **95 种来源／生成策略**，包含合成仓库修复、已有 SWE 环境、人写的论坛问题、代码／命令生成、不同语言和工具任务。这里 95 是“生成策略”而不是 95 个互不重叠环境族；同一上游语料可以对应多个转换方式。[P §3.1；A.1, Tables 2/12/13][P5]

| 来源策略 | 三项准确率 | Raw | 全表名次 |
| --- | --- | ---: | ---: |
| SWE-Smith | 32.33 / 17.63 / 6.37 | 18.78 | 1 |
| StackExchange SuperUser | 13.33 / 16.68 / 10.86 | 13.62 | 2 |
| StackExchange Tezos | 16.33 / 16.94 / 9.36 | 14.21 | 3 |
| IssueTasks | 24.00 / 16.44 / 6.74 | 15.73 | 4 |
| R2E-Gym | 28.33 / 16.57 / 4.12 | 16.34 | 6 |
| pymethods2test | 6.33 / 9.68 / 3.00 | 6.34 | 85 |
| AgentTuning-OS | 0.00 / 5.64 / 0.37 | 2.00 | 95 |

SWE-Smith 更偏仓库修复，SuperUser 更偏终端；综合排名不等于每项都占优。最后进入混合的四类来源保留了这种互补。**不能据此将 Tezos 的加密货币知识认作终端能力提升的因果来源**：转换方式、任务结构和示范行为仍共同变化。

原文说明任务被转换成可执行 agent 形式，但没有对 95 条生产线分别提供统一的“原始候选→构建成功→oracle通过→完整轨迹→训练消费”数字。本文不从来源名称自动继承 SWE-Smith／R2E 原论文的所有质量保证。

### 3.2 混合：不是来源越多越好，也不是 Top-4 在每种排序下第一

在总量 10K 固定时，Top-$N$ 从每个入选来源取 $10,000/N$ 个任务。random-shuffle 分支中：Top-4 为 **29.33/17.00/8.24**，Top-2 为 **29.00/18.12/7.12**；Top-1 为 **30.67/14.80/4.49**，SWE 较强而另一面较弱；Top-32 为 **20.33/18.67/5.99**。这支持适度混合的平衡收益，不证明精确比例普适。[P §3.2, Table 3；A.2, Table 14][P6]

附录还完整给了 **sequential round-robin**：Top-8 为 **32.67/16.28/8.99**，Raw=19.31，在该分支最好；Top-4 为 28.00/17.86/8.61。正文选择 Top-4，不应抹掉另一种 presentation 下 Top-8 更强的结果。附录 C 的 `disable_shuffling=True` 与这些实验的初始来源排列不能简单视为同一个开关；缺少逐实验最终配置时，不替作者重建所有 shuffle 操作顺序。

### 3.3 增强：10K 下无综合改善，不能写成“改写永远无效”

Table 4 比较增加约束、增难、约束后增难、原始与增难混合、不同来源组合，以及 trace-derived hints。未改写基线为 **20.67/17.22/8.99，Raw=15.62**；constraint 后 hardening 为 17.33/17.56/9.36，Raw=14.75；harden-only 为 10.67/17.73/8.61，Raw=12.34；trace hints 为 22.67/17.17/5.99，Raw=15.27。[P §3.3, Table 4][P6]

“所有干预未胜过基线”指作者的综合选择标准；某些干预在单项上仍更高。§4 在规模变大后又采用改写解决重复瓶颈，不是相同条件下自相矛盾：第一次是在固定 10K 下换描述，第二次是在有限独特问题上扩展至更大数据量。仍不能把改写带来的表层变化称作新增底层任务。

### 3.4 任务过滤：教师回答长度是代理信号，不是环境有效性证明

Table 5 的随机基线为 **19.67/14.77/7.87，Raw=14.10**；按 GPT-5 回答较长的任务筛选为 **22.67/19.51/10.11，Raw=17.43**，平均约 +3.33 pp。较短回答筛选、AskLLM 和 embedding 策略也列入比较，分别 Raw=15.99、15.80、14.76。[P §3.4, Table 5][P6]

这个信号不直接测目标学生通过率，也不验证 oracle、no-op 或合法替代解。较长教师回答可能反映难度、文风、工具需求或题型，机制没有被完全隔离。§4 进一步使用 **gpt-5-nano** 的回答长度作加权补采，不再是 hard top-k；它与本节写的 GPT-5 不宜合并成同一个精确模型实验。

### 3.5 教师：最强求解器未必是最佳示范来源；“最佳”还取决于选型指标

Table 6 在固定任务混合上换教师：

| 教师 | 三项准确率 | Raw | 平均 z-score |
| --- | --- | ---: | ---: |
| GLM-4.7-AWQ | 28.00 / 17.86 / 8.61 | 18.16 | 0.73 |
| Kimi K2.5 | 33.33 / 14.19 / 8.24 | 18.59 | 0.66 |
| GLM-5 | 33.00 / 14.30 / 7.50 | 18.27 | 0.66 |
| GLM-4.6-AWQ | 26.00 / 16.99 / 6.37 | 16.45 | 0.08 |
| GPT-5.3-Codex | 21.67 / 10.42 / 3.75 | 11.94 | −1.47 |

作者据 z-score 选择 GLM-4.7，不是据 Raw 或 SWE 单项。GPT-5.3-Codex 作为求解器表现更强却给出较差训练数据，是本实验的经验事实；**不能仅据结果断定原因就是轨迹太短、太难、风格或 tokenizer mismatch**。GLM-4.7 相对 Codex 在 TB2.0 的差是 **4.86 个百分点**，不是严谨计算后的相对 5% 降幅。[P §3.5, Table 6][P7]

此处是离线全轨迹 SFT，不存在本文已验证的 teacher-on-student-prefix OPD 比较。教师服务与生成成本没有完整报告，因此也没有得出“最佳教师同时最省钱”的结论。

### 3.6 Rollout 过滤：最扎实的证据是附录等 token 对照

正文 Table 7 的三种过滤结果：保留至少 5 个 model turns 为 **29.00/19.10/11.61，Raw=19.90**；去掉 timeout 为 26.67/18.03/10.49；去掉 subagent traces 为 23.00/17.31/10.86。该表没有独立 unfiltered 行，不能自行补一个基线后计算增益。[P §3.6, Table 7][P7]

固定行数时，长轨迹大约多 45% token，作者在 A.3 另做匹配：

| 选择 | 行数 | 训练 token | SWE100 / OTLite / TB2.0 | Raw |
| --- | ---: | ---: | --- | ---: |
| 至少 5 turns | 9,859 | 144.76M | 24.7 / 18.4 / 10.9 | 18.0 |
| 随机子集 | 14,470 | 144.78M | 19.3 / 17.1 / 7.1 | 14.5 |

这是本篇较有辨识力的对照：差异为 **+5.4/+1.3/+3.8 pp，平均 +3.5 pp**；作者认为 OTLite 的变化仍在噪声范围。[P A.3, Table 15, p.24][P24]

**本文判断：**匹配 token 明显排除了“仅因为总 token 更多”的解释；但不能无条件升级成相同 attention FLOPs、墙钟、教师费用或任务结构完全一致。它也不证明“越长越好”或“RL 应奖励更多 turns”。这里优化的是示范选择，不是给运行中的策略加长度奖励。

<a id="scaling"></a>
## 4. 扩大数据量：底层问题数、表面描述数、轨迹数与数据行数

### 4.1 四条路线并非同一种多样性

作者列出：①同题生成更多轨迹；②同来源增加不同任务；③改写已有任务描述；④增加初始来源。Fig.3 显示，①从 31.6K 到 100K 的 SWE100 约 +3 pp、TB2.0 约 −2 pp，作者称都落在误差范围；因此考虑描述多样性不足。Tezos 只有 **997 个独特底层问题**，限制了直接扩题。[P §4, Fig.3][P8]

100K 下的来源扩展实验 Table 8：

| 来源组合 | SWE100 | OTLite | TB2.0 |
| --- | ---: | ---: | ---: |
| Top-4 | 45.33 ±1.73 | 36.90 ±1.82 | 21.72 ±1.54 |
| Top-8 | 49.00 ±1.45 | 38.87 ±2.09 | 22.85 ±1.30 |
| Top-16 | 40.33 ±1.41 | 33.14 ±2.01 | 20.60 ±1.67 |

Top-8 三项点估计均高于 Top-4，但作者判断并非每项都有可靠改善，选择保留 Top-4；Top-16 三项都下降。本文保留点估计和作者决策，不将表标题“negligible”解释为已证明两者等效，也不自行用误差条重叠判显著性。

最终替换 Tezos 子集：对**相同 997 个底层问题**改写，表面形式从约 902 扩至 21K 以上；用 gpt-5-nano 回答长度作采样权重，每个独特任务至少一条 rollout，剩余容量按得分分配；四来源统一至少 5-turn filter。[P §4, pp.8–9][P9]

因此，引言中的“expand the set of data sources”不能替代具体流程：最终方法保留 Top-4，主要扩展 Tezos 的描述形式，而不是发现了 21K 个全新现实问题。它是有限种子描述增广的正面证据，不是在线自适应 curriculum 或自博弈生产线的证据。

### 4.2 “100K”发布的实际数量得到交叉核对

Fig.4 原始计数：SWE-Smith 9,998、IssueTasks 4,830、SuperUser 12,817、Tezos 997。最终分流标注为 **25,000、25,000、22,848、21,486**，相加 **94,334**，不是 100,000。[P Fig.4, p.9][P9]

本轮打开官方 [SFT-100K 数据查看器][D-SFT]，实际显示 **94,334 行、约 1.75GB**，与图中加和一致；但卡片文字仍写 Rows:100,000。因此本文使用 **“100K 档／名义 100K，公开实际 94,334 行”**。这不是静默改论文，而是保留论文命名、图中计数和公开资产三层证据。是否历史训练另行补采到整 100K，没有取得足够记录。

查看器还显示 `conversations`、`task`、`trace_source`、`result`、`trial_name` 等字段。可见样例中 `task` 是 `swesmith-..._copy...` 标识，`trace_source` 有 `main`、`summarization-1-summary`，`result` 有 null 与 AgentTimeoutError。**它不是每行均可直接认定为独立、成功、完整 episode 的数据集**；数据卡将 trace_source 解释为四个原始来源，但实际可见值并不完全一致。未下载全量，因此不估计这些情况的占比，也不据个别样例断言训练一定消费了它们。

这种资产检查对复用很重要：原始 task lineage、派生描述、重复尝试、摘要片段和训练行数不能共用一个计数。

### 4.3 32B 与 8B scaling 的准确含义

32B 最终档在统一 Terminus-2 的三个开发坐标为 **55.7 / 41.3 / 26.2**，31.6K 档为 **48.0 / 39.0 / 21.3**。后两者差值应据各表四舍五入值解释，正文将 TB 增量约称 +5.0 pp。[P §4；Fig.1/3][P8]

8B 附录 B：100K 档 **SWE100=39.7、TB2.0=10.9**，31.6K 为 26.3/7.9；对比 Nemotron 相同档为 34.3/9.0。Fig.5 明确说在多数匹配规模上领先；Fig.1/Fig.5 也有竞争数据在小规模或某单项更高的点。**摘要“every training set size”的宽泛措辞不应用来替代具体曲线。**[P B, Fig.5, p.25][P25]

同规模数据比较仍需看 epoch、长度、底座和 harness；不同数据集天然长度不同，数据行数相同不意味着训练 FLOPs 与教师成本相同。SERA 原集最多约 47K 且有原生 SWE-agent 评测，曲线和平均值使用方式已在 Fig.1 脚注区分。不是所有线都只换了数据而完全固定所有系统变量。

<a id="rl"></a>
## 5. RL：来源选择、冷启动、优化语义与后期崩溃

### 5.1 八种来源只说明“能学”远远不够

§5 在相同 ColdSFT 初始化、算法和评测条件下换 RL 数据。奖励在主描述中是 verifier 的二元正确性：每个测试的实际结果必须符合预期 PASS／FAIL。不同来源 verifier 的具体构造未被统一审计；尤其 `llm-verifier-freelancer` 不能仅凭这段总述当作纯 deterministic unittest。[P §5.1–5.2][P9]

| RL 来源 | SWE100 / OTLite / TB2.0 | Raw |
| --- | --- | ---: |
| pymethods2test | 35.67 / 16.02 / 13.48 | 21.72 |
| R2E-Gym | 28.67 / 16.84 / 6.74 | 17.42 |
| nemo-code | 25.00 / 16.78 / 6.74 | 16.17 |
| llm-verifier-freelancer | 22.33 / 14.87 / 8.61 | 15.27 |
| inferredbugs | 26.00 / 14.30 / 6.37 | 15.56 |
| SWE-Smith | 24.33 / 14.30 / 6.74 | 15.12 |
| code-contests | 23.67 / 13.75 / 7.87 | 15.10 |
| nl2bash | 21.00 / 14.51 / 6.74 | 14.08 |

表按其综合排序展示；Raw 与 z-score 排序可以不同。**SFT 排名第 85 的 pymethods2test 成为本轮 RL 最优，SFT 最优 SWE-Smith 不是 RL 最优。** 这是对“给任务永久打一个通用质量分”的直接反例，但不是因果证明某个单独任务特征导致排名反转。[P Table 9, p.9；Table 13, p.23][P9]

pymethods2test 将 Codeforces/CodeChef/TopCoder 风格问题改成单函数 Python contract，附生成的 docstring 说明与 unittest；作者描述其 reference code 通常较短，不要求复杂多文件初始化。这支持“短而可执行的任务也可能产生 agentic 迁移”，不说明它与真实 SWE 相同，也不证明所有自动生成测试可信。[P §5.2；W][P10]

### 5.2 SFT 与 RL 的互补：主实验不是“最强 SFT 接 RL”

Table 11 是同 Terminus-2 的 pipeline 比较：

| 路线 | SWE100 / OTLite / TB2.0 | 三项 Raw |
| --- | --- | ---: |
| ColdSFT + RL | 35.7 / 16.0 / 13.5 | 21.7 |
| 单独 SFT-10K | 24.3 / 15.6 / 7.9 | 15.9 |
| ColdSFT | 23.7 / 14.8 / 6.7 | 15.1 |
| 直接从 Qwen3-8B 做 RL | 1.0 / 7.8 / 1.9 | 3.6 |
| Qwen3-8B | 5.3 / 1.3 / 1.5 | 2.7 |

这组结果支持**在该数据／配方下先建立可执行行为再 RL**。它不证明 RL 一般不能从 instruct 模型起步，也不证明“故意少训 SFT”优于完整 SFT：没有同一初始数据、不同 SFT 训练时长、随后等预算 RL 的完整网格。更没有 SFT-100K+RL 一臂。[P §5.3, Table 11, p.11][P11]

七项主结果的 SFT+RL 相对 Qwen3-8B 约 +17.7 pp，是整个训练链收益；相对最强 SFT-100K 只多约 **0.5 pp**，且部分能力回退，见 §7.2。不能将前者全部称为 RL 独立增量。

### 5.3 论文披露的优化和执行设置

| 层 | D.1–D.8 实际披露 |
| --- | --- |
| 主算法 | async RL；RLOO，`grpo_norm_by_std=true`；advantage normalization per-batch；token-mean loss |
| 比率／正则 | PPO clip low/high=0.2/0.2，c=3；无 KL control、无 entropy regularization |
| Policy optimizer | AdamW，lr=5e-6 constant、无 warmup，betas=(0.9,0.999)，weight decay=0，global norm clip≤1 |
| 数值 | bf16 autocast、fp32 gradient accumulation |
| 训练单位 | 64 prompts ×8 samples，名义 512 trajectories/update；policy mini-batch=64 prompts；每 batch 一次更新 epoch |
| 调度 | 48 global steps、2 epochs、sample packing；micro train=1、forward=4/GPU；非重入梯度检查点；每 5 步 HF export |
| 硬件 | NERSC Perlmutter，6 nodes×4 A100-SXM4-80GB=24 GPUs；2 nodes policy/reference、4 nodes inference |
| 后端 | FSDP2、fsdp_size=4、CPU param offload；policy/ref 共置；不是全部训推共置；SP=1 |
| 异步 | max staleness=16 steps、768 parallel workers；并非本文已验证的严格 on-policy 组采样 |
| 生成 | 16 vLLM engines、eager，temperature=.7、top-p=.95、top-k=20；单次 generation 4096、model context32768；prefix cache/chunked prefill；memory target .9 |
| Rollout | Harbor Terminus-2、interleaved thinking；1 vCPU/2048MB RAM/2048MB storage；agent1800s/verifier120s；280 concurrent trials |
| 终止与失败 | turns 无显式有效上限，主要受时间约束；最多3次retry，60–600s backoff；masked transient infra/network；TimeoutError、parse、OOM写为0reward |

出处：[P Appendix D, pp.26–28][P27]。768 generator workers、280 sandbox trials、16 engines 是不同层并发，不能据此推定有 768 个环境同时运行。

**公式边界。** 本篇没有给出完整 RLOO-n、per-batch normalization、dual-clip、stale ratio 与跨段损失的联立公式。一般 LOO 可写作 $r_i-\frac{1}{G-1}\sum_{j\ne i}r_j$，但这只是解释名称，不足以恢复这里的 std 对象、有效成员集、异常 mask 时机与最终分母。RLOO 配方表列了 critic optimizer 默认值，并不能证明该实验训练 critic。本文不借用 SAO／miles 的默认公式补缺。

动作与 observation 的 token mask、summary 子轨迹是否进训练、全零组是否补采、失败轨迹是否影响他人 baseline、实际 tokenizer 模板逐段对齐，也不能仅凭框架名称判断。后文只给已核定的配置和代码边界。

D.5 还有 `eval T=0, top-k=-1, n=8`，G 却是每 benchmark 三次随机评测。这更可能属于不同 evaluation 入口，但没有完整运行日志逐一绑定；两套设置分别记录，不用训练配置覆盖最终 benchmark 协议。

### 5.4 附录 F 是必须保留的结果，不是可删除的失败日志

作者分析约 **11K hero rollout** 与 **53K llm-verifier-freelancer rollout**，加上 held-out pre/post 轨迹和每条路线 30 对同题轨迹的 GPT-5-2025-08-07 判断。[P F, pp.29–33][P29]

**pymethods2test：更多探索，随后过度延长。** 在同 100 个 SWE 任务每题3次的 300-row eval 中，think token/trace **30.3→65.4**，tool calls **31.3→40.9**，self-correction phrases **.63→1.14**，conversation turns **40.5→53.3**，conversation token **18,432→23,686**。judge 在25/30对中偏好训练后；18题fail→pass，1题回退。另有8/30对被标注更短／更少调用，并非所有任务都变冗长。[P Table 21][P30]

训练期 reward 在约 **.47–.51** 徘徊，之后下降至约 **.13–.14**，尾部 agent timeout 达约 **80%**。Fig.8 同时显示 turns、每条 assistant 输出、thinking、自我纠正飙升，productive tool calls 反而下降。作者解释为探索压力导致的过度延长，不是独立证明其所有因果环节。没有对应地隔离超时预算、KL、entropy、长度处理等因素。[P Table 22、Figs.6–8][P31]

**llm-verifier-freelancer：行为收缩，reward 更稳。** 训练 reward 约 **.54→.73**，turns −7.8、tool calls −8%、think tokens −42%、自我纠正19.7→8.0，conversation tokens约+1%。judge偏好post为22/30。这里的 `compacts` 是行为变得简短，不是实施 CompactionRL 或显式摘要训练。[P F.2, Table 22][P31]

**关键统计区别。** hero 的“有结果／完成 trials 条件均值”从 **.652→.541**，但将错误／超时计0的 all-trial eval 约 **.19→.33**。难样本从超时变成完成尝试，可以让条件均值降低而总体效果提高。训练后期的崩溃与所选 checkpoint 的 held-out 改善也不矛盾：作者说选择了崩溃前 checkpoint。[P F.3][P31]

仍有未闭合项：F 图轴是五月 wall-clock，D.8 pin 称二月 run start；Table 22 称reward约step35峰值，公开模型标step45，D诊断step48。本文保留这些身份与时序信息，**没有足够日志将它们强行拼成一条精确曲线**。同理，11K/53K是行为分析轨迹量，不应等于48×64×8名义训练消费量。

作者题为“not reward hacking”的论证主要依赖工具行为与少量judge／held-out改进。它削弱部分格式投机解释，**不等于经过独立隐藏verifier、攻击测试或评分隔离审计**。Table21 的平均tool errors除以平均tool calls也不等于其另列平均per-call rate；没有逐条聚合定义，不擅自重算替换。

## 6. SFT 配置与成本：正文、附录、示例存在不同口径

### 6.1 附录 C 的可恢复配置

| 配置 | 32B | 8B |
| --- | --- | --- |
| 基础优化 | AdamW betas=(.9,.98), wd=.04, lr=4e-5 | 同左 |
| schedule | cosine，warmup ratio .1 | 同左 |
| global batch | 96 | 96 |
| context | 32768 | 32768；部分长变体131072 |
| precision/backend | bf16，DeepSpeed ZeRO-3 | 同左 |
| 通用硬件表 | 24 nodes，每node4 GH200 | 24 nodes，每node4 GH200 |
| template | qwen3_thinking | qwen3_nothink |
| shuffling | disable_shuffling=True | disable_shuffling=True |

[P Tables16/18, pp.25–26][P25]

32B 规模表：3.16K、10K用7epochs和`max_grad_norm=1e-4`，约.5h/1.5h；31.6K、100K用5epochs和`1e-3`，约3h/5h。**Table17图注把小规模称looser、大规模称tighter，与数值限幅方向不一致；图注还写H100而通用表写GH200。** 保留数值，不按措辞擅自交换。[P Table17][P26]

8B规模表各档7epochs、clip=1；1K/3.16K/10K/31.6K/100K约1/2/4/10/30h。正文却说每10K消融160 GH200-hours；若机械用附录24×4GH200×4h会得到384 GPU-hours，两者不能直接闭合。**不能据其中一个数字声称整项研究消耗了精确总算力**。[P §3；Table19][P26]

这些极小梯度限幅和大集群SFT配置不应复制成八卡默认。原文没有证明它们对Qwen3-30B-A3B MoE、LoRA、另一harness同样合适；也没有SFT observation mask／每段加权的完整实现复现。

### 6.2 成本分类

| 成本面 | 可确认内容 | 仍缺内容 |
| --- | --- | --- |
| 任务与环境生产 | 95策略、公开生成框架和taskbundle | 全部候选／构建失败漏斗、CPU-hour、人工、验证与镜像存储成本 |
| 教师与校准 | GLM轨迹、GPT-5/5-nano选择信号、不同教师实验 | API费用、教师GPU-hours、失败尝试、每保留样本成本 |
| SFT | 正文160GH200h/10K；附录分规模配置与不一致 | 单项实际日志、总实验成本、不同数据长度下精确FLOPs |
| hero RL | 24×A10080GB，1.66e5s约46h | 是否计启动／重试／停机与外部sandbox；其他7来源和近重复运行总成本 |
| 评测 | 3次随机、双harness策略、按尺寸调timeout、API补充 | 全suite总费用、各模型实际尝试／失败／重跑账单 |

**本文算术估计：**24×1.66e5/3600≈**1,106.7 A100 GPU-hours**（若按46h取整为1104）。这只是把作者hero运行时长乘配置GPU数，不是全项目总成本，更不是本项目RTX PRO 6000的预计预算。[P D][P28]

<a id="evaluation"></a>
## 7. 评测：共同 harness、最佳系统和不同规模必须分列

### 7.1 最终七项均分的组成

最终平均包括：**SWE Verified全500、TB2.0、Aider、BFCL-Parity、MedAgentBench、GAIA-127、FinanceAgent-Terminal**；不包括OT-TBLite与SWE100。Table23虽然同时展示9列，Avg仍只平均上述7项。[P Table23][P35]

| 测试 | 数量与设定 | 本篇作用 |
| --- | --- | --- |
| SWE Verified-100 | 从500按仓库分层的100题 | 开发／消融；不能称独立于完整500测试 |
| OT-TBLite | 100题、4难度桶，TB风格proxy | 开发／消融 |
| TB2.0 | 89题 | 开发与最终均分共同使用 |
| SWE Verified-full | 500题 | 最终主表，但含已使用的开发100题 |
| Aider Polyglot | 225题，6语言代码修改 | OOD |
| BFCL-Parity | BFCLv4分层随机123题 | OOD；不是BFCL全套 |
| MedAgentBench | 300任务、FHIR约70万records | OOD；非医疗训练／临床可用性证明 |
| GAIA-127 | text-only validation127，不配searchAPI | OOD；不等于全GAIA或标准联网最强配置 |
| FinanceAgent-Terminal | 50题SEC财报，提供SERP/EDGAR | OOD；API与小样本噪声重要 |

每个(model,benchmark,harness)平均3次pass@1，不是至少一次成功的pass@3。所有本项目训练模型按G使用32Kcontext、16Koutput cap、proactive summarization threshold=2048；**原文没有仅凭这行明确2048是剩余空间还是其他触发量，不能写成每2K就压缩**。默认32concurrent，并复用Daytona snapshot。[P G][P34]

baseline除Terminus-2外还跑原工作推荐harness／服务配置，主表取每模型每benchmark较高准确率。Table23符号包括OpenHands、SWE-Agent、SERA-SWE-Agent、R2E-Gym-Edit-Agent、SkyRL-ReAct、mini-SWE-agent；下划线表示从原论文补入而非作者复跑。**“开放模型的最佳系统比较”与“全表共同harness的权重比较”不能混称。**

### 7.2 两张主结果表里最应保留的对照

下表只转录用于判断的行；完整跨模型清单见原文Tables1/10/23。

| 32B路线 | SWE500 | TB2.0 | Aider | BFCL | Med | GAIA | Finance | 七项均分 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OT-Agent SFT100K档 | 54.0 | 26.2 | 32.4 | 85.9 | 47.8 | 23.6 | 44.0 | 44.8 |
| Nemotron-Terminal SFT264K | 41.9 | 25.1 | 24.9 | 69.1 | 62.6 | 22.3 | 40.7 | 40.9 |
| Qwen3-32B | 29.1 | 7.5 | 28.9 | 68.3 | 6.8 | 9.7 | 9.3 | 22.8 |

OT均分约+3.9pp、SWE+12.1pp，但Med **−14.8pp**。论文的排名限定Qwen3或更早底座、≤32B级别和开放数据模型，不是2026-09全部模型排行。不同表中native结果有下划线补值，比较应保留来源。[P Tables1/23][P35]

| 8B路线 | SWE500 | TB2.0 | Aider | BFCL | Med | GAIA | Finance | 七项均分 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ColdSFT+RL | 31.9 | 13.5 | 18.1 | 71.5 | 31.1 | 6.8 | 22.7 | 27.9 |
| OT SFT100K档 | 38.9 | 10.9 | 15.9 | 65.9 | 36.2 | 6.6 | 17.3 | 27.4 |
| Nemotron-Terminal264K | 22.1 | 13.1 | 12.6 | 59.9 | 48.6 | 14.4 | 11.3 | 26.0 |
| OT SFT10K | 22.7 | 7.9 | 14.2 | 79.4 | 25.8 | 5.5 | 14.7 | 24.3 |
| Qwen3-8B | 13.2 | 2.2 | 11.7 | 34.4 | 3.8 | 5.0 | 1.3 | 10.2 |

ColdSFT+RL对最强SFT100K仅均分+0.5pp，SWE **−7.0pp**、Med **−5.1pp**；没有七项均分差的完整显著性结果。对SFT10K的部分指标也有退化，例如BFCL71.5低于79.4。结论应是**另一个性能组合和学习路线**，不是SFT被RL全面支配。[P Table10, p.10][P10]

主表与Table23中SWE-Lego-8B等行的BFCL及平均数还有差异；本文不依赖这些行做主张。对原文内部同名模型数字冲突，不能随意选更好的一组。

### 7.3 预算与复现细节

G使用：

$$ t_{\mathrm{effective}}=\min(2\ \mathrm{hours},\ t_{\mathrm{base}}\times m),\quad m_{8B}=2,\ m_{32B}=16. $$

动机是避免较慢模型因吞吐被额外惩罚。这样比较没有固定相同wall-clock；native harness也可能采用不同长度和步骤。它回答的是作者定义的能力对比，不是固定资源部署排名。[P G p.34][P34]

OpenSWE原报告62.4是**完整500题**，作者以128Kcontext、300steps、temperature=.7和取得的SWE-Agent配置，在**100题子集**测得44.0。作者明确仍未解释差距，不能将18.4pp直接当同题复现失败；CoderForge未发模型所以不进主模型表，不代表它的数据无效。[P G][P34]

TB2.1核验仅重新测Qwen3.5-27B：TB2.0 **40.1±1.6**、TB2.1 **43.1±1.4**。作者因成本继续使用2.0。这只对一个baseline提供版本敏感性观察，不能证明所有数据配方的排名在2.1都保持，也不能声称已经检验最新TB。[P Table24][P36]

### 7.4 近重复运行：有帮助，但不是严格独立复现

E中的三条pymethods2test运行共享ColdSFT、算法、24A100，但改变了export step，其中一条还改lr；hero checkpoint另作两次评测。它们不是只换seed的完整训练复制，也不是其他团队复现。[P E, pp.28–29][P29]

Table20列三项Raw均分 **21.72、21.19、19.68**，范围 **2.04pp**；正文却写Core范围20.2–21.8、1.6pp。正文还引用caption中的mixed-variance estimator，实际caption未给公式。并且lr5e6被称不同于其他两条默认lr，但D的默认同样列5e-6。这些未闭合处影响精确不确定性重建，不应靠猜测填补。

作者报告OOD均值约26.5–28.5，小样本Finance两次评测相差约11pp。没有逐评测完整表和估计公式，本文不推算更多标准误，也不把三条实验的观测范围当作任意未来运行保证。相对于base的大改进和相对于强SFT的0.5pp差，需要不同的统计置信强度。

<a id="assets"></a>
## 8. 开放资产与代码：能重建哪些环节，哪些仍不闭合

### 8.1 资产访问状态

| 资产 | 本轮直接核到什么 | 不能据此宣称什么 |
| --- | --- | --- |
| [论文][P] | v1全部正文／附录、主要图表 | 所有实验已复现 |
| [官方博客][W] | 发布说明和核心资产入口 | 额外算法细节或独立验证 |
| [SFT-100K][D-SFT] | 94,334行、字段与部分样例；卡片Apache-2.0 | 10万个独立成功任务；完整RL环境；所有原始来源权利已审核 |
| [RL-5K][D-RL] | 卡片5000task，`path`和gzip `task_binary`；标准任务bundle而非示范 | 本轮已解压／构建5000任务或检验oracle |
| [8B RL模型][M8] | step45、ColdSFT lineage、9437冷启动、Qwen3架构说明及配置文件名 | 名称带GLM意味着学生是GLM；eval数字已经由卡片验证 |
| [32B模型][M32] | Qwen3-32B全参SFT配方、共同harness和七项结果区分 | 32B也做了本文RL；Hub自动参数计数一定准确 |
| [OT代码][C0] | 研究代码、安装／数据／SFT／评测入口 | stableAPI、所有依赖固定或一键复现 |
| D.8 W&B | 原文写available on request | 本轮访问了全部训练日志 |

模型卡和数据卡声明Apache-2.0，不等于95个上游语料、镜像、教师服务条款都由本轮完成许可核验。本篇是技术审读，不作法律结论。HF元数据自动显示的模型参数数量与架构名称可能异常；本文按明确模型身份而不是页面自动计数解释实验。

**模型卡与论文的范围差异。** 8B RL卡仍写“该源artifact无verified benchmark numbers，TBD”，论文则已经给Table10；卡片称on-policy，D却描述有16-step staleness的async。本文分别记录，不能用卡片抹去论文结果，也不能用论文默认所有发布权重和运行完全对齐。[M8]

### 8.2 固定代码给出的几个关键事实

**a. 历史 RL README 不足以代表本篇最终配方。** `[C1] rl/README.md` 主要描述更早的OpenThinker-Agent-v1、另一数据集和GRPO。不能只阅读该README，就把v1 recipe填进本篇8B RLOO实验。

**b. 真实入口确实选择 fully-async trainer。** `[C3] .../entrypoints/main_tbench.py::TerminalBenchExp.get_trainer` 在`trainer.placement.colocate_all=false`时选择`FullyAsyncRayPPOTrainer`，否则是普通`RayPPOTrainer`。其dataset从`cfg.data.train_data`构造；这里只核到入口，不宣称已审完跨版本概率或数值等价。[C3]

**c. thinking保存是实际版本修改。** OT固定commit改`chat_templates/qwen3_thinking_acc.jinja2`：优先读取`reasoning_content`，否则解析文本think区段，保留历史assistant thinking；多个RL YAML同时增加模板路径。这个动作证明作者有处理多轮格式一致性的需求，**不证明所有采样token、教师文本和训练mask已逐token对拍**。[C2]

**d. 同一pin的基础YAML也不是论文最终run config。** `[C4] hpc/skyrl_yaml/jupiter/24GPU_base.yaml` 与D对照：

| 字段 | 论文D | 固定基础YAML |
| --- | --- | --- |
| max_steps | 48 | 60 |
| max_grad_norm | 1 | 10 |
| CPU offload | true | false |
| generation max | 4096 | sampling8192，model_info另列4096 |
| GPU memory utilization | .9 | .75 |
| 错误处理 | TimeoutError写0reward | mask_exceptions包含AgentTimeoutError/ContextLengthExceededError；另有retry exclude名单 |
| thinking／summary | interleaved thinking | interleaved=true、enable_summarize=false、store_all_messages=true |

这些可能由最终CLI覆写或不同cluster模板解释；没有运行导出的resolved config，不将基础YAML判作论文错误，也不任选其一冒称复现。`exclude_exceptions`属于retry策略，`mask_exceptions`属于错误处理，两者不能因为都列错误名就混为一个过滤列表。

**e. trial结果不是总能从job汇总读取。** Harbor固定commit修复`src/harbor/utils/traces_utils.py::_extract_trial_result_value`：先检查job-level汇总，缺失时回退到trial `result.json`，先读exception再读verifier reward。注释明确RL trial可能没有eval/datagen那种job总表。对离线轨迹导出而言，这是数据完整性问题；本轮没有证明该bug影响任何论文数字。[C5]

**f. 当前生产框架区分任务和轨迹。** `[C6] data/README.md` 的两条入口为轻量`generate.py`与`BaseDataGenerator`；后者经`GenerationRequest/Result`、engine、task generation、trace generation、上传组成流程。单脚本复用适合窄实验，不必为了复用数据生产构建整个HPC平台。README声称“版本控制脚本足以重现数据”仍需外部数据revision、模型/API版本和环境资产共同成立。[C6]

当前根README安装SFT extra可能触发submodule `--remote`同步；正式复现应冻结实际依赖，不把仓库主SHA视为整个运行环境已固定。论文没有给LLaMA-Factory fork精确pin，ALST存在不代表每个32K实验都采用相同长序列策略。[C0]

### 8.3 本轮没有做到的代码／资产验证

没有读取所有95个generator、最终混合器、完整loss reducer、RLOO-n异常组实现、全部harness parser、完整eval adapter，也没有全量数据统计、镜像启动或模型推理。因此不提供“整条链正确／错误”的断言。源码本轮是为解释已披露实验和识别复用边界，而不是另起一次全框架审计。

## 9. 证据强度与尚未回答的问题

### 9.1 对哪些结论较有把握

**有匹配比较的局部证据：**10K下来源／混合／教师选择、近似等token长轨迹过滤、相同基础配方下RL来源比较。仍主要是同团队、Qwen3、Terminus-2、固定几个开发指标，不能称不同团队独立复现。

**有训练结果、但归因不完整：**最终32B／8B七项成绩、SFT+RL整体收益、大规模改写配方。主表多个变量和best-harness选择同时变化，不能分摊成每个组件的贡献。

**有描述与轨迹分析、但没有充分因果隔离：**教师为何更适合学生、探索如何形成迁移、为何后期崩溃、为什么某数据源使行为更简短。作者给出了合理解释；本文不将它们写成已确证的心理机制。

### 9.2 最影响迁移／复现的缺项与不一致

| 项目 | 查到的状态 | 后续应如何使用 |
| --- | --- | --- |
| 95来源的环境质量与污染 | 没有统一构建／oracle/no-op/替代解/去污染漏斗 | 不因数据在论文里有效就直接进入rh2可信训练 |
| 100K实际行数 | 图加和及HF viewer均94,334；卡片仍100K | 保留名义档位与实际行数，禁止当作100K独立任务 |
| ColdSFT实际数量 | 名称10K，卡片9437 | 预算按实际数据，不按名称 |
| 教师和归一化选型 | GLM4.7是z-score胜者，Kimi Raw更高 | 明确我们最终优化哪组任务及聚合方式 |
| SFT算力／梯度限制 | §3 vs C成本不闭合；C表H100/GH200及looser/tighter冲突 | 原文数值并列，不照抄为推荐配置 |
| RL精确目标 | 无完整ratio、std、mask／loss分母联立公式 | 需最终resolvedconfig与实际后端实现才能复现 |
| 重复实验误差 | Table20均值范围与正文不合；mixed estimator公式缺失 | 不生成虚假的显著性或稳定性承诺 |
| hero checkpoint与崩溃时间 | step45发布、step48指标、F五月曲线、D二月pin | 不从几个局部记录反演完整run时序 |
| 正文与附录行为描述 | §5.2强调紧凑探索—修复；F显示主hero在SWE评测扩展 | 指明比较对象和cohort；不静默只保留“更高效” |
| 原文/代码/API资产版本 | 三个历史pin可取，但示例和卡片不能闭合全部运行 | 代码可复用≠实验一键复现 |
| 独立验证 | 作者近重复运行，未提供不同团队复现 | 标签不是R级独立复现 |

### 9.3 作者自己承认的限制与影响

§6指出主要SFT数据只到100K档、RL主要8B，不能保证多百万数据／更大RL同样保持趋势；底座固定Qwen3，更新家族属于未来研究。研究目标是扩大开放可复用数据和工具，而非给最终agent部署完整安全保证。更强工具执行也可能用于不当活动；开放代码／模型的价值与误用风险同时存在。[P §6/Broader Impacts, pp.11–12][P11]

本篇没有全面能力保持、生产安全、重复可靠性、跨日任务或用户协作训练。因此不把七benchmark均值转述为完整“通用可靠agent”。

<a id="project"></a>
## 10. 对 RepoHarness 项目一的意义：数据配方应由本地现象选择

映射仅适用于 §1 的分支快照：miles/SGLang、真实coding harness、rh2环境与训练消费职责，目标约30B-A3B、单节点8×96GB。论文dense8B/32B与A100/GH200配置不能直接换算。本轮没有审核本项目新GPU结果，也不沿用旧probe作成熟训练证据。

### 10.1 本篇支持哪些候选，而非批准哪些组件

| 候选 | 来源证据 | 对项目的适用条件 | 低成本辨识方式 |
| --- | --- | --- | --- |
| 分开评价SFT供给与RL任务 | 同一pymethods2test在两阶段排名反转 | 已有合法任务，且要决定warm-start或在线训练用途 | 固定目标模型／harness，比较可执行性、成功分布、反馈与少量SFT/RL结果；不用一个永久质量分代替 |
| 强的多轮SFT基线 | 32B只SFT已获得主要结果；8B100K均值接近SFT+RL | 目标模型欠缺基本工具行为或在线rollout昂贵 | 同来源示范与同等token随机过滤对照，再测是否降低真实RL成本 |
| 模型相对的教师选择 | 强求解器不必是z-score最优教师 | 有API／本地教师预算且可生成合法示范 | 先固定小任务池、预算、harness比较示范可用性与短SFT迁移；不按教师榜单直接选 |
| 先扩描述覆盖，再决定扩环境平台 | 同题重复平台期、Tezos表面改写有效、Top16负结果 | 真有重复瓶颈且环境复用可信 | 固定底层题数与总token，比较原题补采、描述改写、不同任务；记录派生lineage |
| 监测有效完成与超时，而非只看有分样本 | F中条件均值与all-trial指标方向相反；hero后期崩溃 | 真实agent存在长尾，终止状态可观察 | 每checkpoint分开记录全部尝试、完成尝试、失败／超时、tokens／tools；不修改任务来隐藏失败 |
| 训练与评测轨迹复用 | Harbor trial结果导出修复、SFT行与episode非一一对应 | 正在接数据生产和离线分析 | 检查result、task、trial、segment、mask的实际消费；复用现有rh2身份，不新建通用平台 |

**主要设计判断：**本篇没有直接支持“项目一必须增加在线动态课程”。它更支持一条有限、可测量的闭环：先识别数据／初始化／执行问题，再选择已有方法并比较。固定offline recipe可能已经是强基线；也可能需要特定反馈或任务扩容，需由本项目数据判断。

### 10.2 三个最有用的反事实问题

**首先，所谓RL收益是否已经由强SFT解释大部分？** 不能只对比base与SFT+RL；应把相同初始化的RL增量与更强SFT方案分别测清。原文0.5pp综合差和能力取舍提醒我们，单一平均数不是足够的选择依据。

**其次，所谓数据质量究竟改变了什么？** ≥5turn筛选可能改善多轮监督，但不能成为“排除短成功、鼓励冗长”的运行时规则。任务长度、基础技能、参考信息、teacher风格和语料覆盖最好至少保存可分析字段，不必先造自动策展系统。

**最后，提升是否依赖更宽松执行预算或特定工具面？** Terminus-2示范迁移到Claude Code，需要考虑工具表达、thinking保留、摘要、权限和环境状态；只把messages换成目标schema不能证明语义迁移。独立小规模对照比全面多harness接入更便宜。

### 10.3 对简历叙事的支持与限制

可支持的方向是：基于成熟训练后端，建立**可执行任务、教师示范、在线反馈与独立评测之间可反复验证的数据流程**，并准确解释哪些样本和训练阶段值得计算。若本项目进一步测出降低无效rollout或提升独立结果，才形成个人成果。

不能据本篇直接声称：我们已有100K可信SWE任务、采用其教师即有同样收益、异步staleness16最合适、32B/30B-A3B可直接复制、任务生成器比普通SFT必然更有价值。本文没有要求迁移框架、加入新loss或扩大项目范围。

## 11. 快速查阅与后续维护

| 要回答的问题 | 本文 | 原文定位 |
| --- | --- | --- |
| 哪个教师／来源最好，按什么指标？ | §2–3 | §3，Tables2–7、12–14 |
| 长轨迹是否只是更多token？ | §3.6 | A.3，Table15 p.24 |
| 100K是什么计数？ | §4.2、§8 | Fig.4 p.9；HF SFT viewer |
| 为什么SFT与RL数据排序不同？ | §5.1 | Table9 p.9与Table13 p.23；机制仍未完全识别 |
| SFT后RL的独立收益多大？ | §5.2、§7.2 | Tables10–11 pp.10–11 |
| rollout、异步、mask和硬件怎样设置？ | §5.3、§6、§8.2 | D pp.26–28；固定代码／最终config缺口 |
| RL具体改变什么、为何后期坏掉？ | §5.4 | F pp.29–33，Tables21–22、Figs6–8 |
| 主榜是否全统一harness？ | §7 | G pp.31–36，Table23脚注 |

关联已有笔记：[SWE-smith](E5_swe_smith.md)、[R2E-Gym](O03_r2e_gym.md)、[CalibForge](E2_calibforge.md)、[SkyRL-Agent](O01_skyrl_agent_sa_swe.md)。关联仅用于比较问题，不以其他文章补本文未披露事实。Nemotron-Terminal、ECHO、SDPO也应比较，但本文不猜其当前文件名建立失效链接。

本稿是新的一篇来源精读，不是旧外部Pro建议的重新包装。上一轮的“100次消融、通用配方、高优先级”只是选题依据；本次正文补上了其具体分母、负结果、预算和资产差异。

## 12. 作者自查与残余边界

已完成正文／A–G全文阅读、主要图表原图核对、三处历史代码pin恢复、配套资产的实际访问检查和独立算术校核。没有训练复现、没有全量数据／权重下载、没有独立reviewer。**状态：作者自查完成，待独立复查；Table1单页目视仍缺，但文本／Table23／模型卡已核其关键数值。**

本轮只增加本篇和[自查记录](reviews/task08_openthoughts_agent_self_check_20260908.md)；数值核查结果保存在自查记录中，不更新共享索引、训练实现、配置或其他线程的成果。

## 一手来源链接

[P]: https://arxiv.org/pdf/2606.24855v1
[P4]: https://arxiv.org/pdf/2606.24855v1#page=4
[P5]: https://arxiv.org/pdf/2606.24855v1#page=5
[P6]: https://arxiv.org/pdf/2606.24855v1#page=6
[P7]: https://arxiv.org/pdf/2606.24855v1#page=7
[P8]: https://arxiv.org/pdf/2606.24855v1#page=8
[P9]: https://arxiv.org/pdf/2606.24855v1#page=9
[P10]: https://arxiv.org/pdf/2606.24855v1#page=10
[P11]: https://arxiv.org/pdf/2606.24855v1#page=11
[P24]: https://arxiv.org/pdf/2606.24855v1#page=24
[P25]: https://arxiv.org/pdf/2606.24855v1#page=25
[P26]: https://arxiv.org/pdf/2606.24855v1#page=26
[P27]: https://arxiv.org/pdf/2606.24855v1#page=27
[P28]: https://arxiv.org/pdf/2606.24855v1#page=28
[P29]: https://arxiv.org/pdf/2606.24855v1#page=29
[P30]: https://arxiv.org/pdf/2606.24855v1#page=30
[P31]: https://arxiv.org/pdf/2606.24855v1#page=31
[P34]: https://arxiv.org/pdf/2606.24855v1#page=34
[P35]: https://arxiv.org/pdf/2606.24855v1#page=35
[P36]: https://arxiv.org/pdf/2606.24855v1#page=36
[W]: https://www.openthoughts.ai/blog/openthoughts-agent
[M32]: https://huggingface.co/open-thoughts/OpenThinkerAgent-32B
[M8]: https://huggingface.co/open-thoughts/OpenThinkerAgent-8B-RL
[D-SFT]: https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-SFT-100K
[D-RL]: https://huggingface.co/datasets/open-thoughts/OpenThoughts-Agent-RL-5K/blob/main/README.md
[C0]: https://github.com/open-thoughts/OpenThoughts-Agent/blob/3bd1917e62c9d03d73063b433f5c442c279c0563/README.md
[C1]: https://github.com/open-thoughts/OpenThoughts-Agent/blob/4e2b8422b7ee5ca4af3566df603c1ca58d576238/rl/README.md
[C2]: https://github.com/open-thoughts/OpenThoughts-Agent/commit/4e2b8422b7ee5ca4af3566df603c1ca58d576238
[C3]: https://github.com/penfever/SkyRL/blob/ada3bd4f952ef5ff59134389e5577f54530d29f6/skyrl-train/examples/terminal_bench/entrypoints/main_tbench.py
[C4]: https://github.com/open-thoughts/OpenThoughts-Agent/blob/4e2b8422b7ee5ca4af3566df603c1ca58d576238/hpc/skyrl_yaml/jupiter/24GPU_base.yaml
[C5]: https://github.com/harbor-framework/harbor/commit/94f358bc51fb214d8089f098c746ef6f3f66e9a3
[C6]: https://github.com/open-thoughts/OpenThoughts-Agent/blob/3bd1917e62c9d03d73063b433f5c442c279c0563/data/README.md
