# R3 独立审查：Qwen3-Coder-Next Technical Report

## 审查对象、版本与方法

- 审查日期：2026-09-07；独立审查者按派工使用 GPT-6 Astra / high、干净上下文，仅收到原文、初稿、模板位置与项目映射边界；未再委派其他审查者。
- 原文：[arXiv:2603.00729v1](https://arxiv.org/abs/2603.00729v1)，23 页；以提供的 PDF 和对应 `tmp/pdfs/R3.txt` 为正文依据。arXiv 版本页独立打开，确认 v1 提交于 2026-02-28 16:25:04 UTC；PDF 封面印 2026-03-03。没有改用未指定的新版本。
- 初稿：[R3_qwen3_coder_next.md](../R3_qwen3_coder_next.md)，本次审查时 495 行。下文行号仅用于定位这一版初稿；修订后可能移动。
- 先读原文 §2–6、A.1–A.4 并建立结构与事实清单，再完整读初稿作逐项对应。§1、作者和 References 概要读。原图额外检查 p5、6、8、9、10、19、20、21、22：覆盖 Figures 3、5–8，组合公式，Tables 2、10–16 与 packing 公式；p7 Figure 4 结合整页提取文本核对三种格式轴。
- 独立打开 [PrimeVul 原论文 v2 §IV-B2](https://arxiv.org/html/2403.18624v2#S4.SS2.SSS2)，只核指标定义及表头方向，不把其训练配置迁移到 R3。没有精读 SWE-Universe、MegaFlow、FIM 关联论文或使用二手综述填补 R3。
- 辅助窄读初稿固定的 [provenance](../sources/R3/provenance.json)、Next / Next-Base 模型卡和 Qwen3-Coder README 的模型、部署、采样与语言覆盖字段。模型卡 revision 分别为 `a7fbcb5c0e12d62a448eaa0e260346bf5dcc0feb`、`1b6df59d5f75ab51edb9ad8cb3ea69c5d0aedd57`；Qwen3-Coder revision 为 `33bc6aabd7791ad7b32f7e92104f11f2359ba890`。本次未重新获取 Hugging Face/GitHub API 元数据，不把快照 provenance 当成独立复验过的在线元数据。
- 为检查项目映射，窄读 `CURRENT-STATE-BRIEF.md` 与 `project1_design_advice_20260907.md` 中基线、候选训练配置、REALIGN/rewrite/FORK、真实评分和上游复用边界。没有代码审计，也没有批准新训练语义。
- 仅写本审查文件，未改笔记正文。沿用现有 PDF/文本，未创建额外摘要或下载 TeX 文件。

## 独立后训练覆盖表

前两列依据原文标题与内容建立；最后一列在读完初稿后补入。精读包含对应正文、图表、图注及附录说明，不以是否直接适用于 SWE 决定取舍。

| 原文章节 / 页 | 独立核对的完整内容 | 初稿位置与覆盖判断 |
|---|---|---|
| Abstract、§1 Introduction，p1–2 | 80B/3B、Qwen3-Next 起点、分阶段 agentic training、专家回归统一模型；Figure 1 总览 | §1–3、§7；背景概要足够，Aider 在 Table 7 对应保留 |
| §2 Scaling up Agentic Training；§2.1 Task Synthesis，p2–3 | 两条数据管线；PR 去污染、bug/fix/test patch、构建 agent、non-functional verifier 过滤、专门模型及 QA agent；既有容器仓库注入 bug、测试失败/回退成功、issue 生成、测试排除；Figure 2 | §4.1–4.4；完整，实例/环境/轨迹/消费量分开 |
| §2.2 Infrastructure，p3 | MegaFlow、阿里云 Kubernetes、Argo；rollout / evaluation / post-processing，agent 与环境同 pod，专用评分容器 | §6；完整，不冒称已知异步 learner 调度或完整私有评分隔离 |
| §3 Mid-training；§3.1 Data，p3 | 天然数据为主、最小必要合成量；专门化/多样性/适应性取舍 | §3.1；完整，未编造混合比 |
| §3.1.1 Natural Data，p4 | GitHub 文件/仓库级、92→370 语言、600B 仓库 token、截止日、上下文扩展；网页 grounding 与 480B 改写、Table 1；PR 文档构建与去污染 | §3.1–3.2、§4.4；完整 |
| §3.1.2 Synthetic Data，p4–5 | grounded QA、允许不生成、Wikipedia-style 虚假引用负结果；六种轨迹框架、480B teacher、三种过滤；Figure 3 同/跨 scaffold scaling | §3.1、§4.3；完整，迁移非对称与非单调被保留 |
| §3.1.3 Instruction-Following Data，p5 | 少量指令数据用于中训阶段下游监测 | §3.1；完整 |
| §3.1.4 Fill-In-the-Middle Code Completion，p5 | Stack-V2、chat-FIM / search-and-replace FIM、proxy、相同规模相对结果与作者解释 | §3.1；完整，未把关联论文实验算入已读 R3 |
| §3.2 Training，p5–6 | 万亿量级 NTP/FIM、262,144、BFP、超长文 split、重复段 mask；文档索引构建的局部效率声明 | §3.2、§5.4；主要机制完整；局部效率声明可补，见 R3-02 |
| §4 Post-training；§4.1 Supervised Fine-tuning，p6 | 内部安全对齐语料、验证轨迹、功能/安全过滤的 grounded QA；Mini-SWE-agent 用户模拟器；n 候选、组合数、pairwise checklist / ordinal ranking、风格与主动性结果 | §3.3；完整，不误写 DPO 或 learned SWE reward |
| §4.2 Expert Models，p6 | 同一初始化、不同数据和训练配方；专家不是顺序四阶段或 MoE 内部专家 | §3 流程图与说明；完整 |
| §4.2.1 Web Development Expert，p6–7 | Playwright/Chromium、Vite、静态截图 VLM、DOM 与自动动作、前后截图动态验证；过滤后轨迹训练 | §3.4；完整，未冒称 WebDev RL 或多模态学生 |
| §4.2.2 User Experience Expert，p7–9 | 多来源/多 scaffold 数据清洗与混合消融、通用失败与格式过滤；三种格式轴、多模板；Figures 4–5、五匿名 scaffold 内评 Table 2 | §3.5、§7.1；完整，92.7 并非最高、格式正确不等于任务完成 |
| §4.2.3 Single-turn Question Answering Expert，p9–10 | 执行可验证单轮 RL；库/API、I/O、多语言、复杂指令、安全生成/修复；候选测试与独立解多数共识；Figure 6 九类能力 | §3.6、§5.1；完整，保留共识不保证正确、曲线非因果消融 |
| §4.2.4 Software Engineering Expert，p10–11 | 开源/自建环境、SFT/RL prompt 互斥、pass-rate 过滤；终局 reward、unfinished penalty、非法调用 token penalty；未来 commit 泄漏与新 blocker；Figure 7 | §4.4、§5.2–3；完整，训练上限未知、75.1/84.6 与平均 turns 边界清楚 |
| §4.2.5 Expert Distillation，p11 | 四领域 expert 蒸馏到 SFT model，保留指令遵循、单模型部署 | §3.7、§5.5；完整，未把 480B teacher 误作此阶段教师或补写 OPD |
| §5 Experiments；§5.1 Agentic Evaluation，p11–12 | baseline 复测及标准防泄漏；SWE Verified / Multilingual / Pro 多 scaffold、Terminal 2.0 四配置；Tables 3–5、300 turns | §7.2、§6；完整，未知 split/采样/预算明确，破折号不作零分 |
| §5.2 Other Coding Tasks，p12–13 | 函数级、推理/竞赛、full-stack、SQL、多语言编辑，Tables 6–7 | §7.3；全部 benchmark 与数值保留，明确退化项 |
| §5.3 General Tasks，p13 | 通用知识/推理、竞技数学，Tables 8–9，作者迁移解释 | §7.4；全部指标保留，不补写专项数学 RL |
| §6 Conclusion, Limitation, and Future Work，p13 | 复杂大型 SWE、更多交互轮、UI 短板；harder pretraining、RL/planning、视觉与 agentic cybersecurity/CTF 未来方向 | §2、§7.6、§8；完整，较低总训练算力只是未量化作者声明 |
| §7 Authors、References，p14–18 | 作者列表与关键引文身份核对，特别 Pan et al.=SWE-Gym；架构/基准/关联工作入口 | §1、§4.3、§11；概要读合理，未混入关联论文配置 |
| A.1 Data Statistics for Synthesized Tasks，p19 | Tables 10–11，真实 PR 与注入 bug 分别统计；语言、repo raw/cleaned/used、四策略、平均任务数 | §4.1–2；完整，两个池不直接当作去重训练集相加 |
| A.2 The Checklist of Tool Chat Templates for Scaling，p19–20 | 原文声称 21、实际 20 行；各定义/调用格式与特殊模板来源 | §3.5；逐行核对一致，原文计数矛盾已保留 |
| A.3 Detailed Implementation on Best-Fit-Packing，p19–20 | C++ / Megatron、文档开头工具定义、fragmentation / padding 的两种分母 | §5.4；完整，统计口径与 RL loss 分开 |
| A.3.1 Two Variants of Sample Packing Strategy，p20–21 | RLD 头部重启/尾截断/头 token 重权；PLD padding mask 与预算补偿；Figure 8 | §5.4；完整，公式和计算正确 |
| A.3.2 How to Tackle Long Documents with Best-Fit-Packing，p21 | split、slide、drop；残块处理、BFP 容量前提 | §5.4；完整；中文 backward 方向可写得更明确，见 R3-03 |
| A.3.3 Ablation Study on Sample Packing Strategy，p21 | Agentless 定位/patch 两步；Model Loc/GT Loc/GT File、similarity/empty、73B/89B、Table 13；drop 最佳但主实验 split；非单调取舍 | §5.4、§7.5；完整，22% fewer 分母问题已纠正 |
| A.4 Experiments on Cybersecurity，p21–23 | AthenaBench-Mini 六项及 greedy；PrimeVul-Paired 函数/成对指标与 greedy；SecCodeBench 53 Java、hint、严重度加权 pass@k；CWEval func@1/func-sec@1、n=10/T=0.8；Tables 14–16 | §7.6；四类评测完整。P-C 方向纠正有依据；还可补成对比例合计疑点，见 R3-01 |

结论：没有发现遗漏整个后训练阶段、专家领域、附录或评测类别。初稿没有把未读的关联论文当成 R3 事实，已列“未披露”字段在本次逐节阅读范围内也未找到相反披露。以下是局部补充和精度问题，不应被扩大为初稿整体错误。

## 逐项发现与建议

### R3-01 · P2 · Table 15 还存在成对比例合计的未解释缺口

- **初稿位置**：§7.6，行 380–382；§9.1 / §9.2 的 P-C 问题汇总。
- **性质**：确定的算术现象；其成因未知。不是初稿抄错数字，也不能确定作者评测实现错。
- **原文证据**：R3 A.4 p22 Table 15 原页中，Next 四列为 `0.88 + 53.01 + 41.29 + 4.64 = 99.82`；GLM-4.7 为 `20.55 + 38.60 + 26.57 + 12.53 = 98.25`。四项保留两位小数的舍入误差不足以解释这两个缺口。
- **为何影响解读**：按 [PrimeVul v2 §IV-B2](https://arxiv.org/html/2403.18624v2#S4.SS2.SSS2) 的二元成对定义，P-C/P-V/P-B/P-R 覆盖完整预测对的四类结果。若同分母且每个函数都有可解析二元预测，合计应约为 100%。原文没有说明缺失/无效预测、有效子集、分母变化或另一个类别。初稿已经正确拒绝 P-C 优越性结论，但只写函数与 pair 分母不同，还未显式记录这一组内一致性疑点。
- **建议**：在已有 P-C 警示后补一句上述合计及条件，并说明尚缺逐对预测、有效样本分母和无效输出处理。保持原表数值，不重新归一化，也不自行推定缺口全来自解析失败。可以作为同一原文指标问题的补充，无需新增长篇附录。

### R3-02 · P3 · 可补回 BFP 的局部实现效率声明

- **初稿位置**：§3.2 / §5.4，行 97、233；§6 / §8 的性能边界。
- **性质**：次要事实覆盖遗漏；现有“无端到端吞吐数字”结论仍然成立。
- **原文证据**：§3.2 p5 说该 BFP 实现在 **document index construction** 阶段的效率接近传统 concatenate-then-split；A.3 p19 说明在 Megatron 中用 C++ 重实现。
- **建议**：在 BFP 段补“作者称文档索引构建效率接近 concat-then-split，但未给具体计时或吞吐数”。限定到索引构建，不能扩为 GPU 训练吞吐、RL rollout 或端到端成本提升。本项不要求新增实验或更多外部来源。

### R3-03 · P3 · slide 的方向用词宜避免歧义

- **初稿位置**：§5.4，行 250 的“末块合并/向后补齐”。
- **性质**：表述精度，非算法方向已确定写反。
- **原文证据**：A.3.2 p21 的 slide 是重叠滑窗；最后一块与前块合并，或 **extended backward** 以维持目标长度。这里强调借入末块之前已有的上下文。split 则明确保留不足长度的最后残块。
- **建议**：写成“末块与前块合并，或向文档前文延伸以补足长度”；split 可同时加“保留短末块”。这样读者不易把“向后”理解为向文档末尾补未来内容或 padding。保留实现未详述的边界，不扩写伪代码。

## 已独立核对、无需纠正的关键事实

| 核对项 | 原文证据与判断 |
|---|---|
| 模型与教师关系 | §1 p1–2、§3 p3、§4.2.5 p11 支持 Qwen3-Next pretrained base → mid-training → SFT → 四 expert → 蒸馏回 SFT model。§3.1.1–2 的 Qwen3-Coder-480B-A35B-Instruct 用于改写、QA、多轮轨迹；没有证据让它替代最后四 expert。 |
| 中训数量与目标 | §3.1.1 / §3.2：92→370 语言、600B repository tokens、32,768→262,144 context、总量万亿级、NTP/FIM、重复段 mask。600B 不是总训练 token；训练语料截止日不推广到所有 RL PR。 |
| SFT 偏好组合数 | p6 原页是 n 选 2，初稿 `n(n−1)/2` 正确。专门 judge 排序不构成 DPO/Bradley–Terry/RLHF 公式披露。 |
| 两池计数 | Table 10：807,693 instances / 52,960 repos，均值 15.25；Table 11：6,012 raw / 5,456 cleaned / 5,019 used repos、851,898 tasks，851,898/5,019≈169.73。四策略总量及初稿逐来源数与表一致。 |
| 模板多样性 | Figure 5 的 1/2/4/8 模板图读约 48.0/52.0/53.4/53.8；固定数据量与训练配置。A.2 的“21”与 Table 12 实际 20 行冲突确实存在；初稿未补造第 21 项。Table 2 Next 五列平均 92.7，DeepSeek-V3.2 平均 93.7。 |
| RL 惩罚与作弊 | §4.2.4 是终局 trajectory reward、超轮数 trajectory penalty、非法 tool-call 关联 token penalty；没有数值或总 loss。Figure 7 确有 75.1/84.6、图注平均 50→130 turns；75.1 不是最终统一模型 Table 3 成绩，300 turns 也不是已披露训练 cap。人工检查消除作弊不等于全量零残余。 |
| 最终 agentic 结果 | Tables 3–5：Verified 70.6/71.1/71.3，Multilingual 62.8/56.2/64.3，Pro 42.7/38.7，Terminal 2.0 为 34.2/36.2/30.9/25.8。初稿 harness 顺序、主要对照值和 300 turns 的阶段边界正确。 |
| 其他能力与负结果 | Tables 6–9 的初稿数值逐项一致，含 FullStack、BIRD-SQL、EvalPlus 等下降和数学提升。Figure 3 跨 scaffold 弱迁移、Wikipedia-style 虚假 URL、Figure 6 波动均被保留；未把横向模型比较或训练过程曲线写成已隔离的因果收益。 |
| Packing 公式与分母 | A.3 p20–21 的 fragmentation 是文档比例，padding 是 token 槽位比例；PLD 为 `T/(1-p)`，73/(1−0.1755)≈88.54B，对应表中 89B。BFP 比 PLD 少约 18.0%，反向为 PLD 多约 21.9%；初稿对原文“22% fewer”的纠正正确。 |
| Packing 代理指标 | Table 13 为 patch similarity / empty rate，含模型定位与两个 GT 条件，不是 task pass rate。BFP+split AVG 20.17/25.01、drop 20.84/24.34，主实验使用 split。初稿没有把 fragmentation=0 扩大为原始超长轨迹从未切断。 |
| 安全指标与采样 | Tables 14–16 的 Next 数与对照摘录一致；Athena 的 RMS 为 F1、其余 accuracy，PrimeVul 为 greedy；SecCodeBench 53 Java task 的严重度加权 pass@k 未披露具体 k；CWEval 两指标 n=10、T=0.8，不能写成 pass@10。 |
| P-C 方向纠正 | R3 p22 实际印 P-C↓ 并声称低值较好；PrimeVul v2 §IV-B2 定义为一对均正确，且其 Table V 明确 P-C↑。初稿撤回“最好 paired consistency”有充分依据，并恰当地保留 R3 列名/实现真相未知。新增合计疑点见 R3-01。 |
| 资产与复现边界 | 固定卡片确有 non-thinking、262,144、SGLang≥0.5.8/vLLM≥0.15.0、1.0/0.95/40 和示例 65,536；卡片 prose 4 GPU 与 TP=2 示例的矛盾也存在。这些不是生产 RL 配置。未下载权重、未实测吞吐，不能宣称全训练复现。 |
| 项目映射 | 当前文档支持 miles + SGLang + 外部 harness；GRPO n=8、faithful DIS、Qwen3-30B-A3B 是项目候选而非 R3 配方。初稿明确设计层候选、上游复用和需自行实测，没有恢复已删除 command-filter 或自动批准多 expert/OPD。 |

## 审查结论与残余未知

未发现 P0/P1 级正确性错误，也未发现后训练覆盖表漏掉整段原文内容。建议主作者处理 R3-01 的指标一致性补充；R3-02、R3-03 为低优先级的完整性与表达改进。对初稿已有的原文三类实质纠偏——模板 21/20、token 百分比分母、P-C 方向——本次均独立确认。

尚不能从报告恢复的内容仍包括完整 RL/蒸馏 loss、策略与教师更新、每题采样和 group 统计、失败/截断的梯度消费、训练参数和硬件、任务到实际训练消费的完整漏斗、全套评测 split/预算，以及 PrimeVul 的逐对预测和实际分母。不能为了消除未知而拿框架默认值、家族报告或官方部署建议补成生产事实。本审查不是对训练可复现性或本项目学习效果的验收。

## 主作者处理记录

本段留给主作者在修订后逐项记录 R3-01、R3-02、R3-03 的处理位置、采纳情况与残余不确定性；审查者未提前填写已处理或通过。

### 主作者逐项处理（2026-09-07）

已收到独立审查者的最终回报后进行本记录。下列是主作者修订，不冒称审查者重新执行了完整第二轮审查。

| 发现 | 处理状态与正文位置 | 原文证据 / 复核结果 | 残余边界 |
|---|---|---|---|
| R3-01（P2） | 已采纳，笔记 §7.6，并在 §9.3 / §12 留记录 | 对 Table 15 p22 五行重新求和：99.99、100.00、99.99、98.25、99.82；明确 Next 与 GLM 缺口超过舍入误差 | 不猜无效预测类别，不改表值；仍需作者逐对预测、样本分母和解析政策 |
| R3-02（P3） | 已采纳，笔记 §5.4 | 补入 §3.2 p5 的 document index construction 局部效率声明，保留未给计时/吞吐的限定 | 不升级成 GPU 训练、RL rollout 或端到端加速结论 |
| R3-03（P3） | 已采纳，笔记 §5.4 策略表 | 按 A.3.2 p21 将 slide 改为“末块与前块合并或向文档前文延伸以补足长度”；split 加“保留短末块” | 不推断未披露实现或生成伪代码 |

主作者保留审查全文和全部残余未知，不删除发现、不将原论文未披露项伪装为已核事实。原任务范围内的后训练章节、附录与独立审查/修订已完成；仅发布本任务专属文档和必要来源快照，不涉及训练代码或新的训练语义定案。
