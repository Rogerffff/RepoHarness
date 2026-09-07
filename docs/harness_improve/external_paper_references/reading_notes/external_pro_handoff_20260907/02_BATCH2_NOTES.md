# 第二批七份精读笔记全文

导出日期：2026-09-07。使用方式与边界见 [交接说明](00_HANDOFF.md)。各篇正文完整保留；本地链接转为仓库引用文字，页内导航转为文字；需要原图/代码时请访问官方来源。


---

## 文档 1 / 7：R2_nemotron_3_ultra.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/R2_nemotron_3_ultra.md`

# R2 Nemotron 3 Ultra: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning：后训练与项目一精读

Nemotron 3 Ultra（550B 总参数、55B 激活参数）采用两阶段通用 SFT、统一多环境 RLVR、轻量 MOPD warmup、两轮异步多教师 on-policy 蒸馏，最后冻结主干、仅强化 MTP 草稿头。其价值不仅是 SWE：报告完整讨论办公、搜索、终端、工具、安全、聊天、事实性、数学证明和多语言。MOPD 在 agentic 行为上的恢复较强，在 HLE 上只恢复教师差距的 16.9%；多数 agentic MOPD 使用单轮 rollout，而 SWE 教师另有多轮端到端 RL。报告给出 sampled-token 蒸馏公式、部分预算与工程负结果，但没有完整 SWE 环境漏斗、失败样本组统计和 loss 分母，不能据此复现生产训练或推出八卡成本。

导航：来源与覆盖 · 阶段与数据 · 教师与环境 · 目标与训练语义 · 系统与评测 · 边界、项目映射与审查

## 1. 来源、版本与覆盖

- 正式标题如上；署名机构 NVIDIA；封面日期 **2026-06-09**；阅读日期 **2026-09-07**。这是技术报告，没有在封面注明 v1/v2。
- 主资料：原本地 PDF〔仓库引用：`docs/harness_improve/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf`〕。[官方 PDF](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf) 于本次下载后与本地 `cmp` 相同，均 65 页、3,876,804 bytes；未静默换版本。本次固定来源副本〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R2/online_20260907.pdf`〕。PDF 元数据创建/修改时间为 2026-06-09 18:49:09 UTC（与封面日一致），不是另一个发布日期。
- 本文 **p.n 是从 1 起算的 PDF 物理页，也等于报告印刷页 n**；封面无页码，但下一页印刷为 2。文本内部分图形字体含控制字符，按 `\f` 分割会错误地产生超过 65 个片段，不能拿该片段序号作页码。本次按 `pdftotext -f/-l` 物理页分块读；关键公式和图像回原页核对。
- 正文 §1–6、唯一附录 A.1/A.2 和图 1–17、表 1–18 均纳入覆盖；§3 全文与附录精读。作者/参考文献 p.51–63 用于确认来源结构及相关引用身份，不另精读所有被引论文。无网页动态案例需要补开。
- 官方资产入口：[Nemotron 仓库](https://github.com/NVIDIA-NeMo/Nemotron)、[Evaluator 的 Ultra 复现目录](https://github.com/NVIDIA-NeMo/Evaluator/tree/9758d8d5508e0d1bea79cb99ed56d595a1c3acdc/examples/nemotron/nemotron-3-ultra)。实际只核验入口与复现说明，不把当前仓库默认配置当作 6 月报告的训练配置。资产查阅范围见 §9。
- 阅读原文、建立覆盖后，才查旧稿：重定位审核〔仓库引用：`docs/harness_improve/repositioning_design_review.md`〕 §2.3/T3/T4、训练配方矩阵〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 §7.2。旧稿纠错见 §10；未修改旧稿。

| 原文章节及物理页 | 阅读深度及主要图表 | 本笔记位置 |
|---|---|---|
| §1 Introduction，p.1–3 | 全读；图1 的模型、引擎、吞吐口径；发布声明 | §1、§8、§9 |
| §2.1–2.2 Architecture / NVFP4，p.3–5 | 概要；图2–3、表1；保留影响 MTP 与精度的约束 | §2 |
| §2.3.1–2.3.6 Data，p.4–9 | 概要；code refresh、QA、fact-seeking、moral、全部 legal 类别与 mixture，图4；纯预训练不逐数据集展开 | §2 |
| §2.4–2.6 Hyperparameters / LC / Base eval，p.8–11 | 概要；表2；LC 与后训练长度分开 | §2 |
| §2.7 Stability，p.11–14 | 全读相关机制；图5–8 字体失真处回图；两次发散与 routing 相关性 | §2、§10 |
| §3/3.1 SFT，p.15–20 | 精读图9、两阶段参数、所有数据段落与 packing | §3 |
| §3.2 RL，p.20 | 精读全部领域、课程、batch 原措辞 | §3、§5 |
| §3.3.1 MOPD，p.20–22 | 精读图10、式1–3，目视教师箭头及概率符号 | §4、§5 |
| §3.3.2 Teachers，p.22–26 | 所有11种教师逐项读；STEM 表3及全部制数/训练细节 | §4 |
| §3.3.3–3.3.5 Warmup / Results / Limitations，p.27–29 | 精读表4–5及三组负结果 | §6 |
| §3.4 MTP Boosting，p.29–30 | 精读训练/推理不一致、式4、表6；回原页 | §5.3 |
| §3.5 Control，p.31 | 精读 medium-effort 配方和图11 | §3.3 |
| §3.6.1–3.6.3 Infrastructure，p.31–36 | 精读全部优化及 Future Work；图12、表7–9 | §7 |
| §3.7.1–3.7.3 Evaluations，p.36–40 | 精读全评测范围、held-out 协议、证明推理扩展；图13、表10–11 | §8 |
| §4.1–4.6 Quantization，p.41–47 | 全读 PTQ、缓存、部署与负结果；图14、表12–18 | §7.3、§8.3、§9 |
| §5.1–5.2 Inference，p.48–51；§6 Conclusion p.51 | 全读与 rollout 性能相关的全部机制；图15–16 | §7.4 |
| Appendix A.1 Benchmark Details，p.64 | 精读四类具体协议 | §8.2 |
| Appendix A.2 Harness Robustness，p.64–65 | 精读五类任务、六类训练 harness；图17逐项读图 | §8.2 |

## 2. 底座与预训练约束（不归入 RL 成果）

550B/55B 是总参数/每 token 激活参数；108 层、hidden 8192、每 MoE 层 512 专家、top-k=22、latent size 2048、2 个共享权重 MTP 层（p.3–4，表1）。这里的 MoE experts 是模型内部路由单元，后文 specialized teachers 是独立训练的模型，二者不能混称“多专家”。预训练 NVFP4 的部分敏感层保留更高精度，不代表后训练、优化器或全部算子均 FP4。

预训练为 15T 广覆盖 + 5T 高质量，共 20T text tokens；包括新增截至 2025-09-30 的 173B GitHub code tokens、合成选择/开放 QA、事实、道德、法律及多语言数据。QA 使用公开数据 train split 作种子，不使用 held-out test split；这是一项来源策略，不是全面无污染证明。法律 64.6→74.7、fact-seeking SimpleQA 改写为选择题的 40.24→50.16 等消融都在 **Nano/其他 Nemotron 底座** 上，不是 Ultra 后训练增益（p.4–9）。

WSD 峰值 LR 2.5e-4，200B warmup，最后 5T minus-sqrt 衰减到 2.5e-6；经过 checkpoint merge 选择后再做 33B-token LC continued pretraining：1,048,576 context 占 92% iterations，4096 占 8%，每步固定 25,165,824 tokens，长数据 46% + phase2 54%，不混长度于同一步；仅短迭代用 math/code SFT-style 数据，不使用 RULER-style 数据。LC 使用 GB200，CP32/TP8/EP128/PP2；不能将这些配置移作 RL 硬件布局（p.8–9）。Base 的 RULER 1M=76.83（表2），最终模型 94.7（表10）不是只隔离一个训练阶段的消融。

两次预训练发散均需保留：约 8T 的输出层局部梯度累积 FP32→BF16 使很小的 MTP 梯度贡献丢失；回滚并恢复完整 FP32 reduction 后稳定。约 16T 的原因**未确定**，回滚至15T后提前衰减 LR 缓解，最终将 horizon 缩到20T；切回全 BF16 本身没有解决。报告定义 MaxVio=max expert token load / mean expert token load，理论上限 E/k=23.27，20 iterations 共500M tokens作测量；Ultra 跨层 median≈1.2，但最坏层升到≈12，早层残差范数也异常。作者只称 routing skew 与不稳定相关，没有确证因果（p.4–5、11–14，图3/5–8）。预训练 §2.7 把 MTP 总系数0.1写为每块0.05；不要据此自行改写 §3.1 的 SFT per-token auxiliary-loss scaling 0.1。

## 3. 学生准备、全域 SFT 与统一 RLVR

### 3.1 阶段图与数量口径

原图9（p.15）总体为 `Base → General SFT → RLVR → 一次轻量 MOPD warmup → MOPD（两轮）→ MTP Boosting → Ultra`。教师在并行专门路径发展；warmup 是学生的短 SFT，不是 teacher scoring，也不是参数平均。图10与具体教师文字的差异在 §4 明列。

| 阶段 | 报告实际配置 | 数量/目标边界 |
|---|---|---|
| SFT Stage 1 | packed length 294,912；global batch64；204,800 samples；cosine LR峰值1.5e-5、最低1e-6；warmup9,600 samples | 完整对话 packing 后的训练 sample 配置，不能写成204,800原始题；p.15 §3.1 |
| SFT Stage 2 | packed length515,000；追加最长512K数据；batch64；19,200 samples；LR1e-5→2e-6；warmup6,400 samples | 两阶段都保留共享权重 MTP objective、2层、per-token auxiliary scaling0.1；p.15 |
| 统一 RLVR | asynchronous GRPO；global batch8,192；每 sample16 rollouts；生成上限48K→64K | 原文没有在此明定8192是 prompts还是生成样本，不能直接相乘或除16后当确定值；p.20 |
| 学生 MOPD warmup | 教师训练分布数据作很轻量 SFT | 一次；规模、LR、准确混合未给；p.15/27 |
| MOPD 1/2 | 每批1,024 prompts×1 rollout；最长生成192K；异步 rollout→teacher scoring→learner | 不是GRPO16条组；多 rollout未获额外收益；p.20–22 |
| MTP Boosting | 冻结 backbone，仅更新 MTP头；12K steps、batch64、8K sequence | temp1生成学生轨迹；assistant位置 full-distribution KL；p.29–30 |

### 3.2 SFT 全部数据领域

所有下述数量均按原文单位列出，不累加成“去重训练任务总数”，因为题、轨迹、语言翻译和重采样可重叠。

| 领域 | 来源、生成、筛选与行为 | 已知规模及定位 |
|---|---|---|
| Long context | 沿用合成 pipeline，覆盖多文档推理、顺序扫描、合成表查询 | 最长512K；p.15 |
| Reasoning control | GPT-OSS-120B medium-effort 生成数学/STEM/IF响应；另随机截断思考而保留最终答复，对截断样本的 `</think>` mask loss | 数量未给；p.16 |
| Safety | Super的45K英文安全 blend；回应与推理的两阶段生成，使安全反思与最终回应保持一致；Riva Translate4B v1.1逐块译为德/西/法/日/意/中，回译相似度<0.8过滤，各语言删约10–15%，人工抽高低分，再分层平衡 | 最终≈135K：英文≈45K，每译语≈15K；p.16 |
| Search | Wikidata hub做4–8跳随机游走，MiniMax2.1+Tavily解；OpenResearcher用gpt-oss120b、离线15M FineWeb索引与bootstrapped evidence、search/open/find；Ultra只筛商业许可，不重新生成；另 vendor难题需50–100次搜索，MiniMax2.5/GLM5.1用 BrowseComp harness采轨迹 | 原OpenResearcher >97K轨迹，商业许可筛后≈21.7K；vendor数量未给；p.16–17 |
| Terminal | OpenCodeReasoning/OpenMathReasoning/SWE-bench/SWE-Fixer-Train-110K/SWE-rebench/SWE-smith作seed；一部分Nemotron-Cascade数学/代码改写，一部分DeepSeek-V3.2合成；同模型在Harbor Terminus-2实际终端中执行 | ≈370K多轮 conversations，thinking/non-thinking混合；不是370K独立环境；p.17 |
| Conversational tools | 六阶段全合成，含user与environment simulation，类似Super recipe | 未在本文展开六阶段；p.17 |
| SWE issue resolution | MiniMax-M2.5 thinking 与 Qwen3-Coder-480B-A35B-Instruct non-thinking；SWE-Gym/R2E-Gym/SWE-rebench/v2任务；OpenHands/SWE-agent/Mini-SWE-agent/Opencode采样；详细过滤见 §4.2 | 题数/轨迹漏斗未给；p.17 |
| Math/proof | Nemotron-Cascade-2数据：非证明来自Cascade/Math-v2，DeepSeek-V3.2生成带工具、Speciale生成无工具；AoPS Math-Proofs-v1生成proof/verification/refinement | 1.8M工具+1.9M无工具samples；proof数量未给；p.17–18 |
| Science | Nano的synthetic/real/document seeds，physics/chemistry/biology；Data Designer扩格式，LLM judge筛格式与推理；另DeepSeek-V3.2生成Tavily搜索和搜索+Python轨迹 | 数量未给；p.18 |
| Chat | LMArena/WildChat seeds；GLM5多候选、Nemotron-GenRM选当轮最佳；同LLM模拟用户追问、挑战、改述等；前轮可放次优assistant回应 | **只在最终assistant回应训练**，让模型能应对不完美历史；p.18 |
| Competitive code | Codeforces/AtCoder/AIZU/CodeChef；严格去重、难度平衡，GPT-OSS120B+rejection sampling | 1.2M Python、1.0M C++14、1.3M Python tool-calling reasoning traces；p.18 |
| CUDA | DeepSeek-R1/GPT-OSS120B生成PyTorch reference→kernel或自然语言spec→kernel；库/API/BackendBench seeds；编译、数值正确性、runtime checks拒绝无效，在有效候选选最快；内部agent补错误→修复、Nsight日志→优化；另CUDA-X库数据含Thrust/CUB/cuBLAS/cuDNN/cuSPARSE/cuRAND/cuSOLVER | ≈100K samples；不只正确性，也有性能筛选；p.18–19 |
| RTL | ACE-RTL/ScaleRTL，许可检查、去重、过滤、语法验证；DeepSeek-R1/GPT-OSS120B生成spec→RTL，以及缺功能编辑/注bug调试；syntax、benchmark decontamination、human-rubric语义对齐过滤 | ≈1.2M samples；p.19 |
| Multilingual | 平行句语料+英数学/code/science SFT翻译；用DeepSeek-V3-0324整JSON输入→整JSON输出代替逐行，格式筛查、沿Super过滤和轻后编辑；日语MMLU-ProX消融定性改善 | 新印地/日/韩/巴葡；其余复用Super；没给增益数值，不能外推安全数据也换此pipeline；p.19 |

Packing 使用 length-aware best-fit：round-robin交错读各源，仅保留固定数量开放序列；为每个完整 conversation找剩余空间最贴合者，小余量即退休；**不截断、不切分对话**，同pack禁止重复prompt，最终shuffle，避免每源聚集。减少hallucination和改善稳定性是作者解释，未提供独立 packing消融（p.19–20）。其“完整对话”规则与预先构造截断思考的 control样本不冲突。

### 3.3 统一 RLVR 与推理控制

RLVR 覆盖 terminal、office/productivity、SWE、search、一般tool-calling、math/code/STEM、safety/chat/IF、long-context QA、inductive/transductive reasoning、structured output、usability（p.20）。奖励并非所有域都是代码二元验证；教师部分也有LLM judge/RLHF。作者先刷新数据、做reward profiling，课程/mixture采用Nano报告的Gaussian approach，异步GRPO与稳定优化沿Super；本文没有展开Gaussian参数、GRPO公式和所有环境奖励，不能移植外篇数字为Ultra事实。

三种推理模式为 off、regular、medium；后两者可叠加推理预算控制。medium由SFT引入、RLVR优化；约2.5%的RLVR prompts为medium，覆盖math/STEM/code，对其reward作长度调整，但系数/函数没给。图11以Qwen3.5-397B各任务token为参考、平均AA Intelligence Index V4十项，作者称medium平均少用约2.5倍tokens、accuracy约降7%；这里不是“每题固定省60%”，也未明确7%为相对比例还是百分点（p.31）。

## 4. 教师关系、SWE 环境与其他专业训练

### 4.1 两轮教师怎样合并

图10（p.21）第一轮列出 STEM、chat、instruction-following，以及 agentic 分支的 terminal、conversational tool、SWE、search、office、usability、agentic safety，共10类；全文另有competitive coding教师，因此“more than ten”不等于每轮恰好11台同时在线。RLVR学生还充当未被专项教师覆盖领域的self-teacher；不能把它解释成每个token临时自举的自教师算法。

第二轮图中 refreshed/new 为 coding、chat2、conversational-tool2、SWE2、office2；复用 STEM、IF、terminal、search、safety。具体箭头中 coding由STEM教师引出，其他四个从Ultra MOPD1引出。caption与§3.3的概述说新教师从更新学生初始化，但 **competitive coding正文明确从General Reasoning Teacher继续RL**（p.26）；应优先保留这一分支事实，不能一律改成MOPD1。图未在第二轮复用区列usability，未解释其独立信号是否/如何继续。

图10把office放在agentic分支，但office段落明确从完成general SFT的Ultra checkpoint初始化（p.23）。因此图是概览，不能用它覆盖具体教师段落。专门teacher模型与外部合成数据teacher也要区分：例如DeepSeek-V4-Pro为STEM数据生成者，不等同MOPD时直接评分的Ultra STEM teacher。

### 4.2 SWE：SFT过滤和RL奖励必须分开

SFT 的轨迹分析器逐条 include/exclude，检查有效提交、禁用git操作（push/pull/fetch/clone/cherry-pick/reflog/fsck/remote/ls-remote）、反复edit-test或自我回滚、只探索很少编辑、频繁坏tool-call、最终patch残留print/pdb/breakpoint，以及编辑后未测试。报告没有给每规则阈值、误杀率或消融，不能把这些启发式当作普适好轨迹定义（p.17）。

SWE teacher三阶段为 **Ultra base → agentic SFT → 单步agentic环境PivotRL → 多轮端到端SWE RL**。最后在repo里多轮tool/bash产出patch，verifier运行hidden tests，给二元reward用于GRPO；生成上限192K、最多200 agent turns（p.22）。

| 层次 | 已披露 | 尚不能推出 |
|---|---|---|
| 环境/题来源 | 通用SWE SFT列四种公开数据源 | 不能断言teacher RL题池等于SFT来源；无原始repo→可构建→有效评分→最终RL消费数量 |
| 未完成轨迹 | 达到最大agent turns，或agent/eval timeout，mask trajectory loss | 是否仍入group reward mean/std、是否补采、是否整组丢弃；没有单独规定“token上限”必然同处理 |
| 坏格式 | malformed reasoning/tool call 的 offending tokens 给负advantage | penalty值、识别器、与终局优势叠加方式、是否修改provenance mask |
| 泄漏防线 | 容器git历史物理重写为base时刻fresh clone，future objects不可低层恢复；runtime command filter拦remote git与GitHub web/raw/Pages HTTP下载 | 不等于完整网络隔离或经对抗证明阻断一切下载；隐藏测试投放时点、gold/no-op/alternate-solution验证、fresh grader隔离未给 |
| 成本/稳定性 | GB200生产集群与全局故障归因见§7 | 没有SWE专项镜像数、CPU-hour、API花费、flakiness检查或超时秒数 |

### 4.3 其余十种教师（完整覆盖）

| 教师 | 初始化、数据与训练事实 | 证据及限定 |
|---|---|---|
| Office/workplace | general-SFT Ultra初始化；AfterQuery任务含reference files、分析与最终工件，强模型产生多条完整轨迹；先在student作light SFT传workflow priors，再在MOPD阶段用这些轨迹的pivots进行pivot RL、把SFT-trained teacher蒸给student | p.22–23；原文称“after this MOPD warmup”再pivot，未给teacher单独SFT所有超参或strong model名称；输出可能是sheet/doc/report/music/audio，但不证明Ultra具有音视频输入模态 |
| Search | 从Ultra checkpoint出发，SFT加入context-management轨迹；有discard-all和summary compression，以前者为主，超预算移去旧搜索观察以延长有效搜索 | p.23；不是原始context窗口被扩展，未披露compaction token训练mask |
| Terminal-use | 专家轨迹任务专门挑战长timeout，可运行至一小时；PivotRL迭代，饱和时重新profiling | p.23；一小时是该任务设置，非所有域wall-clock上限 |
| Conversational tool-use | 沿Super数据/配方，PivotRL；新增需要顺序、依赖多步动作任务抑制过早终止 | p.23；没有teacher专项batch或训练步数 |
| Usability | 五schema JSON/YAML/XML/TOML/CSV；六类任务：直接抽取、翻译、相关/无关多步、仅schema、纠错；再加嵌套document extraction+distractors、inline citation、自由markdown格式 | p.23；Data Designer+gpt-oss120b制seed，NeMo-Gym实现环境；未给独立teacher优化公式 |
| Agentic safety | 企业正常read任务的tool response植入恶意指令，目标是不同的敏感write工具；unauthorized action/data modification/DoS/exfiltration；Super attacker反复改写攻击Nano defender，仅留成功攻击 | p.24；确定性verifier以“未用目标参数调用目标工具”判抗攻击，不能单凭这一条件保证正常任务完成 |
| Chat | 基于Ultra SFT训练Ultra GenRM：给context与两候选，按用户principles或一般helpfulness判断；RLVR教各回应分数+ranking三元组，多principle各组三元组后总判断；RLHF只用overall scores | p.24；chat policy多轮RLHF，每轮内部chat评测→弱点定向数据；无需每轮重训GenRM。大RM缓解而未消除reward hacking |
| IF/factuality | §3.2 RL checkpoint上专项RLVR，严格格式、中途指令改变、多轮一致性；程序/LLM judge；动态校准abstention reward，混RLHF防行为崩塌与环境过拟合 | p.24–25；abstention强度公式未给，非“只追正确率” |
| STEM/general reasoning | 从student再SFT+RL，覆盖数学、code、natural science、humanities、sociology与工具；详细数据如下 | p.25–26；名称STEM不意味着只训STEM |
| Competitive coding | 从General Reasoning Teacher追加coding RL，Cascade来源与强tests；删掉teacher在8/8 rollout全对的prompt，剩3.5K | p.26；LiveCodeBench v6从90.0增至92.4（+2.4分），8次是难度筛选采样，不能当训练group数 |

STEM教师数据与优化（p.25–26）：

- Science reasoning从Nano science、chemistry、Multi-subject-RLVR、内部proprietary数据删最易题；DeepSeek-V4-Pro每题4条，难题16条；gpt-oss120b判正确。正确解长度中位数>16K的部分题再采8条。保留3,000题作RL evaluation，筛选pass rate0.25–0.80且正确解中位长<64K；这是经过难度筛选的内部评测，非无条件随机测试。
- Coding取十年国际竞赛≈14K题加OpenCodeReasoning难题4K，每题DeepSeek-V4生10条，明确删除编译失败；这一段未声称每条都经语义全测试通过。
- Math保留95,164独立题，V4-Pro high生成COT/TIR，gpt-oss120b对reference answer判对才入SFT：285,516 COT +259,915 TIR=545,431 examples。
- Proof取AoPS5,751题，V4-Pro max生成proof/verification/meta-verification；保留满足结构、未撞context上限的82,737 samples。不能将上述“结构验证”升级成全部证明由人验证正确。
- SFT blend按**generated token**配额而非题数：40B=23.5B science(58.75%)+9.45B math/proof(23.63%)+4.05B code(10.13%)+3B general(7.50%)；比例四舍五入合计100.01%。超配额随机downsample，不足upsample；pack294,912，沿§3.1 setup一epoch。
- 此后RL重点放non-STEM humanities/sociology；每批128 prompts、global batch2048，其余大体沿§3.2。作者观察其他域也提高；未隔离数据、SFT和RL各项贡献。表3教师HLE32.1（student25.6）、GPQA88.5（85.0）、MMLU-Pro87.7（85.7）、LCB90.0（87.4）、IMO92.5（84.5）、Apex85.4（68.9）；表注把1分内差别视为噪声，不是提供了置信区间。

## 5. 优化目标、概率身份与 mask

### 5.1 MOPD 的 sampled-token 目标

p.21 式(1)以领域i的数据集D_i、teacher π_Ti、学生π_θ和domain sampling/loss weight λ_i定义：

\[
J_{MOPD}(\theta)=\sum_i\lambda_i\,\mathbb E_{q\sim D_i,y\sim\pi_\theta}[\sum_{t=1}^{H}(\log\pi_{T_i}(y_t|s_t)-\log\pi_\theta(y_t|s_t))],\quad s_t=(q,y_{<t}).
\]

这是最大化负 reverse KL，对应每个学生访问prefix上的 `KL(student || teacher)`。正文把期望放在student自己生成轨迹上；不能称为teacher离线轨迹cross entropy。这里只使用**学生实际采到token**的teacher logprob，不是top-k/full-vocab分布匹配。

异步时区分三种policy：behavior产生旧轨迹；proximal是trust-region中心；current是learner正优化的参数。令各自对同一token的logprob为ℓ_b、ℓ_p、ℓ_T，式(2)–(3)（p.21–22）为：

\[
\hat A_t=\operatorname{sg}[\ell^{T_i}_t-\ell^{prox}_t],\qquad
c_t=\operatorname{sg}[\pi_{prox}(y_t|s_t)/\pi_{behav}(y_t|s_t)],\qquad
r_t(\theta)=\pi_\theta(y_t|s_t)/\pi_{prox}(y_t|s_t),
\]
\[
J_{async}=\mathbb E_{q\sim D_i,y\sim\pi_{behav}}[\sum_{t=1}^{H}m_t c_t\min(r_t\hat A_t,\operatorname{clip}(r_t,1-\epsilon,1+\epsilon)\hat A_t)].
\]

`sg`为stop-gradient。c补偿behavior→proximal偏差，**PPO clip作用于r，即proximal→current**；不能写成直接clip current/behavior。m_t原文仅称IcePop token-level mask，未在Ultra文中给判定公式/阈值。式(3)本身省略式(1)外层领域求和；实际混合权重也未给。

报告的数学表达是token sum再trajectory expectation，**没有1/H，也没有披露实际训练实现的token/trajectory/batch归一化分母**。因此可陈述印刷目标，但不能断言生产代码按等token或等trajectory加权；group标准化不是这份MOPD advantage定义的组成。teacher选配按任务领域，未披露多teacher同题组合权重、tokenizer对齐、teacher frozen周期、特权上下文、打分精度或API logprob方式。明确的两轮teacher刷新不等于训练中每步自更新teacher。

### 5.2 不同 loss mask 不能合并

| 位置 | 明确处理 | 未披露边界 |
|---|---|---|
| 通用SFT control，p.16 | 随机预算截断样本的 `</think>` 不入SFT loss | 其他role mask总表 |
| Chat SFT，p.18 | 仅最终assistant response入训练 | 不能推至全部SFT数据 |
| SWE教师RL，p.22 | 未完成轨迹loss mask；坏reasoning/tool token负优势 | 两者是否在同一轨迹重叠时的优先级，group统计/补采 |
| MOPD，p.22 式3 | IcePop m_t | assistant/thinking/tool observation、context reset及pivot前缀的精确mask；未完成SWE规则能否沿用 |
| MTP boosting，p.30 式4 | assistant位置A | 明确分母N_mtp×|A|，不能回填给RLVR/MOPD |

统一RLVR的KL、entropy、optimizer、LR、steps、clipping、每prompt/trajectory加权、advantage baseline/std，以及跨轮token版本记录均未在§3.2/3.6展开。只知道引用Super的稳定优化不能证明routing replay或top-p replay已用于Ultra。

### 5.3 MTP boosting：另一个方向的蒸馏

MTP是主干内部草稿头。teacher forcing训练把前一步MTP整条隐状态移位喂给下一步；实际autoregressive drafting则混合已存在backbone历史与新增MTP状态，深draft更偏离训练分布（p.29）。Boosting从MOPD checkpoint出发，冻结backbone、只训共享MTP头；第k步输入隐状态从先前1…k−1步状态中采样，模拟部署噪声。它不是MOPD的domain teacher合并。

seed来自Nemotron-Post-Training-Dataset-v2与Nemotron-RL-Super-Training-Blends，MOPD学生temp1 rollout；训练12K步、global batch64、sequence cap8K。assistant位置集合A、N_mtp=7、蒸馏temperature T=2，式(4)（p.30）：

\[
L_{MTP}=\frac{T^2}{N_{mtp}|A|}\sum_{k=1}^{N_{mtp}}\sum_{t\in A}
D_{KL}\big(\operatorname{softmax}(z_{t+k}/T)\;||\;\operatorname{softmax}(z^{mtp_k}_{t+k}/T)\big).
\]

这是 **forward KL(backbone || MTP)**、全词表logits匹配，关闭对gold token的普通CE项；与MOPD的reverse KL sampled-token截然不同。冻结主干避免参数更新使主干质量回退，但不能据此忽略部署量化、cache和采样实现的影响。

表6 SPEED-Bench qualitative split，draft length7：greedy平均acceptance length 4.387→4.584，temp1 4.165→4.331；coding5.152→5.452（greedy），summarization4.413→4.552。caption称相对speculative-decoding speedup改善3.15%–5.82%，其数值与这些acceptance length比值一致；不要把它当真实全训练wall-clock提升。与Qwen3.5/DeepSeekV4-Flash的表比较也不是同主干消融。

## 6. MOPD 效果、消融及失败经验

表4（p.27）`Warmup`列指**经过warmup后再MOPD的结果**，不是仅light SFT完成时的分数：GDPVal student28.9 / warmup+MOPD46.7 / no-warmup MOPD35.3 / teacher49.5；BrowseComp31.0/44.4/33.0/51.0；HLE25.6/26.7/26.3/32.1。说明agentic域warmup效果较大，但并未给equal-total-compute、重复seed或误差。

| 表5 benchmark（p.27） | SFT | RLVR | MOPD1 | MOPD2 | Teacher | Recovery |
|---|---:|---:|---:|---:|---:|---:|
| Terminal Bench **2.0** |34.5|44.5|50.8|54.0|50.0|172.7%|
| GDPVal |23.2|28.9|46.7|46.7|49.5|86.4%|
| SWE-Bench Verified |63.5|65.8|70.1|71.7|72.5|88.1%|
| TauBench Telecom |55.7|82.7|91.2|92.9|94.0|90.3%|
| BrowseComp |14.3|31.0|41.0|44.4|51.0|67.0%|
| LiveCodeBench v6 |85.5|87.4|90.0|89.0|92.4|32.0%|
| IMOAnswerBench no tools |85.1|84.5|88.1|88.6|92.5|51.3%|
| HLE no tools |19.7|25.6|25.9|26.7|32.1|16.9%|
| OmniScience non-hallucination |4.8|46.3|77.9|78.7|87.0|79.6%|
| IFBench prompt loose |62.3|78.4|80.0|81.7|83.0|71.7%|
| Multi-Challenge |53.3|60.3|62.8|63.8|63.3|116.7%|

Recovery=(MOPD2−RLVR)/(Teacher−RLVR)，是弥合teacher gap的比例，不是相对准确率增益，可超过100%。MOPD2相对RLVR全表提高，但LCB从MOPD1的90降为89，GDPVal不再提高，RLVR的IMO又低于SFT，不能写“每阶段各领域单调提升”。SWE表5的71.7与最终表10的70.7不同，报告未给足解释；Terminal表5是2.0而最终是2.1，不能拼同一曲线。

作者解释（p.28）：MOPD更易迁移学生本来能采到的工具选择、执行与abstention等token偏好；STEM teacher额外大规模离线数据学到的稀有推理路径，学生很少采到，on-policy评分不足以移植。HLE warmup效果小与此解释相符，但不是对“路径支持集”机制的直接因果证明。Terminal超过teacher可能来自office数据科学迁移，作者亦用potential表达。

三类负结果与未做实验（p.28–29）：

1. Top-k或full-vocab logit matching未改善，部分Terminal等agentic benchmark持续弱于sampled-token；作者猜测student的低teacher-support前缀造成噪声/过强局部约束。不可推广为所有OPD都不应full-vocab。
2. 共享统一SFT后再分化teacher，或先用specialist产SFT数据再训student，两方案因时间/资源限制**未系统实验**，不是验证失败。
3. 端到端agentic与单轮reasoning混MOPD时rollout时长差异造成明显低效，实践中**多数agentic采用类似PivotRL的单轮rollout**。端到端能否进一步提高仍开放；不是已经解决了任意长程异步训练。

## 7. Rollout、可靠性、量化与推理系统

### 7.1 异步与可归因的速度

§3.6.1（p.31–32）明确 **one-step off-policy asynchronous**：rollout与policy update重叠，step受较慢一方约束，通常是长尾generation。MOPD还将teacher scoring完全pipeline；未披露每token weight version、consume-time阈值、backpressure、取消、重试或跨更新partial-resume协议。不能用“asynchronous”推成任意陈旧度FIFO。

图12 sweep k=0/3/5/7 MTP，k=5时**平均每步rollout-generation time**快1.46倍；长尾benefit更大，作者解释长轨迹token更多、批尾concurrency低，更适合speculative decode。这个1.46不是总RL wall-clock、不是SWE成功任务/GPU-hour，也不是boosting前后消融。

### 7.2 生产故障与工程优化

GB200、Slurm，CPU共置执行sandbox；NeMo-RL不同roles含training/vLLM-generation/gym/judge（p.32–36）。表7的56% generation engine failure/timeout、36% sandbox/tool、8% other，是**观察到的RL软件故障内部构成**，不是所有请求的故障率；无样本总数、观察周期或训练有效率。

| 机制 | 结果与实施含义 | 原文位置/不能外推处 |
|---|---|---|
| Slurm launch / Ray GCS | 多次srun改一次multi-node srun，controller RPC O(n)→O(1)，启动>30min→10min；3K+GPU actor注册拥塞原25–49min；短期actor转task、node池化，注册减40%；Ray2.55含修复 | p.33；启动延迟不是训练吞吐 |
| NVLink域rank placement | 按ClusterUUID/domain、topology rank与GPU排序，EP组留同NVL72 rack（72GPU/18nodes）；不完整segment舍弃；Megatron相信external GPU mapping | p.33–34；报告GB200端到端吞吐+20%，不是“模型routing replay” |
| NUMA binding | policy/vLLM绑GPU本地CPU socket，优化offload、pinned memory、tokenization | p.34；报告GB200端到端+10%，与上项不能相加成必然30% |
| Async checkpoint | 60s exposed blocking→NVRx 6–8s→overlap NCCL/D2H、持久worker、后台finalization、缓存save plan和分片optimizer后<1s | p.34；写盘总时间/恢复完整性不是<1s |
| JIT cache | shared持久tar、startup本地seed、训练只写本地、FlashInfer cubin烘进镜像 | p.34–35 表9；所谓38.8→0.4min有算术疑点见下 |
| vLLM init可靠性 | 统一kernel库ABI、向spawn子进程转发env、临时禁受影响multi-node NVLink memory registration；设备/TP通信health checks、RPC timeout、有界清理 | p.35–36；表8多节点启动25→9.5min |
| Container/storage | ≈44GB squashfs并发读致错误/12+min长尾；Enroot本地cache；仅一个sidecar归档写回，避免全节点I/O storm | p.36；表8正常2–3min→warm≈0s，不含所有冷节点 |

表9列28.0+5.5+2.0+2.5+0.4=**38.4**，总栏却写38.8，正文又说约49min cold init中38.8由JIT主导；原样保留其38.8→0.4（作者称99%减少），不擅改组件或拿作精准总账（p.34–35）。

Future Work（p.36）包括fail-fast fault isolation、组件独立重启、sandbox/tool disaggregation，以及in-flight rollout/KV/conversation细粒度checkpoint与snapshot replay；这些写在未来工作，不能列成已完成训练能力。

### 7.3 PTQ 与缓存：影响部署，但不是 RL 方法

最终5.03 BPE mixed recipe：routed experts NVFP4，shared expert/Mamba mixer linears FP8 per-tensor，embedding/output/MTP/attention/latent projections/conv1d BF16，KV FP8，SSM cache FP16+stochastic rounding（p.41–46，表12）。BPE是不同recipe的汇总轴，不是单一连续旋钮。

固定中间checkpoint的BPE sweep4.85–7.19，AA-LCR62.25→64.69（4.85→5.03）后平台；作者将其归到targeted mixed FP8，而非“多用bit都变好”；CritPt接近地板，Omniscience non-hallucination低BPE略好被作者视为噪声（表13）。重复数SciCode16、GPQA32、CritPt8、Omni20、IF8、AA-LCR16，指标均avg pass@1而非pass@k。

表14换FP4 weight scales：5.03时max/MSE/Four-Over-Six accuracy recovery中位数96.78/98.40/98.50%，但4.85时Four-Over-Six跌到84.71%；量化误差MSE更低不保证下游更好。最终4/6 per-block weight grid、global scale1.75倍、M=4的block scale较M=6大1.5倍；activation仍max。范围是6个AA benchmark和中间checkpoint，不是SWE收益（p.42–43）。

SSM cache在Ultra短于约64K时可大于FP8 KV；它的状态是固定大小但每token覆盖更新，舍入误差累积。表16的8-bit cache与CC=8 checkpoint/replay实验在 **Nemotron 3 Super NVFP4 emulated quantization** 上，不是Ultra已发布INT8缓存。例：FP8 RTN无checkpoint accuracy drop4.68%、verbosity+25.17%，CC8后0.46%/+3.69%；INT8 SR较稳。当前Ultra发布仍FP16 SR；optimized8bit kernels尚开发（p.44–46）。

同一NVFP4权重供Blackwell原生W4A4和Hopper W4A16。8×H100 TP8共640GiB HBM时，FP8权重≈540GiB只余约10GiB/GPU，W4≈330GiB余约40GiB/GPU，可容更大batch/MTP；因此该工作点W4A16 Pareto优于或等于W8A8。直接W4→FP8会饱和而严重降准，保准需BF16中转且多cast，未发布W4A8（p.46）。这不是Hopper所有模型量化格式的通用排名。

### 7.4 推理工作点与 routing 的真实含义

图1（p.2）GB200 NVFP4、max-throughput、output tokens/s/GPU，Ultra用TRT-LLM，其他用vLLM，可用时比较有/无spec decode取最好。8K输入/64K输出相对GLM5.1=5.9×、KimiK2.6≈4.8×、Qwen3.5≈1.6×；引擎和模型均变，不是算法受控消融。§5.1又称图15两工作负载禁用spec decode，而图15 caption说measurement methodology匹配图1；保留这一描述差异，不断言所有柱子均同spec设置。

50K/2K prefill-heavy时图15以GLM=1，Ultra3.9而Qwen4.6，Ultra落后；active params55B/17B≈3.2决定prefill计算，large-batch decode更受total weights550B/397B≈1.39及Mamba状态成本影响（作者解释，p.48–49）。图16单GB200 node、TP4、10K/16K、BS1，draft length6峰值2.89×，与RLVR k5的1.46×不同实验。

§5.2（p.49–51）小batch常宽TP减weight I/O，大batch常宽EP减collective；least-loaded **request routing**平衡DP rank token，hot expert replication作EPLB。不是轨迹捕获的MoE routing replay。混合Mamba需每draft步snapshot SSM才能rollback，也可较粗粒度做prefix reuse；prefill/decode分离同时转KV与SSM，作者称已上游接入vLLM，prefill-heavy端到端约+10%。真正all-to-all替代AllGather/ReduceScatter，FlashInfer NVLinkOneSided在GB200约+5%，原all-to-all占15–20%runtime；DWDP被列为另一思路，未给Ultra采用结果。另有MoE内部token chunking解决wide-EP资源上限、load-time weight padding处理TP/量化/kernel alignment。均未据本文查源码验证对应patch。

## 8. 评测协议、完整范围与泛化限制

### 8.1 主评测与训练中间结果

§3.7（p.36–40）用Evaluator SDK，主要NeMo Gym/Skills/Harbor（AWS ECS sandbox）及Multi-Challenge专用容器；作者称模型之间agentic CPU/timeout、input、prompt、repeats、metric相同，但temperature/top_p/max tokens按各model card，**不等于所有模型推理token预算相同**。报告未在PDF列全suite每项repeat和harness版本。

表10六基线：MiniMax2.7、GLM5.1、KimiK2.6、Qwen3.5、DeepSeekV4-Pro/Flash。Ultra结果覆盖：

| 范围 | Ultra主要结果（表10，p.38） | 解释边界 |
|---|---|---|
| Agentic | TB2.1 56.4、GDPVal46.7、SWE Verified70.7/Multilingual67.7、ProfBench56.0、PinchBench90.0、BrowseComp44.4 | 不是每项最优；SWE/TB中间表差异见§6 |
| Conversational tools | TauV3 Airline81.5/Retail86.4/Telecom92.9/Banking22.6，四域平均70.9 | 不能只引Telecom代表全域 |
| Finance | FAB1.1无web60.1、有web53.7 | 工具增加不自动提升；仅其validation子集 |
| Coding/math | IOI2025 570/600；LCBv6 89.0；IMO无/有工具88.6/92.3；Apex74.9/84.8 | IOI分数非准确率570%；数学tools是Python |
| Science/knowledge | GPQA87.0、SciCode subtask44.6、HLE无/有工具26.7/37.4、CritPt无工具3.1、MMLU-Pro86.8 | HLE有工具条件与无工具不同 |
| Reliability/IF/chat | OmniScience accuracy24.1、non-hallucination78.7；IFBench prompt loose81.7；Multi-Challenge63.8 | 非幻觉高不代表知识准确率高；abstention作用需分看 |
| Long context | AA-LCR65.4、RULER1M94.7、LongBenchv2≤1M61.9 | retrieval与复杂长文推理不可互代 |
| Multilingual | MMLU-ProX十语平均83.0；WMT24++ en→xx83.7 | 前者en/de/fr/es/it/ja/zh/hi/pt/ko；不同任务指标勿混平均 |

**ProfBench与PinchBench**仅final model完成后评一次，不用于监控/checkpoint selection/开发决策，是作者明确的held-out协议（p.39）；不意味着base预训练污染已排除。“只评一次”是开发流程一次final evaluation，不否定ProfBench内部16次重复。

### 8.2 附录全部协议和图17

- **TauBenchV3**：所有域user simulator增防过早终止prompt；banking用terminal_use搜索knowledge base；DeepSeekV4用max reasoning，用户模拟器GPT5.2 low；8 trials平均（p.64 A.1）。
- **ProfBench Search**：Finance MBA、Consulting MBA、Chemistry/Physics PhD，专业rubric；search+browse，context256K、无context management，16次平均（p.64）。
- **BrowseComp**：自定义Tavily search/browse+terminal；检索全文存每任务磁盘，仅元数据/snippets进入context，shell选择读，context reset后磁盘证据仍保留（p.64）；不要套成所有teacher共用同一compaction策略。
- **FAB1.1**：正式私有test337题未用；本次200题=公开validation50+私有许可validation150。无web有EDGAR/HTML parser/retrieval/submit四工具，有web加Tavily Google search。GPT5.2对expert答案judge，三次评判取mode（p.64）；是validation benchmark结果。
- **训练harness覆盖**：五vertical为zero-to-one terminal/SWE、existing-repo bugfix、office/productivity、general/multi-domain knowledge、search；每类至少用Stirrup/OpenHands/OpenCode/Terminus/Droid/custom internal中的两种，不是每题都跑六种（p.64–65 A.2）。

图17只有图像而无可抽取数字，已逐项看图。Ultra一行如下（p.65）：

| harness | SWE-bench Verified | Terminal-Bench2.1 |
|---|---:|---:|
| Mini SWE Agent2.3.0 / Terminus2.0.0（分别两列） |65.0|55.1|
| OpenCode1.14.33 |67.3|46.7|
| Pi v0.72.1 |70.4|52.1|
| Claude2.1.126 |60.3|47.2|
| Hermes v2026.4.30 |69.9|52.8|
| OpenHands1.17.0 |70.3|52.6|
| Codex（SWE0.128/0.135，Terminal0.128.0，按图标签） |21.1|35.5|
| Average |60.6|48.9|

图中GLM5.1两平均73.8/58.9，Kimi2.6为71.6/58.3。**读者判断**：这支持评测harness敏感性，而不支持“训练多个harness已普遍鲁棒”或“增加第二harness造成某分数增益”；图无单harness训练控制组，Codex退化原因未交代。图17的Terminus55.1和主表56.4亦不同；不自行选高分或猜是精度差。

### 8.3 数学 test-time scaling、量化评测

证明任务用generate→verify→refine高计算搜索，起始每题128 proof attempts、512K context，其余沿被引方法；图13把轮数作为compute proxy，不是精确FLOPs。IMO-ProofBench Advanced累计77→125→153→173/210，最终82.3%；IMO2025 35/42=83.3%，Putnam2025 116/120=96.7%，USAMO2026 41/42=97.6%。前三human expert graders，USAMO沿Dekoninck方法；均是评分点分母，不是173道题或pass@128，不能写成单次模型数学能力（p.39–40表11/图13）。

表17（p.47）W4A16/W4A4/BF16五项对照中HLE26.92→25.12/25.67，且quantized completion更长，不是无损；表18最终BF16与NVFP4分别用vLLM0.17.1/0.22.0，TB56.4→53.9、SWE70.7→69.5、GDP46.7→47.9、Browse44.4→41.4、RULER94.7→94.0。模型精度和引擎同时变，不能把每分差全归到量化。

## 9. 资源、资产与复现程度

成本须按阶段分开：本报告未给完整SFT/RLVR/各teacher/MOPD的GPU-hour、总GPU数/天数、CPU环境构建、teacher/API、评测或失败重启总账。3K+GPU是GCS观察规模，1K+GPU是cold-init测量规模，GB200是生产硬件，均不能自动当整段训练恒定配置；也不能以激活55B估八卡可复现。

唯一定量PTQ资源表15（p.44）：HF单node4×B300+CPU offload，model load40min、load+calibration85min、export42min、total约2h；Megatron16×B300、EP=DP16，load<2min、load+calibration9min、export33min、total表写45min，正文写42min。9+33=42，但不要擅自抹去45；两路线卡数不同，墙钟更快不等于GPU-hour更低。未验证CPU/IO成本或执行命令。

| 开放对象 | 本次核验范围 | 仍缺什么 |
|---|---|---|
| [Base BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-Base-BF16)、[posttrained BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16)、[NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4)、[GenRM](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-GenRM) | p.2的发布声明与PDF超链接；2026-09-07实际查询四模型HF metadata，均public、non-gated；各模型revision及访问状态〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R2/model_metadata_20260907.json`〕 | 未下载权重、未验完整tensor/许可证条款（metadata license标签为other）；发布模型不等于十余teacher全部checkpoint公开 |
| [Posttraining-v3 collection](https://huggingface.co/collections/nvidia/nemotron-post-training-v3) | p.3入口；原文仍使用proprietary/vendor数据和商业许可筛选 | 不证明所有SFT/RL/pivot/hidden tests可取得，未批量下载数据 |
| Nemotron recipe repo | 2026-09-07入口可达，HEAD `907d408c67cb70e9f1ed28fb67702e7bd36e3239` | 本次未追训练代码；不能以main框架默认值补本文未给配置 |
| Evaluator Ultra recipe | HEAD `9758d8d5508e0d1bea79cb99ed56d595a1c3acdc`；读 `examples/nemotron/nemotron-3-ultra/reproducibility.md`，[固定远端](https://github.com/NVIDIA-NeMo/Evaluator/blob/9758d8d5508e0d1bea79cb99ed56d595a1c3acdc/examples/nemotron/nemotron-3-ultra/reproducibility.md)、读取快照〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R2/evaluator_reproducibility_20260907.txt`〕 | 当前说明分v0.2 instruct/Gym与v0.3 native SWE/terminal；不是六月所有评测配置的冻结证明 |

当前Evaluator说明还同时写Tau2/TauBenchV3 recipe与“TauBench3未onboarded”，terminal标Hard/2.0，而PDF主表为2.1；default instruct max_new_tokens262144、temperature1、top_p0.95是**后续入口说明**，不能移作Ultra SWE训练192K的解释或补全6月PDF评测预算。仅核入口未运行复现实验。

## 10. 证据边界、原文冲突与旧稿纠错

| 未回答项 | 已查范围 | 正确使用边界 |
|---|---|---|
| SWE任务/环境漏斗、测试资格、数据cutoff与train/dev/test去重 | §3.1.1、§3.2、§3.3.2、附录A | 公开来源名单不能替代teacher实际RL题池；173B code cutoff属预训练 |
| Failure/timeout：reward、group统计、gradient、补采四件事 | §3.3.1–2、§3.6 | 只确证SWE未完成loss mask，未确证其他三项 |
| RLVR8192单位、loss实际分母、SWE group/steps/LR | §3.1–3.3/3.6；MOPD式1–3 | STEM128×16=2048可提示习惯，但不能解决§3.2原措辞歧义 |
| Teacher概率/支持集、IcePop阈值、role/pivot/context-reset mask | §3.3.1–5 | 不从Super、IcePop原论文或NeMo defaults补Ultra训练事实 |
| 行为版本发布、陈旧度阈值、routing/top-p replay | §3.2/3.3/3.6与全文检索 | one-step async不等于完整版本协议；routing失衡/硬件placement/EPLB与routing replay分开 |
| 成本/复现资产、实验重复与因果归因 | §3–5及A、公开recipe入口 | 局部优化/表格成功率不证明端到端学习成本或单组件因果 |

原文差异已贴相应数字：office/coding teacher图文关系（§4.1）；8192单位（§3.1）；表5与最终SWE及TB版本（§6）；JIT组件总和（§7.2）；图1/15的spec-decode说明（§7.4）；PTQ42/45min（§9）。不把这些小差异夸成整篇不可信，也不默默修成一致。

旧稿需更正的内容：

1. **《重定位审核》§2.3第10项/T3将MoE routing replay与top-p mask replay归到Ultra§3.6，未获本版原文支持。** §3.6实际讨论MTP、NeMo-RL拓扑、NUMA、Ray/JIT/checkpoint等；全文只在MOPD式3明确IcePop mask。MOPD需要teacher sampled-token logprob则仍有式2直接证据。不能由“训练继承Super稳定优化”确认具体replay机制。
2. **《配方矩阵》§7.2称坏token负advantage“不修改provenance loss mask”，后半句原文未披露。** 保留负优势事实，撤回对provenance mask的确定说法。跨篇“Nemotron超长token都mask”也应收窄到SWE teacher明确列的max turns/agent/eval timeout未完成轨迹；不能外推所有token上限或所有域。
3. **旧矩阵物理页19、24–27、35–36不准确覆盖其引用。** 当前同源PDF SFT为p.15、统一RLVR p.20、MOPD p.21–22、SWE teacher p.22、one-step与故障 p.31–32。控制字符造成的错误分页可能解释偏移，但这是读者推测，不当作旧作者原因。
4. 旧稿有关reward profiling、多harness、长程MOPD效率困境、56/36/8故障构成大体正确；应补故障分母、范围与图17反例。“因此我方必须加prewarm/注册制张量槽”是旧方案建议，不是Ultra已证明的唯一设计。

## 11. 对 RepoHarness 项目一的有限映射

映射日期2026-09-07；使用主资料checkout HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`，实际 `reference/miles-rh2-integration` HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`，未用本任务worktree默认分支代替。当前简报〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕更新于09-05，项目一建议〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕09-07强调已有真实链与实际消费缺口优先；建议不是C包批准。只做窄读取，没有重新全仓审计。

当前职责是miles/SGLang提供训练/推理基础，外部coding harness行动，rh2承担环境/评分与训练消费边界。实际读主checkout `rh2/src/repoharness2/adapters/miles/group_admission.py` 的 `admit_group` / `rh2_group_admission_filter`：rh2这里不判staleness阈值，而是核版本事实与组准入，consume-time阈值由miles `DefaultDataBuffer.get()`承担（完整路径 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py`，上述integration commit，已读其get实现；rh2文件注释亦明确）。这是当前接线边界，不应因Ultra一句one-step再造第二套阈值。

| 候选借鉴 | 归属与适用条件 | 最小验证及指标 |
|---|---|---|
| 把未完成loss mask、reward和group统计分开 | rh2跨层集成候选；Ultra仅提供loss一层证据，不能替C包决定整组处置 | 用正常失败/turn超限/eval timeout反例，在固定组参考计算中核实际梯度、分母、补采计数；不把未核披露当实现标准 |
| 环境有效性与行为启发式分开 | rh2环境/评分应用层；SFT筛“少编辑/未测试”不能变成所有RL样本永久资格 | 已有任务上人工核一小批合法替代解、评分和失败类型；统计有效任务及误杀/无效成本，非只看筛后pass rate |
| second-harness先评测 | 外部harness复用；原图17反而说明迁移风险，新增混训要有证据 | 固定checkpoint/task/grader预算测harness差异，先修接线，再判是否混训；不承诺第三harness泛化 |
| 长尾与系统成本拆分 | 通用async/checkpoint/推理优化优先归上游；rh2增量由trace发现 | 记录env准备、decode、tool、grading、buffer、learner及失败成本；比较actual consumed groups/GPU-hour和held-out学习；GB200的20%/10%不能套PCIe八卡 |
| OPD前检验支持集/数据缺口 | 设计层条件候选；先比较反馈修复完整轨迹SFT与等预算重试，确有价值才接teacher logprob | 独立开发集同时量SFT/OPD收益、teacher成本、mask与token对齐；不预设多教师MOPD为第一版需求 |

论文可支持“真实agent后训练需要跨层处理环境、失败、轨迹和吞吐”的背景叙事；本项目个人贡献必须来自实际目标模型、harness、GPU、可信grader与独立学习结果。不能把NeMo优化或miles基础能力写成我方原创，也不能把有限日志审计等同已完成八卡训练。

## 12. 快速定位、关联与独立审查记录

- SWE端到端teacher/未完成mask/反作弊 → §4.2；原文p.22。
- MOPD sampled-token、三policy身份与clip → §5.1；原文p.21–22式1–3。
- 全域SFT/教师、STEM40B-token配额 → §3.2/§4.3；原文p.15–19/22–26。
- MTP full-vocab forward KL与明确分母 → §5.3；原文p.29–30式4。
- 长程负结果/warmup/teacher recovery → §6；原文p.27–29表4–5。
- 故障/成本/真实性能分母 → §7/§9；原文p.31–36、41–51。
- 附录全部协议与跨harness反例 → §8.2；原文p.64–65图17。
- 关联已存在笔记：R1 MAI-Thinking-1〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R1_mai_thinking_1.md`〕、N01 KAT-Coder-V2.5〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md`〕、N11 miles〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕。R1的SFT专家合并不能填作本篇MOPD事实；其他第二批尚未完成任务仅以编号参考。

独立审查与修订于 **2026-09-07完成**，记录见 07_R2_review〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/07_R2_review.md`〕。

- 主任务ID `01a07827-1e2f-78c3-8c14-1d222dda34c7`；子任务ID `01a0782d-89ca-7723-ac6f-947eb979e7d7`，agent path `/root/r2_independent_review`。两者session turn_context均核实际 `gpt-6-astra / high`；唯一审查者以 `fork_turns="none"` 创建，无递归扩团队。
- 原文为2026-06-09的65页报告；被审版本 固定初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R2/R2_nemotron_3_ultra_draft_20260907.md`〕（385行），审查期间及修订后均保持不变。该副本按原笔记位置解释相对链接，最终导航以本正文为准。
- 审查者先读原文全部§3和A，再核相关§2/4/5并逐项对照初稿；关键教师箭头、公式、harness图回原页。结论为没有重大训练语义错误或整块主题遗漏，实际发现F1已处理：§3.2 Safety撤回未披露的“先回应/后推理”顺序，改为回应与推理的两阶段生成（p.16）。未另声称审查者对修订后全文二次复审。
- 作者另将审查期间完成的四模型HF metadata查询纳入§9，并为§11的miles符号补完整路径及实际读取依据；不是为报告训练配置补默认参数。
- 未披露项仍见§10。正文、审查与来源附件的本地链接按最终主资料位置核验；只发布本任务专属文件，没有修改共享索引、旧稿、训练代码或实验定案。


---

## 文档 2 / 7：R13_kimi_k3.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/R13_kimi_k3.md`

# R13 Kimi K3: Open Frontier Intelligence：后训练与项目一精读

Kimi K3 的主线是 SFT 冷启动、三个领域与三个推理投入档位形成九个 RL 专家，再用多教师 on-policy 蒸馏（MOPD；由学生策略采样）整合为一个可按 effort 控制的模型。报告明确继承 K2.5 的策略优化，并直接给出 MOPD 逐 token 奖励；不能说“算法完全未知”，也不能据此补齐 K3 的跨版本概率、mask 和损失分母实现。其长程方案是同步迭代内的 partial rollout：达到完成比例便暂停生成，未完轨迹下轮优先恢复，同题 K 条全部完成后才送优化。可借鉴的是预算、组完整性、独立评分与状态保留之间的分工；1M 上下文、数千万沙箱和几百卡共置训练不是 RepoHarness 的配置依据。正文同时覆盖通用/视觉/专业工作、偏好式奖励、部署量化及 draft 训练，并保留负结果和复现缺口。

导航：来源与覆盖 · 训练阶段与算法 · 数据环境与评分 · 长程系统与模板 · 评测与负结果 · 旧稿纠错及项目映射

## 1. 来源、版本与覆盖

- 正式标题 **Kimi K3: Open Frontier Intelligence**，作者 Kimi Team，机构 Moonshot AI / Kimi；技术报告，阅读日期 2026-09-07。
- 主证据：资料库 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/k3_tech_report.pdf`〕，47 页，无 arXiv 水印，PDF 元数据生成于 2026-07-27。以下 `p.` 指此 PDF 的物理页；封面算 p.1，p.2 起与印刷页一致。
- [arXiv 记录](https://arxiv.org/abs/2607.24653)：v1 提交 2026-07-27，v2 修订 2026-08-07。另保存 v1 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/arxiv_v1.pdf`〕、v2 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/arxiv_v2.pdf`〕、两版 TeX 源码。主 PDF 与 arXiv v1 **不是同一个字节版本**：逐页去空白比较，只有 p.1 的水印/版式及 p.41–42 贡献名单不同；p.2–40、43–47 正文和技术附录文本一致。故称“本地报告，与 arXiv v1 技术正文一致”，不直接把其文件身份改成 v1。
- 已逐文件比较两版源码，包括 `4-post-training.tex`、`5-infrastructure.tex`、`6-eval.tex`、`tables/`、`7-case-study.tex`、`appendix.tex` 及附录 F。**后训练、数据环境、全部评测表、案例、技术附录 B–F 均无实质增删。** v2 的相关增量见下表。源码中的注释、`\iffalse` 内容不是已发表正文。
- K3 §4.1.2 明确引用的 K2.5 算法，仅沿这一依赖核对：[Kimi K2.5: Visual Agentic Intelligence v1](https://arxiv.org/abs/2602.02276v1)，资料库 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/R7_kimi_k2_5_2602.02276.pdf`〕 p.8 §4.4.2 Eq.(1)，及 原 TeX 对应文件〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/k25_tex/4-pipeline.tex`〕。这不是 K2.5 全篇精读，也不把其全部配方归入 K3。
- 官方 [Kimi K3 模型卡](https://huggingface.co/moonshotai/Kimi-K3/tree/f831ab66814297da540d832a5235f8e904f29d06)：仅核发布资产与部署入口，查询 revision `f831ab66814297da540d832a5235f8e904f29d06`。AgentENV 只采用 K3 §5.3.2 的依赖说明及官方仓库可访问性，不展开环境系统专题。
- 按原文章节先建立独立覆盖底稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/coverage_before_old_notes.md`〕，随后才读旧相关性笔记〔仓库引用：`docs/harness_improve/external_paper_references/k3_agentenv_relevance_notes.md`〕、旧证据矩阵〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕 §7.1，及旧 Pro 长文〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/外部pro探索回答粘贴.md`〕 K3 部分的算法、阶段、预算、系统、继承关系等段落。旧稿不是事实源。

| 版本差异 | 实际核对范围与结论 |
| --- | --- |
| 本地报告 → arXiv v1 | 技术正文文本一致；首图数字一致，封面增加 arXiv 标记；贡献名单变化。没有凭 PDF 日期推定完全相同文件 |
| v1 → v2 §5.3 | 改写引言；§5.3.1 把内存争用更准确表述为长上下文 KV 保留增加 DRAM 需求、与训练状态竞争，并强调 prefill/decode 的 prefix 管理与调度。后面的 write-back/CPU/NVMe 机制未改 |
| v1 → v2 §2、§5.2.3 | Flash Attention FP32 输出的归因措辞调整；QB 补 expert-threshold 引用；Per-Head Muon 补既有工作引用；ViT pipeline bubble 分解补 Optimus 引用。不能据 v1 措辞夸大原创归属 |
| v1 → v2 图1/其余 | 首图从 PDF 改为 TeX 绘制，逐 panel 数字与脚注核对未变；贡献名单和参考文献更新。§4、§6、§7、技术附录不变。v2 PDF 提取触发 Poppler 字典/字符串警告，实质差异判定以可读的完整两版 TeX 为准 |

**覆盖表。** 不把架构“专家”与九个后训练专家混为同一单位。

| 原文位置 | 主题与阅读深度 | 本笔记位置 |
| --- | --- | --- |
| p.1–2 §1、图1 | 摘要、贡献、综合表现，通读；非组件因果证据 | §2、§7 |
| p.3–10 §2.1–2.5、图2–6 | KDA/Gated MLA、AttnRes、Stable LatentMoE、视觉、Muon；概要读并核影响后训练的量化/路由/缓存约束 | §2、§6 |
| p.10–12 §3.1–3.4、表1、图7 | 数据、scaling law、预训练、上下文扩展；概要读 | §2 |
| p.12–14 §4.1.1–4.1.4、图8、Eq.(15)–(16) | SFT、九专家 RL、partial rollout、effort、GRM、MOPD、QAT、draft；全读并目视公式页 | §3–4 |
| p.14–17 §4.2.1–4.2.7、图9–10 | 七类环境/合成机制；全读并核图中流程与曲线口径 | §5 |
| p.17–21 §5.1.1–5.2.3、图11、Eq.(17) | KDA kernel/KCP、MoonEP、内存、视觉 encoder；概要读，技术附录对应检查 | §6.4 |
| p.21–22 §5.3.1–5.3.2 | 长程 RL 状态管理、AgentENV；全读 | §6.1–6.2 |
| p.22–25 §5.4.1–5.4.3、图12 | prefix cache、decode/AttnRes/MoE kernel、在线调度；全读，防止把 serving 当 RL | §6.4 |
| p.25–28 §6.1.1–6.1.4、表2 | 四大领域、baseline、配置与结果；全读、回原表 | §7.1–7.2 |
| p.28–31 §6.2.1–6.2.2、表3–4 | 内部体验/能力、网络安全评估与失败分析；全读 | §7.3–7.4 |
| p.31–32 §6.3–6.4、表5、图13 | 第三方快照与推理费用；全读并目视图13标记 | §7.5、§8 |
| p.33–34 §7–8、图14–15 | kernel、编译器、芯片、科学/知识工作、视频，全部六类案例及结论；全读，补读图15和尾页 | §7.6 |
| p.35–40 References；p.41–42 附录A | 依赖与贡献名单定位；不逐人摘要 | §1 |
| p.43 附录B；p.43–44 附录C；p.44–45 附录D；p.45–46 附录E | SiTU 局部/有界性质、QB 推导/直方图、MoonEP 上界；概要读与正文关系核对，无独立 RL 配方 | §2、§6.4 |
| p.46–47 附录F、图16 | XTML、options、保留 thinking、工具序列化与明确 mask；全读 | §6.3 |

## 2. 底座与后训练的约束

表1给出 2.78T 总参数、104.2B 激活，摘要取整为 2.8T/104B；93 层，896 个 routed experts 中每 token 选16个，另有2个 shared experts；160K 词表。**这里的 expert 是单层 MoE 子网络，不是九个独立 RL policy。** 69 KDA 与24 MLA 层，基本3:1混合、末端额外 MLA。NoPE 加 KDA 递归门承担位置机制，不需 RoPE 重缩放，但仍经过 **8K → 64K（预训练）→ 256K → 1M（cooldown）** 的训练课程；不是“无额外训练即可具备1M能力”。原生视觉从头联合 next-token prediction，无后加模态对齐阶段（§2.1、§2.4、§3.3–3.4，p.3–12）。

MoonViT-V2 约401M参数、27层，图像与视频共享参数，2×2 pixel shuffle 压到四分之一视觉 token，支持最高3584×3584输入。相较 SigLIP 初始化的 MoonViT-3D，图6显示较低且较少尖峰的梯度范数；作者报告视觉成绩可比。它是底座稳定性观察，不能解释为 K3 “zero-vision SFT”（§2.4，p.9–10）。

Stable LatentMoE 将 routed 路径压到3584维，聚合后加 RMSNorm；SiTU-GLU 平滑限制两乘法分支，参数4和25，输出界100，附录B给局部与极限关系。QB 按全局 token 分布分位数更新 routing bias，下一步才生效，推理时冻结；bias 参与 Top-k 选择、不参与所选 experts 的混合权重。附录C的完整分配求解、D的 pooled histogram 是路由负载机制，不是 RL prompt group。D例子 `B=1000` bins，不能把正文“few hundred bins”概述当精确配置；更不能从冻结部署 bias 推出 RL 已实现 routing replay（§2.3、附录B–D）。

预训练文本域为 Web/Code/Math/Knowledge，视觉包括图文/OCR/视频/视觉代码；规则与分类器过滤、去重、改写后核忠实性，长数据另做结构检查及视频感知 hash、上采样和跨全文任务合成。Per-Head Muon、weight clipping、cosine、1% warmup、weight decay=0.1 都在底座章节；**这些数不能不经说明填入 RL 配置表。** 图7的约2.5×是架构/数据/配方共同形成的预训练 scaling efficiency，非 RL 吞吐或 MOPD 增益（§3，p.10–12）。

## 3. 真实阶段与模型关系

| 阶段 | 模型、数据与目标 | 已知边界 |
| --- | --- | --- |
| SFT cold start | 此前 Kimi 系列领域专用模型合成长程轨迹，多阶段验证、人工参与标注，以 XTML 序列化；建立 adaptive reasoning、工具调用、长期执行 | 生成教师不等于后面的九个 K3 RL 专家；数量、图文比例、失败轨迹比例、训练 epoch 未给（§4.1.1 p.12） |
| 领域专家 RL | general tasks：通用体验、视觉、推理、faithfulness、搜索、知识工作；general agents：长程 assistant、deep research、段落写作；coding agents：SWE、coding experience、kernel、webdev | 三个 broad domain，各有 low/high/max policy，共九个；不是每 benchmark 一个专家（§4.1.2 p.12） |
| effort 课程 | 每域先较宽预算训练 max，再退火预算倍率获得 high/low；倍率按域由人工指导调整 | 是阶段课程，不能画成九条全独立、同时从同一 SFT 开始的训练线；确切 checkpoint 分叉/复用顺序未给（p.13） |
| 专家轨迹回收 | 三档专家轨迹共同收集，供 SFT 与 MOPD | p.13 确实写二者；没有说明是否构成固定的额外 SFT 阶段、与 MOPD 的先后或混合比例 |
| MOPD 整合 | 领域 d、effort e 选匹配教师，将稠密逐 token 信号融入 RL 框架，得到单一 effort-conditioned student | student 初始 checkpoint、教师刷新/冻结规则、训练规模未给（§4.1.3） |
| 部署配套 | QAT 自 SFT 起贯穿后训练；预训练 MTP 层另训为 EAGLE-3-style draft | draft 是单独部署加速模型；这一步明确冻结 target，仅更新 draft 层和特征融合投影（§4.1.4） |

论文没有独立列出 DPO、最终安全对齐或 MOPD 后再 RL 的阶段。faithfulness、通用体验、GRM 比较均在本篇覆盖；网络安全能力评测不等于安全对齐训练。也不能因存在 subagents/Swarm Bench 就补写 K2.5 PARL 的冻结 subagents 方案。

## 4. 算法与训练消费语义

### 4.1 先区分三个采样单位

K3 §4.1.2 p.13：一次 rollout 活跃池有 **N 个 prompts，每题 K 个 completions，共 NK 条轨迹**；暂停阈值是已完成轨迹数达到 `λNK`，`0<λ<1`。同题全部 K 条完成后才提交优化。这里 completion 可为很长的多轮 agent 轨迹，不能按一次 API response 计。原文没有给 N、K、λ 数值，也未具体描述跨轮新题补位与实际 learner batch 装配。

长轨迹会跨多个迭代，原文把由此产生的 stale data 称为高度 off-policy；局部逐 token 正则用于约束更新。**同步迭代的生成阶段仍会暂停并进入优化，取消的是等齐全部 NK 终止的要求，并非取消所有全局阶段边界。** 逐题完整 K 是另一条条件。未完前缀进入队列续跑不代表已作为独立样本参与 loss，报告没有提供这种片段训练规则。

### 4.2 明确继承 K2.5，但不能伪造一份 K3 完整 loss

K3 p.13 直接写 policy optimization follows Kimi K2.5；这比单纯“家族近似”强。沿引用回到 **K2.5 p.8 §4.4.2 Eq.(1)**，可核：旧策略每题 K 响应，基线为同题平均 reward；概率比为新/旧策略在同 token 和 prefix 上的比值，目标包括 Clip 概率比乘 reward 差，以及平方 log-ratio 正则。

为避免 K2.5 与 K3 同名符号混淆，下式只摘其明确定义并改名，不冒充 K3 新公式：

\[
\bar r(x)=\frac1K\sum_{j=1}^K r(x,y_j),\quad A_j=r(x,y_j)-\bar r(x),\quad
\rho_{j,t}=\frac{\pi_\theta(y_{j,t}\mid x,y_{j,<t})}{\pi_{\rm old}(y_{j,t}\mid x,y_{j,<t})},\quad
Z=\sum_{j=1}^K|y_j|.
\]

K2.5 把分母记为 N，并称 total generated tokens in a batch；与 K3 活跃池的 prompt 数 N **不同**。已发布式呈现 `Clip(ρ,α,β) A_j` 与 `−τ(logρ)^2`；说明文字则称 log-ratio 在 `[α,β]` 内才保留梯度、区间外归零，且不依赖 advantage 符号，不同于标准 PPO clipping。该公开目标没有 value/GAE 项或 reward 标准差归一化，支持“**采用组相对、无需显式 critic 的已披露优化路线**”这一继承解释。

但 K2.5 原式/文字存在实现歧义：Clip 写在 ratio 上，文字边界说 log-ratio；平方正则的求和括号不完整；正文称“minimize”而式的符号呈 reward 最大化形态。此处保留原页〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/k25_page-08.png`〕供核对，不擅自修成可运行 loss。旧长文写出的 `m(ρ)ρA−τ(logρ)^2` 只是概念重写；mask 是否也作用于正则、跨 prompt 分母、最终符号不能由它定案。

**K3 可确认继承方法，不等于确认全部 K2.5 配置。** K3 未重述准确行为 logprob、跨版本 token 对应策略、优化 epoch、reference/old 的具体缓存关系，亦未把 K2.5 的 MuonClip 名称明确列为本篇 RL 优化器。其 §2.5 的 Per-Head Muon 属另一个披露位置。不能据“继承”断言未知内部变体绝不存在，或补写统一 `π_old` 覆盖整条跨版本轨迹。

### 4.3 Reasoning effort 与奖励长度偏置

K3 p.13 的文字规则可等价整理为（下式是阅读者整理，非报告编号公式）：

\[
r_{\rm effort}(x,y)=\begin{cases}-1,&T(y)>\tau b_0(x),\\r_{\rm task}(x,y),&\text{否则}.\end{cases}
\]

`b0(x)` 来自 cold-start model 的初始预算估计；一般任务 T 为 thinking tokens，agentic 为累计模型输出 tokens，含 reasoning traces 和 tool-call arguments。观察输入、工具 CPU/GPU、等待墙钟、并行 subagent 计算的汇总规则未给。先大 τ 的 max 再减小到 high/low；max 仍有上限，但具体 τ、b0 估计采样数及上限未披露。这是 **覆盖 reward 为 −1**，不是自动丢弃；是否对所有超预算 token 产生梯度还取决于未披露的过滤/mask。它也没有规定一到阈值立即硬终止。

不可直接验证的 general tasks 用 Agentic GRM：候选间 tournament-style 二元比较，judge 必须先读结果/工件/文本、生成 rubric、逐候选按 rubric 打分、记录 scorepad。另一长度规则从 cold-start 估计初始 verbosity `ℓ0`，输出长度超过 `σℓ0` 的候选自动输掉比较。**verbosity 控制的对象是候选输出长度与 pairwise 输赢，effort 控制的对象是问题预算与任务 reward**；不是同一个阈值或处罚公式。GRM 具体模型、rubric 校准、比较图、tie/顺序处理未给（§4.1.2）。

### 4.4 MOPD 的明确公式与有限含义

K3 Eq.(15)，p.14（已对原页与 TeX）：

\[
r_{\mathrm{opd}}^{d}(y_t\mid e,x,y_{<t})=
\operatorname{clip}\!\left(
\operatorname{sg}\!\left[\log\frac{\pi_{\mathrm{teacher}}^{(d,e)}(y_t\mid x,y_{<t})}
{\pi_\theta(y_t\mid e,x,y_{<t})}\right],-R_{\max},R_{\max}\right).
\]

d 指领域，e 从 low/high/max 中采样，`π_teacher^(d,e)` 是匹配专家；并非九个教师投票。student 显式以 e 为条件，teacher 的 e 编入专家身份。`sg` 切断 reward 计算自身的梯度；`Rmax>0` 裁剪极端信号，值未知。评估的是**当前 token** 的教师/学生概率；OPD 用学生访问的前缀进行监督，而不是只学习教师离线轨迹。结合 partial rollout 时，报告未明确定义此处 `πθ` 的打分版本与逐段行为版本如何对应。

阅读者数学解释：若固定前缀、token 从当前学生采样，并忽略裁剪与训练近似，其期望 log-ratio 为 `−KL(πstudent || πteacher)`，对应反向 KL 方向；这不是报告公布完整 KL loss。原式不要求把 full-vocabulary KL 当最终目标，也不证明 teacher forward 无需生成全词表 logits，更不证明某种 top-k 通信实现。**作者尝试更细 top-k distillation，在该设置中未见收敛速度或最终性能明确优势**，未报 k/误差条/计算对齐（§4.1.3）。

稠密奖励可进入原 RL 框架，支持 partial rollout；但 return/advantage 如何累积、是否保留 K-group、task reward 混合比例、loss reduction、teacher/student tokenizer 是否一致、教师是否冻结、特权上下文和刷新规则均未给。尤其不能从 `sg` 推导训练全过程 teacher 一直冻结；明确冻结只出现在下面 draft 训练。

### 4.5 QAT 与 draft 后训练不可省略

QAT 从 SFT 起覆盖 SFT/RL：**routed MoE expert 权重 MXFP4，输入激活 MXFP8**；attention projections、latent MoE projections、shared experts、routers 留高精度。RL rollout/trainer 共享量化方案。报告的消除 train–inference mismatch 限于此设计语境，不是 tokenization、采样支持集、MoE routing、kernel 舍入、跨版本 KV 全部一致的证明（§4.1.4 p.14）。

预训练已有一个 MTP 层，将其微调为 EAGLE-3-style draft。冻结 target，只更新 draft 层及无 bias 的融合投影 `W_E3`。输入拼接 target 第1、第4、最终 AttnRes block 的特征；`W_E3=[0 0 I]` 初始化，只读原先 MTP 使用的高层特征，再学融合低/中层。训练展开7步，第一步后使用 draft 自身早期输出，模拟推理递归。其 Eq.(16)：

\[
\mathcal L_{\rm LK}=-\log\sum_{v\in\mathcal V}\min(p(v),q(v)).
\]

p 为 target、q 为 draft 下一 token 分布，均 temperature=1；没有辅助 ground-truth CE。括号内为无损 speculative sampling 的逐 token 接受率；作者认为有限容量 draft 的 KL 降低不保证接受率增加，故直接优化此目标。draft 也遵循上述 QAT 配置。它优化推理接受率，与能力 MOPD 是不同教师/学生关系（§4.1.4）。

## 5. 全领域任务生产、环境与评分

### 5.1 统一白盒 harness 与知识图谱

白盒指内部可配置/组合的 harness 模块：工具接口、system prompt、context management、skills、memories、subagents 等。配置可实例化 Kimi Code、Claude Code、Codex、OpenClaw、Hermes 及新组合；RL 按不同 task groups 动态构造配置。作者的动机是避免固定 schema/协议过拟合。它**不表示 hidden verifier 对模型可见，也不保证直接运行各产品原版二进制**，没有给软件 commit 或组件拆分消融（§4.2.1 p.14–15）。

知识图谱是由粗到细的 DAG：先定粗粒度种子，为节点派 agent 搜索；添加概念前查已有图，复用等价/相关概念，边始终从粗指向细；新节点继续扩展，agent 判断足够原子时停止。采样不同层级的单节点或相关组合，加祖先上下文成检索关键词，从公开文章、博客、代码库取材料，再每实例选一种任务类型合成。图9覆盖 knowledge/coding/vision 等，不是只做 SWE。**self-evolving 指概念图探索扩展，未披露由 learner 失败自动驱动的闭环 curriculum**；也没有候选数、图节点数、质量筛选漏斗或 train/test 去污染比例（§4.2.2 p.15）。

### 5.2 任务与奖励逐类覆盖

| 领域/原文 | 输入与执行 | 评分与边界 |
| --- | --- | --- |
| 多步可验证问题 §4.2.3 p.15–16 | 多步搜索证据并生成可验证答案；投行/数据分析/法律专业流程需分解任务、操作工具、形成交付；视觉 STEM/谜题/图表通过隔离 Python 裁剪、缩放、变换、计算与检查，生成图像回作 observation | 专业流程数十到数百步；未列逐题 verifier、各域比例，不能把法律/投行训练说成正式专业意见系统 |
| GPU kernel §4.2.4 p.16 | 从优质 GitHub 库（如 FLA）取单算子到 fused mega-kernel，CUDA/Triton/CuTe DSL/Gluon/ThunderKittens/TileLang，跨 GPU 架构与 BF16/FP8/FP4；有 PyTorch reference | 数值误差超阈值=0；匹配 expert 实现性能=0.5，逼近硬件 roofline 趋向1；未给插值公式。惩罚 CUDA graph replay、缓存输入、降精度等作弊，随新策略更新检测。reference 是否对 agent 可见未说明 |
| Personal assistant §4.2.5 p.16 | Gmail/Notion/Slack/Canvas 的 mock apps 保留核心语义，避免外部 API/rate limit；跨多个模拟日、多个应用、几十个相互依赖事件，持久演化环境；agent 搜索素材构建初始 workspace | 每事件有独立判据，规则或 LLM evaluator；单 rollout 可达数千 tool calls、数百万 context tokens。事件分数到总 reward 的聚合未知；累积量不等于单次超过1M窗口 |
| AET §4.2.6 p.16，图10 p.17 | 初态、目标/约束、工具动作空间、执行预算、独立 verifier；agent 只见目标、上下文、约束、验证接口，无 reference trajectory/预设流程；黑盒系统复刻、量化因子发现、税务审计等 | 独立 verifier 看最终环境状态，不取自报完成；公开 verifier 给诊断，hidden verifier 评 held-out 情境；提交预算与 penalty 限制投机。未给 penalty 公式及提交次数，不能写“每次失败提交统一扣某值” |
| Webdev §4.2.7 p.16 | 专家筛选的 prompt，从一句场景到多段说明，产物涵盖网站、游戏、3D/WebGL、数据可视化、SVG、全栈；container sandbox 与多 scaffold | 确定性功能检查，复刻任务用结构/像素相似；构建失败、运行错误、伪造产物=0。内部 RM 的其他模型检查源码或观看/交互产物；两个分量权重、judge 模型未给 |

图10是 Camera Repair Management System 黑盒复刻**单例**：横轴归一化 executor tool-call progress，纵轴 verifier-assessed completion；图例 K3 1.000、Opus4.8 0.918、GPT5.5 0.893、K2.6 0.560。没有绝对 tool-call 数；不能改写成总体 AET 成功率或相同成本的完整排名。

### 5.3 SWE 数据漏斗与可靠评分的缺口

SWE 被明确列为 coding domain；但 K3 没有公开从原仓库/PR到成功构建、有效题、solver可解题、最终 RL 消费轨迹的计数漏斗。不能把 **1,505,678 images** 当独立仓库/题目，也不能把 **51,219,741 sandbox creations** 当 RL 轨迹；二者含训练及评测、可重复启动（§5.3.2）。

关于数据时间、仓库切分、许可、hints/gold 剥离、训练污染防控、no-op/golden/alternate-solution 检验、flaky test 重复与误杀率，§4.1–4.2没有足够配置。AET“无参考轨迹”不能外推到所有 SWE/kernel 任务；AET public/hidden 隔离也不能外推成各任务都用相同 fresh grader。构建错误/不可评分/超时/解析错误在所有域如何记 reward、进入组统计或补采，同样不完整。已披露的 kernel/webdev/effort 特定零分和负分规则保留，不用“失败统一丢弃”填空。

## 6. 长程 rollout、状态与训推接口

### 6.1 RL 时序及四类状态

§5.3.1 p.21–22 的共置方案意在把每个1M-context K3 RL experiment 控制在**几百GPU**内，未给具体型号/数量/并行度。与§4.1.2合起来：活跃轨迹生成 → 完成比例λ触发暂停 → 完整K组优化 → 下轮优先恢复未完项。不能把 serving 的独立调度策略当成 fully async learner。

| 状态/机制 | 本篇明确说明 | 未获保证 |
| --- | --- | --- |
| 环境执行状态 | AgentENV 增量 checkpoint/resume、fork、snapshot | 不自动恢复 RL group、评分结果、行为概率、trainer ACK |
| GPU KV / KDA state | active decode blocks 留GPU；可复用闲置 prefix 被逐出GPU时才 write-back 到 CPU DRAM pool，下次复用前预取；KDA状态与MLA KV一起迁移 | 没说旧权重下缓存跨权重更新直接可用；weight/cache invalidation 与 re-prefill规则未知 |
| 训练权重/optimizer | 一轮训练后 offload 到 NVMe，给 rollout 期间 CPU KV pool 留DRAM；一轮 rollout 后释放 pool 避免争用 | 不能说 KV pool 无条件永久跨 trainer update 保留；持久轨迹、GPU缓存、CPU池生命周期不同 |
| 非 policy forward | reference 等权重留CPU，借 policy FP32 gradient buffers 临时上卡；ZeRO-2 每GPU保留两个VPP chunk缓冲，一块forward、一块预取 | 此例未标定为九个 MOPD teacher 的具体服务部署方案 |

request 层 auto-throttling 用活跃数、排队数、KV利用率动态调发给引擎的请求数量：早期充分利用，context增长后降并发防preemption。未给阈值或受控吞吐表；它观测的是请求与缓存压力，不能据此声称 K3 有 staleness N 判据。

### 6.2 AgentENV 的范围与测量口径

K3 同时用传统 container、GPU sandbox、Firecracker microVM AgentENV，不能把全部任务都称为 microVM。早期 container 试验曾被意外 agent 操作引发 kernel panic/deadlock；作者选择更强隔离且允许mount磁盘、嵌套container/VM的环境，不是报告“container一概不安全”（§5.3.2 p.22）。

- 增量保存自上次 checkpoint 后 dirty memory pages；最低 checkpoint/resume **133ms/49ms**，不是均值/P99或所有工作负载保证。
- Pause/resume：暂停 sandbox 不占CPU/内存；等待模型 inference 最多可达 sandbox 生命周期 **98%**。此数不是GPU空闲率，也不保证整体成本省98%。
- Fork：复制运行中精确状态，原实例继续，用于评分副作用隔离。它并不自动去掉已被 agent 篡改的控制面或秘密材料。
- Snapshot：可定期存以错误恢复；没有声明 learner 端 exactly-once。
- OverlayBD、自定义ublk、共享存储/P2P与COW/page-cache优化；报告大规模sub-second启动、实际工作负载最高 **6.5× memory overcommit**。没有相同资源下可比吞吐基线。
- 全训练与评测合计创建 **51,219,741 sandboxes / 1,505,678 images**。不知独立题数、同时活跃数或每条轨迹的启动次数，不能倒推数据集规模。

官方 [AgentENV](https://github.com/kvcache-ai/AgentENV) 可访问且仓库 metadata 标 MIT；本次不把其当前 API、内核/KVM要求、README速度数字纳入 K3 报告事实。

### 6.3 XTML：保留 thinking 与显式工具边界

附录F p.46–47、图16 是后训练重要正文补充。XTML用保留token `[open]`、`[sep]`、`[close]` 表示结构，`[end_of_msg]` 为生成停止标记，目标是可扩展、少额外SFT即可学会、便于流式解析与约束解码。

| 层面 | 规则 | 对学习/缓存的意义 |
| --- | --- | --- |
| 消息 | system/user/assistant/tool 输入消息；global options 在历史前，one-shot options 在历史后；动态 tool-declare 可插历史中 | tool declaration、effort 作用全会话；tool_choice/response_format 只作用本请求，后置避免改变历史KV |
| 通道 | assistant含 think、response、tools；generation prefix 选择 thinking或instruct | **只支持 preserved thinking**：thinking模式保留历史think，空think也保留；instruct历史只有response/tools。不是强制单轨迹永不compaction |
| 工具 | 并行call用tool/index，结果重复同配对且按call顺序；字符串argument用raw text，其他JSON类型compact序列化 | 代码不必转义成JSON字符串；pure-JSON fallback仅可在输入、不在模型输出，**该fallback的loss被mask** |
| effort | global `thinking-effort` option在工具声明之后、input之前，以自然语言表达 | schema预留low/medium/high/max，K3只支持子集；§4.1.2实际训练为low/high/max。不是向模型暴露数值token预算 |

除了 fallback 明确mask，报告没有完整给出 thinking/response/tool observation/compaction 进入 loss 的选择、重分词/TITO实现、shared prefix去重计权。`preserved thinking` 是格式/历史规则，不能拿来证明每个历史 token 都被训练且只训练一次。

### 6.4 其余 infra 与技术附录：上游层面的工作

这些内容已读，但不是 rh2 自建任务。

- **KDA计算**（§5.1 p.17–18，Eq.17）：FlashKDA CUTLASS chunkwise kernel把token并行与head递归解耦重叠；单GPU SM级CP与跨GPU KCP不同。KCP交换每段累计状态转移矩阵和从零生成状态，按文档顺序组合 `S←M S+S_local`；直接把零初态结果相加不正确。固定大小all-gather使长上下文分片可行；非RL样本切段算法。
- **3T预训练**（§5.2、图11）：PP/VP、EP、ZeRO-1 DP、Pipeline ZeRO-2、CP；MoonEP从当前microbatch路由规划冗余expert，forward预取、backward还原梯度至home rank，消除跨rank token负载不均与动态shape开销。附录E证明每rank至多E/R个冗余expert足够、近乎紧；不是每个expert自己token数完全一样。GPU近优planner替代每步精确ILP。
- **内存与视觉**（§5.2.2–5.2.3）：activation统一存储政策组合量化/重算/本地和远端offload，单GPU池减少碎片；MoE backward重算dispatch、AttnRes边界块缓存、PP远端activation均衡、ZeRO-2双grad buffer与CPU累积、Muon按owner P2P取矩阵；视觉动态CP与计算填入pipeline bubbles。未给本项目八卡拓扑可直接沿用的配置。
- **在线prefix cache**（§5.4.1、图12 p.23）：KDA固定状态与MLA随长度增长KV共用paged pool；存储块可为6144 tokens，hash粒度例如512，命中2560须所有KDA组都有同边界checkpoint。copy-on-write MLA部分块、先pin所有组、当前调度步新copy未完成时禁止命中、任一组checkpoint驱逐同时失效兄弟组。结尾“任意512边界”须连同**状态存在条件**阅读，不能理解每512 token都必然有checkpoint。
- **decode与fleet**（§5.4.2–5.4.3）：speculation只缓存小投影输入，在芯片上重放已接受前缀来恢复KDA状态，避免每draft位置保存大state；AttnRes融合/并行、latent GEMM与router合并、token-centric MoE、离线weight排布降低内存流量。线上会话primary/secondary consistent hashing保持cache affinity，故障后secondary重prefill；按请求class分预算避免长请求挤占短请求。400K缓存prefix+4K新增是典型coding请求例子，非训练horizon；不构成 rh2 必建粘滞路由/故障恢复平台的理由。

## 7. 评测、案例与负结果

### 7.1 统一配置与重要例外

K3 自测全部 max、temperature=1.0；单步 reasoning/knowledge/无工具视觉 top-p=0.95，agentic top-p=1.0。**这是评测配置，不是训练采样配置。** baseline通常最大effort，GPT5.5为xhigh；Fable5结果含fallback，GPT5.6 Sol含potential cyberguards（§6.1.2–6.1.3 p.26）。

| 对象 | 具体协议 / 限制 |
| --- | --- |
| Coding | Kimi Code/Claude Code/Codex之一；Terminal-Bench2.1对所有模型取跨harness最好分，非固定单harness对照 |
| DeepSWE | v1.1任务，自测K3=67.5；文中另引官方mini-SWE-agent成绩67.3，不能混成一个协议 |
| SWE-Marathon | 2026-07-09、最终v1.1之前的H20校准branch；镜像、性能门、GPU reference oracle重校准，正确性与anti-cheat validators保持；Fable5 35%任务fallback |
| PostTrainBench | K3/Fable5/Sol官方Harbor，max，在H20而非官方H100，三次均值 |
| FrontierSWE | 2026-07-16官方脚本从raw重算dominance；分数非普通未经定义pass@1 |
| BrowseComp | 300K触发context compaction为91.2；完整1M窗口不做context management为90.4。没有给compactor模型、summary训练或等总token预算 |
| OfficeQA Pro | 每题提供整个PDF corpus渲染图，无机器可读文本 |
| MCP-Atlas / AutomationBench | 前者500题公开子集、100-turn、Gemini3.1 Pro judge；后者600题公开子集 |
| Vision | 一般三次均值，ZeroBench-main按官方跑5次、报pass@5；MMMU-Pro保持输入顺序，图放文字前；WorldVQA经prompt强制回答以处理拒答 |
| 外部成绩 | AA与ALE截至2026-07-23；Toolathlon/JobBench截至07-24；Vals AI引用。ALE每模型绑定特定harness，表2脚注Fable5 xhigh且40%任务降级，与通常max规则不同 |

多数benchmark没有在报告列出全部运行预算、重复seed、置信区间或分层排除。不能把表2各指标都冠名pass@1，也不能将未知统一填作“默认官方配置”。

### 7.2 四大能力域结果

下表选关键比较并将其余结果压为同域条目；所有数字来自原表2 p.27，不是当前实时榜单。

| 域 | K3结果与读法 |
| --- | --- |
| Reasoning/Knowledge | GPQA93.5、CritPt23.4、AA-LCR74.7；HLE无/有工具43.5/56.0。CritPt低于Fable28.6、Sol32.3和GPT5.5 27.1；HLE也落后最强专有模型，研究级推理仍是短板 |
| Coding | DeepSWE67.5、ProgramBench77.8、Terminal2.1 88.3、FrontierSWE81.2、SWE-Marathon42.0、PostTrainBench36.6、MLS-Bench-Lite48.3、SciCode58.7。ProgramBench略高Sol77.6/Fable76.8；DeepSWE低Sol73/Fable70。小分差无误差条，不能判显著胜出 |
| 搜索/工具/综合代理 | BrowseComp91.2、DeepSearchQA95.0 F1、ResearchRubrics76.2、Toolathlon76.5、MCPMark94.5、MCPAtlas84.2、Automation30.8、JobBench54.3、ALE28.3。强搜索不等于始终可靠自主完成；Automation与ALE绝对分仍低 |
| 工作与交互代理 | GDPval1686 Elo、AA-Briefcase1548 Elo；APEX41.0、OfficeQA63.3、Spreadsheet2 34.8、OSWorld-Verified84.8/2.0 58.3、SaaS60.1、τ3-Banking33.4、Harvey94.6 criterion-pass、CorpFin71.6、FinanceAgent54.4、LegalResearch44.2。Elo、criterion-pass与任务完成比例分母不同 |
| 视觉感知/视频 | WorldVQA ForceAnswer51.0、OmniDoc91.1、Perception58.5、VideoMME带字幕90.0、MMVU82.1、BabyVision带Python85.7 |
| 视觉推理工具收益 | MMMU-Pro81.6→83.4，CharXiv84.8→91.3，Math-Vision94.3→97.8，ZeroBench pass@5 23.0→41.0。是在评测中加Python后的系统差异，不能分离归因于视觉RL或MOPD |

作者总体描述是接近但落后最强专有模型；“其他模型全面被超过”应理解套件总体，不是逐行严格支配，例如K3 HLE低于Opus4.8、Faithfulness低于GPT5.5。图8随RL FLOPs增长的八类score/assistant steps只给趋势，无数字刻度、种子或同算力对照；有局部波动，不能宣称单调scaling law或“步数增加本身导致能力提升”。

### 7.3 内部能力、体验与harness

§6.2.1 p.28–30 的内部benchmark经常更新、用于引导数据/训练迭代，属于开发诊断性质，不能当从未触碰的final holdout。表3中Harness列一般仅说明K3；其他Claude/GLM用Claude Code、GPT用Codex。明确共同harness例外：24/7用OpenClaw，MIRA用内部OOD MIRA，Agent Behavior/Chat All-in-One用Kimi Work，CLIF/Agentic Vision用Kimi Code。

| 内部项目 | 任务定义 / K3分数（表3） |
| --- | --- |
| KCB2.0 / Coding Experience | 实际端到端软件工程 / 沟通、行为、遵指等使用体验；KCB在Claude Code73.7、Kimi Code72.9；Experience59.9/56.6 |
| 24/7 ClawBench / MIRA | 多日并发事件与中断48.3；多角色企业系统协作及委派判断64.1 |
| KAET / CLIF | 自主执行83.5；从上下文学习复杂交错skills52.4 |
| Agentic Vision / Swarm | 在执行中正确利用视觉事实78.3；协调分解并行76.3 |
| Online Experience / Deep Research | 常见用户交付文件77.9；专家query与rubric90.0 |
| Finance / KWV / DECK | 专业全流程62.6；工作中的原子视觉能力64.7；演示文稿73.5 |
| Agent Behavior | 完成之外的用工具质量、效率和纪律65.0，落后Fable75.5/Sol76.4 |
| Faithfulness / Chat All-in-One | 事实检查后 **1−hallucination rate=85.5**，不是幻觉率85.5；全阶段会话体验85.2 |

KCB的80题脚注：Fable13次fallback+1拒答，Sol10拒答，GPT5.5 3拒答；另有各内部集拒答脚注，不能从分数反推出纯模型解题能力。表4 Webdev用同Claude Code、两者max、专家盲评代码质量/功能完整/视觉/交互：K3相对Opus4.8总体win58.6%、tie13.8%、lose27.6%，净胜31.0个百分点；Games净14.9，3D/WebGL/Shader59.1，Website/UI Clone26.3。未给各域题数和置信区间，不能把净胜当绝对任务成功率。

### 7.4 网络安全评测与失败

§6.2.2 p.30–31分漏洞发现/PoC（Tier1）与端到端利用（Tier2），对近期系统、开源软件及内部设施评测。闭源frontier模型因拒答未作可比对照。这里只总结能力证据，不补写操作步骤。

Tier1找到数百候选；**经过人工审查的子集约70%确认真实**，含六项目16个此前未知漏洞，不是全部候选或所有任务70%成功。报告举内核越界写与权限检查遗漏为例。Tier2共36题（用户态16、内核20），均经专家确认可解，估总540专家小时。K3解14/36=38.9%，GLM解8/36=22.2%；K3的14个成功中10个为用户态。剩余差距归于：利用链末段不能完成、防护下策略不当、陷入无效debug循环、提交前未验证产物。

报告转述UK AISI/CAISI独立评估：ExploitBench32%对GLM24%，32步模拟网络完成17对11步，另一端到端任意代码执行0/41；这些是报告引用的外部设置，不与内部36题合并。作者视当前覆盖为能力下界。**未给安全对齐/拒绝训练配方或整体滥用风险定量结论。**

### 7.5 第三方快照与可归因程度

§6.3/表5：截至2026-07-23，AA Intelligence Index v4.1为57.1，4/580（合并Sol effort entries则第三）；Vals Index74.7%、2/39；WebDev Arena1678 Elo、1/99；Text Arena1486、8/200；Agent Arena9.1、4/37。这是作者记录的第三方快照，不宣称今日名次或相同设置下重新复现。

本文没有九专家vs单模型joint RL、MOPD vs SFT/参数融合、多harness vs单harness、QAT vs量化后处理、partial rollout vs全等齐、数据量/算力严格匹配的消融。最终成绩证明所报模型+协议的表现，不能把差额独占归因某一个后训练组件。

### 7.6 六类案例及其分母

- **Kernel优化**（p.33/图14）：四kernel AttnRes/DSA/KDA/MLA，Hopper及另一厂商GPGPU，相同sandbox、每题最多24h；AttnRes283.6→114.4ms，runtime下降约59.7%，图轴写speedup百分比但不应改称“吞吐仅升59.7%”；DSA/KDA runtime下降55.1%/73.6%，MLA达一半以上peak TFLOPS。这些结果不构成通用kernel加速保证。早期K3 checkpoint参与内部kernel优化是作者经验叙述。
- **MiniTriton编译器**（p.33–34/图15）：从Python tile DSL经MLIR到PTX，配eager/compiled库、autograd/NCCL；L20核心suite几何均值优于PyTorch eager/compile，大shape matmul约测得machine roof90%；图15明确包含输给baseline的点。GPT loss接近，fp64参照下梯度差不超torch本身fp32舍入约1e−4；双GPU曲线是成品编译器验证，不是K3训练曲线。
- **芯片原型**（p.33）：Kimi Code一次48h，nano架构、INT4 group128、Nangate45；4mm²解析预算，100MHz、RTL模拟>8700tokens/s、1.46M标准单元、0.277MiB SRAM。不是已流片芯片、也不是2.8T K3解码速率。
- **科学coding**（p.34）：I–Love–Q复现，>20论文、>300状态方程、>3000行Python及交互dashboard，作者称约2h，相比熟练研究者通常1–2周。人类时长是作者估计，非随机对照。
- **知识工作**（p.34）：AI ASIC行业42年网站，>120轮、87季报+99原PDF（>11000页）、>2800搜索、>1100终端query；另例391个GWTC-5事件、>20并发subagents、7图2表与>10论文。不是平均任务预算或训练数据量。
- **视频/motion**（p.34）：自身架构动画解释及56原片段预告剪辑，涉及镜头/节拍/音频/多轮修改；熟练编辑1–2天为作者类比，未给实际完整生成成本。

负结果需和成功一起保留：top-k蒸馏无明确优势；研究级reasoning与agent纪律仍弱；kernel利用大量题未完成；在相同模型规模与训练 token 预算、固定最低学习率，并分别搜索各自最优峰值学习率和 batch size 的比较中，cosine 最终 loss 低于 WSD（预训练§3.2；未给硬件控制条件）；SigLIP初始化梯度不稳定（§2.4）；长程容器早期panic/deadlock与高并发KV preemption（§5.3）。均不外推成普遍定律。

## 8. 成本、公开资产与复现程度

§6.4/图13报告的是 **per-task推理美元费用**，非训练GPU-hour或数据生产成本：KCB2.0 K3/Kimi Code相对Fable/Claude Code差4分、38%费用，high约以Opus max三分之一成本接近成绩；BrowseComp91.2%、$2.03/题，约Sol一半；GDPval相对Sol低50Elo、费用低13%，相对Fable约2.6倍便宜；AA-Briefcase第二、约Fable一半。KCB为内部计费，BrowseComp混内部与已发表charts，后两者用AA截至07-23的按token API价格。harness、缓存/价格政策及effort不同，不是等硬件训练成本对照。

图13(b) K3只有红星 **max**；medium/high/max黑线是GPT5.6 Sol，其他medium标记属于Claude系列。**不存在“该图披露K3 medium训练档”的证据。** 图13(a)的K3才是low/high/max。图13(b)另标 **Claude Mythos 5 (max)**，包含1M/3M/10M tokens三个点，另有Opus4.8与Sonnet5；主表2及主要正文基线则是Fable5。可能采用了另一比较基线，现有证据不能认定Mythos5就是Fable5或作者图错，因此不擅自换名。该身份边界在v2同图中仍保留。

公开资产核查限于2026-09-07可访问元数据/模型卡与报告所指入口：

| 资产 | 已见与未核 |
| --- | --- |
| [模型](https://huggingface.co/moonshotai/Kimi-K3/tree/f831ab66814297da540d832a5235f8e904f29d06) | API标private=false/gated=false，列权重分片、模型定义、tokenizer、encoding与vision processor；模型卡标Kimi K3 License（不是自动MIT/Apache）。未下载权重；不判读许可法律效果 |
| [AgentENV](https://github.com/kvcache-ai/AgentENV) | 报告与官方仓库metadata确认开放MIT；不代表公开K3任务全集、hidden verifier或训练作业 |
| [MoonEP](https://github.com/MoonshotAI/MoonEP)、[FLA](https://github.com/fla-org/flash-linear-attention) | 报告给系统源码/PR入口（§5.1–5.2）；本次未逐代码复现实现 |
| [MiniTriton](https://github.com/MoonshotAI/minitriton)、[nano-kpu](https://github.com/MoonshotAI/nano-kpu) | §7案例成品入口，不是K3训练脚本 |
| 九专家/GRM/环境数据/训练配方 | 本次查看的报告、源码、模型目录未提供可重跑完整后训练的资产组合。不能把“开放权重”写作完整训练可复现 |

没有SFT/RL/MOPD总GPU-hour、GPU型号与拓扑、总token、teacher API费、每道有效题生产成本、总体sandbox成本；几百GPU实验与数千万创建计数无法换算总训练费用。

## 9. 证据边界集中表

| 未知项 | 已查范围 / 可确认的局部 |
| --- | --- |
| SFT数量、视觉比例、安全/偏好数据、epoch、packing | §4.1.1、附录F；只确认来源生成/验证/标注和序列化，不继承zero-vision |
| RL N/K/λ、τ/σ/b0估计、horizon硬上限 | §4.1.2、§4.2、§5.3；已有符号与特定预算reward规则，无数值完整表 |
| 行为/更新/参考策略、staleness、loss分母与mask | K3 §4.1.2、K2.5 §4.4.2、附录F、§5.3；继承目标有依据，跨迭代概率版本与cache invalidation不可复现 |
| 失败/截断/infra error | §4.1–4.2、§5.3；特定归零/负一已知，组统计、补采、梯度参与三者不能混答 |
| MOPD接口与配置 | §4.1.3、§5.3.1；token log-ratio/clip明确，其余teacher权重刷新、tokenizer、loss聚合/混reward未知 |
| 数据漏斗/污染/评分误差 | §3预训练过滤、§4.2任务合成、§6评测；预训练去重不等于后训练benchmark去污染，未给SWE完整漏斗 |
| 组件因果与成本 | 图8、表2–5、§6.4、§7；最终表现、趋势/单例有证据，同预算消融和总成本不足 |

事实：报告明文与明确引用依赖。作者解释：如harness多样性促进泛化、局部正则稳定stale data。阅读者推论：如未裁剪OPD与反向KL的关系、状态隔离分层。项目建议见下一节，仅候选；四者不能互相替换。

## 10. 旧稿纠错与 RepoHarness 项目一映射

### 10.1 旧稿之间的分歧怎么解决

| 旧说法/位置 | 本篇处理及证据 |
| --- | --- |
| 旧相关性笔记§1、矩阵§7.1：“没给GRPO/PPO/DIS或正则公式” | 对K3自身没有重印RL loss这一点成立，但漏掉明确K2.5继承入口及K3自己的MOPD Eq.15。补充“直接披露/引用继承/仍未知”三层，不把算法降为完全未知 |
| 旧长文§四：“可补全K3算法”、MuonClip及总token分母 | 核K2.5原式后保留组均值/概率比/局部mask解释；收紧为引用继承的路线，不承诺K3全配置或修复原式歧义。K2.5 N是生成token分母，K3 N是活跃prompt数 |
| 旧长文§五：“消除全局batch barrier”“部分异步” | 改为减少等待全部终止，仍有同步迭代生成暂停/优化阶段；同题K完整条件保留（K3 p.13） |
| 旧长文§六：“图32 medium 与正文low不一致” | 原图13(b) medium属于其他模型、K3仅max红星。撤掉这项伪冲突；附录F四档schema与三档实际训练也不矛盾 |
| 旧长文§八/九：终局advantage覆盖全部token、teacher只打采样token即可节省全词表成本 | 前者只能按已引用优化路线理解，K3具体mask/事件聚合未披露；后者描述了公式所需信息，不证明full logits不计算/不存储或真实通信实现 |
| 旧相关性笔记：AgentENV速度、E2B API及KVM要求与K3混列；07-24题名 | 环境代码专题说法不纳入本篇事实；本地PDF元数据07-27、arXiv提交07-27，旧稿题名日期不能当正式报告版本日期。其后追加澄清仍可独立保留 |
| 旧项目FA/slime映射、精度eligibility/平台候选 | 按09-07现状重映射miles；不据本篇恢复旧FA自建控制面、pending replay、microVM或额外staleness阈值 |

### 10.2 当前基线与少量候选

映射日期2026-09-07。只读主资料checkout，HEAD **`ce2009f879cf38071d7898a1387e01d4e27741d6`**；其 `reference/miles-rh2-integration` HEAD **`98a0272e4158b2c20e3a34d210c79b50159af0f6`**。以09-05简报〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕定位，结合更新的09-07设计建议〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕所列未闭合缺口。后者是咨询建议，不替代C包定案。未把本worktree基线当当前miles，未扩为全仓审计。

实际窄读：`reference/miles-rh2-integration/miles/rollout/fully_async_rollout.py::FullyAsyncRolloutFn` 是连续生成、与训练步解耦；`reference/miles-rh2-integration/miles/backends/training_utils/loss_hub/opd.py::apply_opd_kl_to_advantages` 接已有teacher logprob/预计算reverse-KL；本体 `rh2/src/repoharness2/adapters/miles/group_admission.py` 核全员KEEP_FULL、零方差与版本来源，staleness阈值归miles消费时；`rh2/src/repoharness2/grading/trusted_projection.py::build_trusted_scoring_projection` 拆出控制面，仅重放candidate路径。以上分别对应上述I/主仓commit的完整相对路径，是静态阅读，不宣称当前GPU路径已验证。

| 候选借鉴 | 外部依据 | 上游/我方增量/不适用及最小验证 |
| --- | --- | --- |
| 保留完整K与区分暂停/预算终止 | §4.1.2 | 当前miles+rh2已有组及版本边界；我方核真实黑盒harness的结束原因、完整组消费。小型同任务同预算测试，分别统计暂停续跑、预算失败、infra故障和有效消费；不把K3 λ方案改造为第二套scheduler |
| 公开诊断与隐藏评分分工 | AET、kernel、webdev | rh2实际应用增量：在既有fresh grader/可信投影上核具体任务控制面与合法替代解。用no-op/参考/不完整解/替代解/实际parser攻击样例，报告样例内误奖励/误杀，不宣称全库零风险 |
| token/成本与长度的实测 | effort、图8、§6.4 | 复用miles/SGLang现成采样与统计；我方按任务族看生成/训练token、discard、wall时间、成功率。是否引入负一预算reward须由本项目实验定，不因K3已有就修改奖励 |
| 有条件的OPD探针 | Eq.15、top-k负结果 | 上游已有OPD基础接口；rh2要证明teacher真实打到学生token、tokenizer/版本/mask正确，且不被GRPO零方差过滤吞掉。先窄实验对照SFT与OPD成本/收益；不默认九个专家或复制整个K3流程 |
| 第二harness评测 | §4.2.1、表3/4 | 设计层候选：相同checkpoint/任务/预算，比主harness与简单第二harness，排除工具/compaction差异；没有证据前不造白盒统一平台 |
| KDA缓存/共置/microVM/fleet | §5.1–5.4 | 属引擎/大规模runtime层，首版暂不适用；不改变八卡miles/SGLang放置、不造NVMe池、粘滞路由或AgentENV生产服务 |

简历叙事可引用该报告说明长程coding训练确有组完整性、评分与多层状态成本问题；**自己的贡献仍须由实际环境有效率、训练token覆盖、等条件吞吐/成本及held-out学习收益证明**，不能把K3规模、分数或公开组件归为RepoHarness成果。

## 11. 快速定位与关联

- 阶段/九专家/effort：本篇§3–4；原文p.12–14。
- 继承算法：本篇§4.2；K3 p.13 → K2.5 p.8 Eq.1；MOPD与draft是K3 p.14 Eq.15/16。
- 数据、verifier、各域reward：本篇§5；原文§4.2 p.14–17。
- 调度/cache/sandbox：本篇§6；原文§5.3 p.21–22；XTML在附录F p.46–47。
- 评测协议/失败/成本：本篇§7–8；原文§6–7 p.25–34。
- 已有关联：miles工程精读〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕、Qwen3-Coder-Next〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md`〕、KAT-Coder-V2.5〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md`〕。K2/K2.5整体另见来源R7；未完成第二批笔记只按任务编号关联，不造链接。

## 12. 独立检查与修订记录

主任务ID：`01a07827-1e44-7133-85d7-65aee3707e7f`；派工主任务ID：`01a077c4-9f0d-7ef0-a40a-688b42f1b294`。主线程实际配置 GPT-6 Astra / high（派工主线程已核验）；日期2026-09-07。

被审版本：固定初稿〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R13/R13_kimi_k3.draft_20260907.md`〕，371行，交审期间保持不变；归档副本中的相对链接按正式正文位置解释。唯一审查者为调度器实际返回的 canonical agent ID **`/root/review_r13`**，实际参数 **`model="gpt-6-astra"`、`reasoning_effort="high"`、`fork_turns="none"`**；工具未提供单独UUID，不用根任务ID冒充子ID。

独立审查报告〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/08_R13_review.md`〕已真实返回。审查者先读原文包含树与全部指定范围，再对照固定初稿，核对版本差异、关键公式/数字、全领域后训练、附录和项目映射；未发现重大算法错误或整块遗漏。三项发现全部于2026-09-07修订：R1摘要保留on-policy及学生采样含义；R2按原文重写cosine/WSD比较条件；R3保留费用图Mythos5与正文Fable5的身份边界。主作者回源定点核验并修订，未声称又做第二轮独立全文审查。

审查文件末尾记录逐项处置和链接核验。来源未披露项仍见§9；阅读审查不代替训练复现、GPU资格或项目设计批准。


---

## 文档 3 / 7：R4_minimax_m2_series.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/R4_minimax_m2_series.md`

# R4 The MiniMax-M2 Series：后训练与项目一精读

MiniMax-M2 系列以约 10B 激活的 MoE 为底座，经多领域轨迹生产、interleaved-thinking SFT 和分阶段的混合领域 CISPO RL，发展到 M2.7。报告最有用的部分是把真实工作空间、按产物选择 verifier、请求级策略动作及训练系统解耦放在同一流程中；覆盖 SWE、应用开发、terminal、搜索、办公、金融表格、幻灯片、推理、对话和角色扮演。Windowed FIFO 与 prefix tree merging 提供系统设计依据，但最高 40 倍是训练侧局部声明，不能换算成端到端 RL 加速。M2.7 多数评测提高，MMLU-Pro 却低于 M2.5；训练关键配置和若干图文口径仍未闭合。

导航：来源与覆盖 · 全流程与数据 · CISPO 与奖励 · Forge 与 token 边界 · 评测与负结果 · 项目映射和审查

## 1. 来源、版本和完整覆盖

正式标题为 **The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence**，机构/团体作者 MiniMax；个人贡献者见附录 A。阅读日期 2026-09-07。

- 本地主资料指定 PDF 是 **arXiv:2605.26494v1，2026-05-26，35 页**，见固定 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R4/source.pdf`〕及[官方 v1](https://arxiv.org/abs/2605.26494v1)。本文 p.n 使用 PDF 物理页，p.2 起与印刷页码相同；首页按 p.1 计。
- 当前官方版本是 **v2，2026-07-30，35 页**：[官方 v2](https://arxiv.org/abs/2605.26494v2)、固定 PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R4/source-v2.pdf`〕。已下载两版官方 TeX，并逐文件比较；仅 `app.tex` 改变，新增贡献者并将 Lunbin/Qunhong 的 Ceng 改为 Zeng。`main.tex`、`intro.tex`、全部 `section/*.tex`、`eval.tex`、`conclusion.tex`、图表资产和文献文件相同。PDF 提取文本差异仅首页版本水印和附录名单排版，见版本差异〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R4/version-diff.txt`〕。因此后训练、环境、infra、评测和全部附录均已覆盖当前版本；没有新增技术内容要另补。
- v1 TeX 入口〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R4/tex/main.tex`〕递归包含架构、预训练数据、后训练数据、SFT、RL、agent mechanism、评测、结论和 `app.tex`。源码用于核对公式及目录，**不是训练实现代码**。本次未查 Forge 内部源码；不借 M1 或配套博客补齐实现。
- N10 是 2026-02-13 独立官方文章，针对 M2.5；其 200k、样本吞吐、黑盒 reward 曲线等见N10 笔记〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N10_minimax_forge.md`〕，不合并为本报告实测结果。

先按原文结构阅读，再对照旧稿。覆盖表的页码也适用于 v2。

| 原文目录/图表 | 深度与主要内容 | 本文位置 |
|---|---|---|
| 摘要、§1，p.1–3；Fig.1 | 全读；系列定位、三项贡献、headline 结果，回看首页图 | §2、§7 |
| §2.1–2.2.1，p.3–4；Table 1 | 架构概要；细粒度专家与 MTP 小规模消融 | §2、§7.3 |
| §2.2.2，p.4–6；Tables 2–3 | 全读注意力选择及 SFT 后长上下文负结果 | §2、§7.3 |
| §2.3，p.5–7；Fig.2 | 全读 MTP 复制初始化、冻结/联合训练与推测解码 | §2、§6.4 |
| §3，p.6–7 | 概要；数据组成与 8K→32K→192K 延展 | §2 |
| §4.1.1 SWE，p.7–9；Fig.3 上半 | 全读六阶段与任务类型对应验证器 | §3.1 |
| §4.1.2 AppDev，p.9–11；Fig.3 下半 | 全读专家 query、prompt distillation、三层 AaaV | §3.2 |
| §4.1.3 Terminal-Gym，p.11–12 | 全读来源过滤、环境修复、hint 演化与难度校准 | §3.3 |
| §4.2.1–4.2.4，p.12–14 | 全读搜索、办公、金融/表格、幻灯片四条管线 | §4.1 |
| §4.3–4.5，p.14–16 | 全读推理、多轮对话写作、role-play/RLHF | §4.2–4.4 |
| §5，p.16 | 全读 SFT 与 interleaved-thinking 冷启动 | §2、§5.4 |
| §6.1.1–6.1.6，p.16–19；Eq.1–7 | 全读生成接口 MDP、CISPO、奖励、混合领域课程 | §5 |
| §6.2.1–6.2.6，p.19–23；Eq.8，Fig.4–6 | 全读 Forge 三层、黑白盒、Windowed FIFO、训练前缀合并、三项推理优化 | §6 |
| §7.1–7.2，p.23–26；Eq.9–10，Fig.7–8 | 全读思考状态保留、自演化系统及人机决策边界 | §5.4、§7.4 |
| §8.1–8.3，p.25–30；Table 4，Fig.9–10 | 全读全部评测、预算、系列演进、MLE 案例；原页核表与图 | §7 |
| §9，p.30–31；References p.31–34 | 结论全读；文献用于识别来源，不将引用论文视作已精读 | §8 |
| Appendix A Contributors，p.35 | 查全；只有名单，没有隐藏技术附录 | 本节 |

所有十幅图和四张表均已检查；Fig.1/9/10 的结果口径差别见 §7。未把排版残留或 TeX 注释当实验事实。

## 2. 底座、阶段链与模型关系

**原文事实。** M2 是 62 层 decoder-only Transformer，总参数 229.9B、每 token 激活 9.8B；hidden size 3,072，词表 200,064。每层完整注意力，48 query heads / 8 KV heads 的 GQA；256 个专家、每 token 选 8 个，sigmoid gating 与可学习专家 bias。它不是 MiniMax-Text-01/M1 的混合 Lightning Attention 架构，不能继承旧模型的配方。预训练总 29.2T tokens，包括 constant phase 19.9T 和 decay phase 9.3T；上下文从 8K 经 32K 扩展到 192K。语料涵盖 web、书籍、学术、代码与 QA，提升代码/数学/STEM 权重，长上下文用代码拼接、长 PDF 和主题相关 packing。（§2–3，p.3–7）

已知依赖关系为：

1. 预训练/continued pretraining 建立底座；MTP 初始一个模块，loss 权重 0.3 衰减到 0.1。continued pretraining 的 decay 阶段复制主模型权重扩成三个模块，先短暂冻结主模型、只训 MTP，稳定后联合训练。持续只训 MTP 的最终质量较差，随机初始化也比复制初始化收敛慢并暂时损害主模型。（§2.3，p.5–7，Fig.2）
2. 领域数据经 rejection sampling 与多阶段清理，构成 chat/reasoning/code/cowork 四类 SFT 语料；SFT 学习思考、动作、观察交替的轨迹，为 RL 冷启动。（§5，p.16）
3. RL 使用 CISPO，在**多个训练阶段中的每个阶段同时混合** reasoning/coding/agent/general，跨阶段调整领域比例、各领域 context 和难度。（§6.1.6，p.18–19）
4. M2→M2.5→M2.7 是公开 checkpoint 的系列演进。报告没有给每个版本逐阶段的 checkpoint 血缘、SFT/RL token 预算，也没有披露先训多个 policy experts 再融合的方案。轨迹由轮换的强 teacher 产生，不等于 token 级 OPD；MTP 的 top-K KL 是另一条辅助训练机制。（§4.2、§6.2.6、§8.2）

**作者解释。** 以高可信 reward 和数据覆盖提升真实任务能力，比仅扩大激活参数更重要。**阅读者判断。** Table 4 是最终系统的横向/纵向表现，未隔离 SFT、RL、数据、harness 或自演化各自贡献；不能把所有 M2.5→M2.7 提升归给 CISPO。

## 3. Coding / SWE / terminal 任务生产

### 3.1 SWE：真实 PR 到按任务类型验证

来源是采用宽松许可的公开 GitHub 仓库，采集 PR、关联 issue、diff 和测试；规则筛选已合并 PR 及相关测试。六阶段为采集过滤→逐 PR Docker 环境构建→任务类型 tagging/routing→测试 reward→模型检查题意与测试一致性→任务转换扩增。Fig.3 把最终数据集画为第七个节点，它不是额外的第七道过滤。（§4.1.1，p.7–9；Fig.3）

环境 agent 用专家知识和执行反馈迭代修复构建脚本。非 Python 环境较不可靠，难点包括 Java/Go/Rust/C++ 工具链版本、异构测试接口、仓库结构和依赖定位。报告称覆盖 **十余种语言**，但没有逐语言构建成功率。（p.8–9）

| 任务类型 | 构造/接受信号 | 必须保留的边界 |
|---|---|---|
| Bug fix | 提取 F2P/P2P；golden patch 通过后认定任务有效；solver sandbox 同时验修复与回归 | 没有完整 no-op/替代合法解/评分隔离协议 |
| Feature addition | 抽新功能测试点，要求 golden patch 通过 | 新测试可依赖新代码，不能机械套 F2P/P2P |
| Performance optimization | 用 P2P 测试确认行为稳定且性能差异稳定、显著 | 未给性能重复数、显著性阈值或资源控制 |
| Bug injection / commit merging | 注入额外 bug；合并相邻 commit/PR 增加多步复杂度 | 每次转换后重新验证的完整门槛未列 |
| SWE-Test | 让 agent 写在 pre-patch 失败、post-patch 通过的测试 | 训练动作是写测试，不能当修复轨迹统计 |
| Code review | 静态看改动、找潜在缺陷；第二个 LLM 检查一致性 | 原文明确不需要 runnable environment，只有近似可验证性 |

模型还检查描述与测试一致性，补足信息，使题目自洽可执行。这是质量改写，不是已证明不会泄漏参考解。报告末称每个 SWE instance 含题意、测试 reward 与 Docker，需与 code review 的无运行环境例外并读，不把概括推广到所有变体。（p.9）

### 3.2 AppDev：专家先验与可交互 verifier

AppDev 从零搭建完整应用，涉及 frontend/backend/mobile/desktop/simulation。专家贡献 **meta queries、种子分布、生成 system prompt、评价 rubric**。meta query 指定技术栈与架构约束，从 UI 库、CSS、构建工具、SaaS 与场景种子采样，高温 LLM 扩写具体需求；MinHash 去近重复，LLM 按技术栈合理性、功能可实现性、需求清晰度过滤，阈值未给。专家用下游质量反馈修整模板。（§4.1.2，p.9–10）

生成 prompt 包含功能完整、代码完整、内容真实性和审美指导，并鼓励先规格、TODO、测试、自验证与 skills 使用。作者举早期模型滥用模板式渐变背景为待矫正行为。**Prompt distillation** 的具体披露是采样时给完整指导、训练时选择性删除部分指导，使行为内化；没有公开 teacher/student KL 或 token 概率匹配目标。（p.10）

AaaV（Agent-as-a-Verifier）在 sandbox 部署应用，按专家 rubric 用工具主动交互，每项二值 pass/fail 并要求证据：

- 执行层：文件与语法、依赖安装、构建和服务启动、HTTP 状态、加载时 JS 错误；失败立即拒绝。
- 交互层：Playwright 检查元素、按钮/表单、核心流程端到端完成和状态变化。
- 视觉层：布局、层次、配色和设计质量。

各层总体通过率作为 rejection sampling reward，执行层是硬门槛。不是只看截图/静态代码的普通 judge；但 rubric 权重、阈值、误判率未给。该体系作为后续 RL 的任务/奖励基础，不能把所有采样过滤自动视作线上 RL 过程奖励。（p.10–11）

### 3.3 Terminal-Gym：先真实问答，再演化题目和环境

以完整 Stack Overflow 数据集为原始来源，按时间重建帖子，去掉无 accepted answer、低分、过长问答，按 tag 保留终端操作、系统配置、调试、脚本等。标注质量、任务类别、可验证性、复杂度、环境/执行特点，仅保留可脚本化、适合 terminal、可验证、Linux/Docker 相关且难度适中的帖子，清噪并选择一个高质量答案。时间范围、许可处理、各阈值未披露。（§4.1.3，p.11）

问答被改为结构化任务，明确环境、工具、输入输出与成功标准；按可测试性、完整性、清晰度分四档，仅留前两档。任务含自然语言指令、必要文件/脚本及预期终端行为。后续三阶段：（p.11–12）

1. Agent 合成 Dockerfile 与测试脚本；执行失败返回结构化诊断，迭代修复到通过或达到最大重试数。**确有重试上限，但数值未给；这是环境合成，不是 RL rollout 重试策略。**
2. 有控制地抽象/删除显式 hints、路径和预期环境输出，同时保持语义。所有变体用同一套 LLM 生成测试，避免只适配提示写法。作者称有效，但本文未给量化消融。
3. 排除过易任务，偏好 hints 少且 zero-shot pass rate 低的变体，并参考 reference solver 历史通过率与环境修复次数。solver 身份、每题重复数、接受区间未给；不能把低通过率当已证有效/可学习。

Anything2Docker 和 CVE-Factory 扩展是后续方向，本报告没有其完整新管线或独立实验，不能算已完成的额外精读来源。

### 3.4 数据漏斗与失败边界

| 对象 | 本报告实际可知 | 不可据此声称 |
|---|---|---|
| 原始仓库/PR、有效环境、验证任务、最终采样轨迹、RL 消费轨迹 | 流程和十余语言；各环节数量均未给 | N10 的十万量级不是这里的最终 SWE 题量 |
| 已知失败淘汰 | AppDev 执行失败；低质量 query；terminal 过易/不合规格任务 | 所有 infra 失败为 reward=0、整组丢弃或无限补采 |
| 环境合成停止 | terminal 达到最大重试限制后停止修复；后续处置未披露 | 达上限必定丢弃、隔离、保留或转人工 |
| 测试可信性 | golden patch、F2P/P2P、交互证据、题意核对 | 完整抗作弊、隐藏测试隔离、flakiness/替代解审核已实施 |
| 去重/污染 | SWE 宽松许可；AppDev MinHash；其他领域有清理 | 全局 repo/time split、benchmark 去污染、SWE 测试不可见性已证明 |

## 4. 其余后训练领域：完整保留

### 4.1 Cowork 的四条管线

共同原则是 runnable workspace、轮换强 teacher、刻意扰动 scaffold、按产物格式选择 verifier。对非机器可验证结果，多个候选在**推理/动作轨迹和最终产物**两轴作 pairwise 比较，再 rubric 严筛。这里的蒸馏是轨迹来源描述，teacher 名称/采样成本/具体学习目标未给。（§4.2，p.12）

| 领域 | 任务生产 | 通过标准与鲁棒性 |
|---|---|---|
| Deep search / open web | seed question 经 guide-and-rewrite 与实体隐去逐渐变难；开放报告题另设 rubric | 必须基于实际检索证据，不能以模型记忆替代；报告评价事实、透明度、不确定性、风险披露；轮换 teacher、扰动工具布局（§4.2.1，p.12–13） |
| Knowledge-worker office | 从 GDPval 筛 harness 可支持的 canonical tasks；按公开职业分类细分行业/地区/文化，再合成任务、真实支持文件、多精细程度 query 和产物规格 | rubric 含正/负行为、严重错误、地区适当性、推理深度；typed cleanup 去捏造数据/引用/实体（§4.2.2，p.13） |
| Financial tools | 先执行真实工具获得 trace，再反推由工具输出蕴含的任务与答案 | evidence-driven 合成，覆盖检索/计算/推理；多 scaffold 采样（§4.2.3，p.13–14） |
| Spreadsheet | seed workbook 上走原子操作，回收中间状态为新 seed；由轨迹推答案，再由答案推问题，改写表述/难度 | 执行产物、外部引擎重算公式、与 gold workbook 比 cell value；允许形式变体时改用 rubric/agent judge。覆盖一般/竞赛操作、PE/VC/M&A 建模、半结构资料还原（同上） |
| Slides | 两条流：源文档→不同粒度/语言要求的 deck；真实 deck→元素/页/全文件编辑，变化内容/风格/结构与复杂度 | teacher 偏好视觉质量；执行、agent 功能、规则布局、渲染后视觉评分叠加；混不同生成库避免工具库过拟合（§4.2.4，p.14） |

**污染边界。** 报告明确把 GDPval seed 用于训练数据，又评 GDPval-AA；没有给 seed 与测试去重/拆分的可审计说明。这个事实构成评测独立性缺口，不能据此直接判定发生具体污染。视觉 verifier 和多模态办公评测也不等于报告披露了 M2 视觉编码器或完整多模态后训练配方。

### 4.2 推理数据不只扩 query

§4.3（p.14–15）同时扩三轴：query 扩展覆盖稀缺难度与错误分析发现的弱技能；同题多条正确 response 扩大解法空间，作者观察收益主要体现在 OOD；固定训练算力下调 query/response 比例，并按阶段、难度饱和和当前弱项动态分配。质量检查分别覆盖 query 标记和 rollout 交叉比较、verifier 边界 case 分析、多模型答案分歧核错、推理轨迹 rubric。未给各轴数据量、预算、曲线或受控增益，不能推出“多 response 总优于新题”。

### 4.3 通用对话、写作与工具使用

§4.4（p.15–16）用高质量长 CoT 保留通用能力并冷启动 RL。写作强调风格，并接文件系统读写实际文档；简单 QA 在多个候选中做偏好质量选择；多轮强调跨轮一致性、指令/rubric 遵循和长上下文跟踪。工具增强与无工具样本并存，前者用代码解释器/搜索，后者保留独立推理；规则和模型 verifier 加系统质量检查。未单独披露 DPO 配方或 preference reward model 训练过程。

### 4.4 角色扮演、RLHF 与安全披露边界

§4.5（p.16）将 role-play 表述为用户偏好条件下 Worlds×Stories 的长程生成，保持物理、叙事和风格一致性。Role-Play Bench 用多轮 self-play 对失角色、逻辑错误等具体失配扣分，作者称离线指标与线上互动相关。数据来自风格多样 expert 的大规模 self-play，四轴 dispersion sampling、Best-of-N 和周期性片段 judge 重写防模式坍缩；**四轴具体定义未在本报告展开**。

该领域明确提 RLHF：从真实产品隐式/显式反馈出发，用因果推断和分层去偏降噪，监测 entropy 防 reward hacking；没有给 estimator、干预设计、reward 数值或效果表。安全相关还散见真实证据要求、去捏造、CVE 方向和自演化 harness guardrails；**无独立全面安全对齐、拒答、红队评测或安全 RL 配方章节**。不能将 persona 对齐等同完整安全对齐。

## 5. 训练目标、token 与信用分配

### 5.1 动作边界与 episode

把 LLM 当 policy，模型生成接口之外的工具、memory、上下文变换、分支和 sub-agent 调度都归环境。一次 action 是**一次 LLM completion**，可含 reasoning、工具调用、CM 请求或 sub-agent 通信；state 是本次实际呈给模型的内容，下一状态为 `s[t+1]=f_trans(s[t],a[t],o[t])`（Eq.1，p.17）。训练原子样本为 `(s_t,a_t)`；奖励传播、advantage 和信用分配仍可按完整 episode 计算。一次请求一条样本不代表每次请求具有独立终局 reward，也不要求把重写后的历史拼成一条虚构 append-only tape。（§6.1.1–6.1.3，p.16–17）

### 5.2 CISPO 原式和不完整处

以下按 p.17 Eq.2–3 与 TeX〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/R4/tex/section/post_training_rl.tex`〕记录，最大化目标为：

\[
J_{\rm CISPO}(\theta)=\mathbb E_{(q,a)\sim D,\{o_i\}_{i=1}^G\sim\pi_{\theta_{old}}(\cdot|q)}\left[
\frac{1}{\sum_{i=1}^{G}|o_i|}\sum_{i=1}^{G}\sum_{t=1}^{|o_i|}
\operatorname{sg}(\hat r_{i,t}(\theta))\hat A_{i,t}\log\pi_\theta(o_{i,t}|q,o_{i,<t})\right],
\]
\[
\hat r_{i,t}=\operatorname{clip}\left(\frac{\pi_\theta(o_{i,t}|q,o_{i,<t})}{\pi_{\theta_{old}}(o_{i,t}|q,o_{i,<t})},0,1+\epsilon^{IS}_{high}\right).
\]

`G` 是每 prompt 的 rollout trajectory 数，值未给；`|o_i|` 是原文所称 trajectory token 长度，`sg` 阻断 importance weight 的梯度，`θ_old` 是采样策略而非另一个 KL reference model。**clip 对象是 IS 权重，然后 stop-gradient 后乘 log-prob 梯度**；不是 PPO 对 surrogate 的 min 分支，也不是直接把该 token 的梯度清零。下界 0，上界 `1+ε_high^IS`；具体 ε 未给。

分母为组内全部 `|o_i|` 之和，**不是每条轨迹先均值再平均**。但 §6.1.3 的请求级样本如何组织到 Eq.2 的轨迹级 `o_i`、thinking/工具观察/重写后重复前缀的 mask、实际 loss 分母是否按有效 token 计，报告没有实现说明。不能把该排版公式当完整 train tensor 合同。

p.18 Eq.4：
\[
\hat A_{i,t}=\sum_{p=t}^{T}r_p-B_i.
\]
`B_i` 仅描述为 trajectory-level baseline，**不是已经披露的 GRPO group mean/std，也不能断言有/无 learned critic**。Eq.2 的 `t` 是 token 索引，Eq.4/奖励讨论又按 step 使用；completion/工具步奖励到每 token 的传播规则未展开。作者称 stop-gradient 避免 second-order terms；严格数学上这里只是去掉对重要性权重求导的乘积项，未提供 Hessian 算法，不宜照抄为二阶优化结论。

### 5.3 Reward：过程、完成速度、任务表现

§6.1.5，p.18 Eq.5–7：
\[
r_t^{speed}=h(T_{completion}/T_{baseline}),\qquad
r_t=\alpha r_t^{process}+\beta r_t^{speed}+r_t^{perf},\qquad
G_t=\sum_{\tau=t}^{T}\gamma^{\tau-t}r_\tau.
\]

过程信号罚语言混用、工具格式错，也奖励结构清楚的中间 reasoning；task performance 信号由 §4 的领域 verifier 支撑。`h` 单调递减，completion 是 rollout wall-clock，baseline 是参考时间，鼓励工具/子代理并行。`h`、参考时间如何估计、是否控制任务难度与 infra 拥塞、α/β、重复计入速度的时点都未给。

**原文内部未闭合：Eq.4 是无折扣求和，Eq.6 有 γ；未给 γ 值或解释二式连接。** 不擅自设 γ=1。Reward-to-go 是未来奖励求和，baseline 是控制变量；不能从文字“归一化/稳定”补出组内标准化。也没有 dense reward 或 speed reward 的独立消融、正确率/速度帕累托曲线。

### 5.4 混合领域课程与思考状态

§6.1.6（p.18–19）每个阶段同时取 reasoning/coding/agent/general，早期重推理与通用，后期提高 coding/agent 比例；各域 context 逐步变长，难度转向更难实例。作者将其解释为降低灾难遗忘与顺序域训练的负迁移。没有给比例/阶段数，且 Table 4 的 MMLU-Pro 退化限制了“全面保留”的强结论。

§7.1（p.23–25，Eq.9–10，Fig.7）的 interleaved thinking 为 `(r1,a1,o1,…,rT,aT,oT)`，其中 `r` 在此是 reasoning、不是前文 reward。下一轮 history 保留完整 assistant thinking/action 和 tool observation，使模型可计划、执行、反思；对照是把思考全放前面，或每轮丢掉历史 thinking。论文说做了 stripping 消融却没有数表，末段“stripping … yielding consistent gains”字面与上下文支持保留思考的方向存在歧义，**无法提取明确效应量或无歧义的消融方向**。Fig.7 是序列示意，并非消融结果图；其 “No Thinking” 列仍画 Final Thinking，标签也不能按字面扩成严谨实验定义。

## 6. Forge：调度、前缀和推理

### 6.1 架构与黑白盒支持

§6.2.1 Eq.8 将目标写成 throughput×sample efficiency，约束 update variance 与收敛误差；前者是单位时间处理 token；R4 未进一步定义 SampleEfficiency。作为术语补充，N10 §1 将它解释为每样本带来的平均表现提升，此定义不计作 R4 单独披露。它是系统设计目标，δ/ε/J* 无操作化数值，不是已证明的收敛定理。（p.19–20）

Fig.4（p.20）分 Agent Side、Middleware、Engines 三层。请求流为 **Agent↔Gateway↔Rollout Engine**：Agent 执行环境，Gateway 路由 completion，Rollout Engine 生成并返回响应。训练流为 **Gateway→Data Pool→Train Engine**：池异步收集完成请求与 reward，Train Engine 消费数据做 CISPO；另由 **Train Engine→Rollout Engine** 同步权重。图示 completion 里有 `prompt_ids`、`response_ids`，reward 有 outcome/process；没有给完整捕获协议。（§6.2.2）

白盒允许框架知道 CM 逻辑并重建训练状态；黑盒只需将实际请求送 Gateway，框架读取每次真实 context，不要求 agent 内部循环可见。支持 memory compression、history rewrite、hierarchical multi-agent。作者称数百 scaffold 和数千工具格式已验证；没有逐 scaffold holdout 结果。（§6.2.3，p.21）

原文白盒段使用“backpropagate through context transformation”表述，但没有可微 CM 计算图，且前文把 CM 放在环境边界。只能确认训练暴露于 CM 后状态，**不能据此宣称梯度穿过任意字符串重写或外部工具执行**。黑盒接入也不意味着 prompt token 重分词、loss mask 和行为概率自动正确。

### 6.2 Windowed FIFO 精确取样对象

§6.2.4（p.21–22，Fig.5）针对长短任务完成时间从秒到小时：严格按原顺序取样会队头阻塞，完全先完成先消费会先偏短/易样本、后集中难样本。作者提出训练端只从**按生成提交次序排列的队列**中一个窗口取**已经完成的轨迹**：`Q=[T0,…,T(N−1)]`，头为 i，允许索引 `[i,i+W−1]`。窗口内可任取已完成项；窗口外完成也不能越界；队头被消费才推进窗口。W 小趋 FIFO，大趋全局 greedy。`W=0.3N` 是例值/作者实践描述，未给扫描曲线。（正文）

例如 i=0、W=4 时 1/2/3 可先于 0 被取走，但 4 即便完成也不能进训练；若 0 长时间不完成，取尽窗口内短项后仍会等待。**此例是阅读者展开原规则**：它限制乱序，牺牲部分吞吐保住队列分布；不是按长度排序、调度最短推理请求、保证每个 batch 精确同分布或直接删除长任务。

Fig.5 的具体例子 N=8、W=4，画出 0–10 除 7 外已训练，此时仅 7 留在可见窗口，11 以后仍阻塞；标注最大乱序 3=`4−1`、max off-policy lag 10=`8+3−1`，起始样本来自 model version 0。该图确实涉及版本，但未定义一次消费/optimizer update/权重发布的对应关系，也没给 partial rollout 的 token-version 计数。**不能把示意数字 10 迁移为任意流水线通用 staleness bound。**

### 6.3 Prefix tree merging 与 40× 的分母

多轮/分支请求拥有共同 token prefix，逐请求独立 forward 会反复计算相同历史。§6.2.5（p.22–23，Fig.6）先合并为树，公共 prefix forward 一次，各响应分支各算；再依 metadata 还原每个样本、独立算 loss。图中 `seq2` 同时作为一个 completion，又成为下一 completion 的前缀，展示的是计算复用。

作者称与独立样本训练数学等价、最高 **40× training speedup**，且节省内存。但没有列 baseline 实现、GPU/数量、序列长度/重合率、batch、耗时明细，不能声称相对 miles/SGLang 的 40× 或端到端训练 40×。**阅读者推论：** 等价要求 token/位置/因果可见性以及 loss 权重语义保持一致；只因文本相同就合并、或顺便改变共享 response 的梯度计数，都不是文中所声称的等价变换。无需由 rh2 自研 attention kernel。

### 6.4 三项推理优化

- **MTP speculative decoding**：RL 过程中用 top-K KL 持续协同训练 draft modules，跟上 policy 分布，保持接受率。K、KL 方向、归一化/尾部处理、系数、梯度流入主 policy 与否没有展开。不能等同领域 teacher→student 的 OPD。（§6.2.6，p.22–23）
- **Prefill/Decode 分离**：两阶段分别调度、用适合各自计算特点的并行布局，减少 MoE 混合排程干扰；没有具体 TP/EP/DP 或硬件映射。（p.23）
- **全局 L3 KV cache**：DFS 支撑，配 group-level rollout，路由权衡排队延迟和 cache 搬迁成本；未给 cache 一致性、eviction、命中率或速度实测。（p.23）

训练 context 上限描述为 192K，不能当单次 completion 的 max_new_tokens；也未给训练轮次/工具次数/wall-clock 限额。版本发布频率、backpressure 上限、retry/cancel、partial rollout、过期丢弃/重算、跨版本 token 处理统一列于 §8。

## 7. 评测、消融、负结果和自演化

### 7.1 评测条件优先于分数

§8.1（p.26–27）默认 temperature=1.0、top-p=0.95；M2.5/M2.7 开 thinking/interleaving；Claude Opus/Sonnet 4.6 用 extended thinking，GPT-5.4、Gemini-3.1-Pro 用 high effort。开头概称所有 agent benchmark 共用 scaffold，后文**明确例外**如下，不能仅引用前半句：

| 评测块 | 实际设置和预算 |
|---|---|
| SWE-bench Pro、Multilingual、Multi-SWE、NL2Repo | 内部设施；Claude Code 统一 scaffold、覆盖默认 system prompt；**GPT-5.4 使用 native CodeX**；4 trials 平均。scaffold 版本、token/时间 cap 和前三者具体 split 未给 |
| Terminal-Bench 2.0 | Terminus-2 XML，`zai-org/terminal-bench-2-verified`；8 vCPU/16GB、2h timeout，4 trials；未重评的 baseline 引官方结果。未给该 dataset revision |
| VIBE-Pro / HyperTask | 前者 container 部署，用 Claude Code verifier 看交互和视觉、3 trials；后者每题约 100 条 feature/step requirement、专家 rubric、3 trials |
| BrowseComp / Wide Search / RISE | WebExplorer，小改 system prompt/tool description；token 使用超过最大 context 的 30% 时**删除全部 assistant replies 和 tool returns**；RISE 再启 Playwright。不是“保留全历史”的评测 |
| GDPval-AA / office | GDPval-AA 为 Artificial Analysis 对开放 GDPval 的再评；MM Claw、MEWC v2、Finance Modeling Pro 专家 rubric、3 trials；MEWC v2 为内部 100 道困难题 |
| 通用七项 | Artificial Analysis Index v4.0，无工具单样本 pass@1：AIME 2026、GPQA-Diamond、SciCode、IFBench、AA-LCR、HLE、MMLU-Pro |
| MLE Bench Lite | 22 competitions，每题 single A30 sandbox 24h，内部 self-evolution scaffold（Bash+WebSearch），选择最佳 validation checkpoint 在 test 评 medal；最终均值来自 3 次独立 24h trials，见 §7.4 |

所有这些是**评测预算**，不是 RL 训练配置；未报告误差条/置信区间。不同 harness、官方引用结果与内部 rubric 限制横向因果比较。

### 7.2 全部主结果与系列曲线

下表为 Table 4（p.28）两列 M2 结果；保留全域而非只选上涨项目。单位/指标按各 benchmark，不把 rubric 分数统一叫 pass@1。

| Benchmark | M2.5 | M2.7 | 阅读定位 |
|---|---:|---:|---|
| SWE-bench Pro | 55.4 | 56.2 | GPT 57.7、Opus 57.3；scaffold 有例外 |
| SWE-bench Multilingual | 74.1 | 76.5 | Opus 77.8 |
| Multi-SWE-bench | 51.3 | 52.7 | 此表最高；非所有 coding 表最高 |
| NL2Repo | 26.6 | 39.8 | 内部 benchmark |
| Terminal-Bench 2.0 | 51.7 | 57.0 | GPT 75.1；并非接近所有 baseline |
| MLE Bench Lite | 51.5 | 66.6 | 与 Gemini 66.6 持平；Opus 75.7 |
| VIBE-Pro | 54.2 | 55.6 | Sonnet 56.1，Opus 55.6 |
| HyperTask | 59.4 | 67.6 | 内部长程 AppDev |
| BrowseComp | 76.3 | 77.8 | Gemini 85.9 |
| Wide Search | 70.3 | 75.2 | 搜索 |
| RISE | 50.2 | 64.3 | 内部，浏览器 |
| GDPval-AA | 35.0 | 50.0 | 训练 seed 独立性缺口见 §4.1 |
| Toolathlon | 38.3 | 46.3 | 异构工具 |
| MM Claw | 57.6 | 62.7 | 内部办公 |
| MEWC v2 | 49.8 | 63.3 | 100 道内部困难题 |
| Finance Modeling Pro | 33.8 | 57.0 | 内部金融模型 |
| AIME 2026 | 87.2 | 94.2 | 与 Fig.9 AIME 2025 不同 |
| GPQA-Diamond | 85.2 | 89.8 | 无工具 |
| SciCode | 43.0 | 47.0 | 无工具 |
| IFBench | 72.0 | 76.0 | 指令遵循 |
| AA-LCR | 65.0 | 72.0 | 长上下文 |
| HLE | 19.0 | 28.0 | no-tool 子集 |
| MMLU-Pro | 85.2 | 81.8 | **下降 3.4 点** |

Fig.9（p.29）另选十一项绘 M2→M2.5→M2.7：Multilingual 56.5→74.1→76.5；Multi-SWE 36.2→51.3→52.7；MLE 40→51.5→66.6；VIBE-Pro 42.4→54.2→55.6；BrowseComp 44→76.3→77.8；Wide Search 62.3→70.3→75.2；Toolathlon 18.8→38.3→46.3；GDPval-AA 34→35→50；**AIME 2025** 78→86.3→94；GPQA 78→85.2→89.8；AA-LCR 61→65→72。其 BrowseComp M2 数取 HF 官方分数，因此正文“全在我们 scaffold 下”也有例外。十一项全升不等于所有评测全升，MMLU-Pro 不在这张精选图中。

Fig.1（p.1）是另一个 headline 图，含 Artificial Analysis 汇总指数 M2.7=50/M2.5=42，而 Table 4 未列这一行；不是将 Table 4 七个通用分数简单平均的结果。原图文字密集，使用 Table 4 核主数字，不能靠 PDF 文本抽取的交错标签重建名次。

### 7.3 确有负结果，因果证据有限

- **Hybrid SWA**：§2.2.2，Tables 2–3（p.4–6）在预训练及 SFT 后比较 full attention 和 hybrid SWA。预训练 RULER 128K CWE 90→72、MTOB e-k ChrF 44.8→27.2；但 MMLU 85.5→85.6、MATH 60.3→60.3，并非所有行下降。SFT 后 SWE-verified 54.7→50.2、Terminal-Bench 26.7→23.8、BrowseComp-zh 32.8→28.7、telecom 32.5→21.0；另一方面 IFBench 23.1→27.2、XBench-ds 58→63、retail 62.3→67.5。作者强调超过 32K 的退化更明显，不应写成 SWA 所有场景更差。
- **MTP 的限度**：Table 1 是 **17.8B total / 2B activated、500B tokens** 的消融，不是 229.9B M2 的 RL 消融。Baseline→MTP 的 MATH 19.6→21.3、HumanEval 29.7→30.1，但 MMLU 39.8→39.7；作者“consistently improves”有小例外。细粒度专家 32/top2→128/top8，在同规模预算下 MATH 达 24.1、HumanEval 32.5；不能与 MTP 两种独立列相加收益。
- **联合 MTP 优于始终冻结**有定性报告，无数表；训练 CM 分布、混合领域 RL、防 reward hacking、interleaving 和 Windowed FIFO 也没有完整独立受控消融。严谨结论是设计动机与作者观测，不是组件收益已确证。
- **泛化和遗忘**：Table 4 MMLU-Pro 下降 3.4 点；最明显的 agent/office 提高与新数据同时发生，不能据此推出混合 RL 消除了遗忘，或新数据是唯一原因。

### 7.4 自演化是运行工作流，不是新的自更新 loss

§7.2（p.24–26，Fig.8）描述由内部 M2.7 生成的 harness，作者称零人工代码，含层级 skills、persistent memory、guardrails、eval infra。人配置目标、对话引导、审查并决定下一轮；agent 自动看 logs/profile、诊断指标、改代码/配置。作者估计承担日常迭代工作量 **30%–50%**，未披露计量方法。另有**100 轮**内部 programming scaffold 改进循环，出现 loop detection 和更好参数组合，内部评测性能提高 **30%**；基数、相对/绝对口径和 heldout 协议未给，不能写成 +30 个百分点或纯模型权重收益。

§8.3（p.29–30）MLE 案例用 memory file、自我批评和后续优化方向推进迭代。最佳 run 得 9 金+5 银+1 铜，即 15/22≈68.2%；正文最终报告是三个 trial 的 **66.6% 平均 medal rate**，两者分母口径不同。每任务每 trial 配一张 A30 的 24h 沙箱，22×3×24=1,584 A30-hour 只是**按满额运行计算的评测沙箱上限预算**，不含 LLM 服务，非实际花费或 M2 权重训练成本。

**Fig.10 的未解口径。** 横轴为 Maximum Cumulative Effective Runtime (hours)，延伸超过 24h；蓝色 Any Medal 曲线末段约 70%，红色 Any Medal (Real / CV-selected) 约 50%上下，后者并非单调上升。图未明确这些曲线如何对应三个 trial、22 个任务和 Table 4 的 66.6%；不能把最高蓝线当可部署 validation 选择结果，也不能用该图“证实 66.6% 单调累积”。v2 未改图或解释。正文声称最佳 validation checkpoint 选 test medal，仍需作者提供原始运行/选择记录以对齐。

这些案例说明固定模型可执行 ML 工程、修改 scaffold；没有说明 MLE 评测期间持续更新 M2 policy 权重，也没有消除人类的实验选择角色。

## 8. 成本、开放资产与未披露项

本次实际获得的是 v1/v2 报告、TeX 与图表。论文没有给可运行 Forge trainer、完整 post-training dataset、环境镜像清单或配置入口；没有沿官方模型仓库检查训练可复现性，故不对模型仓库全部资产作否定断言。模型开放与训练过程开放必须分开。

| 缺口 | 已查范围 | 对复现/项目的影响 |
|---|---|---|
| 每阶段题量/轨迹量/token、teacher 型号、采样数/温度、SFT optimizer/LR/batch/epochs | §4–5、附录 A | 不能估环境漏斗、teacher 成本或重跑 SFT |
| CISPO G、ε、baseline、γ、reward 尺度与权重、loss mask/分母实现、KL/entropy 主 loss、更新次数与 LR | §6.1 Eq.1–7；§4.5 | 公开目标不等于公开训练语义；role-play entropy monitoring 不等于主 policy entropy loss |
| 行为 logprob/token 捕获、tokenizer 版本、重分词、CM 后遗失/复用 token、分支梯度归属 | §6.1–6.2，Fig.4/6 | 黑盒网关抽象不能替代逐 token 对齐 |
| 超时/坏环境/截断奖励、group 统计/梯度/补采、重试/取消、partial rollout/resume | §4.1、§6.2、附录 A | terminal 环境合成重试不回答 RL 终止语义 |
| 发布频率、weight span、lag 的单位、过期丢弃/重算、buffer 上限 | §6.2.2–6.2.4，Fig.5 | 有 sync weights 示意，不能补为“每 token 用最新权重” |
| GPU 类型/数量、并行/精度、训练时长、总成本、40× baseline 与 workload | §2、§5–6、§8 | A30 是 MLE 评测；不能用于估 10B 激活训练成本 |
| 任务切分/去污染、hidden tests/抗作弊与替代解、评测原始样本和方差 | §4、§8、附录 A | GDPval seed、内部 rubric 和跨 scaffold 比较均有限制 |

旧稿更正：原证据矩阵 §7.4〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕基本阶段结论可保留，但“p.12–22”不足以定位 SWE/AppDev（p.7–11）、推理/role-play、思考状态与评测（p.23–30）；应以本笔记逐节定位替代。M1 的 group-relative advantage 不能挪给这里未定义的 `B_i`。矩阵其他段的“MiniMax 80K”不能作为本报告训练 hard cap，R4 明确是 192K context 能力范围。原infra 映射〔仓库引用：`docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md`〕关于上游承担 prefix/PD/KV 的职责原则可保留；这些不是 Forge 已接入 rh2 或已保证 token 完整性的证据。

## 9. 对 RepoHarness 项目一的有限映射

映射日期 2026-09-07。已读当前简报〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕（更新 2026-09-05）与项目一建议〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕（2026-09-07，咨询建议）。实际主资料 HEAD=`ce2009f879cf38071d7898a1387e01d4e27741d6`；miles 集成目录 HEAD=`98a0272e4158b2c20e3a34d210c79b50159af0f6`，来自实际目录读取，不是本 worktree 默认分支。

本次窄查确认：`reference/miles-rh2-integration/miles/rollout/fully_async_rollout.py::FullyAsyncRolloutFn` 持续生产完成组；同 commit 的完整相对路径 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py::DefaultDataBuffer` 用已完成组 FIFO，put 做 ABORTED/dynamic filter，get 做 consume-time staleness、按组最老行为版本判定。它不是按原派发队列建立的 Forge Windowed FIFO。主仓 `rh2/src/repoharness2/adapters/miles/canonicalize.py::canonicalize_sample` 与 `rh2/src/repoharness2/adapters/slime/capture_wire.py::CaptureRegistry` 是现有转换/捕获接口；这里只核职责入口，未重新审计整条 token 链。

| 候选借鉴 | 已有职责/我方增量 | 最小验证及限制 |
|---|---|---|
| 真实任务应绑定可执行环境与任务类型相符 verifier（§3） | rh2 的环境/评分可信入口；并非重造模型训练框架 | 先做选定 taskset 的 golden/no-op/替代解和失败分类验证，量从候选到消费的漏斗；不能照搬未公开阈值 |
| 每次真实请求 state 与生成 action 成对（§5.1） | 上游 rollout/session 与 rh2 现有捕获/转换共同承担 | 固定真实 Claude Code rewrite/compaction/fork trace，比生成动作→训练 token 覆盖、mask 和权重；不能用“黑盒兼容”代替证据 |
| 排程影响所消费任务分布（§6.2） | miles 已有异步队列和 consume-time staleness；rh2 候选是测偏差 | 同一 trace 按派发/完成/消费次序看任务族、长度、耗时、lag、丢弃分布；测出问题后才考虑 window，保留整组准入 |
| 训练前缀复用（§6.3） | attention/训练后端承担；rh2 不写 kernel | 先量真实请求重复率，固定 workload 比 forward/loss/梯度等价和成本；40× 不是预算承诺 |
| 多领域与 artifact verifier（§4–5） | 可供未来 taskset 扩展；office/role-play 暂非首训内容 | 当前 SWE 闭环完成后才用同模型/预算看迁移与遗忘；不扩成首训全域 RL |

可用于项目叙事的是“以真实 harness 请求和可执行 verifier 建立训练证据链”的外部动机；rh2 的吞吐、学习增益、跨 harness 泛化都要自己的实测。未批准新的 reward、调度器、CM 策略或 loss。

## 10. 独立检查与修订记录

主任务 ID `01a07827-1e44-7133-85d7-658445c04597`，实际配置 `gpt-6-astra / high`（派发主线程已核验）。独立审查和处理记录见09 审查〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/09_R4_N10_review.md`〕。交审固定副本为 `sources/R4/R4_minimax_m2_series.draft-20260907.md`；来源版本 v1+v2，初稿日期 2026-09-07。独立审查者 ID `01a07831-76f5-7ae1-8211-2dc348e68bbd`，实际 `gpt-6-astra / high`、`fork_turns="none"`，父子关系与配置已从会话日志核实。2026-09-07 收到完整审查后修订 F1–F3：§3.4 区分重试停止和淘汰，§6.1 标注 SampleEfficiency 释义来自 N10，并拆开请求/训练/权重同步流。无整块后训练遗漏或重大算法、数字错误；残余未知与图文不一致仍保留。固定初稿未改，同一审查者已定点复核 F1–F3，全部关闭；此复核不是第二轮全文审查。最终核验记录见审查文件。


---

## 文档 4 / 7：N10_minimax_forge.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/N10_minimax_forge.md`

# N10 Forge: Scalable Agent RL Framework and Algorithm：后训练与项目一精读

Forge 是 MiniMax 对 M2.5 内部 agent RL 系统的官方介绍。文章把吞吐、训练稳定性、agent 灵活性放在一起设计：Gateway/Data Pool 解耦真实 harness 与训推引擎；Windowed FIFO 限制训练消费的乱序范围；prefix tree merging 减少训练中的重复前缀计算；CISPO 配合过程、时间及任务奖励。最明确的工程启发是“实际进入训练的分布和 token 语义必须一起看”。但文章没有公开完整训练配置、失败/重试合同或可运行 Forge 代码；40× 和百万量级日处理样本也没有足以复现实验的分母。黑盒 reward 图呈总体改善与明显波动，不能当严格收敛或未见 scaffold 泛化的证明。

导航：来源与覆盖 · 系统与黑白盒 · Windowed FIFO · 前缀与推理优化 · 算法与奖励 · 证据边界和项目映射

## 1. 来源、版本、日期与覆盖

- 正式标题：**Forge: Scalable Agent RL Framework and Algorithm**。作者为 MiniMax 官方 HF 组织 `MiniMax-AI`，页面共同作者列 Hyn、zhi zhang、Jiayuan Song、Da Chen、xkc、Yaoyao、kennyKK、zpysky1125；它是官方组织发布的 Community Article，不是独立同行评审论文。
- [官方文章](https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm)，页面日期 **2026-02-13**。2026-09-07 读取的 HTML JSON-LD 标明 `datePublished/dateCreated=2026-02-13T04:18:07.300Z`，`dateModified=2026-02-13T08:46:39.885Z`。只确认这些元数据，未获得当天编辑前版本，不能猜具体修改内容。
- 固定 HTML〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/forge.html`〕、提取文字（含公式原始 TeX）〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/forge.txt`〕。本文用原网页 §号和图名定位；网页四张技术图均已实际目视，封面也已检查，见下表。HTML 正文未发现 tabs、details、select、iframe/video 或交互案例；不把评论回复折叠当技术内容。
- 本文指向 **M2.5 的 Forge**。独立来源 R4（2026-05-26 v1、2026-07-30 v2）的更多 MDP/奖励/数据细节见R4 笔记〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R4_minimax_m2_series.md`〕。R4 两版技术内容未变；**本篇不会用后来的报告悄悄补全早期文章**。
- 未精读 M2.1、M2-Her、M1、Magi Attention 配套论文或模型仓库；链接或名词只作导航，不能增加成品数量或继承配置。

| 原文章节 | 独立阅读覆盖 | 本文位置 |
|---|---|---|
| 引言和封面 | M2.5、十万量级 scaffold/environment、200k、百万量级 samples/day | §2、§7 |
| §1、§1.1–1.3 Problem Formulation | Effective Agent Training Yield、token 一致性、长尾/分布、稀疏信用、执行速度 | §2 |
| §2.1 RL System Design；`arch` 图 | Agent / Middleware / Engines 及同步权重、数据记录 | §3.1 |
| §2.2 White-Box CM | context rot、训练/推理 CM 分布差异、状态转移 | §3.2 |
| §2.3 Black-box；`black_rl` 曲线 | OpenCode、Truncate BC、无侵入接入、实验曲线限制 | §3.3、§7 |
| §3.1 Windowed FIFO；`window` 图 | 队列、窗口、局部 greedy、全局阻塞、lag 例子 | §4 |
| §3.2 两个子标题；`tree_merge` 图 | 重复计算、前缀树、attention primitives、还原 loss、40× | §5.1 |
| §3.3 Extreme Inference Acceleration | MTP/top-K KL、PD 分离、全局 L3 KV | §5.2 |
| §4.1 RL Algorithm | mixed-domain CISPO、完整公式、baseline/奖励项缺口 | §6.1 |
| §4.2 Dense and Efficiency-Aware Reward | 过程/时间信号、reward-to-go | §6.2 |
| §5 Conclusions | 系统联合设计的作者主张，无附录 | §7 |
| 文末推荐与评论 | 仅检查发布/资产线索，非额外方法来源 | §7.3 |

这是一篇系统/算法短文，没有另外的 SFT、数据生产或安全附录；没有因只关注 SWE 而忽略其 Reasoning/General QA 内容。

## 2. 要解决的问题与规模口径

文章引言称 M2.5 构建过程中经过**超过十万种不同真实 agent scaffolds 与 environments**，context 可达 **200k**，每天处理**百万量级 samples**。这几个量不能互换：没有 scaffold 与 environment 各自数量、唯一题数、每题采样数，也没说明 sample 是一次 completion、整条 episode、入池对象还是最终消费对象。百万 samples/day 不能除成已证实的训练 trajectories/s，更不能当 RL 总训练样本量。

§1 定义概念目标：
\[
\max_\theta J(\theta)=\operatorname{Throughput}(A)\operatorname{SampleEfficiency}(A),
\quad A\in\Omega_{agent},\quad E[\operatorname{UpdateVariance}]<\delta,
\quad E[\|J^{(T)}-J^*\|]<\epsilon.
\]

Throughput 指原始 token/s，受 rollout、training、data processing、I/O 四段制约；sample efficiency 是平均每样本的性能增益，取决于任务分布/质量、算法和 off-policy 程度。公式是设计目标和代理约束，未给 δ/ε、J* 的估计，也不是实测“有效产出”指标。

三类冲突为：（§1.1–1.3）

1. Agent 与训练共享内部状态会限制 CM、多 agent 等循环；TITO（Token-In-Token-Out）要求 agent 深度理解 token，复杂 CM 时高层逻辑与训练 token 难保持一致。作者批评这种耦合，**不是证明 token 一致性从此无需验证**。
2. 完成时间从秒到小时。按派发顺序严格 FIFO/同步会被最慢任务卡住；greedy/FFFO 先完成先取则可能先偏短/易、后集中难任务，引发分布偏移与梯度波动。短耗时与“容易”是作者描述的相关性，不是普适定义。
3. 长程任务数千动作的稀疏终局 reward 难做信用分配；只优化正确率又不激励减少实际工具与串行执行延迟。

## 3. 系统分工与真实 harness

### 3.1 三层架构与一条数据流

§2.1 的架构图〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/arch.png`〕显示：

- **Agent Side** 是真实白盒/黑盒 agent 及其环境，编排思考、CM、工具和交互，作为轨迹生产者。
- **Middleware** 内 Gateway Server 通过标准协议路由 agent 的 completion 请求到模型；Data Pool 分布式异步收轨迹/报告，为生成与训练解耦并提供处理/组 batch 空间。图示 `Completions: prompt_ids, response_ids, …` 和 `Rewards: outcome, process`。
- **Engines** 中 Rollout Engine 生成 token；Train Engine 消费 Data Pool 序列、更新 policy，并向 Rollout Engine 同步权重。

这只给逻辑流程，不给逐 token 捕获时机、重分词规则或日志 schema。图中的标准接口不等于精确 OpenAI API 版本；Gateway 的 `prompt_ids/response_ids` 也不能证明所有改写前动作均被无重复捕获。所谓物理隔离是架构分离描述，不能推为安全沙箱、隐藏测试隔离或抗作弊保证。

作者称已集成数百种 scaffold、数千工具调用格式，与引言“十万量级 scaffold/environment”是不同集合和粗粒度单位。离线评测发现 scaffold 会明显改变表现，是多 scaffold 训练动机；未给每 scaffold 的 heldout 测试矩阵。（§2.1）

### 3.2 白盒：将 CM 放入 RL 交互分布

§2.2 指出 context rot 可在尚未超 context cap 时发生：重复 observations 与中间 reasoning 稀释注意力。只在部署阶段加入 CM 会让模型遭遇训练未见的上下文转换。Forge 把 CM 当驱动状态转移的功能动作，训练策略适应压缩/剪枝后状态，学习保留任务关键内容。

这是**作者机制解释**，没有 CM 具体阈值、summarizer 版本、压缩质量曲线，或独立 CM 改善数表；不能推成已披露的可微 memory policy、专门训练 CM 网络或梯度穿过任意字符串重写。后来的 R4 才更明确形式化生成接口 MDP；本篇应保留自己的披露层级。

### 3.3 黑盒：接请求而不改 agent 内部

§2.3 中 agent 把请求路由到 RL Gateway，训练框架负责收集和训练，支持 memory compression/history rewrite、Deep Think、多 agent 等内部循环。明确例子是把 **OpenCode Agent 完全作为黑盒训练**，以及使用激进上下文压缩的 **Truncate BC**；名称出现不等于给了它们的 commit、工具配置和输入语料。

Black Box Agent RL 图〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/black_rl.png`〕横轴 Training Time (hours)，约 0–54h；纵轴 Reward。目视起点约 0.51、末点约 0.64，中间最高约 0.72，明显多次回落。这是图上近似读数，非作者数表。它支持“在某个黑盒训练实验中 reward 总体上升”的有限判断；没有任务身份/样本数、平滑方法、多个 seed、基线或独立评测曲线，不能证明所有黑盒都收敛、稳定单调，或未见 scaffold 泛化已被单独验证。

## 4. Windowed FIFO：选择已完成轨迹的可见范围

§3.1 明确约束的是 **Training Scheduler 从 global generation queue 取完成轨迹**，不是推理端按 token 长度安排请求。队列为 `Q=[T0,T1,…,T(N−1)]`，按生成派发次序，当前头为 i，窗口 W；只可取 `[Ti,…,T(i+W−1)]` 内已完成项。

- **窗口内局部 greedy**：允许后项先完成先取，不必等待绝对第一项。
- **窗口外全局阻塞**：即使完成，也不能抢先进入训练。
- **推进规则**：队头被消费后窗口才前移；因此长期 straggler 会在窗口内其他项耗尽后继续阻塞。

`W=0.3N` 是示例，**不是论文证明的最佳比例，也不是只取最短的 30%**。N 是 generation batch size，不是 CISPO 每题 rollout 数 G。源文范围上界为 `i+W−1`，但描述窗外的例句写 `j>i+W`，漏写恰好 `j=i+W`；本笔记按显式闭区间理解窗外从 `i+W` 起，保留该边界措辞缺口。

**阅读者例解。** i=0、W=4 时，仅 0–3 可消费；若 1–3 完成则可先取，4 即使完成也不可取；0 消费后向前推进。这保存派发顺序附近的分布，同时容忍有限乱序，无法消除所有长尾或保证每 batch 的类别比例一致。若任务永久挂起，文章没有提供窗口越过它的取消/超时规则。

window 原图〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/window.png`〕用另一个示例 **N=8、W=4**，初始 0–7 来自 model version 0；当 0–10 除 7 外都完成训练，窗口剩余容量为 1，7 之后图示 11/12/13 仍不可越界。标注 Max Out-of-Order Tolerance=3=`4−1`、Max Off-Policy Lag=10=`8+3−1`。这说明作者考虑了策略滞后，但**没有给消费次数、optimizer update、权重版本发布的转换定义**；不得泛化为生产环境统一版本界 `N+W−2`，更不能替换 rh2/miles consume-time staleness。

没有 Windowed FIFO 对严格 FIFO/FFFO 的吞吐、任务分布距离、最终 reward 或同预算 benchmark 对照表；因此其定量收益未公开。相同任务最终全部消费和固定墙钟下实际消费是不同问题，窗口规则不能自动消除后者的选择偏差。

## 5. 训练前缀合并与推理优化

### 5.1 Prefix tree merging

§3.2 两个小节指出多轮 append、不同 sampling branches、CM/summary 后请求仍可共享很长 prefix，逐样本独立算前缀浪费算力。合并把这些请求组织为树，共同部分 forward 一次、后续分支分别算，用 attention primitives（举 Magi Attention）保持标准 forward 的逻辑；随后按 metadata 拆回样本计算 loss。原图〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/N10/tree_merge.png`〕有共享 `long common context`、`seq1` 与 `seq2→seq3` 两条分支。

作者声称 **40× training speedup**，降低内存开销且与标准训练严格数学等价。直接 baseline 只是“每个样本独立重复计算共同前缀”的朴素方法，**没有公开硬件、长前缀比例、轨迹长度、batch、具体实现或端到端耗时**。这不是已测“RL 全流程加速 40×”，也不是同一硬件下优于成熟 miles/verl 内核 40×。R4 后来表述为 up to 40×，不能偷偷改成本文已带该限定的原句；本篇仍仅以局部作者声明引用。

**阅读者推论。** 必须保留原有 token、位置/因果可见性和独立样本 loss 权重，才能主张等价。计算一次共享 prefix 不代表这个 prefix 只应贡献一次 loss，也不授权把多个逻辑 episode 合成一个样本；共享 assistant response 在多少请求中训练，要由原有目标确定。本文未披露梯度累积、dropout/RNG、MoE routing、mask 和分母的实现一致性验证。

### 5.2 三项推理工程

| 原文 §3.3 技术 | 披露的机制 | 未披露的关键量 |
|---|---|---|
| MTP speculative decoding | draft heads 在 RL 中持续用 Top-K KL 微调以跟随变化中的 policy，维持接受率 | K、KL 方向/系数、teacher/主 policy 是否冻结、head 数、接受率和实测速度 |
| Heterogeneous PD disaggregation | 分开调度 Prefill/Decode，避开 MoE 混排干扰，各实例独立选并行策略 | GPU 类型/数量、TP/EP/DP、网络/KV 搬迁与尾延迟分布 |
| Global L3 KV Cache Pool | DFS-backed cache；group-level rollout 增 prefix 命中；路由权衡排队与迁移成本 | 容量、eviction、命中率、版本失效与收益数表 |

MTP top-K KL 属于追随 policy 的 draft 训练，不是披露“多领域专家 OPD”；不能从 M1/M2 架构或 serving 默认值补齐 Forge 文章参数。

## 6. CISPO、混合领域和 reward

### 6.1 公式实际写了什么

§4.1 明确用 CISPO（Clipped Importance Sampling Policy Optimization），同时混 **Reasoning、General QA、Agent**，作者以它对比顺序多阶段域训练的干扰。文章没有 SFT→RL 详细阶段链；也不应将其“unified”措辞扩为 M2 全家族从未分阶段，R4 后来明确每阶段内混域的课程。

网页公式及 HTML 中原始 TeX 为：
\[
J_{\rm CISPO}(\theta)=\mathbb E_{(q,a)\sim D,\{o_i\}_{i=1}^G\sim\pi_{\theta_{old}}(\cdot|q)}\left[
\frac{1}{\sum_{i=1}^G|o_i|}\sum_{i=1}^G\sum_{t=1}^{|o_i|}
\operatorname{sg}(\hat r_{i,t}(\theta))\hat A_{i,t}\log\pi_\theta(o_{i,t}|q,o_{i,<t})\right],
\]
\[
\hat r_{i,t}=\operatorname{clip}(r_{i,t},0,1+\epsilon_{high}^{IS}),\qquad
\hat A_{i,t}=\sum_{p=t}^{T}(r_p^{speed}+r_p^{perf})-B_i.
\]

含义按公式可确定：新 policy 的 log-prob 梯度，被停止梯度的 clipped importance weight 与 advantage 缩放；上下界是 0 和 `1+ε`。这不是 PPO `min` surrogate，也不是超过 clip 就一律删 token。分母是所示组内全部输出长度总和，不能改成每轨迹等权均值。

披露边界：G/ε 未给数值；`r_{i,t}` 在本文未展开成策略比率定义；`B_i` 未定义计算方法，不能用 M1 的 group mean/std 补齐。`q,a,o_i` 关系、request/episode/turn 的组织、reward step 到 token 的映射、哪些 token 包含在 `|o_i|`、tool observation/thinking/CM masks、失败组统计都没有完整说明。R4 后来补了比例公式及 trajectory baseline 的文字，但仍不是本文证据。

### 6.2 三类奖励及公式/文字不一致

§4.2 的 process reward 处罚语言混用和特定工具调用错误，补终局反馈稀疏的问题；completion-time reward 使用相对完成时间，计入工具执行与 sub-agent 延迟，鼓励并行；reward-to-go 用于降方差、改善信用分配。

**公式只出现 speed+perf，正文另述 process reward**，没有交代 process 如何进入 `A` 或单独 loss。不能把 R4 的 `α process+β speed+perf` 移入本篇作为文章已公开公式；也没有 baseline 时间、shaping function、α/β、discount γ 或标准化方式。文字说 reward-to-go “normalize returns”，但所示公式是未来奖励求和减 baseline，不能据此推断 GRPO 标准差归一化。

没有公开三种奖励的独立消融、speed reward 对正确率影响、混域比例和遗忘测试。本文没有额外 role-play RLHF、偏好模型、安全对齐、SFT 或数据过滤部分；这些在 R4 中另有范围不同的描述。

## 7. 实验、成本与复现程度

### 7.1 证据清单

| 可引用声明/图 | 测量对象与边界 |
|---|---|
| 引言的百万量级 samples/day | 全系统日处理量级，sample 定义与 GPU 分母未给；不是有效训练样本吞吐 |
| §3.2 的 40× | 训练侧重复 prefix 计算优化的声明，没有匹配 workload 表；非端到端 RL |
| §2.3 black_rl | 单条 reward vs hours 曲线，约 54h；是一次黑盒案例，非全部 M2.5 训练时长 |
| 数百 scaffold / 数千 tool formats | 兼容性规模声明；没有各自测试结果或 unseen split |
| Windowed FIFO 的 W=0.3N / 图中 lag=10 | 设计例子；非模型成绩、最优超参或通用版本上界 |
| “解决 impossible triangle” | 作者对联合系统的总结，未给一般收敛证明或每组件受控增益 |

文章没有标准 benchmark 最终成绩表、模型准确 checkpoint、同底座同数据同算力对照、多次训练重复或方差。黑盒曲线明显起伏，应保留这个负面信号；也没有系统列出的失败实验。不要将缺少对照包装成已经证明“CISPO 比 PPO 更稳定”或“Windowed FIFO 在所有场景更快”。

### 7.2 训练资源与终止语义未知项

已查引言、§1–5、全部技术图和公式，没有披露：

- SFT/训练初始化、任务生产漏斗、训练题量与真正消费量、teacher 模型、任务/仓库/time split、污染防控、license 处理、gold/no-op/替代解验证及隐藏 grader 隔离。
- GPU 型号/数量、拓扑、精度、并行布局、optimizer/LR/steps/batch/minibatch、每题 rollout G、KL/entropy 主损失、速度/过程奖励权重。
- max_new_tokens、单次 context hard cap 配置、工具轮次/请求上限、wall-clock 训练 episode 预算；200k 是范围描述。
- rollout 失败/截断/工具超时/坏环境的 reward、group statistic、梯度 mask 和补采；取消、重试上限、幂等、partial rollout/resume、完成前 token 是否继续用于训练。
- sync weights 时机、policy-version 标记与跨版本 token spans、lag 单位、过期丢弃/重生成、recompute logprob、队列背压与永久 straggler 的退出语义。

因此环境/API、teacher、RL training、评测四类成本均无法由本文重建；黑盒图小时数不能充当全流程成本。

### 7.3 开放资产边界

正文把 Forge 称内部框架，没有给可运行源码/数据/环境/config 链接。评论区有 M2.5 模型/仓库发布线索，这只能证明页面有资产导航，不能证明开源了 Forge 训练实现。本次不下载权重、不检查整仓；“未见正文公开 Forge 实现入口”是检查范围内结论，不断言所有网络位置都不存在代码。

## 8. 对 RepoHarness 项目一的意义及旧稿校正

映射日期 2026-09-07；参考当前简报〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕和项目一设计建议 §4–6〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕。主资料 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`；实际 miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`。本次仅窄查接口与职责，没有扩成全仓审计。

`reference/miles-rh2-integration/miles/rollout/fully_async_rollout.py::FullyAsyncRolloutFn` 持续派发并把完成组送入 buffer；同 commit 的 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py::DefaultDataBuffer` 以**完成入池顺序** FIFO，put 作 ABORTED/dynamic filter，get 作 consume-time staleness。文件中的 FIFO 是已完成组 FIFO，不能与 Forge 原始生成队列窗口混为同一算法。miles 已有 buffer capacity、unused handler 与关停接线，不能把这些列成 rh2 必须从头造的新平台。

| 借鉴候选 | 上游承担 / rh2 增量 | 最小验证 |
|---|---|---|
| 实际消费分布而不只看生成 TPS（§1、§3.1） | miles 管异步消费/版本；rh2 只补已有事件的离线分析 | 同任务池看派发→完成→消费按任务族/长度/耗时的分布，连同 stale drop、实际消费组/GPU-hour；先发现偏差再讨论 window |
| 黑盒请求流与 CM 训练一致性（§2） | 主仓 `rh2/src/repoharness2/adapters/slime/capture_wire.py::CaptureRegistry`、`rh2/src/repoharness2/adapters/miles/canonicalize.py::canonicalize_sample` 是现有接线 | 真实 Claude Code rewrite/fork/compaction trace，核生成动作和训练 token、mask、重复权重与行为概率；不是另造 Gateway |
| Prefix computation reuse（§3.2） | 训练 attention 和推理 KV 优化归后端 | 固定请求集验证 loss/梯度等价与 prefix 重复率，再量局部/端到端成本；不承诺 40× |
| 速度 reward 和多 scaffold（§4、§2.3） | 当前首训先用既定任务 reward；此处是以后候选 | 先把 tool/queue/inference/grade 时间分开测；第二 harness 先作等预算 eval，不能直接引入时间罚或多 agent 训练 |

旧训练证据矩阵〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕把 M1/M2 并排只能作导航，M1 的 group-relative advantage 不应补本文 `B_i`；R4 的 192K 与 N10 的 200k 各有来源，不擅自统一为实际 hard cap。旧infra 映射〔仓库引用：`docs/harness_improve/external_paper_references/infra_mapping_for_repoharness_rl_serving.md`〕将前缀、KV、PD 交给上游的职责原则仍合理，但前缀 digest 或“支持黑盒”不自动证明训练 token 与概率对齐。设计建议 §4.2〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕“先测消费偏差、不先重写 scheduler”的判断有本文支持；未因此批准新的调度策略。

可支持简历叙事的是对真实 harness、队列选择偏差和 token loss 边界的理解。自己的吞吐、预算收益与 heldout 学习改善仍需要匹配实验，不能借 MiniMax 的规模声明代替。

## 9. 独立检查与修订记录

主任务 ID `01a07827-1e44-7133-85d7-658445c04597`，实际 `gpt-6-astra / high`，主派发线程已核验。与 R4 共用唯一一名干净上下文审查者，记录见09 审查〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/09_R4_N10_review.md`〕。固定初稿副本 `sources/N10/N10_minimax_forge.draft-20260907.md`；来源为 2026-09-07 抓取、元数据最后修改 2026-02-13 的官方 HTML，初稿日期 2026-09-07。2026-09-07 已收到完整审查：审查者 ID `01a07831-76f5-7ae1-8211-2dc348e68bbd`，实际 `gpt-6-astra / high`、`fork_turns="none"`，会话日志核实身份与配置。N10 未发现必须修订的事实错误或整块遗漏；R4 的三项发现已逐项修订，处理见审查记录。N10 仅补本审查状态，原有披露边界继续保留。


---

## 文档 5 / 7：E10_intern_s2_preview.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/E10_intern_s2_preview.md`

# E10 Intern-S2-Preview: Scientific Agentic Foundation Model：后训练与项目一精读

Intern-S2-Preview 从科学多模态预训练模型出发，先做广域 SFT，再从同一 SFT checkpoint 分别训练推理与 agentic 两个专家，最后经专家轨迹 SFT warmup 和 sampled-token OPD 汇合。报告最有用的披露是：推理 RL 的完整 REINFORCE 目标、逐 token 跨版本修正，以及黑白盒 harness 的语义轨迹与精确 token 双视图。它还覆盖科学生成、通用多模态、时序预测与独立 Memory Decoder 扩展。主要限制是数据消费漏斗、teacher/训练成本和 agentic 完整 loss 未给；397B 论文与脚注链接当前的 35B 模型卡也不能混用。

导航：来源与全篇覆盖 · 模型关系与 SFT · 推理 RL 与系统 · Agentic 数据、轨迹和评分 · OPD · 评测、边界与项目映射

## 1. 来源、版本与覆盖

- **原文**：Intern-S2-Preview Team, Shanghai AI Laboratory，《Intern-S2-Preview: Scientific Agentic Foundation Model》，[arXiv:2608.13505v1](https://arxiv.org/abs/2608.13505v1)，2026-08-13 17:31:28 UTC 提交；本次查阅日 2026-09-07。正式标题不含“训练配方”等目录说明。
- **定位口径**：本地 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E10_intern_s2_preview_2608.13505.pdf`〕 共 35 页，PDF 物理页与印刷页一致；第一页未印页码。下文 p.、Eq.、Fig.、Table 均指这一 PDF。正文 p.1–27，References p.28–35，**没有附录**。已从 TeX `main.tex` 的全部 `input` 到 `end{document}` 及 PDF 尾页核对，不把参考文献后的空白当成漏读附录。
- **交叉材料**：[官方 TeX 下载](https://arxiv.org/src/2608.13505v1)，已保存在 E10 来源目录说明〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E10/README.md`〕，读了全部正文源文件；文本提取〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E10/paper-layout.txt`〕 用于检索，公式、全部图表回本地 PDF 渲染页核对。下载的部分图形素材排版与本地 PDF 不同，本文页码、图示与数值以指定 PDF 为准，TeX 用于公式文字交叉核验；未重新编译或替换 PDF。
- **开放资产检查**：查阅论文脚注所指 [HF 模型卡](https://huggingface.co/internlm/Intern-S2-Preview/blob/4f57cab513689b089019fce4ad24e26520df183c/README.md)，revision `4f57cab513689b089019fce4ad24e26520df183c`；API 返回 lastModified `2026-05-29T07:30:04Z`。此卡介绍 **35B**、continued pretrained from Qwen3.5，而非论文主表的 397B。只用于识别资产与版本边界，未用其内容补写 397B 配方。
- **框架入口检查**：[InternLM/xtuner](https://github.com/InternLM/xtuner/tree/76e705134521eff867b409f3b3451df1c4d8dd36)，读取该 commit 的 `README.md`；只核公开入口和其披露状态，未将当前框架默认值认定为本论文配置，也未完成框架实现审计。
- **旧稿最后才读**：旧摘要〔仓库引用：`knowledge/summary_intern_s2_preview.md`〕。另检查配方矩阵〔仓库引用：`docs/harness_improve/external_paper_references/agentic_rl_training_recipe_evidence_matrix.md`〕全文检索结果；该文件最近核验为 2026-08-03，本次没有找到 Intern-S2/E10 专属段落，不能假称已有对应配方行。

原文无目录页，下表由全部章节标题与 `main.tex` 输入结构独立建立，先于旧摘要阅读。

| 原文范围 | 深度与覆盖 | 本笔记位置 |
| --- | --- | --- |
| Abstract、§1 Introduction，p.1–2 | 全读；问题、阶段关系、科学 agent 目标 | §2–3 |
| §2.1 Memory Decoder，p.2–4，Fig.1、Eq.1–4 | 精读；独立扩展、retrieval teacher、冻结与训练参数 | §7 |
| §2.2.1 Encoder、§2.2.2 Generation，p.4–5，Fig.2 | 架构概要；影响训练/评测的输入压缩与数值预测完整记录 | §2、§7、§8 |
| §3.1 VP，p.5–6，Fig.3、Eq.5–9 | 预训练概要；冻结对象与联合目标已核 | §2 |
| §3.2 Interleaved Data、§3.3 Retrieval，p.7–8，Fig.4–5 | 预训练概要；OCR、PPL 筛选、长文拼接、图像召回 | §2 |
| §4.1 Framework、§4.2 SFT，p.8–9，Fig.6 | 精读；安全、科学生成、多模态、工具、长轨迹均覆盖 | §3 |
| §4.3.1 Partial Rollout，p.9–10，Fig.7、Eq.10–13 | 精读；pause/resume、IS、R3、精度、BKL | §4.1、§4.5 |
| §4.3.2 Length Regularization，p.10–12，Fig.8、Eq.14–17 | 精读；正 advantage 条件、质量保持、35B 消融 | §4.3、§8.3 |
| §4.3.3 Speculative Decoding，p.12–13，Eq.18–24 | 精读；在线 draft、KL/TV 混合、速度口径 | §4.6 |
| §4.3.4 GEPO、§4.3.5 Unified Objective，p.13–15，Eq.25–29 | 精读；组熵、不对称 shaping、LOO、分母与已知参数 | §4.2–4.4 |
| §4.4 总述、§4.4.1 Infra，p.15–17，Fig.9 | 精读；黑/白盒、三协议、TITO、PrefixTree、双视图 join | §5.1–5.2 |
| §4.4.2 Task Construction，p.17–18，Table 1、Fig.10 | 精读；七公开源、skill 合成、离线选择性模仿与反馈闭环 | §5.3–5.4 |
| §4.4.3 Training，p.18–20，Fig.11、Eq.30 | 精读；session advantage、过程反馈、verifier 防漏、训练曲线 | §5.5–5.6、§8.3 |
| §4.5 OPD，p.20–21，Eq.31–36 | 精读；两专家、warmup、reverse KL、prox/beh、通信量 | §6 |
| §5.1.1 Scientific、§5.1.2 General，p.22–24 | 全读各 benchmark 定义与已给 harness；非 SWE 全覆盖 | §8.1–8.2 |
| §5.2 Main Results、§5.3 Architecture，p.24–26，Table 2–5、Fig.12 | 全读所有表与雷达图；保留退化和不支持的排名说法 | §7–8 |
| §6 Conclusion、作者贡献，p.27；References，p.28–35 | 结论全读；参考文献检查到最后一条 [112]，不递归精读全部被引论文 | §9–10 |

## 2. 模型问题与预训练背景

**论文事实。** 科学任务既要理解图表、分子/生物序列、数值信号，也要生成结构、使用外部程序并在长流程里验证结果。主评测对象为 Intern-S2-Preview-397B；35B 在 Fig.8 的长度正则消融中单独出现，Memory Decoder 则是冻结 397B 主干的可选扩展。不能把三个对象的数字合并为一个实验（§1–2、§4.3.2、§5.3）。本报告未给 397B 完整配置表、激活参数量与精确 pretrained checkpoint ID。

三条预训练材料线为后训练提供科学表示，不能当成 SFT/RL 任务量：

1. **Visual Pre-training**：科学 PDF 渲染为页面；冻结视觉 encoder，保留前景 latent 并按 raster 顺序输入 LLM，预测下一个 latent。温度缩放余弦相似度形成 batch 内对比 loss，正确下一 latent 为正例，其余 target 为负例；联合目标为 `λ_text L_CE + λ_vis L_VP`，更新 LLM、输入投影、预测头，视觉 encoder 不更新。这条 VP 本身不需要 OCR/配对标注（§3.1，p.5–6，Eq.5–9，Fig.3）。
2. **交错图文长文**：另一条线使用 MinerU2.5-Pro 做 OCR 和布局解析，裁剪图片、行间公式、表格；按页面阅读顺序拼接，用 `PPL_text-only − PPL_interleaved` 衡量视觉增益，结合人工与分域阈值过滤，再按原页序构成长文。每 chunk 最多 256k token、重叠 512 token，重点生命科学、化学、材料学。这与“不需 OCR 的 VP”是两条机制，不能互相矛盾地概括（§3.2，p.7，Fig.4）。
3. **图像检索增强**：按图像 SHA256 去重，8B embedding 模型生成 1024 维向量，Milvus 分片 collection 支持数亿规模；文字直接召回，图像联合其 embedding 与 caption embedding 召回，再去重、rerank、质量过滤，提高高质量科学图片的采样比例。数亿是数据库规模描述，不是最终训练消费图像数（§3.3，p.7–8，Fig.5）。

## 3. 后训练依赖关系与 SFT

```mermaid
flowchart LR
  P[科学多模态 pretrained checkpoint] --> S[广域 SFT checkpoint]
  S --> R[多任务 reasoning RL expert]
  S --> A[黑盒与白盒 agentic RL expert]
  R --> T[两个专家生成高质量轨迹]
  A --> T
  S --> W[轻量 SFT warmup student]
  T --> W
  W --> O[student 采样的 OPD]
  R --> O
  A --> O
  O --> U[统一 Intern-S2-Preview]
```

图中分支依据 §4.1/Fig.6 与 §4.5；原 Fig.6 简写了最终合并，warmup 由 p.20 文字补全。**同一 SFT 初始化分叉为两个专家**，不是先完成 reasoning RL 再在同一权重串行做 agentic RL；也不是每个 harness 对应一位 teacher。黑盒与白盒是 agent 控制循环的接入方式，不是对模型权重或 teacher 概率是否可见的区分。

SFT 混合包含：通用对话、instruction following、**safety alignment**、代码生成与推理、图文理解、视觉感知与空间 grounding、工具使用、专业科学任务、长 horizon agentic 轨迹。数据清洗、过滤、去重；显式推理任务由上一代 **Intern-S1-Pro** 与其他领先开源模型 rejection sampling 产生 CoT，随后由语言模型及人工领域专家验证事实、推理和格式。原文没有给各域数量/比例、接受率、其他模型名或 SFT 优化超参数（§4.2，p.8–9）。

多任务 RL 以可验证目标改善正确性、推理深度、科学生成、响应效率，范围为科学和通用任务（§4.3）；没有逐个给出分子、晶体、蛋白设计的 RL reward 和混合配方，不能从 §5 的评测列表倒推每项都作为某阶段训练集。安全后训练的明确落点是上述 SFT，以及 §4.4.2 不安全技能过滤和 verifier integrity；未单独披露 DPO/RLHF 安全阶段或安全评测表。

## 4. 推理 RL：目标、分母与 rollout 系统

### 4.1 共置 partial rollout 与逐 token IS

**论文事实**（§4.3.1，p.9–11，Fig.7）：XTuner 训练 + LMDeploy 推理共用 GPU 池。推理期间不断补入新请求；收集足够**完成**轨迹成 batch 后，未完成请求原位暂停，保留 prefix 与元数据；GPU 切到训练，更新后 offload 训练状态、同步新权重，再从保留 prefix 恢复。未完成前缀不单独进入当次 batch。它避免等全部长尾结束，但不是训推分离的 fully asynchronous 拓扑；图示 GPU 0–5 是机制示意，不能读成实训仅六卡。

同一轨迹可能跨多个行为版本，因此每个 sampled token 记录生成时 logprob 与版本。令 `s_{i,t}` 为生成第 i 条轨迹第 t 个 token 时的状态：

\[
\rho_{i,t}(\theta)=\frac{\pi_\theta(y_{i,t}\mid s_{i,t})}{\pi_{\mathrm{beh}(i,t)}(y_{i,t}\mid s_{i,t})},\qquad
\bar\rho_{i,t}=\operatorname{clip}(\rho_{i,t},1-\epsilon^{IS}_{low},1+\epsilon^{IS}_{high}).
\]

Eq.10–11（p.10）的分母是**该 token 真正的行为策略**，不是统一 rollout 起点版本或 teacher。`barρ` 在 loss 内 detach，只作常数权重；这是裁剪 IS 权重，不是 PPO 的 `min(ratio*A, clipped_ratio*A)` surrogate。它不会仅因 ratio 超界就将该 token 的梯度置零；但 BKL mask、零 advantage 仍可使贡献为零。裁剪控制方差，不代表消除了所有 off-policy 偏差。

若轨迹最老保留 segment 比当前 learner **早超过三次 policy update**，丢弃轨迹（p.10）。原文未把这一版本单位与后述 8 个 mini-batch step 精确对应，不能自行乘除换算；丢弃如何影响已组装组与补采亦未给。

### 4.2 奖励、LOO 与 GEPO

每 query 采 G 条 response，verifier 给序列 reward `R_i`。在线丢弃 reward 全相同的 query group 并补采新组；保留组计算 leave-one-out advantage（p.14，Eq.27）：

\[
A_i^{LOO}=R_i-\frac{1}{G-1}\sum_{j\ne i}R_j.
\]

这是不含 critic 的 REINFORCE 基线；公式没有除组内标准差，不能改称标准化 GRPO。G 数值未披露，8,192 条 response 也不是 8,192 个 query。

先做 **GEPO（按组熵调节 advantage）**，后做长度正则（Eq.28）。组熵的采样估计为（p.13，Eq.25）：

\[
H_g(x)=-\frac1K\sum_{i=1}^{K}\sum_{t=1}^{T_i}\log\pi_\theta(y_{i,t}\mid y_{i,<t},x).
\]

这里对 response 平均、对 token 求和，**没有每条除以 T_i**。它不是平均 token entropy，也不是逐位置全词表熵；K 是该式的组 response 数，不是 speculative decoding 的 K=4。低熵组的正 advantage 乘 `α_low`，高熵组的负 advantage 乘 `α_high`，其余保持不变，两系数均在 (0,1)（p.13–14，Eq.26）。目的为避免低熵组过度利用、高熵组过早压制探索；无需额外采样或显式任务标签，是作者给出的设计解释。

**原文疑点**：p.13 文字说低熵干预应较温和；p.14 却排印 `α_high ∈ (0,1) > α_low ∈ (0,1)`，该串式不是清晰的系数不等式。不能据此确认两系数大小关系，也不能自行“修正”后当成作者配置；本篇保留确定的分支条件和衰减方向。上下阈值的算法与数值均未给。

### 4.3 自适应长度正则

在 GEPO 后 advantage `Â_i` 上定义正集合 `P_q={i: Â_i>0}`，只当 `|P_q|≥τG` 激活。对其中 response：

\[
w_i=\alpha+(1-\alpha)\left(1-\frac{L_i-L^+_{min}}{L^+_{max}-L^+_{min}+\epsilon}\right)^\gamma,
\qquad
\widetilde A_i=\frac{\sum_{j\in P_q}\widehat A_j}{\sum_{j\in P_q}w_j\widehat A_j+\epsilon}w_i\widehat A_i.
\]

其余 `Ã_i=Â_i`。`L_i` 是 reasoning 长度，`L_min/max^+` 是正集合内极值，α 给长 response 最低权重，γ 控衰减形状，ε 稳定分母（p.11，Eq.14–17）。短正 response 权重大，长正 response 仍保留正号，且近似保持正 advantage 总和；**不修改 verifier reward，也不直接给失败轨迹加长度负奖**。

原文用 pass rate 解释激活条件，但精确定义是**正 advantage 比例**，不是一个独立成功标签；一般非二元 reward 下不能自动等同任务通过率。§4.3.2/Fig.8 的实证是 35B 两条训练曲线：正则后输出缩短、reward 接近，未给独立评测或统计区间，不能推成 397B 所有领域“无损压缩”。

### 4.4 完整 reasoning loss 与已披露配置

Eq.29（p.14）为：

\[
\mathcal L_{RL}=-\mathbb E_{(q,\{y_i\})\sim\mathcal B}
\left[\frac1G\sum_i\frac1{|y_i|}\sum_t
m^{BKL}_{i,t}\operatorname{sg}[\bar\rho_{i,t}]\widetilde A_i\log\pi_\theta(y_{i,t}\mid s_{i,t})\right].
\]

先对每 response 的 token 求和并除原长度，再对 G 条 response 平均，最外层对 buffer 的 query group 取期望；不是全 batch token 扁平平均。BKL 剔除 token 仍留在 `|y_i|` 分母，不按 mask 存活数重归一化。序列 advantage 共享给该 response 的 policy token。公式无额外 reference-model KL 或 entropy bonus；GEPO 是 advantage shaping，BKL 是数值 mask，均不是那种正则项。

| 配置 | 原文值与单位 | 限定 |
| --- | --- | --- |
| optimizer / LR / weight decay | Muon；1×10^-6；0.01 | §4.3.5，p.14；不外推为所有 SFT/OPD 参数 |
| rollout batch | 8,192 条**完成的 response** | 每 query 的 G 未给 |
| mini-batch 更新 | 每 rollout batch 8 次 update steps | 非“同一数据 8 epochs”的明确声明 |
| 最大生成长度 | 65,536 token | p.15，reasoning RL；不是所有 session/评测预算 |
| staleness | 最老 segment 超过 3 policy updates 则丢轨迹 | §4.3.1；版本发布单位未进一步解释 |
| IS clip、BKL φ、GEPO 与长度系数 | 有符号，没有数值 | 不用旧模型或框架默认值补齐 |

### 4.5 R3、精度与 BKL mask

LMDeploy 记录 MoE expert 路由，XTuner 对对应 token 重放，减少离散计算路径差异。专家线性层 FP8，其余层 BF16，但 `apply_rope`、RMSNorm、MoE router、Gated DeltaNet recurrent states、LM head 用 FP32（p.10）。这些是本文训练机制描述，不是硬件型号或完整混合精度配置表。

在**相同模型参数且路由已重放**下比较 training 与 rollout 的 sampled-token 概率 p、q，定义二元 KL（Eq.12–13）：

\[
D_{BKL}(p\Vert q)=p\log(p/q)+(1-p)\log((1-p)/(1-q)),\quad
m^{BKL}=\mathbf1[D_{BKL}(p\Vert q)\le\phi]\mathbf1[D_{BKL}(q\Vert p)\le\phi].
\]

这将单个 sampled token 与“其余 token 总质量”组成 Bernoulli 分布；不是全词表 KL。它筛数值离群点，不能用当前参数与老行为参数的差异冒充训推误差；IS 另处理策略更新差异。原文没给如何对跨版本片段重新取得 matched-parameter p/q、阈值、极端概率保护及额外计算成本。

### 4.6 在线 speculative decoding

轻量 draft 预测多个候选，当前 policy 以精确 rejection sampling 验证，因此在该采样前提下保持 policy 分布。每 RL iteration 用新 rollout 状态上的当前 policy 分布更新 draft，policy stop-gradient；两分布均处于 rollout sampling temperature（§4.3.3，p.12–13，Eq.18–24）。

以 `p=sg[π_θ]` 为 target、`q=π_draft`，forward KL 为 `Σ_v p_v log(p_v/q_v)`，TV 为 `½Σ_v|p_v−q_v|`；接受概率 `a=Σ_v min(p_v,q_v)=1−TV`。第 k 个 draft 位置使用：

\[
L_{LK}^{(t,k)}=\lambda_k KL(p\Vert q)+(1-\lambda_k)TV(p,q),\qquad
\lambda_k=e^{-\eta\operatorname{sg}[\bar a_k]},\quad
L_{draft}=\frac1K\sum_k\frac1{|\mathcal T_k|}\sum_{t\in\mathcal T_k}L_{LK}^{(t,k)}.
\]

`bar a_k` 跨序列和 batch 聚合；K=4 个未来位置，η=3。接受率低时以 KL 稳定对齐，接受率高时提高直接优化分布重叠的 TV 权重。此 draft 是加速器，不是最终能力合并的 reasoning/agentic teacher，也不是 Memory Decoder。

作者报告 rollout 生成约 **2×**、整体 RL pipeline **1.7×** 加速（p.13）；未给对应 GPU、基线绝对时间、工作负载、draft 规模或分项成本表。它们是不同测量范围，不能再相乘，亦不能作为共置优于 fully async 或八卡复现成本的证据。

## 5. Agentic：数据、harness、训练与 verifier

### 5.1 harness × task 的真实含义

Harness 决定实例化、驱动、观测、消息与工具循环；task 决定初始环境、可执行目标、verifier outcome。两者独立组合成统一 session（§4.4，p.15）。白盒 loop 可直接编排；黑盒经原生 CLI/SDK/model API 接入，保留其内部逻辑。列举的黑盒包括 OpenClaw、Claude Code、OpenCode、OpenHands、Mini-SWE；“黑盒”不等于闭源，白盒也未被限定为必须自研。

Agent Rollout Runner 接收 harness-task 对、准备环境、管理正常与异常终止。Judger Adapters 对同一 session 状态和执行工件做 outcome 与过程标注；Shared Sandbox Provider 抽象 local/remote/custom 环境创建、命令、隔离、错误处理和清理。原文并未给具体容器/网络权限、fresh grader 的进程拓扑或 sandbox TTL（§4.4.1，Fig.9）。

### 5.2 服务端 token 捕获与双视图

Model serving 接受 OpenAI Chat Completions、Responses、Anthropic Messages，支持普通与 streaming；native text/reasoning/tool-call 事件返回 harness。同时服务端捕获精确输入/输出 token IDs、rollout logprob、逐 token router experts，客户端不需要理解训练扩展。

**TITO**：Session Server 复用已记录 tokenized prefix，仅 tokenize 新增 context，把 token IDs 直接送 inference engine；生成 token 和统计来自交给 agent 的同一响应流。它不是先存可见文字再整段重分词。**R3** 再保留产生 token 的 MoE 路由（p.16）。

两类记录通过 session 与 segment join（p.16–17）：

| 记录 | 内容与用途 |
| --- | --- |
| Replay Buffer | 语义 action–observation 轨迹、最终 reward、过程标注、session 元数据 |
| Rollout Trace Store | token IDs、loss labels、behavior logprobs、router experts；每 session 的增量 PrefixTree |

PrefixTree 节点为 context delta 或 assistant response；最长前缀匹配复用稳定历史，只增新段；训练时物化 root-to-leaf。system/user/tool observation 不进 loss，eligible policy segments 保留 labels。树保留多轮与分支的 lineage 和调用边界，供消息→token span 对齐及过程 credit。

**证据边界**：这证明作者提出精确采样 token 的保存与拼接路径；不能从“树支持 branching”推出 compaction/rewrite 后被移除响应的训练覆盖、共享前缀跨 leaf 如何去重计权、子 agent 的 reward 归属或 teacher 上下文重建已公开解决。这些细则正文和图中没有给出。

### 5.3 Coding / terminal 公开来源：这是来源库存，不是消费漏斗

Table 1（p.17）列出用于构造任务的公开 collection；数字逐格照原表，不擅自将 environment 数校正成任务数：

| Provider / Collection | #Tasks | #Environments |
| --- | ---: | ---: |
| SWE-bench / SWE-smith | 59,136 | 222 |
| SWE-Gym / SWE-Gym | 2,438 | 2,401 |
| R2E-Gym / R2E-Gym-V1 | 7,480 | 8,101 |
| Nebius / SWE-rebench-V2 | 32,100 | 32,075 |
| AweAI-Team / Scale-SWE | 20,200 | 19,472 |
| NVIDIA / Nemotron-Terminal-Synthetic-Tasks | 80,000 | 8 |
| RUC-AIBOX / ClawGym-Task | 13,500 | 1 |

来源含真实 GitHub issue/PR/history 挖掘与程序化/合成任务，覆盖仓库修复、调试测试、软件安装、文件数据操作和 terminal 工作。归一化方法是 materialize base repo/container/assets、issue/instruction 转目标、原 tests/reward program 保留为 verifier，保持来源特有执行与 reward 语义（§4.4.2）。

原文没有逐源“原始候选→构建成功→gold 验证→当前模型可解→最终训练消费”的数量，也没给跨源重叠、最终采样比例、来源 revision/许可汇总、repo/time split、去重与污染评估。R2E 的 8,101 environments 大于 7,480 tasks 是**原表值**；未解释计数定义，不能拿它计算镜像复用率。公开源库存相加也不是独立训练题量。

### 5.4 社区 skill 合成、离线轨迹与自演化

Fig.10、§4.4.2（p.17–18）提供另一条通用 agent 任务线：

1. 收集 community skills，过滤不可执行、不安全、低质量、冗余项，包括不可得认证、外部交易和有毒内容；按领域平衡重采样。
2. 建 skill-state graph：节点是可观察环境状态，边是 skill 提取出的状态变换；仅组合输入/输出状态兼容的能力。抽不同路径长度，形成多种 horizon/复杂度。
3. 依次生成 environment、task instruction、verifier；每阶段都有 executable validator。规则检查结构、依赖和可执行性，rubric 检查语义质量和阶段一致性；失败就局部 repair/regenerate，验证后才下传。
4. 验证任务进入 online RL，也产生 reusable offline rollout。outcome 过滤后逐步标注正常进展、工具错误、重复失败、错误恢复、过早结束、协议违规、无依据假设、虚构观察。错误步骤保留在 context 中，但可标 `skip`，不进 **imitation loss**，后续正确动作仍能利用其因果上下文。
5. 按 skill domain 和合成阶段汇总失败与 verifier 反馈，更新采样权重、合成 skills、环境模板及 prompts，再生成下一批。Fig.10 明示 reusable supervision 可用于 SFT / replay-based RL，但正文没有后者的单独目标和具体运行比例。

此处未给合成器/solver/validator 模型 ID、teacher 预算、每题重复次数、repair 上限、技能/任务数量或消融。不能把有流程图写成“已证明自演化优于静态数据”，也不能把离线 `skip` 等同下一节在线 `adv_penalty`。

### 5.5 Session credit 与 process advantage

同 task 的 rollout group 中，每个完整 session 一个 outcome reward；计算 group-relative `A_i`，广播给该 session 的全部 eligible policy segments，**不把每次模型调用当独立 episode**（p.18–19）。此节引用组相对范式，却没有给标准差/LOO 的具体公式，因此 agentic 的 `A_i` 不能强填为 §4.3.5 的 reasoning LOO，也不能声称其一定是标准 GRPO。

过程 annotator 为确定性错误消息添加 `adv_penalty`，**不改 session reward，不改 token labels**。PrefixTree 将消息映到准确 token span；对 segment k 的可训 token t（p.19，Eq.30）：

\[
\widetilde A_{i,k,t}=\begin{cases}w_{i,k}A_i,&A_i>0,\\A_i,&A_i\le0,\end{cases}\qquad w_{i,k}\in[-1,1].
\]

非可训 token advantage 置零。过程权重可抑制甚至反转成功 session 中错误行为的正 credit；非正 advantage 原样保留。可标错误包括 parse/格式、工具名/参数、重复或失败工具调用、context/turn/session limit 终止。原文没有给每类 w 的值或标注规则实现；这不是单独训练出来的逐步 reward model。

失败处理须拆开：有定义的 session 失败保留非正学习信号；超限可得到过程惩罚；但各种超时/截断/解析错误是否进入 group reward 统计、是否整条/整组丢弃、是否重试补采，并无完整表。也没有 agentic 完整 scalar loss 的 token/segment/session 分母公式；Fig.9 的 “clipping · IS · process weights” 不能补出这些细节。

### 5.6 Verifier integrity：已做什么、未证明什么

§4.4.3（p.19–20）披露：

- gold patch、held-out tests、精确 scoring test IDs 不放入 rollout workspace，仅评分基础设施在执行后使用；Git history 清为单 baseline commit、删 remote refs，必要时去掉暴露 upstream issue 的 task ID。
- agent 停止后恢复/覆盖 canonical tests，并在 agent source change 上应用 gold test patch，防止 agent 修改可见测试直接改变评分。
- SWE 用 all-correct 语义，target-fix 与 regression checks 都必须通过；存在 canonical expected test-state map 的任务要求观测结果精确匹配。
- 缺 grading 工件、执行故障、无法解析 verifier 输出单独记账，与真实任务失败分离，避免基础设施错误被认成策略成功。

这些措施不是无条件防作弊证明。原文没有 no-op/gold/合法替代解验证数量、重复评分稳定性、误杀率、测试 plugin/config 控制面、网络隔离或成本。不能从“恢复测试”推成所有 evaluator 控制面都不可改，也不能从“错误单列”推成错误必然全部丢组或给固定 0 reward。

## 6. OPD：两专家、warmup 与 sampled-token 训练

### 6.1 专家与学生是谁

§4.5（p.20）明确两位教师来自**同一个 SFT checkpoint**：mixed reasoning RL expert 与黑白盒 agentic RL expert。先让两专家生成高质量轨迹，对**原 SFT 模型**做轻量 SFT warmup；warmup checkpoint 才是 OPD 初始 student。动机是缩小 student 与 teacher 行为差异，使 teacher 能对 student 生成的前缀提供可靠信号。

作者的 preliminary evaluation 认为，为很多细域分别训练专家会增加 RL/infra 成本，额外收益有限；这是**该设置的定性经验判断**，没有对照表或金额，不能概括成“明确否决所有多专家方案”。两专家并不意味着两个外部商用 API，也没有证明 teacher 总成本低。

每 query 归 reasoning 或 agentic 域，选择对应 teacher；不是每个 token 混两份 logits。student 自己产生 trajectory，teacher 在相同 student prefix 上评分。原文以固定专家策略描述 OPD，但未给 teacher refresh 日程、精确 checkpoint ID 或跨 tokenizer 对齐实现；同 SFT 起源支持行为相容的动机，不是 tokenizer 等价性的单独检验报告。

### 6.2 理想目标与实际 surrogate 分开

令 `d∈{rea,agt}`，域 prompt 分布 `D_d`，域权重 `λ_d`，teacher 为 `π_Td`，student 为 `π_θ`。p.20，Eq.31–32 的理想 fully on-policy 目标最大化：

\[
J_{OPD}=\sum_d\lambda_d\mathbb E_{q\sim D_d,y\sim\pi_\theta}
\left[\sum_{t=1}^{H}\big(\log\pi_{T_d}(y_t\mid s_t)-\log\pi_\theta(y_t\mid s_t)\big)\right],
\]

作者将其表述为在 student-induced states 最小化 **reverse KL `KL(student || teacher)`**。序列求和的理想目标与后面训练 surrogate 的按轨迹长度归一化并非完全同一个权重口径；不能说 Eq.36 是无需近似或修正的逐字等式实现。

实际只传 student sampled token 的 teacher logprob，通信 payload 从 full vocabulary `O(HV)` 或 top-k `O(Hk)` 降到 `O(H)`（p.20–21）。作者点名 top-64 在最长 **256K sequence** 上仍有较大负担。此数是 OPD 上下文的 maximum sequence length 描述，不等于每轮新生成 256K，更不是所有评测预算；`O(H)` 仅指传输 teacher 概率的载荷，不代表 teacher forward 计算降为常数或无需完整词表归一化。

p.21，Eq.33–36：

\[
\widehat A_{i,t}^{OPD}=\operatorname{sg}[\log\pi_{T_d}(y_{i,t}\mid s_{i,t})-\log\pi_{prox}(y_{i,t}\mid s_{i,t})],
\]
\[
\rho^{OPD}_{i,t}=\pi_\theta(y_{i,t}\mid s_{i,t})/\pi_{beh(i,t)}(y_{i,t}\mid s_{i,t}),
\]
\[
L_{OPD}=-\sum_d\lambda_d\mathbb E_{\mathcal B_d}
\left[\frac1{N_d}\sum_i\frac1{|\mathcal T_i|}\sum_{t\in\mathcal T_i}
m^{BKL}_{i,t}\operatorname{sg}[\bar\rho^{OPD}_{i,t}]\widehat A^{OPD}_{i,t}\log\pi_\theta(y_{i,t}\mid s_{i,t})\right].
\]

这里 `π_prox` 是构造蒸馏信号用的**冻结 proximal student**；`π_beh(i,t)` 是生成 token 的行为策略；当前 `π_θ` 更新。三者不能混成一个 old policy。teacher 与 prox 的差决定方向，current/behavior ratio 修正 partial rollout 与更新差异；IS clip 区间与 reasoning RL 相同，数值未公开。prox 多久刷新未给。

`T_i` 为 policy-generated token 集，排除 prompt、environment observation、tool output、padding；每条除 `|T_i|`，域内 N_d 条等权，再乘域权重。BKL mask 乘入分子，**没有将分母改为 BKL 存活 token 数**。OPD 有 R3/BKL，但不将 reasoning 的 LOO、GEPO、长度正则塞进 teacher-token advantage。它也没有显示使用 reward 全同组过滤；不能从 reasoning 动态采样推断 OPD 会丢弃全失败组。

teacher 的 GPU/评分吞吐、warmup 数据量、λ_d、prox 刷新、OPD optimizer/step/batch、特权上下文与失败/截断轨迹处置未给。最大长度和 payload 阶数不足以复现训练成本。

## 7. 非 SWE 后训练：Memory Decoder 与时序

### 7.1 独立 Memory Decoder 的训练完整链

这是附加到冻结主干的领域专长模块，不是 agent 的会话记忆，也不是最终 OPD 的第三个专家（§2.1，p.2–4，Fig.1）。

领域 SFT corpus `D_sft={(q,a)}` 的答案 token 位置形成 datastore：prefix `c_t=[q;y_<t]`，冻结特征函数 φ 得 key，value 为目标 token。近邻集合 `N(k_t)` 形成 retrieval teacher（Eq.1）：

\[
p_{ret}(y\mid c_t)\propto\sum_{(k_j,v_j)\in N(k_t)}\mathbf1[y=v_j]\exp[-d(k_t,k_j)/\tau].
\]

训练 Memory Decoder（Eq.2）：`L_mem=β KL(p_ret || p_mem)+(1−β)(−log p_mem(y_t|c_t))`。这里是 **retrieval teacher→memory 的 forward KL**，不同于 §6 student→expert reverse KL。β 在 [0,1]，距离、近邻数、温度和具体数据规模未给。

推理时冻结的 397B 主干与 memory 并行处理同 context，router 取双方 hidden states、confidence/entropy 特征，预测 `λ_t∈[0,1]`，输出 `(1−λ_t)p_S2+λ_t p_mem`（Eq.3）。训练 router 时双方模型都冻结，只训练 router，使用领域与通用指令混合数据，loss 为 fused CE 加 `α_s s_t λ_t`，其中领域 s_t<0、通用 s_t>0、α_s>0（Eq.4）。即鼓励领域调用 memory、通用例子减少调用；具体权重与混合比例未给。

实例 Intern-MemDec-4B 在 21 个 Biology-Instructions tasks 上把报告平均分 **56.92→60.32，+3.40 分**（约 +6.0% 相对变化）；不是 +6 个百分点。Fig.12a 全部子任务已核：14 个提高、7 个下降，下降为 DNA-tf-h 56.57→55.99、antibody-antigen 40.24→36.44、siRNA efficiency 63.05→60.63、Protein-FunctionEC 61.88→60.10、Solubility 68.60→68.00、Stability 69.67→67.80、Thermostability 58.44→53.97。较大增益有 promoter-enhancer interaction 22.46→38.47、CRISPROnTarget 6.61→17.18（p.26）。

Fig.12b 各类轴做 task-specific normalization，不能按图形面积计算整体增益；蛋白类别下降。Fig.12c 另外比较 MMLU Pro、Mol-Instructions、MMMU Pro、MicroVQA、IMO-Answer-Bench、SFE，作者描述与冻结主干接近，图未提供新一轮全部精确值/误差或完整 agentic 回归测试；“主干不更新”也不保证融合系统所有域行为不变。

### 7.2 Time-series 模块与结果

§2.2（p.4–5，Fig.2）：按时间 chunk，normalization 保留 channel mean/std，CNN 提局部特征，Q-Former 压缩 patch；动态 patching 控 token 长度，新增 channel-wise Transformer 学跨通道关系，再做全局时序 Transformer。输入上限由约 240,000 增到 300,000 time steps；最大长度处报告 encoder 推理 5–6× 更快、GPU memory 为原版约 20%，但无硬件/绝对时间。不是全模型 RL 加速。

数值 forecasting 独立分支从 LLM semantic context 与 encoder temporal representation 经 Q-Former 抽取、cross-attention 条件化 causal Transformer，horizon predictor 判断预测长度。避免将全部数值作为离散文本生成；本报告未给该分支 loss、训练数据配比、冻结策略或是否单独参与 RL。

Table 4（p.25）的 11 个 SciTS understanding task 报 F1：S2 依序为 ASU01 97.1、ASU03 91.0、BIU01 36.5、BIU03 98.3、EAU01 100.0、MEU01 81.8、NEU06 70.2、PHU01 66.9、PHU04 99.9、RAU01 88.4、RAU02 60.2。两模型共有九项中七项超 S1-Pro，ASU01 98.0→97.1、NEU06 71.3→70.2 退步；新增雷达两任务不能当旧模型原先 0 分。PHU01 为 36.8→66.9。

Table 5（p.27）预测结果为 **MAPE（成功率%）**：ENG02 60.2(100)、ENG03 7.1(100)、MEG03 32.8(100)、NEG03 59.2(100)、PHG02 72.2(100)、URG01 138.9(100)、URG05 60.6(100)。MAPE 越低越好，成功率另计，100% 不表示预测误差为零。原文归因 text/VL 方法低成功率于输出长度与格式失败；没有给失败如何进入 MAPE 分母的完整规则。

不可照抄“全部最低”：NEG03 Moirai-Large 为 59.1(100)，略优于 S2 的 59.2(100)；DeepSeek-V3 是 4.3(3.1)，其很低成功率使单看误差会误导。horizon predictor accuracy 99%，GIFT-Eval zero-shot MASE 0.785，是另外两个指标（p.26），不与表中 100% 混用。

## 8. 评测、消融与负结果

### 8.1 科学、多模态与通用覆盖

下表数值来自 **397B** 的 Table 2–3（p.24–25），benchmark 描述来自 §5.1（p.22–24）。这些是原报告的 score，不能全部改标 pass@1 或统一成功率；题库规模也不等于每项实际运行样本分母。

| 领域 / benchmark | S2 分数 | 原文任务与设置要点 |
| --- | ---: | --- |
| Biology-Instructions | 56.92 | 多组学生物序列；另有 §7 的 21 task memory 研究 |
| Mol-Instructions | 52.37 | 分子、蛋白、生物分子文本三类指令 |
| MolecularIQ | 61.49 | SMILES 图推理；5,111 问题、849 个结构 held-out 分子；计数、索引、约束生成 |
| SciReasoner | 63.97 | 九领域、149 concrete tasks、十子基准；选择/填空/程序协议 |
| TOMG-Bench | 65.66 | 编辑、属性优化、定制分子；各三子任务、每子任务 5,000 tests；有效性/约束/相似与新颖 |
| MP20 | 67.88 | ≤20 原子晶体条件生成；描述 27,136 train/9,046 test；§5.2 称实际采用 internal evaluation set |
| ProteinBinder-9 | 4.36 | 九靶点 binder 设计；多阶段结构/物化检验，涉及 RFdiffusion、AlphaFold 3；§5.2 同称 internal set |
| XLRS-Bench | 51.97 | 超高分辨率遥感；16 subtask，感知/推理 |
| MicroVQA | 68.81 | 1,042 专家显微 VQA；图像理解、假设、实验设计 |
| SFE | 61.67 | 830 VQA、66 task、五科学领域 |
| ObsCrisis-Bench | 26.07 | 4,202 VQA、127 events、八灾害类、61 国；多时刻观察与可选站点信息 |
| MMLU-Pro | 89.75 | 多学科知识推理 |
| SimpleQA-Verified | 69.90 | 1,000 人工核题；无检索，评分区分正确/错误/未尝试 |
| AdvancedIF | 74.44 | 1,645 prompt、最多 20 独立 rubric；全部适用约束满足才成功 |
| HMMT-2026 | 91.57 | 2026 年 2 月竞赛 33 题；具体重复次数未给 |
| MMMU-Pro | 80.46 | 专业多模态理解推理 |
| ChartQAPro | 69.65 | 1,341 图、1,948 问、99 来源；数理/视觉、对话、事实核查、假设 |

ProteinBinder-9 描述称应报告每靶点 passing count 与 fraction，但当前报告仅总表标量 4.36，未提供每靶点候选分母/成功数，不强解为“4.36% 已验证湿实验成功”。MP20 与 ProteinBinder 的 internal set 表述也限制公开复现。以上评测展示科学能力广度，但没有 SFT、两 expert、warmup、OPD 分阶段的同条件分数表。

### 8.2 Agentic 评测：模型、harness 与预算必须绑定

| Benchmark | S2 分数 | harness / 已披露设置 | 关键限制 |
| --- | ---: | --- | --- |
| SciCode | 49.11 | 80 main/338 subproblem、16 科学子域；可选背景/参考解/可执行 tests 的基准描述 | 是否启用背景、实际 split/harness 未给 |
| SGI-Bench | 49.37 | 1,263 专家样本、十领域、75 research directions；deep research/idea/dry-wet experiments/multimodal reasoning | 多维评分；非单一代码 pass@1 |
| ResearchClawBench | 18.44 | **ResearchHarness v0.0.49**；40 题/十领域，从原始数据与文献写报告，隐藏目标论文，专家多模态 rubric | 完整 run token/time/repeats 未给 |
| SkillsBench | 50.03 | **OpenClaw 2026.5.7**；87 task/八域，skills+deterministic verifier | 基准有 with/without skills 比较设计，但此表未列一对控制分数 |
| Terminal-Bench 2.1 | 67.42 | **Terminus 2**；89 task；2.0 中 28 题修订；部分结果来自 Artificial Analysis | 不应混成全部模型统一重跑；per-model预算未给 |
| SWE-Bench Pro | 61.56 | **Mini-SWE-Agent**；修改官方 eval image，防 git log 暴露 ground truth | 1,865题/41 repo 是总库描述，未写所用 split/实际分母/镜像 digest |
| SWE-bench Multilingual | 81.67 | **Mini-SWE-Agent**；300题/42 repo/九语言；F2P 和 P2P | agent version、采样与时间预算未给 |
| WildClawBench | 44.68 | 原生 CLI、中英多模态、真实工具与长流程 | 本实验具体 harness/version/预算未给 |

所有表中 comparator 为 Qwen3.5-397B-A17B、DeepSeek-V4-pro、Kimi-K2.7-Code、GLM-5.2、GPT-5.5、Gemini-3.1-Pro、Claude-Opus-4.8。它们不是统一底座或同训练成本的消融；本文不验证这些远端服务当前榜单。

对项目最相关的差距：TB2.1 67.42 vs GLM 77.90 / Claude 84.60；SWE Pro 61.56 vs 62.10 / 69.20；Multilingual 81.67 vs GLM 82.00（Table 3）。报告称科学 agentic “second only to GLM”不能逐项理解：SciCode 上 S2 49.11 低于三个闭源对照及 GLM；SGI 的 Kimi 50.63 也高于 S2 49.37（Table 2）。应保留数表，而非复述宽泛排名。

### 8.3 方法消融与证据强度

| 实验 / 原文 | 能支持什么 | 不能支持什么 |
| --- | --- | --- |
| Fig.8，p.12，35B 长度正则有/无 | 所示约 1,800 training steps 内，长度更短、reward 曲线接近 | 397B 或所有 test 上无退化；固定算力优势；图中淡色不是已定义置信区间 |
| Fig.11，p.19，160 optimization steps | SWE、General、Terminus 三面板及多个 harness 的代表性优化轨迹，有上升或回升 | 全部 RL 总步数、跨 harness 绝对 reward 可比、未见 harness 泛化或组件因果效应 |
| §4.3.3，p.13，2× / 1.7× | 作者报告在线 draft 系统的生成/端到端不同加速口径 | 绝对 GPU-hour、硬件迁移收益、partial rollout 独立加速比例 |
| Fig.12，p.26 | 冻结 backbone 后 memory 插件有领域平均增益，同时有七项退化 | backbone 不变即端到端能力完全不变 |
| Table 4–5，p.25/27 | 时序模块在多任务和不同成功率下的效果 | 单独由后训练带来的增益，或每项 MAPE 都最佳 |

Fig.11 已核全部曲线：SWE 有 Claude Code/Mini-SWE/OpenClaw/OpenCode/OpenHands，General 为 Claude Code/OpenClaw，terminal 面板含 Terminus。SWE/terminal 某些曲线先下降再恢复，不能删掉这种 transient 后写成单调稳定提升；图注明 local smoothing，没有 seed 数、方差或统一起点条件。

没有 OPD 相对 warmup/experts 的完整对照、GEPO/R3/BKL/两专家/技能反馈逐项消融，也没有训练数据泄漏审计的量化结果。§6 把系统称作 preview，并把长流程可靠性、更多领域 memories/任务环境、强化 verifier 与专用科学工具集成留作未来工作。

## 9. 成本、开放资产与未披露边界

### 9.1 成本与复现程度

数据生产/人工校验、teacher 轨迹与评分、RL learner/rollout、最终 eval 四类成本均没有 GPU型号×数量×时长或 API/CPU 金额。8,192 response/batch、65,536 generation、256K sequence、两个 teacher 是配置/结构信息，不是预算。没有公开最终任务消费清单、SFT/OPD数据、完整 launch 配方或论文实验对应代码 commit。

[XTuner README 固定版](https://github.com/InternLM/xtuner/blob/76e705134521eff867b409f3b3451df1c4d8dd36/README.md) 提供训练框架入口且列有 GRPO，但其 roadmap 将 Multi-turn Agentic RL 标为 Coming Soon。此处与论文指向框架链接形成**公开入口不等于论文完整实现已核实**的证据边界；README 可能落后于代码，不能仅据这一行断言实现绝对不存在。本次未逐文件验证全部 agentic 训练实现。

HF [固定版模型卡](https://huggingface.co/internlm/Intern-S2-Preview/blob/4f57cab513689b089019fce4ad24e26520df183c/README.md) 标 Apache-2.0，模型仓库 metadata 有权重文件条目，未下载权重。该卡对象为 35B；其“文本128K/多模态64K评测长度”和 `temperature=0.8, top_p=0.95, top_k=50` 推荐仅属该卡对象，**本文不用于补填397B论文**。论文指定链接不足以核实397B主表权重、两个expert、warmup student、MemDec均已公开可下载。源数据许可仍须逐来源检查，不能由模型/框架 Apache-2.0 推到所有训练数据。

### 9.2 未披露项与查阅范围

| 未回答的问题 | 已查原文 / 材料 | 为什么影响复用 |
| --- | --- | --- |
| SFT数量/混合、过滤阈值、全部teacher/validator名称 | §4.2、§4.4.2 | 不知道样本生产成本及质量控制分母 |
| RL具体任务reward/尺度、G、学习总量 | §4.3–4.5、全部图表 | 不能靠benchmark列表或batch反推训练配方 |
| IS上下界、BKL φ、GEPO阈值/系数、length τ/α/γ | §4.3.1–4.3.5、Eq.10–29 | 公式可理解，数值无法直接复现 |
| agentic完整loss/分母、group baseline、失败与截断统计和补采 | §4.4.1–4.4.3、Fig.9–11 | reward、组成员、梯度三者不能压成一布尔值 |
| compaction/rewrite、共享prefix分支计权、跨版本 matched BKL计算 | §4.3.1、§4.4.1、§4.5 | “精确存token”不自动解答完整训练投影 |
| teacher/prox版本与刷新、OPD特权context/tokenizer策略、warmup量/域权重 | §4.5、Eq.31–36 | sampled logprob 通信轻不等于调用/训练轻 |
| 训练与评测 GPU/并行/时长、temperature/top-p、session/工具wall-time | §4–5；35B模型卡只作版本对照 | 无法做matched budget对照或推算八卡成本 |
| env验证漏斗、去重split/污染、gold/no-op/替代解/flaky统计 | §4.4.2–3、Table 1、§5 | 公开库存与防漏原则不能替代数据有效性证据 |
| Memory/时序训练完整数据、scheduler、超参数 | §2、§5.3、Fig.12、Table 4–5 | 有机制和结果，不是完整专项训练recipe |

边界用语：公式/表格为**论文事实**；“同源更稳”“很多细域teacher收益有限”“harness引起不同训练动态”为**作者解释**；分母含义与不具控制条件的判断是**阅读者分析**；下节全部为**项目候选建议**，不是训练定案。

## 10. 对 RepoHarness 项目一的候选映射

映射日 2026-09-07；读取主资料 checkout 的 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6` 和实际 `reference/miles-rh2-integration` HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`，不以隔离 worktree 默认分支冒充当前集成。背景为当前简报〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕（09-05）及项目一建议〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕（09-07，咨询而非定案）；后者指出黑盒上下文变化后的覆盖与消费仍须验证。此处只核必要模块，不作全仓审计或 GPU 状态声明。

| 候选借鉴 | 来源依据 | 归属与限制 | 最小可验证问题 |
| --- | --- | --- | --- |
| 精确token与语义轨迹分离后按调用拼接 | §4.4.1 TITO/PrefixTree | miles/SGLang已有token捕获/R3能力优先复用；rh2增量是实际harness rewrite/分支后的覆盖与计权 | 固定真实Claude Code请求序列，核生成动作→训练token、共享prefix重复率、logprob/版本对应 |
| 完整session计reward，按token计训练但保持execution权重 | §4.4.3；Eq.29/36有明确不同分母 | rh2需核当前契约；不得把论文未给的agentic分母补成我方规则 | 固定同一execution拆成不同segments/leaf后，正确参考计算是否保持预期loss/梯度 |
| Git历史清理、评分测试后置与故障分类 | §4.4.3 | rh2现有环境/评分责任，优先检查所选taskset；非新建通用平台 | gold/no-op/合法替代解及实际pytest控制面小例，报告错误归因与成本 |
| sampled-token teacher评分与warmup | §4.5 | 上游OPD能力应窄接；是否值得做由项目失败诊断与预算决定 | 小批学生轨迹核teacher/prox/beh三列与mask，分别量teacher成本和效果；不先造两专家 |
| clipped IS、GEPO、长度正则 | §4.3 | 外部算法对照，**不自动替换**faithful DIS或引入额外reward | 仅在现有正确基线后、有瓶颈假设时做一项固定预算对照 |
| Memory Decoder、数值时序、完整自演化skill平台 | §2、§4.4.2 | 当前SWE首版暂不适用；只保留领域参考 | 不加入首训完成条件 |

实际核过的项目代码定位（均为主 checkout 的读取状态，部分最新材料可能未提交）：

- `rh2/src/repoharness2/adapters/slime/capture_wire.py` 的 `install_capture_wire`/内层 `rh2_call_sglang_generate`：接收 prompt IDs，注入 routing/sampling-support 捕获并暂存。这能定位现有接线，但不证明所有 rewrite 的 PrefixTree 语义已满足。
- `rh2/src/repoharness2/adapters/miles/canonicalize.py` 的 `_convert_slime_sample`：复制 tokens、loss_mask、weight_versions、rollout_log_probs、teacher_log_probs。存在字段映射不等于 teacher 分数已经生产并消费。
- `rh2/src/repoharness2/adapters/miles/faithful_dis_loss.py` 的 `faithful_dis_loss_function` 及模块分母说明：当前为 execution provenance token 分母，区间外 DIS 权重置零；论文 Eq.11 是 ratio 裁到边界，**两者梯度语义不同**。不能把外部 clipped-IS成功当faithful DIS正确性验证。
- 集成 `reference/miles-rh2-integration/miles/rollout/fully_async_rollout.py` 已有 consume-time staleness 相关路径与说明；本篇共置方案的“3 updates”只作外部参数案例，不能替代当前N的项目决策。

这篇支持的简历叙事是“真实 harness 的动作、token、概率和评分之间有重要训练边界”，不支持“我方原创TITO/异步/OPD”或“已实现论文等级提升”。我方贡献必须以自身真实轨迹、目标GPU、正确基线、固定held-out及成本数据证明。

## 11. 对旧稿的更正与快速定位

旧摘要总体正确识别两专家分支、RLOO、TITO与sampled-token OPD；本次保留而非推翻这些内容。需要收紧或补充：

1. “正样本/pass rate”改为 Eq.14 的**正 advantage 集合及比例**；非二元reward不可随意等同正确/错误标签。
2. “明确否决 fine-grained 多teacher”改为本设置的 preliminary qualitative evaluation，未给一般性否决证据或定量成本。
3. “agentic按GRPO算advantage”只保留 group-relative 范式，具体baseline、标准差和loss分母未披露。
4. “框架随XTuner开源/权重链接”改为版本化入口检查；当前HF卡为35B、XTuner README的agentic roadmap仍标coming soon，未核完整397B复现资产。
5. 补全独立Memory训练公式与退化、时序任务负结果、科学/通用全部评测、LOO/OPD的精确归一化、两类mask与process权重差别，以及GEPO排印疑点。
6. 旧稿“同构/可直接进入资格标准”改为§10条件映射；本论文并不证明当前rh2实现或为项目修改训练语义授权。

检索入口：推理公式→§4/Eq.10–29；token捕获与重分词→§5.2/Fig.9；任务漏斗与验证→§5.3–5.6/Table 1；OPD与teacher预算→§6/Eq.31–36；全部评测/负结果→§7–8/Fig.8/11/12、Table 2–5。已存在的关联笔记：miles工程精读〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕、CalibForge〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md`〕、KAT-Coder-V2.5〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md`〕。第二批关联来源 E7/E8/E9/E11/E12 仅保留编号，待各自交付后由主线程建立链接。

## 12. 独立检查与修订记录

初稿日期：2026-09-07。主阅读任务 ID `01a07827-1e43-76b3-a7b5-927d16ceab97`；实际会话配置已核 `gpt-6-astra` / `high`。派工来源任务 ID `01a077c4-9f0d-7ef0-a40a-688b42f1b294`。

固定初稿副本为 `sources/E10/E10_intern_s2_preview.initial-20260907.md`；交审后保持该副本与正文不变，收到审查结果才修改正文。审查范围为原文全部后训练与所有图表、非SWE领域、公式/预算/因果/未知项及项目映射，不以重点问题代替全篇。

独立审查已于 2026-09-07 完成，见审查报告〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/10_E10_review.md`〕。唯一审查子线程 ID `01a0782f-d4e7-7691-ade5-f3ce907e50cb`，agent `/root/e10_independent_review`；实际配置 `gpt-6-astra` / `high`、`fork_turns="none"`，已核真实会话记录与父子关系。

结果为 **0 项必须修订的技术错误或整块遗漏**；审查逐项核了所有正文后训练、12图/5表、关键公式、资产边界和项目映射。主作者收到并完整阅读报告后，仅更新本节审查状态、子线程与报告链接，没有修改已通过的技术正文；固定初稿保持不变。没有虚构纠错或追加一轮未执行的复核。原文GEPO排印、agentic完整loss/失败处置、teacher预算等残余未知仍按§9保留。修订日期：2026-09-07。

技术精读与独立审查流程已完成；链接与专属文件发布的最终检查记录见审查报告第5节。


---

## 文档 6 / 7：E5_swe_smith.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/E5_swe_smith.md`

# E5 · SWE-smith: Scaling Data for Software Engineering Agents：环境与训练精读

SWE-smith 的核心是先固定可执行的仓库版本，再在同一环境中制造、验证大量 bug，摊薄环境构建与存储成本。论文 v2 报告 100,074 个候选产生 50,137 道任务；在 8,686 道唯一任务上作 17,906 次专家尝试，获得 6,457 条成功轨迹，再限制每题最多三条，形成 5,016 条 SFT 数据。Qwen2.5-Coder-32B-Instruct 经成功轨迹微调后，在 SWE-bench Verified 达到 40.2% pass@1。该结果支持合成环境用于 SFT；论文没有 RL 实验。尤其应保留三条边界：有效任务不等于高学习价值，测试通过不等于需求与评分已完整对齐，仓库排除也不等于无污染。附录中的多语言迁移弱、重复动作干预无收益以及多处数字冲突都影响实际借鉴。

导航：来源与覆盖 · 环境漏斗与合成 · 训练与轨迹 · 评测和负结果 · 当前代码与资产 · 项目映射

## 1. 来源、版本与阅读范围

- **论文**：John Yang、Kilian Lieret、Carlos E. Jimenez、Alexander Wettig、Kabir Khandpur、Yanzhe Zhang、Binyuan Hui、Ofir Press、Ludwig Schmidt、Diyi Yang；Stanford、Princeton、独立研究者、Alibaba Qwen。[arXiv v2](https://arxiv.org/abs/2504.21798v2)，2025-05-21；v1 为 2025-04-30。阅读日期 2026-09-07。
- **主文本**：本地原 PDF〔仓库引用：`docs/harness_improve/external_paper_references/pdfs/E5_swe_smith_2504.21798.pdf`〕，46 页，物理页与印刷页均从 1 起且一致；下文 p. 指这份 v2。另存阅读副本〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/paper.pdf`〕、完整提取文本〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/paper.txt`〕、v2 TeX 压缩包〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/arxiv-v2.tar.gz`〕与入口〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/tex/main.tex`〕。未用后来的会议版替换 v2；官方代码首页的 NeurIPS 2025 D&B Spotlight 标签只作后续发表信息。
- **官方实现 C**：[SWE-bench/SWE-smith](https://github.com/SWE-bench/SWE-smith/tree/9b74ac08118a85c39c356802f7961893af73e07f)，本次读取 HEAD 固定为 `9b74ac08118a85c39c356802f7961893af73e07f`。下文 C: 后均给完整仓库相对路径；源码快照〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/official-code/README.md`〕。这是当前实现，不是论文发布时的 commit。
- **资产与 RL 线索**：官方 HF 模型/任务/轨迹卡、官方训练指南；README 的 SkyRL 链接、SkyRL 当前 SWE 示例及2025-06-05历史`swe-smith`接入提交作有限追踪，版本及限制见 §7；来源登记〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/SOURCE_MANIFEST.md`〕保存完整版本入口。没有下载权重、完整数据或镜像，没有执行训练/环境构建。
- **旧稿**：summary_swe_smith.md〔仓库引用：`knowledge/summary_swe_smith.md`〕，在独立读完正文与附录后对照；更正见 §9。项目背景是当前状态简报〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕与项目一设计建议 §3〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕，不作为论文事实来源。

先由 `main.tex` 的实际输入结构与 PDF 建立以下覆盖；随后逐块通读，表格和算法对照 TeX，关键数字回渲染页。参考文献 p.11–15 只用于出处导航，未逐篇展开；没有其他未读的后训练章节。

| 原文范围 | 内容与读取深度 | 本笔记位置 |
| --- | --- | --- |
| 摘要；§1 p.1–2；图1–2 | 全读：问题、环境优先方法与贡献；图1估计口径另核 G | §2、§4–6 |
| §2.1–2.2 p.3–5；表1–2、图3 | 全读：安装、合成、验证、题面、规模成本和难度 | §2–3、§6、§8 |
| §3–4.2 p.5–9；表3–5、图4–8 | 全读：SFT、消融、行为分析、预算 | §4–5 |
| §5–6 p.9–10；致谢 | 全读：相关方法差别、Python 限制、未做 RL、计算支持 | §4、§6 |
| 附录总览 A p.16；图9 | 全读：安装/合成/验证/轨迹/训练的产物流 | §2、§4、§7 |
| A.1–A.3 p.17–19；表6、图10 | 全读：字段、许可、人工安装审核、验证接口 | §2、§6、§8 |
| B.1–B.4 p.20–27；图11–16、表7–8、算法1–2 | 全读：所有 bug 生成策略、参数、提示词与 PR 案例 | §3 |
| C、C.1–C.2 p.27–35；仓库长表、表10–12、图17 | 全读：仓库范围、统计、存储及 Flask 案例；长表按类别检查 | §2–3、§6、§8 |
| D p.35–36；表13、图18 | 全读：四种题面及 Verified 示例、泄漏边界 | §3、§5 |
| E p.37–38；图19、表14 | 全读：额外的难度评分器 LoRA 训练与分类分布 | §4.1、§5.3 |
| F.1–F.3 p.38–42；图20–21、表15–18 | 全读：SFT/ACI/序列化、所有评测集、轨迹组成 | §4–5、§8 |
| F.4 p.42–43；图22–23 | 全读：pass@k、拒绝采样消融、多语言负结果 | §5 |
| F.5.1–F.5.4 p.43–45；图24–27（图27在p.46） | 全读：预算代理分析、动作定义、失败分类、重复缓解负结果 | §5.4 |
| G p.45–46 | 全读：图1对比曲线的估计方式、Web轨迹相关工作、重放失败尝试 | §5.5、§6 |

## 2. 环境优先：从原始仓库到可用任务

### 2.1 核心机制与数量漏斗

传统 SWE-bench 路线先找真实 issue/PR，再为各历史状态构建环境；SWE-smith 先把一个 `(repository, commit)` 安装好、测通，再把 bug 写进这个固定版本。因此 **一个基础镜像可以承载许多不同 bug 分支**。这里复用的是安装与基础环境，不是把多个运行的可写状态混用，也没有证明在线 RL rollout 的复用吞吐。论文 p.3 §2、p.34 C.1。

| 阶段 | 数量、对象与分母 | 筛选/处理 | 原文定位 |
| --- | --- | --- | --- |
| 搜索池 | 2024-11-18 PyPI 下载前 5,000 个包 | 按 GitHub stars 排序；排除 <1,000 stars、12 个 SWE-bench 测试仓库；检查许可、Python 为主 | p.3 §2.1；p.17 A.2 |
| 环境安装 | 报告 128 仓成功；人工审核另放弃 17 仓 | 原版本 >80% 测试通过；SWE-agent 给安装/测试操作，人手确认并写 Dockerfile/输出 parser | p.3；p.19 A.2 |
| 候选 bug | 表10总行 100,074 个候选 | 五类统计（LM两种）；同文件/模块组合输入已是验证过的 bug | p.32 表10 |
| 验证成功任务 | 50,137，候选存活率 50.1% | 必须打破至少一个原本通过的测试；测试执行超过两分钟丢弃 | p.3 §2.1；p.32 表10 |
| 环境发布规模 | 主文 128 仓、295 GB；附录另写 125 镜像、290.54 GB | 数字不一致，不能强行合成“128个镜像实测295GB”；详见 §8 | p.4 表2；p.34 C.1 |
| 生成题面 | 报告支出覆盖 10K bugs；不是已证 50,137 全都有生成题面 | LM 输入 bug diff、F2P 源码与日志；实际最终消费任务数另见下行 | p.4 §2.2；D |
| 专家采样覆盖 | 8,686 道唯一题，占 50,137 的 17.3%；共 17,906 次尝试 | 跨消融与补充采样，不是每题统一采两次或三次 | p.5–6 §4；p.41 表16 |
| 成功轨迹池 | 6,457 条 /17,906 次尝试 ≈36.1% | **不是 36% 唯一任务被解出**；已解唯一题数没有清楚披露 | p.6 §4 |
| 最终 SFT 数据 | 5,016 条轨迹，123 个仓库；91 仓至少10条 | 每题成功轨迹最多3条；最终唯一题数、token数、确切优化器消费计数未给 | p.6；p.42 F.3、表17 |

128+17=145 只是在人工审核描述下能加出的数量；没有完整初始仓库尝试日志，不能用 128/145 当作从 PyPI 搜索池到环境可用的全流程成功率。表10总行另写129仓，见 §8。

**安装仍有人力。** p.19 A.2 的安装专家是 `claude-3-5-sonnet-20241022`，上限 $2、150 calls，平均 $0.72、17步、通常两分钟内结束；初始只有 clone，没有先替它装包/配 conda。人工复核每仓3–20分钟，128仓约18小时，另有 parser 等使主文总人力约20小时（约7分钟安装提取+1分钟 parser/仓）。p.3 主文安装最多100步与附录150 calls 不一致。不能表述为完全自动化或确定的“100步复现配方”。

### 2.2 任务字段与验证的方向

A.1 p.17 定义 `repo`、`instance_id`、`base_commit`、`patch`、`problem_statement`、`created_at`、`FAIL_TO_PASS`、`PASS_TO_PASS`：

- `patch` 是**从正确代码引入 bug 的 diff**，反向应用才是参考解；`base_commit` 指向已经施加 bug 的分支状态。不能照搬 SWE-bench 修复 patch 的方向。
- `created_at` 是 bug 被验证并推送到镜像仓库的时间，不是原始 PR 时间；PR 派生时间切分须另保留源 PR 信息。
- 没有 `hints_text`、`test_patch`，也不需按历史版本配置的 `version`、`environment_setup_commit`。论文 **不合成隐藏测试，F2P 测试在 agent 推理时可见、可运行**。
- 引入 bug 后失败、恢复正确代码后通过的测试构成 F2P；P2P 表示不受 bug 影响的回归测试。A.1 简化成“全部测试减F2P”，但原环境只要求 >80% 测试通过，不能据此认定原有失败/跳过也都应纳入 P2P；当前代码按状态交集分类，见 §7。

验证发现“补丁确实造成回归”，**并不证明**自然语言需求完整、不存在投机解、测试稳定、合法替代解不被误杀。p.35 C.2 明说未检查题面欠明确和答案泄漏，当前产物不宜直接用作正式评测；作者提议移除 F2P 测试并审核题面，但这只是未来改法。Bug patch 的逆向恢复提供参考修复构造，却不能冒称本文实施了完整 no-op/gold/alternate-solution 多门审核或防作弊隔离。

## 3. 全部合成方式、可控性和任务质量

### 3.1 Bug 生成

下表候选成本仅是表1的**生成一个候选**的平均 API 成本；不是每个通过验证任务成本，更不含执行验证与轨迹采样。表10给可复核的分母。

| 方式 | 候选→验证任务；存活率 | 表1候选成本 | 机制、收益与限制 |
| --- | --- | --- | --- |
| LM Modify | 31,950→17,887；55.98% | 0.38美分 | ast 找非测试目录函数/类，让 LM 改出逻辑 bug；提示不要标注 bug 位置、改签名或制造语法错误。开放提示仍常产生赋值错误，质量/多样性弱 |
| LM Rewrite | 11,908→4,173；35.04% | 3.93美分 | 移除目标函数实现，但给**其余完整文件上下文**、签名/docstring，要求正常重实现；收集重写意外造成的错误，不是明确指示写错 |
| Procedural | 各子策略合计 38,866→15,641；40.24% | 0 | AST 条件筛选后随机变异，无生成 API 费，但有 CPU/测试成本；13种操作见下文 |
| Combine | 6,020→5,865 同文件；4,396→4,227 同模块；合计96.89% | 0 | 从已验证 bug 组合、再验证，所以不能与从零候选方法无条件比96.9%的质量 |
| PR Mirror | 6,934→2,344；33.8% | 5.53美分 | LM 根据历史 PR diff 重写当前文件以撤销当年的改动，聚合为一个 bug；当前版本其他逻辑可能已变，原 issue 不一定仍准确 |

来源：p.20–27 B、p.4 表1、p.32 表10。LM bug 主要用 `o3-mini-2025-01-31`（p.22）。LM Rewrite 不是“只看到签名/docstring”：正文缩写必须由图13和B.1补全。论文没有充分试验多种提示词或每函数多次 buggy rewrite。

**程序化筛选与13种变换（p.22–23，表7–8）。** 先确认函数/类、继承、循环、条件、赋值、try/with、if/else、运算符及复杂度上下限是否适用。复杂度是条件、循环、布尔运算、异常块和比较运算的计数和；用于避开 getter/setter 和部分过长函数，不是学习难度标签。13种操作为：删类方法、删父类、打乱类方法；颠倒 if/else、打乱函数行；常数±1、拆运算链、调换操作数、改运算符；删循环、删条件、删赋值、删 try/with 包装。`likelihood` 控制实体内部每次变换概率，避免一次破坏太多；论文没有给所有策略的统一最终概率。各子策略差异大：类方法乱序47/2504=1.88%，if/else颠倒2321/4695=49.44%（表10），不能把“程序化40%”外推给任何变换。

**组合算法（p.24–26，算法1–2、图15）。** 同文件从该文件已验证补丁生成有限组合，依次尝试应用，成功后保存并重新验证；删除后续与已用组合共享原始补丁的候选，减少重复。典型 `num_bugs=[2,4]`、`limit_per_file=3`、`max_combos=40`。同模块先按路径及 `depth` 合并补丁池，再组合，要求最终改≥2文件；典型 `[2,5]`、`limit_per_module=10`、`max_combos=100`、`depth=2`。这些是有限搜索参数，不是自动课程或 RL group 规则；论文没有展示 Combine 的单独等量 SFT 效果。原伪代码局部变量命名不齐，笔记保留机制而不声称可直接执行。

**PR Mirror（p.26–27）。** 通常爬2023-01-01以后PR，少数仓库任意放宽；不尝试改>8文件的PR。直接 `git apply --reverse` 往往因代码位置变化失败，作者检查 sqlfluff 100 PR 后采用 LM。它不要求 PR 引用 issue 或改测试：题面可合成，现有测试决定是否构成任务。Django 100个随机 SWE-bench PR 的 sanity check 恢复92个，其中84个 F2P 相同，8个只剩部分 F2P，因为原测试后来移除。此100题检查不是所有PR的92%产率；此处 Django 是方法验证案例，不应混入主 SFT 训练仓库叙述。作者推测重建 SWE-bench 可少10倍人时、API $126.17，未做全量对照实验。

### 3.2 题面生成、测试可见性和难度来源

D p.35–36 的四类题面：① LM 生成：随机拿一个 **SWE-bench Verified 题面作风格示例**，另给 bug diff、F2P 列表、一条F2P源码及日志；② 固定模板；③ 随机一条F2P源码+日志；④ PR 原始关联 issue（只有部分PR支持）。图18要求别直接解释修复/原因或暴露 pytest 测试名，并尽量提供复现代码，但没有自动泄漏审查；提示词要求不是验证保证。题面生成模型的确切版本未在 D 明确给出，不能把 bug generator 的 o3-mini 自动移作 issue generator。

表13实际有9个模板，概率为0.05/0.10/0.15/0.10/0.10/0.05/0.15/0.15/0.15，和为1；信息从无提示，逐步增加文件、函数、测试和 bug 类型。D 文字写7个，与表不符。原始 issue 只覆盖708个PR任务；D 的分母2345与表1/10的2344相差1。第③种只在题面披露一条F2P，不等于其他测试从仓库隐藏。

任务覆盖不只看题数。p.33 表12中 Combine/F2P中位数15、LM4、PR3、Procedural7；Combine改函数中位2、PR2、其余1。图17显示相较既有数据更多多F2P任务，文件/行修改分布与Verified相近；这是当前配比的分布，调高组合比例可改变它。作者把更广测试覆盖解释为更多功能暴露，这是机制假说，未单独证明相同token预算下的迁移收益。

## 4. 后训练：两条独立学习流程

### 4.1 辅助难度评分器也是后训练

附录E p.37–38训练一个**任务难度分类器**，不是agent reward model或critic：1699条SWE-bench人工标注，通常每题3人，取多数；无多数取中位。原四档 `<15min`、`15min–1h`、`1–4h`、`4+h`，因最后一档稀少，把后两档合成`1+h`。按类别分布作80/20随机train/test，用题面和参考修复patch作输入、难度档作监督输出，Qwen2.5-32B-Instruct经Unsloth LoRA，测试准确率75.3%，报告错误只差一档。论文§2.2只简写“Qwen2.5 32B”；不把它当作主SWE-agent-LM。

为比较数据集，给三档赋值1/5/9后取平均。这是人工预计修复时间的分类代理，**不是模型成功率**，也不是RL的reward尺度。表14每种SWE-smith方式抽1000题：Modify3.304、Rewrite5.272、Procedural3.596、PR4.876、Combine5.720；SWE-bench5.014、Lite3.893、Verified3.960、Gym5.625。正文所写5.27–5.72不覆盖全部方式，不能沿用为全体难度范围。

LoRA rank、学习率、epoch、精确优化器等E未给；没有用评分器在线改课程或学习reward的实验。评分器训练标注来源含SWE-bench，必须与agent主训练的仓库排除政策区别。

### 4.2 Agent 的成功轨迹 SFT

主链为 **Qwen2.5-Coder-{7B,32B}-Instruct → expert成功轨迹监督微调 → SWE-agent-LM-{7B,32B}**。主专家 `claude-3-7-sonnet-20250219`，少量等数据量比较用 `claude-3-5-sonnet-20240620` 与 `gpt-4o-2024-08-06`。没有本文自建预训练、RL、OPD、DPO、偏好/安全对齐、多专家参数合并；§6明确没探索RL。这里“rejection sampling fine-tuning/RFT”是先用测试筛成功，再做SFT，不能因缩写含R就读成强化学习。

p.5–6 §4：先由消融汇成5105条成功轨迹，再对Rewrite/PR补采到6457条；对重复易题设每题最多3条，保留5016条。表17最终方式组成：同文件组合123、同模块7、Modify11、Rewrite1532、Procedural1495、PR1848，恰合5016。123仓中较大的来源为moto378、pandas320、conan243、pydantic209、dvc181；表18虽标题说top ten，实际展示12项。平均58个对话turn，作者解释为约29个agent action；不能将58写成58次模型行动（p.42 F.3、图21）。

论文说明32B的主训练数据是5016，但p.5概述把7B/32B都称在5016上训练，表3却列7B为2k；**7B最终训练量保留矛盾**，不自行判定哪个是精确消费量。

| 项目 | 论文实际披露 | 边界 |
| --- | --- | --- |
| 更新方式 | torchtune全参数SFT，学习率`5e-5`，最多3 epochs，最大context32768 | F.1 p.38；不等于所有实验均训足3轮 |
| 训练资源 | Modal上2–8张NVIDIA H100 80GB | 没有逐实验卡数、训练小时、总GPU小时/费用 |
| 监督单位 | 成功多轮轨迹；teacher function calling 转student XML | F.1 p.39明确直接按原teacher格式微调不工作 |
| 失败处理 | 主实验只消费测试判resolved的轨迹；F.4另做不筛轨迹对照 | 非自然终止仍可能产出可通过patch；不能把超时截断一律等同未成功 |
| loss/权重 | 论文未列公式、token mask、token/轨迹归一化、batch/optimizer细节 | 当前配置可说明示例CE意图，但不得倒填论文，见§7 |

可把方法理解为“在成功数据子集上学习专家行动的条件概率”；**这只是概念解释，不是原文给出的损失公式**。没有必要为该SFT补造GRPO advantage、KL/IS ratio、critic、group统计或off-policy correction。完整未知项集中于§8。

### 4.3 Rollout 到训练消费的时序与预算

1. 固定基础仓库环境，注入bug并验证，保存含bug分支与任务字段。
2. 为任务准备题面；SWE-agent在容器中让expert以ReAct形式思考、行动、接收反馈，输出候选patch及对话记录。
3. 测试harness评候选修复；筛成功轨迹，控制每题重复数，转成学生的XML消息格式。
4. 离线torchtune SFT；用训练后模型再经SWE-agent运行独立benchmark。环境执行、专家API、SFT learner是不同成本与状态阶段；不是边rollout边异步更新的RL流水线。（图9 p.16；§3、F.1）

teacher和student均有bash、`str_replace_editor`（查看/创建/修改）与submit；反馈前缀`OBSERVATION:`，无输出也明确告知成功无输出。图20指导先定位、写复现、改非测试文件、再验证及思考边界情况。teacher用原生function calling；student输出XML思考/行动。二者system prompt、解析器、消息长度限制有差别，因此不是同一序列化harness直接互换。

专家最多75步、$2/attempt；超过context也终止；多数自动终止来自步数。student也是75步和$2，但**student的$2是按2025年4月GPT-4o价格函数算的代理上限**，不是实付GPU账单。student温度0，每次调用仅保留最近5条tool outputs；不是仅保留最近5条全部消息，也不是更改SFT的32768上下文上限。expert有时不同温度，表16列出的采样为0。（F.1 p.39–40）

论文没有同步/异步队列、backpressure、staleness、权重发布、KV缓存、partial rollout恢复或GPU并行拓扑的实测；这些不属于本文SFT证据。也没有给每次生成token上限、所有工具timeout和总wall-clock统一配置。不得把环境构建“两分钟”、验证“两分钟”和agent“75步/$2”合并成同一个预算。

## 5. 评测、消融、行为与负结果

### 5.1 主结果、评测集与可比性

| 实验/集合 | 结果 | 口径与证据 |
| --- | --- | --- |
| SWE-agent-LM-32B / SWE-bench Verified | 40.2% | 500题，pass@1；F.4说为计算该数运行6次；不是best-of-6；表3、图22 |
| 同模型 / Lite | 30.7% | 300题，pass@1，表3；未给清楚的逐次结果 |
| 7B / Lite、Verified | 11.7%、15.2% | 表3，训练量2k与正文5016冲突 |
| Claude3.7 + SWE-agent | Lite48.0%、Verified58.2% | 表3，同类harness；teacher/student格式与预算实现仍有差异 |
| 500成功轨迹等量比较 | 32B Verified28.2% | 1000随机任务：Claude3.5尝试800、GPT-4o200；对Gym/R2E报告差8.2/0.7；§4称relative difference，按百分数相减应读百分点，不能写相对提升率 |
| Multilingual | teacher43.0%、student8.4%、未微调Qwen32B6.5% | 300题；F.4 p.43明确认为学生没有显著改善，不含推断显著性检验 |

图22 pass@k，k=1…6分别40.2/44.5/49.0/51.5/53.4/54.8%。它表示多次尝试中至少一次解出的上界类指标；没有部署一个可选择正确patch的verifier，所以54.8%不是single-run/选择器实际可交付成绩。主文强调不与多尝试系统比；R2E-Gym的51%使用26次尝试，不能与40.2%直接排序（p.10 §5）。表3还混合多harness与底座；这些行只能作当时报告的横向背景，不能把模型/算法/数据收益分开归因。“SOTA”仅保留为作者2025年时点、特定开源口径主张，不作为当前排名。

**评测集范围。** Lite与Verified分别300/500题，来自SWE-bench的12个Python仓库，未评完整2294测试集。本文新建Multilingual：42仓、9语言，C/C++42题、Go42、Java43、PHP43、Ruby44、JS/TS43、Rust43，合计300；由3位作者去除模糊/欠明确题面，平均改48行（增删合计），F2P中位1。C/C++和JS/TS各是两种语言的合并统计。Multimodal为另一套含视觉输入的约510题，学生文本模型没有评它；E中仅用其题面/patch评难度。不能将“评了Multilingual”写成多模态训练或评测。（F.2 p.40–41、表15）

### 5.2 可归属的消融

默认§4.1以Claude3.7作专家，Qwen2.5-Coder-7B-Instruct作学生，Verified作评测。表中的成功轨迹数是**采样产出**，训练会再裁到共同大小；不能直接按整列判断不公平，也不能把匹配轨迹数称作匹配token/算力。

| 对照 | 控制与结果 | 能支持什么、不能支持什么 |
| --- | --- | --- |
| Bug方式（表4 p.7） | 各抽1000题，统一训507条成功轨迹；Modify5.7±1.5、Rewrite8.8±1.7、Procedural8.6±1.8、PR9.2±1.7 | Modify弱，程序化/Rewrite接近PR；没有独立Combine对照；±未定义为SD/SE/CI，也未清楚交代此表重复次数 |
| 题面（表5 p.7） | 同600 PR Mirror题，统一训259条；Fixed6.4±1.5、F2P7.3±1.9、LM7.7±1.5、Original7.8±1.8 | LM题面可产生接近原issue的训练效果；不意味着题面已无泄漏或所有任务域成立 |
| 仓库多样性（图5、p.8） | 固定700条Procedural成功轨迹；图标5/25/50/100仓→10.3/11.5/12.9/15.1% | 支持同轨迹数量下增加仓库多样性；正文却写4而非5，原文矛盾；不是严格每点等token成本 |
| 成功过滤（F.4、图23 p.43） | 同32B、n=100/200/400/800/1600轨迹；每学生3次评测。过滤后14.3/22.4/27.8/30.1/33.4；随机不筛10.2/19.7/18.3/23.4/27.8 | 该SFT设置下只学成功轨迹更好；不等于RL应丢弃所有失败样本 |
| 规模（图1/23） | 32B从100条14.3到5000级40.2 | 数据量增加伴随最终数据配比变化，不是纯粹固定分布扩量的完整因果实验 |

表4采样产出列802/507/745/557；表16 Modify却605。表5 LM328、Original319；表16二者反过来。正确记录是保留这些矛盾，不任选一组算“准确成功率”。

题面行为解释：Fixed轨迹独特action数379 vs LM550，少31%；F2P题面产成功轨迹更多，但学生在Verified上尝试复现bug仅127/500，LM题面训练的为379/500，少约66%。作者认为直接披露测试使模型跳过复现，降低迁移。**这是作者对观测的解释**；同时变了轨迹内容，未以独立因子实验隔离“写复现脚本”本身的因果收益。

### 5.3 难度与专门化

**难度不等于学习价值（p.7）。** 先给随机10K任务评分，再构造各1000题的easy/medium/hard池，各跑3轮expert，成功率58.6/41.0/17.0%。随后从成功轨迹构造各500条、平均难度2/4/6/8的SFT集（例如2=375条easy+125条medium），学生Verified为12.4/10.8/13.6/12.2%。更难确实更难采到成功轨迹，但没有稳定更高的SFT收益。因此不应从“测试能打破”或“难度评分高”直接给数据更高学习优先级。

**SymPy专门化（p.8、图4）。** 用2022-01-01之前的SymPy基准commit生成1276个Procedural任务，采700轨迹；评测Verified里该日期之后22题。7B只训SymPy对比同700条/100仓的泛化训练，在目标SymPy 21.2 vs13.6%，非SymPy 14.0 vs15.3%；32B已有主模型再训SymPy，目标42.4 vs33.3%，非SymPy38.3 vs40.2%。小目标样本、百分数非单次22题的整数分辨率，图4没有明确给重复/聚合细节。结果支持作者所说专门化与少量泛化损失的权衡，不能宣称从未见仓库泛化提升；该额外训练故意包含评测仓库的旧版本，须与主训练分开。

### 5.4 行为分析与失败分类

- **效率分母**：各自成功集合的平均步数student24.9、teacher29.1；仅共同成功集合则24.8 vs25.6，差距明显缩小（p.8、图6）。31题在≥40步才成功；短轨迹不是唯一好行为。自然submit子集的成功率约60% vs63%，不等于总体40.2% vs58.2%，也不证明模型自评已校准。
- **重复的定义**：先剥命令前环境赋值、链式命令只留最后一条，再去参数（部分保留subcommand）；最长相同base-command连续串叫重复。因此不同文件的`view`也算重复，不是同参数重复执行。student超过25%轨迹有≥10长重复，teacher不到4%；长度10对应89%失败概率；最长重复串中73%是view（p.9、F.5.2）。不能把这种简化动作统计当无歧义错误标签。
- **失败分布（图8、F.5.3）**：student53%失败来自cost/step上限，经常尚未改源码。先分环境/格式等error和context，再分预算终止/自然提交；无源码改动再看是否尝试测试，分定位卡住/复现卡住；有源码改动以是否覆盖gold所有源文件分incorrect localization/edit。新增文件和测试文件不算源码修改。**阅读者判断**：合法替代解可能改不同文件，所以这是归因启发式，不是行为真值或reward规则；超预算后仍提取patch，可能成功。
- **预算曲线不是多组真重跑**：F.5.1图24–25由75步单次运行构造，假设第n步提交成功的轨迹在<n上限时失败；不是在各低预算下重新采样，也没检验提前终止时已有patch是否已经正确。平均成本/步数随上限显著变化，不能报无预算的单一“每题成本”。
- **干预负结果（F.5.4 p.45、图27）**：view连续4次、其他6次后提示；到6/8次对后续action最多重采10次，7/9次再注入assistant消息或升温。重复减少，解题数却降到192/500=38.4%；变体无实质改善。作者据此推测重复更多是困难或分布外任务的症状。论文没有证明抑制重复就会增加学习收益。

### 5.5 不要遗漏的其他结果与限制

Multilingual仅8.4 vs基础6.5，远低teacher43%；作者抽查发现一些编辑带Python语法倾向，解释为交互能力有所学到但语言知识迁移不足（F.4 p.43）。这不能变成“扩展AST层即可获得跨语言能力”的证明。

G p.46报告曾尝试从在线代码编辑/commit历史合成并重放轨迹，没有成功；有限文件diff缺少技能、决策与上下文。Web任务的随机游走后补指令、教程监督、人类演示方法只作相关工作，不是本文开展的额外Web训练。

## 6. 成本、存储与污染边界

### 6.1 可核算的成本与不完整分母

| 项目 | 原文数字 | 解释与限制 |
| --- | --- | --- |
| 数据构建API | $1360=$1000 bug+$160安装+$200为10K bugs生issue | §2.2 p.4；不包括expert轨迹API、SFT、最终评测CPU/GPU/存储总成本 |
| 题面API单价 | 2.54美分/issue | $200/10K=2美分，与平均2.54美分并不精确一致；未给可对齐账单分母 |
| 候选API单价 | 表1 0–5.53美分，总行2.32美分 | 总行不是已解释的加权总成本；不能用它直接乘全部候选重建$1000 |
| 人力 | 主文约20小时；安装人工18小时 | 不是完全自动化的pipeline wall-clock；parser可复用 |
| 存储 | 表2 295GB；附录125镜像290.54GB | 镜像数/仓库数不同版本统计没有对齐，见§8 |
| 放大估计 | 50K SWE-bench式实例需50–150TB，作者称约500倍 | p.5；是估计不是同机实测；相对295GB下端约170倍，上端约508倍 |
| teacher rollout | 最多$2/attempt，17906次尝试 | 没给总实付；上限乘尝试数只能是预算上界，不是实测成本 |
| 学生训练/评测 | 2–8 H100；student推理$2为代理计价 | 没有总GPU小时、实际成本与端到端吞吐 |

**Flask案例（C.2 p.34–35）。** 固定`bc09840`版本：402候选→267有效任务（66.4%）；安装人工10分钟，生成23分钟/$2.47，验证14分钟。历史SWE-bench：2434 PR→107静态候选→11环境可用任务，约38人时。作者写每任务$0.00613，但这个数是$2.47/402，按267有效任务应约$0.00925；作者0.176分钟=47/267把10分钟人工与23+14分钟机器wall-clock相加，不能直接与38人时/11=207.27分钟称作公平人力倍数。只算人工安装10/267≈0.0375分钟/有效任务，也仍不包含所有维护工作。

“bug coverage”是被至少一道任务打破的测试占测试总数：Flask SWE-bench为15/207=7.25%，SWE-smith422/474=89.03%。测试集版本（2023-06 vs2024-11-28）和任务数也不同，不能把覆盖差纯归因于合成算法。该案例表明更多代码功能可被制造出回归，不是验证集学习收益。

**图1左图（G p.45–46）** 的SWE-bench对照是在同仓爬PR、筛改Python与测试的候选后，按历史平均20%存活估计；没有实际为所有候选构建环境。不能称两条完整生产线实测任务吞吐。文中还有128仓与绘图“5到250仓”范围不齐的问题。

### 6.2 切分与污染

主训练按§2.1声明排除12个SWE-bench测试仓库，但许可表6出现Flask，C.2明确用Flask做案例；正式仓库长表并未列Flask，前两项不足以确定它进入主训练123仓。另有B.4的Django恢复实验和SymPy专门化训练。因此论文文本不能单凭一句排除声明证明所有公开任务、所有实验数据都仓库互斥；需要最终主训练123仓清单与任务血缘核对，本文未下载完整数据完成该审计。

更直接的交叉暴露是D的Verified题面风格示例，以及E的Verified难度标注训练。它们不能自动证明gold解被复制进主agent数据，却足以否定“完全未接触Verified”的强断言。论文也未给预训练污染、近重复bug/PR派生族跨集合、题面答案泄漏的系统审计。

§4反复用Verified进行方法比较与消融，未明确独立dev集/最终test一次性冻结的选择流程；所以“separate test split”不等于今日严格的开发选择与最终评测隔离。p.35已承认SWE-smith原始任务不宜直接作评测，应优先保留这个限制。

## 7. 官方当前实现、RL 用法与开放资产

### 7.1 当前代码补充：不能倒填论文

以下均是C=`9b74ac08118a85c39c356802f7961893af73e07f`的静态事实，首次引用给完整路径；未运行代码或验证容器安全。

| 路径/符号 | 实际阅读所得 | 与v2的关系 |
| --- | --- | --- |
| C:`swesmith/profiles/base.py::RepoProfile.get_container` | 按profile镜像起新容器，以instance_id checkout任务，UUID防同名；x86_64、10GB内存；镜像按profile复用 | 解释“一镜像多任务”；不是复用一个脏容器 |
| C:`swesmith/harness/valid.py::run_validation`、`swesmith/harness/grading.py::get_valid_report` | 将正确/bug状态日志交集按PASSED/FAILED分类，候选返回timeout/fail/0_f2p/1+_f2p；原不存在于一侧的test跳过 | 可解释F2P方向；当前profile默认timeout90s/reference900s，不能替换论文120s |
| C:`swesmith/harness/utils.py::run_patch_in_container` | 每次验证/评分建容器。评分checkout任务后再`HEAD~1`恢复F2P测试（代码假设分支两提交：bug，再删除测试）；应用修复后回退识别出的F2P/P2P测试文件改动 | **现行测试移除/恢复机制不同于论文测试可见**；不证明全部测试控制面都隔离 |
| C:`swesmith/harness/eval.py::run_evaluation`、`swesmith/harness/grading.py::get_eval_report` | 默认`f2p_only=False`，评F2P及P2P，再委托SWE-bench full resolution；`f2p_only`按F2P所在文件缩减范围，同时保留其中的F2P/P2P判定，并非一般意义的仅检查F2P。超时/缺日志返回未解并带分类；PASSED/XFAIL算通过，缺项/FAILED/ERROR算失败 | 评分选项是消费契约的一部分，不应只说“跑测试给reward” |
| C:`swesmith/train/traj_mgr/collect_trajs.py::process_single_trajectory` | 读report并记录`resolved`，也返回未解轨迹；批处理写出所有转换成功项 | 该步骤**不自动完成成功筛选**；当前教程“输出可直接SFT”不足以复现论文RFT |
| C:`swesmith/train/traj_mgr/combine_trajs.py::merge_and_shuffle_jsonl` | 按instance_id最多3条、随机取样打乱，不检查resolved | 成功过滤需核输入集；max3不是完全去重 |
| C:`swesmith/train/traj_mgr/utils.py::get_messages`、`transform_traj_xml` | 取末步消息历史为近似；注释承认blocked-action requery捕获不全。tool→user，换student system prompt，assistant thought+工具XML；特殊cost-limit文本可能改成submit说明 | 数据有重构/转换，不是loss可用的原始token保真轨迹；不应照搬为rh2在线RL捕获 |
| C:`configs/train/full_ft_qwen_32b.yml`；`swesmith/train/run/ft_torchtune.py::run_train` | 示例`lr=1e-4`、AdamW weight_decay0.01、cosine+5 warmup、CEWithChunkedOutputLoss、batch1/累积1、3epochs、bf16、max_seq32768、`train_on_input=False`、`packed=False`；分布式full fine-tune由Modal H100启动 | 与论文`5e-5`有差别；不能宣称它就是40.2%主实验配置。train_on_input字段表意为不训输入，未追torchtune确切版本的最终mask与归一化 |

当前代码已有多语言profiles；这不改变论文只做Python合成训练的事实。基础镜像+任务branch包含何种git历史、隐藏测试删除是否可被恢复、parser/测试插件是否可被候选控制，本次未作运行安全审计。代码提供fresh container和测试文件回退，不等于完整反作弊证明。

### 7.2 当前 RL 证据有多强

官方C:`README.md`明确说SWE-smith曾用于SkyRL的GRPO式强化学习，并链接[SkyRL](https://github.com/NovaSky-AI/SkyRL)。这是**官方当前用途声明**，与v2 §6“未探索RL”不矛盾，说明发布后的使用范围扩大；不附可直接归给SWE-smith的受控RL收益。

沿官方RL链接继续追踪，找到SkyRL历史`swe-smith`分支的[提交58cfc213c0f7b44a0b5033e68d65782d05f8a13d](https://github.com/NovaSky-AI/SkyRL/commit/58cfc213c0f7b44a0b5033e68d65782d05f8a13d)，提交日期2025-06-05，消息为`support swesmith`。该版本`verl/workers/agentic/swe_agent/utils.py::get_instance_docker_image`识别`data_source`中的`swe-smith`、按任务`image_name`构造镜像名；`verl/workers/agentic/swe_agent/swesmith_utils.py::make_test_spec`调用当时SWE-smith的`get_test_command`生成测试脚本；`verl/workers/agentic/swe_agent/codeact.py::_evaluate_agent`/`_apply_patch_and_evaluate`根据dataset切到SWE-smith测试规范和`get_eval_report`。这提供具体的环境/评分接入证据。

同分支`examples/sky/swebench/run_skyrl_agent_oh7b_s1.sh`设置`algorithm.adv_estimator=grpo`、OpenHands-7B初始化、16条轨迹/题、最多15次agent迭代、lr1e-6、KL loss系数0.001、clip0.2；但脚本仍是SWE-Gym数据路径占位，`examples/sky/swebench/README.md`对应80/220/293数据，而非已钉死的SWE-smith训练集。因此这些字段只能说明该分支的通用RL示例，不能当成SWE-smith已跑实验配方。根README的SkyRL-Agent成绩没有在已读材料中证明由SWE-smith产生，不在本笔记归功于SWE-smith。

当前SkyRL main `0b286bacba2bb51dfe50186b6b5d6b1e0b5f5518` 已重组目录，所读`skyrl-agent/data/swe_data.py`与`skyrl-agent/examples/run_skyrl/run_skyrl_swe.sh`默认R2E-Gym。历史代码依赖旧`swesmith.harness.utils.get_test_command`等API，与本次SWE-smith C版本也不同；未作依赖复原或执行验证。结论是“官方宣布可用于GRPO，存在具体接线；没有从已核来源建立SWE-smith专属受控RL收益”，不是“只有一个无法追踪的链接”，也不是“论文40.2%来自RL”。

### 7.3 资产实际版本

只读取卡片和API元数据，不下载完整数据/权重。远端内容与摘要数不同的情况原样登记：

| 资产 | 实际读取revision与状态 | 可复现边界 |
| --- | --- | --- |
| [SWE-smith任务](https://huggingface.co/datasets/SWE-bench/SWE-smith) | `ea6d7173829c7ec8fa16c22055699ff2e9188091`；卡metadata59136行，旧叙述仍50137；2025-12-14声明转向语言专属数据集 | 不等于论文冻结集；本地卡〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/SWE-smith-card.md`〕 |
| [轨迹](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories) | `08e109b4a59eaeebf80e4675cd125d42e7ac99a4`；tool24100/xml26076/ticks25826行，卡文字称训练5017 | 三种序列化split不能相加成独立轨迹数；5017与论文5016相差1；本地卡〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/SWE-smith-trajectories-card.md`〕 |
| [SWE-agent-LM-32B](https://huggingface.co/SWE-bench/SWE-agent-LM-32B) | `6b6b924ea6f17aeff85e5228772df8fff3aab62d`；卡称5k Claude3.7轨迹微调 | 已核页面可达，未验证权重可完整加载；本地卡〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/SWE-agent-LM-32B-card.md`〕 |
| 官方镜像/其他模型 | C README现列250+环境、52k任务、26k轨迹；官方assets页还列难度评分器和7B | README数字不是一致冻结manifest；没有pull镜像或核对所有模型版本 |

代码/数据卡标MIT；原始仓库许可仍需按具体源repo处理。A.2区分BSD/MIT/Apache与GPL等，表6图注却统称permissive，后者不准确；不把非专有研究用途描述当成所有再分发/商业使用的法律结论。当前官方说明主要支持Ubuntu22.04.4、Docker，不计划支持macOS/Windows；本机只读研究没有验证Linux可运行性。

## 8. 原文冲突、未披露项与证据强度

### 8.1 已回原页/TeX的数字冲突

这些是原文内部问题，不是提取文本缺失。优先报告附表可见分母，并同时保留主文，不擅自“修正论文”。

| 项目 | 冲突位置 | 本文处理 |
| --- | --- | --- |
| 安装步数 | §2.1 p.3 100 vs A.2 p.19 150 calls | 并列，不声称统一配置 |
| 仓库/镜像/均值 | 主文128仓；表10总行129；C.1 p.34 125镜像/290.54GB vs表2 295GB；p.4称平均381任务/仓但50137/128≈391.7 | 分别登记；不能由正文自动推出128个实测镜像 |
| 类别 | 图3六类；C p.27文字七类且计数合100，后续长表又按六类 | 只说明覆盖多领域，不用旧分类计数作精确总体 |
| 产率 | C.1文字PR13.18%、类乱序1.93%、if颠倒47.04%；表10对应33.8%、1.88%、49.44% | 数值分析采用表10可见候选/任务分母，同时注明冲突 |
| 变换与模板 | 表8某行criteria索引12，但表7只有11项；D写7模板，表13为9行 | 不补造缺失定义 |
| 行数统计 | 表1Combine/PR/Procedural改行中位11/14/5；表12为19/20/7 | 没给清楚定义差别，不用其中一组覆盖另一组 |
| 难度 | §2.2写各方式5.27–5.72；图19/表14实际3.304–5.720 | 保留附表完整五类；表14部分外部数据行总数也与分类和不符，不据此重算整体分数 |
| 主实验训练量 | §4概述两模型5016；表3 7B为2k；F.3文字5000；HF卡5017 | 32B用表17合计5016；7B精确量未定 |
| 消融采样与teacher | 表4 Modify802 vs表16 605；表5 LM/Original 328/319 vs表16 319/328；表16 Claude3.5头写20250219 vs§3/F.3 20240620 | 不计算自称准确的对应成功率或悄悄换teacher版本 |
| 最终组成/轨迹池 | 表17合计5016；表16各行覆盖范围难与5105→6457→17906尝试直接逐项核平；表18标题top ten但12项 | 主要池漏斗引§4；表16不能当作完整可复现运行账 |
| 多仓消融 | §4.1 p.8 4仓 vs图5 5仓 | 按图展示并标出文字差异 |
| 成本 | §2.2的$200/10K、均价2.54¢；C.2的每instance $0.00613实为每candidate | 分母区分，见§6.1 |

### 8.2 真正尚未回答的问题

| 未知项 | 已查范围 | 为什么重要 |
| --- | --- | --- |
| 最终主训练唯一题数、逐题完整血缘及排除名单 | §4、F.3表16–18、当前数据卡/代码 | 无法完成训练/benchmark重叠和去重审计 |
| 精确SFT optimizer/batch/mask/loss分母、长序列截断/丢弃、checkpoint选择 | §3、F.1–F.4、当前torchtune配置/启动器/转换器 | 代码示例有版本差别；不能恢复主实验逐token消费语义 |
| 每一消融的重复次数、±统计定义、精确预算与token数 | §4.1、表4–5、F | 不能作严格显著性或等算力结论；F.4明确的3/6次已单列 |
| 验证CPU成本、expert总费用、训练/评测GPU小时及部署吞吐 | §2.2、A.2、C、F.1/F.5 | $1360仅局部成本，存储优势不是端到端训练加速 |
| issue generator确切版本；题面泄漏/歧义审计；flakiness与替代解验证 | D、C.2、验证/评分当前代码 | 提示词与单次测试不足以证明reward可信 |
| SWE-smith专属RL数据revision、真实训练配方/运行与受控收益 | v2 §6；当前README/SkyRL main；历史swe-smith接入提交及示例 | 已确认具体静态接线和通用GRPO示例，仍不能归属专属RL收益；原SFT证据不能升级为RL已验证 |

证据分层：数量/配置/结果为**论文报告或当前代码事实**；“更多覆盖有助暴露功能”“重复是困难症状”为**作者解释**；成本分母重算与潜在替代解误分类为**阅读者推断**；下节为**项目候选建议**。本文不把代码静态阅读称作运行验证。

## 9. 对旧稿的主要更正

1. 旧稿“每实例成本”改为表1“每候选生成API成本”；$1360没有包含全部生产/训练/评测支出，且issue支出仅覆盖10K。
2. 旧稿“125镜像未能核实”纠正：p.34 C.1明确写125/290.54GB；应保留与128/295GB的冲突。
3. 旧稿“36%实例被解出”纠正为6457/17906的**尝试级成功轨迹率**，不是唯一题成功比例。“去重后5016”收紧为每题最多三条，未证明完全去重。
4. 旧稿缺失难度评分器LoRA、等量消融、Multilingual弱迁移、重复干预负结果；本篇全部补入。
5. 旧稿“最低成本扩容路线”“比从头造仓库低一个量级”没有本文受控证据，撤回这种项目级排序。固定环境复用是候选机制，不是本项目已验证默认方案。
6. 旧稿只保留排除12仓，未覆盖Verified题面示例与案例/专门化例外；本篇不再推导无污染。

## 10. 对 RepoHarness 项目一的有限映射

映射日期2026-09-07。主资料目录HEAD=`ce2009f879cf38071d7898a1387e01d4e27741d6`；实际`reference/miles-rh2-integration` HEAD=`98a0272e4158b2c20e3a34d210c79b50159af0f6`，没有用本阅读worktree基线替代它。背景简报为2026-09-05快照，设计建议2026-09-07为咨询而非批准；只核必要代码职责，不扩全仓审计。

已读主目录 `rh2/src/repoharness2/envpack/training_view.py` 的 `TrustedTaskController`/两侧view及 `rh2/src/repoharness2/grading/trusted_projection.py` 的控制面分类与评分投影：前者把公开任务与私有评分材料分离，后者不重放测试控制面的候选改动；后者也明确通用pytest配置/插件面尚未完整定义。miles+SGLang负责训练/推理，外部coding harness负责agent；本论文不足以要求rh2重造这些组件。

| 候选借鉴 | 来源依据 | 上游已有/我方增量 | 最小验证与成本 |
| --- | --- | --- | --- |
| 优先复用现成`repo,commit,image`，有缺口再做小规模合成 | §2、C.1共享环境；§6局部成本 | SWE-smith已供构建/候选/验证；rh2增量是冻结task来源和正式消费接入，不另造通用平台 | 按设计建议3–5仓、两种方式、100–300候选只是候选规模；先真实Linux验证启动、无操作/逆patch、回归与reset，报API/CPU/人时/存储、有效任务数 |
| 分开环境有效性、当前难度与学习收益 | F2P筛选；难度消融无单调收益 | 上游给任务与测试，rh2负责可信评分/可解释失败及采样实验 | 同模型/harness/预算测成功率、长度、失败类；固定held-out对比相同训练token或GPU时，不能只最大化F2P数或评分器难度 |
| 补丁方向、参考解与评分材料专门适配 | A.1逆向bug patch；C当前测试移除/恢复 | 复用已有`TrustedTaskController`与评分投影，具体SWE-smith adapter仍是候选 | 确认source revision的任务branch语义；参考解只在trusted侧；测试恢复后验证候选不能改变评分控制面。两种版本测试可见性各自验证 |
| 按仓库/bug派生族设计划分，控制配比 | 多仓等量收益；组合共享原始bug；Verified风格示例 | 我方数据划分与审计增量，不改miles算法 | 合成前划分源repo/PR/原始bug；近重复派生不跨train/test；最终test不用于选择补题策略 |
| 保留原始轨迹与训练投影差别 | teacher→XML，当前get_messages近似 | SWE-agent有其SFT导出；rh2在线RL已有逐token捕获契约，不应被这套重构替代 | 若试离线SFT单独验序列化与mask；在线RL仍按现有capture/loss边界，不注入合成submit陈述 |

可信的项目叙事是“复用外部环境生产能力，验证任务进入本项目harness、grader与训练消费的边界，并报告受控成本/学习结果”。论文可以支撑为何优先复用环境、为何保留多样性和数据漏斗；不能支撑我们已经训练提升、反作弊完备、或在线RL从该源获得相同增益。首训taskset和C包未定项仍由项目原流程处理，本阅读不新增批准门。

## 11. 快速定位与关联阅读

- 环境与字段：§2–3；原文A–D。真正的可执行任务数量看表10，镜像数冲突看C.1 p.34。
- SFT与辅助LoRA：§4；原文E/F.1/F.3。负结果与消融：§5；原文§4.1/F.4/F.5。
- 预算与分母：§6；特别是C.2 Flask、F.1 student代理价格、G图1估计。
- 当前代码/资产：§7；事实边界：§8；项目建议：§10。
- 已存在关联：E2 CalibForge〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md`〕、N11 miles〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕、N13a Verified审计〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13a_swe_verified_audit.md`〕。任务12/R2E-Gym尚未完成，此处只记编号。

## 12. 独立审查与修订记录

已完成唯一独立审查与修订，日期2026-09-07。审查记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/11_E5_review.md`〕确认正文、A–G全部附录、图1–27、表格/算法/提示词和必要代码的全范围检查，没有发现改变主结论的错误或整段遗漏；提出两处精度修正，均已处理：§7.1明确`f2p_only`仍可能判P2P，§6.2将Flask证据限定到许可表和案例，未声称正式仓库长表列入Flask。同一审查者另定点核查并认可SkyRL历史接线补充，已整合§1/§7.2/§8.2。

主任务ID `01a07827-1e3f-7bb0-85d6-7ac47489ae64`；审查任务ID `01a0782d-eba9-79a3-81cb-51d5e1e7ace7`。主/子会话均从实际`turn_context`核实为`gpt-6-astra` / `high`，审查以`fork_turns="none"`创建。固定初稿为sources/E5/E5_swe_smith.draft-20260907.txt〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/E5/E5_swe_smith.draft-20260907.txt`〕，审查期间保持不变；收到报告后才修订正文。来源版本以§1、§7及来源登记为准；没有git commit/push，没有运行训练。

链接与文件结构检查属于交付验证，不替代论文事实审查或训练复现。原文自身数字矛盾、未披露训练细节及专属RL结果归属缺口仍按§8保留。


---

## 文档 7 / 7：O03_r2e_gym.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/O03_r2e_gym.md`

# O03 R2E-Gym: Procedural Environments and Hybrid Verifiers for Scaling Open-Weights SWE Agents：环境与训练精读

R2E-Gym 的核心成果是从真实 commit 构建可执行 SWE 任务，再用离线轨迹训练编辑 agent、测试 agent 和轨迹判别 verifier。三者均采用 SFT；论文没有在线 RL 实验。论文报告完整集 8,135 题，去除与 SWE-Bench 测试仓库重叠后为 4,578 题；编辑模型用 3,321 条成功轨迹、覆盖 2,048 题，32B 的 SWE-Bench Verified Pass@1 为 34.4%。混合 verifier 将多候选选择提高到 Best@26 51%，不能把这部分归为权重训练收益。最有价值的限制是：历史依赖恢复仍需半人工；生成测试会无区分或偏爱错误补丁；无执行 verifier 会依赖轨迹话术。当前公开数据、配置与论文若干数字不同，下文逐项区分。

导航：来源与覆盖 · 环境生产 · 三条训练路径 · 推理扩展与证据 · 资产与复现 · 项目映射与审查

## 1. 来源、版本与完整覆盖

- **论文**：Naman Jain、Jaskirat Singh（共同一作）、Manish Shetty、Liang Zheng、Koushik Sen、Ion Stoica；UC Berkeley / Australian National University。正式标题见本文标题。[arXiv v1](https://arxiv.org/abs/2504.07164v1)，提交 2025-04-09；截至本次读取仅列 v1；PDF 标注 Preprint / Under review。阅读和修订日期：2026-09-07。
- **原文附件**：arXiv PDF〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/2504.07164v1.pdf`〕、官方 TeX 包〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/2504.07164v1.tar.gz`〕、提取全文〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/paper.txt`〕。全文共 27 页；本文 p.N 同时指 PDF 第 N 物理页与印刷页，两者一致。
- **官网版本**：[项目页](https://r2e-gym.github.io/)及其 PDF 附件〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/project-paper.pdf`〕。官网标题多出 “Environment Generation”；PDF 正式标题与 arXiv 相同。两份 PDF 全 27 页提取文本在去掉 arXiv 水印、归一空白后完全相同，覆盖正文后训练、数据、infra、评测和 A–E 附录，未发现实质文本增删；另将 p.2–27 以 Poppler 60 DPI 渲染，对应 PNG 字节全部相同；p.1 仍有水印/版面差异。图表另回 arXiv 原页检查。不能把官网视为新增训练版本。
- **官方代码**：[R2E-Gym/R2E-Gym](https://github.com/R2E-Gym/R2E-Gym)，实际读取 commit `0d94c4eb9431cd195c55a7ea3abd54006c9a1735`（下文简称 C）；本地只读摘录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/official_repo/README.md`〕。它已加入 DeepSWE/rLLM 指引和更多 runtime 支持，故不是论文实验代码的时间锁定版本。本文单列能影响复现的当前增量，不把 DeepSWE 当作本论文新增 RL 阶段。
- **网页/资产快照**：arXiv 摘要 HTML〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/arxiv_abs.html`〕、官网 HTML〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/project_page.html`〕、资产读取记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/SOURCE_RECORD.md`〕。官网检查了全部正文、图注和 HTML；未见包含额外技术案例的 tab/select，展示图对应论文图。论文图像中的数字和轨迹不只依赖文本提取。
- **版本冲突**：arXiv 摘要网页写 `AgentGym`、`SYNGEN`、`>8.7K`，PDF p.1/§2 写 R2E-Gym、SWEGEN、`>8.1K`，Table 1 为 8,135。这里用完整 PDF 作为论文实验事实，保留网页矛盾，不据摘要另造一版 8.7K 实验。官网及 C 的 README 把 51% 写成 pass@1；本文严格采用 PDF Table 4 的 Best@26。
- **旧稿**：knowledge/summary_r2e_gym.md〔仓库引用：`knowledge/summary_r2e_gym.md`〕，在全文/附录覆盖建立并阅读后才对照。旧稿的 SFT 定位、主要数值基本正确，主要缺失是测试 agent/EF verifier 训练细节、公式、预算、负案例和资产差异，详见 §9。

按原文结构建立的覆盖表如下；“精读”包括相关图表、公式与图像案例，不以派工问题作范围上限。

| 原文章节与页码 | 深度与覆盖内容 | 本文位置 |
| --- | --- | --- |
| Abstract、§1 Introduction，p.1–2，Fig.1 | 精读：两项贡献、训练与 test-time scaling 分界、历史对比 | §1、§3、§6 |
| §2 Procedural Synthetic Data Generation，p.3–4，Tables 1–2 | 精读：commit、build、F2P、backtranslation、repo 去重 | §2 |
| §3 / §3.1 Training SWE-Agents / Results and Analysis，p.4–5，Table 3、Figs.2–3 | 精读：SFT 样本、规模曲线、thought、真实/合成对照 | §3、§6 |
| §4.1 Exploring Different Axes for Training Verifiers，p.5–6，Eq.1 | 精读：EB/EF 两种模型与打分 | §3–4 |
| §4.2 Comparative Analysis，p.6–8，Figs.4–7 | 精读：采样、区分率、毒性、注意力分析 | §4–6 |
| §4.3 Hybrid Inference Time Scaling，p.8–9，Eq.2、Table 4 | 精读：Top-n、回归过滤顺序、Best@K | §4、§6 |
| §4.4 Ablation Studies，p.9–10，Fig.8 | 精读：测试/编辑采样预算、去组件对照 | §6 |
| §5 Related Work、§6 Conclusion，p.10；致谢/参考文献 p.11–14 | 阅读：环境、SFT、SWE-RL、通用 coding verifier 的关系；无新增自身后训练实验 | §3、§6；参考文献仅作线索 |
| Appendix A Dataset Details，p.15–18，Fig.9、Listings 1–5 | 精读：全部阈值、半人工安装、gold-conditioned testgen、issue 模板、两个合成问题、patch minimization | §2、§5 |
| Appendix B SFT Training，p.18–19，Fig.10 | 精读：四工具、无网络、成功拒绝采样、全部已给训练/采集预算 | §3、§5 |
| Appendix C.1 EB Testing Agents，p.19–21，Fig.11、Listing 6 | 精读：正负测试轨迹、full SFT、Django starter 示例 | §3、§5 |
| Appendix C.2 EF Verifiers，p.21，Fig.12 | 精读：Sonnet/本模型轨迹、平衡标签、LoRA | §3–4 |
| Appendix C.3 / C.4，p.22–23，Eqs.3–6、Figs.13–14 | 精读：max 定义、毒性分母、四注意力窗口、oracle Pass@K | §4–6 |
| Appendix D.1 / D.2，p.23–25，Listings 7–8 | 精读：SymPy 成功区分、Django 异常反例；原文删节处明确保留 | §5 |
| Appendix E Agent Trajectory Example，p.25–27，Figs.15–16 | 精读原图：问题及六个 thought/action/observation 阶段 | §5 |

## 2. SWE-GEN：可执行任务怎样产生

### 2.1 数据来源、漏斗与单位

SWE-GEN 从真实 GitHub 历史修复 commit 出发；“synthetic”主要指生成问题描述、补充测试，并不表示全部 bug 都是模型注入。通过 SEART GitHub search 寻找 commit 较多的 Python 仓库，收集历史 diff，再筛选适合修复学习的小改动。环境安装、测试与问题生成是不同工序（§2 p.3、Appendix A p.15–18）。

| 阶段 | 论文数量/单位 | 处理与限制 | 原文定位 |
| --- | --- | --- | --- |
| 搜索仓库、原始 commit、规则/LLM 过滤后 commit | 未给逐层数量 | Python、较多历史 commit；行级和 AST 级筛选 | §2、A |
| 成功构建环境、原有/补生成 F2P 测试 | 未给分层数量和存活率 | Docker 历史依赖搜索；原有测试优先，缺测试时补生成 | §2、A |
| 完整任务集 R2E-Gym | **8,135 任务，13 仓库** | 每题有环境、测试、自然语言描述；不是最终 SFT 消费量 | Table 1 p.3、Fig.9 p.15 |
| 无 SWE-Bench 测试仓库重叠的 Subset | **4,578 任务，10 仓库** | 通常用于全部实验，除非另有说明；不是完整集都用于训练 | §2–3、Table 2 p.3 |
| 编辑成功轨迹池 | **3,321 条，2,048 个独立环境** | Sonnet-3.5-v2，环境测试拒绝采样 | §3 p.4、B p.19 |
| 测试 agent 轨迹池 | **2,203 条** | 含正、负轨迹，minimal rejection sampling | C.1 p.20 |
| EF verifier 轨迹池 | **5,700 条** | Sonnet 采集池加已训 32B 的采样，正负平衡 | C.2 p.21 |

**不能倒推采集成功率**：3,321 是保留下来的成功轨迹，不知总尝试数、逐题重采次数、提前终止或过滤数；2,048/4,578 也不是完整测量协议下的 solver pass rate。两个 epoch 不自动意味着实际消费恰好 6,642 个完整长轨迹，因 32K 采集与 20K 训练窗口之间的处理未写清。

Table 2 实为环图：Subset 中 pandas 31.5%、numpy 17.1%、pillow 13.5%、orange3 10.5%、aiohttp 6.5%、tornado 5.7%、scrapy 4.7%、pyramid 4.1%、datalad 3.9%、coveragepy 2.4%（四舍五入）。Fig.9 完整集另外出现 sympy、matplotlib、moto；完整集最大的是 sympy 28.7%，其次 pandas 17.8%。**repo 去重与问题/commit 去重不是同一声明**；文中未给跨 fork/派生 bug/近重复文本的全面去重方法，也未披露基座预训练污染审计。该分布还说明“题数多”不等于仓库均匀或 bug 机制独立。

### 2.2 筛选和安装的实际工作量

Appendix A p.15 给定的 commit 阈值是：最多 **5 个非测试文件**、非测试文件合计 **100 编辑行**、patch 最长 **2,000 字符**；非测试 AST entity 最多删 **1** 个、加 **3** 个、改 **3** 个；最多 **10 个 statement 级变化**。偏好非文档改动、代码与测试相匹配，另用 LLM judge；judge 型号、提示词和校准统计未给。这里是任务生产偏好，不是证明这些任务更适合 GRPO 的难度定律。

依赖恢复步骤是读取 `requirements.txt/setup.py` 等信息 → 识别版本冲突 → 生成多组 pin → 逐一试装直到成功。作者明确承认 **semi-manual、难扩展**；未来更多使用 LLM 是展望。Listing 1 用 pandas 的 Python/numpy/setuptools 等组合展示尝试过程，属于示意代码（还有参数/排版笔误），不能当可直接运行的完整构建器。论文没有给镜像层复用率、每题构建耗时/磁盘、失败重试成本或总人工时。

当前代码 C 的 docs/ENV_GENERATION.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/official_repo/docs/ENV_GENERATION.md`〕要求给新仓库添加配置、枚举、测试命令，再跑历史采集、可测试 commit 分析及环境验证。对应完整路径为 `src/r2egym/repo_analysis/constants.py`、`src/r2egym/repo_analysis/repo_analysis_args.py`、`src/r2egym/repo_analysis/store_repo_commits.py`、`src/r2egym/repo_analysis/analyze_testable_commits.py`、`src/r2egym/repo_analysis/repo_testextract.py`。文档示例用 `o1-mini`、12,000 max tokens，但不能回填为论文所有生产阶段的模型/预算。`src/r2egym/repo_analysis/repo_testheuristics.py::repo_heuristics` 还有 pyramid fixture/import、aiohttp Makefile 等仓库特例，说明跨仓库迁移仍有工程维护成本。

### 2.3 验证测试、反译问题和最小补丁

1. **F2P 验证**：F2P 指测试在原 buggy commit 失败、fixed commit 成功。先利用历史关联测试，缺失时用类似 Agentless 的 reproduction test generation 补齐。Appendix A p.16 特别说明：**环境生产的测试生成可见 ground-truth patch**。这与推理时测试 agent 只由问题/代码起步的场景不同，不能把后者说成拥有金标修复。
2. **Backtranslation**：给问题生成模型 commit hash/message、非测试 diff、测试 diff、旧/新执行结果、相关失败函数及 assertions。仅看 diff 的朴素反译容易生成空泛描述；加入执行信息是作者的质量理由（§2 p.3、A p.16–17）。
3. **输出约束**：Listing 3 要求简洁标题、错误示例、expected/actual behavior；不直接提测试函数/文件，不泄露 solution；允许短的复现代码，超过约 5–6 行应简化。**这是 prompt 要求，不是泄漏率为零的实测**。题面带 bug 输入和期望属于作者设计，不等于完全无 hints。
4. **Patch minimization**：迭代删除改动、重新跑测试，只保留仍能修复的更小集合，为 localization 评价提供更细信号（A p.18）。没有给该流程的保留数量、预算或对训练/评测的独立收益；“通过有限测试仍成功”也不证明语义上的唯一最小修复。

论文验证的是 F2P、成功修复及测试筛选；没有报告 fresh reset 的重复稳定性、合法替代解接受率、金标/隐藏测试防读、评分控制文件保护、抗输出伪造或全库 flakiness 统计。不能用“可执行 Gym”推出已满足在线 RL 的评分隔离。

## 3. 后训练全流程：三个 SFT 模型，不是三阶段 RL

```text
GitHub commit → SWE-GEN 环境/问题/测试 → 去测试仓库重叠的任务池
                                       ├─ Sonnet 编辑尝试 → 测试通过轨迹 → 编辑 agent full SFT
                                       ├─ Sonnet 测试生成轨迹（含正负） → 测试 agent full SFT
Sonnet 编辑采集池 + 已训编辑 32B 再采样 ──┴─ 正负平衡标签 → EF verifier LoRA SFT
推理时：编辑 agent 多候选 + 测试 agent 产物 + EF 分数 → hybrid 排序 → 选一个补丁
```

三个模型分别训练，最后按工具流程组合；不是参数合并、专家蒸馏或在线共同优化。C.2 的 **on-policy trajectories** 指已训 32B 对任务采样形成 verifier 的监督数据，不能由此推导 PPO/GRPO 更新。论文 §5 提及 SWE-RL 是相关工作；全文和附录没有给本方法的 RL reward/advantage/策略梯度实验，也没有数学、多模态、安全偏好等其他独立后训练阶段。

| 模型角色 | 初始化与训练输入 | 监督/参数更新 | 已披露训练配置 | 采集配置 |
| --- | --- | --- | --- | --- |
| 编辑 agent | Qwen2.5-Coder 7B/14B/32B；Sonnet-3.5-v2 成功 thought/action 轨迹 3,321 条 | **full SFT**；学习端到端探索、复现、修复、测试 | LLaMA-Factory；2 epochs；batch 8；LR 1e-5；warmup ratio 0.1；context 20K | Sonnet，T=0.2；≤40 steps；≤32K tokens/轨迹；≤10 min/轨迹；≤90 s/action |
| EB 测试 agent | Qwen-Coder-32B；Sonnet 测试生成轨迹 2,203 条，正负均有 | **full SFT**；目标为含约 M=10 多样测试的脚本 | 同框架；2 epochs；batch 8；LR 1e-5；warmup 0.1；context 20K | ≤40 steps；≤20K tokens；≤5 min/轨迹；≤60 s/action；本小节未单列采集温度 |
| EF 判别 verifier | Qwen2.5-Coder-14B；Sonnet 采集来源 + 已训 32B 采样；总计 5,700 条，正负平衡 | **LoRA rank 64**；由 issue、thought/action/observation、patch 预测 YES/NO | 同框架；2 epochs；batch 8；LR 1e-5；warmup 0.1；context 32K | 逐来源配比、采样温度/次数、独立环境数未给 |

来源：§3 p.4、B p.19、C.1 p.20、C.2 p.21。若正负完全平衡，5,700/2=2,850/类是算术推得，不是另列的原始采样数。论文称 Qwen-Coder base model 是“初始化模型”的用法；当前配置明确写 `Qwen/Qwen2.5-Coder-{14,32}B-instruct`，不要凭 base 一词改成 pretrained base checkpoint。

**保留与丢弃的不同用途**：编辑 agent 只学测试通过轨迹；失败编辑轨迹可以进入 EF 的 NO 类。测试 agent 使用包含失败的轨迹，原文只说 minimal rejection sampling，未定义失败类别、保留阈值或质量评分。不能统一总结为“三者都只学成功样本”，也不能说失败轨迹受到负梯度惩罚。

**训练 loss 的证据边界**：编辑模型训练目标明确包括 thoughts 和 actions，EF 的预测目标是 YES/NO；论文未列逐 token loss 公式、工具 observation 的实际 mask、assistant 序列边界、长轨迹截断/拆段策略或 token/trajectory/batch 归一分母。此处不从 LLaMA-Factory 默认值补写。没有本论文的 advantage、critic、KL、IS/clipping、动态 group、策略版本/staleness 配方；这些并非已披露 RL 的缺字段，而是本论文没有做这种训练。

## 4. 推理打分机制与诊断公式

### 4.1 EB、EF 和 hybrid 的严格含义

对同一问题 D 的 K 条轨迹 T_k 及补丁 P_k，执行验证 EB 包含两部分：生成复现测试计数，及已有回归测试过滤。论文 Eq.(1)（p.5）为：

\[
\mathrm{TestScore}_k=\sum_i\mathrm{Pass}(P_k,\mathrm{Test}_i),\qquad
s_k^{EB}=\begin{cases}
\mathrm{TestScore}_k,& RS_k=\max_{j\in[1,K]}RS_j,\\
0,&\text{otherwise.}
\end{cases}
\]

`Pass` 是单测试通过指示；`RS` 为 regression test score。**这是候选中相对最高回归分，不是全部回归测试绝对全过**；TestScore 是通过数，不是平均通过率。文字把非最高者叫“过滤”，公式却置 0；全零/并列时公式不独自规定如何选，当前代码用实际列表过滤，见 §7。M=10 是每份生成脚本的目标规模，不保证每条产物都生成十个有效且独立测试。

EF 不执行代码，输入完整轨迹和最终补丁，输出 YES/NO token 的相对概率（§4.1 p.6、C.2 p.21）：

\[
s^{EF}=\frac{P(\mathrm{YES})}{P(\mathrm{YES})+P(\mathrm{NO})}.
\]

概率来自对应 token 的 log-prob；这不是整条轨迹概率，也未证明概率经过校准。这里的 “reward model” 是 outcome-supervised 判别器用于推理排序，不是给编辑 policy 做 RL 的在线奖励。

混合 Eq.(2)（p.8–9）：

\[
s_k^H=\mathrm{Top}_n(s_k^{EF})+s_k^{EB},\quad
\mathrm{Top}_n(s_k^{EF})=\begin{cases}s_k^{EF},&k\text{ 属于 EF 前 }n,\\-\infty,&\text{否则。}\end{cases}
\]

先按 EF 取前 n，再做 regression filtering，然后按生成测试通过数、EF 连续分决定优先级。整数测试分使 EF 通常用于打破同分；论文未给 n 的具体值。官网将流程简写成“先执行过滤、再 EF 排序”，会漏掉前置 Top-n，不能替代 Eq.(2)。当前 C 的实现用 `n=len(candidates)//2`，是代码补充，不能写成 v1 已明示的超参数。

### 4.2 区分率和 toxic test：分母与方向

Appendix C.3 p.22 Eqs.(3)–(6) 定义：将候选补丁划为正确集合 P_c、错误集合 P_i，令 `Pass(p,t)`∈{0,1}：

\[
\mathrm{Distinguish}(t)=\mathbf1[\max_{p\in P_i}\mathrm{Pass}(p,t)\ne\max_{p\in P_c}\mathrm{Pass}(p,t)],
\]
\[
\mathrm{Toxic}(t)=\mathbf1[\max_{p\in P_i}\mathrm{Pass}(p,t)>\max_{p\in P_c}\mathrm{Pass}(p,t)].
\]

两种 rate 都是在同一问题的生成测试集合 T 上求和除以 |T|。注意它比较的是两类中的 **max**，不是任意正确/错误成对样本平均，也不是要求“所有正确通过、所有错误失败”。读者推论：若两类 max 都为 1，则此指标为 0，即使测试能区分部分个体；若错误类 max=1、正确类 max=0，则既 Distinguish=1 又 Toxic=1，所以**高区分率不自动是好信号**。P_c/P_i 为空如何处理、分析子集准确题量没有在该节给出。

§4.2 p.7、Fig.5–6：多数分析问题少于 20% 测试提供上述区分；少部分问题 toxic rate 可达约 10%，不是说“10% 的整个库有毒”或“总体错误奖励率 10%”。大量生成测试属于 Pass→Pass（原 bug 未被复现）或 Fail→Fail（连正确修复也不能通过，常因生成测试异常）；用于展示不同 test generator 的问题级分布，不是原始训练环境 F2P 接受率。

## 5. Harness、运行时与全部附录案例

### 5.1 论文 rollout 时序和预算

论文在 OpenHands 之上设计轻量 ReAct scaffold（§3 p.4）；Appendix B 将实现称为 AgentHub。四个工具为 file editor、search、non-interactive bash、submit/finish。给环境和问题后，自主搜索、写复现脚本、编辑、测试、结束，无固定定位/修复流水线；**训练过程不提供互联网或浏览器**。这项声明不是对容器所有 egress/权限隔离的安全审计。

离线采集后测试保留成功轨迹，再交给 LLaMA-Factory；推理时编辑候选和测试脚本生成可分别运行，随后 EB 执行和 EF 排分、聚合并输出一个 patch。B/C 的 10 min、5 min 等是采集预算；论文没有完整逐项重列最终 benchmark 的全部 timeout/context/token 参数，不能无条件宣布评测完全同预算。

论文未给训练 GPU 型号/数量、GPU-hours、推理服务版本、训推 token 捕获、batch 并行布局、权重发布、异步队列、partial rollout/resume、KV/prefix reuse 或端到端吞吐。不能用当前 runtime 的 Kubernetes、vLLM 示例替它补上历史 fully-async RL 设计。

### 5.2 附录中不能省掉的具体案例

| 原文案例 | 内容与要点 | 证据边界 |
| --- | --- | --- |
| A，Listings 4–5，p.17–18 | PIL 的 thumbnail 在 draft 前 load 导致优化失效；aiohttp 同时含点和冒号的 route name 被拒。都含复现代码、expected/actual | 是生成 issue 示例，未给人工双盲准确率；PIL 描述直接提调用顺序，说明“不暴露解”的 prompt 仍需实际审计 |
| C.1，Listing 6，p.20–21 | 固定 Django starter：配置 SQLite/settings、`django.setup`、模型 app_label、建表/迁移和样本记录 | §4.2 称帮助约 2% 问题的 testgen 格式/领域知识；不是 SWE resolve rate 绝对 +2pp 的完整对照。Django 属测试域；这是公开通用 setup 示例，并非 repo-disjoint SFT 轨迹 |
| D.1，Listing 7，p.23–24 | SymPy PR #24661，`parse_expr(..., evaluate=False)` 与关系运算符、链式比较；打印 resolved/reproduced/other issues | 作者展示成功区分正确/错误补丁；中间六个测试被原文省略，不能凭示例恢复完整脚本 |
| D.2，Listing 8，p.24–25 | Django PR #13933，ModelChoiceField 错误信息是否含非法值，含临时模型、schema 建/删表和合法选择 | **作者明确写多数测试因未处理异常而失败，无区分力**。示例在非法值未抛异常的分支也打印 resolved：读者据代码指出其判据本身值得审计；这不是全库误奖测量 |
| C.4 Fig.13，p.23；§4.2 Fig.7，p.8 | 错误的 `sympy__sympy-24443` 轨迹，最高注意力的 2/4 个滑窗包含“已修复/成功”等 thought、工具动作及自建测试成功输出 | 可见判别器受轨迹线索影响；注意力图是关联性诊断，不是对话术因果影响的严格干预实验 |
| E，Figs.15–16，p.26–27 | `PolyElement.as_expr()` 忽略传入 symbols。搜索类→查看 `sympy/polys/rings.py`→写 reproduction→执行观察→修正无条件覆盖 symbols 的逻辑→再跑脚本 | 图中六阶段展示完整 thought/action/observation 结构；作者称成功例，但图未展示官方 grader 全套输出，不由自报成功推出普遍可靠性 |

## 6. 评测结果、负结果与因果边界

### 6.1 训练收益：单候选 Pass@1

Table 3 p.4 的 resolve rate（%）如下，原样保留误差值；论文未说明 ± 是标准差、标准误还是置信区间，也未清楚报告重复训练数。

| 规模 | Lite 初始化 | Lite SWE-Gym | Lite 本文 | Verified 初始化 | Verified SWE-Gym | Verified 本文 |
| --- | --- | --- | --- | --- | --- | --- |
| 7B | 1.0±1.0 | 10.0±2.4 | 11.0±0.8 | 1.8±1.3 | 10.6±2.1 | 19.0±1.0 |
| 14B | 2.7±1.9 | 12.7±2.3 | 20.67±0.7 | 4.0±1.6 | 16.4±2.0 | 26.8±1.4 |
| 32B | 3.0±1.4 | 15.3±2.5 | 23.77±0.8 | 7.0±1.3 | 20.6±2.1 | 34.4±1.2 |

SWE-Bench Verified 和 Lite 是最终外部评测，本文环境 Subset 按仓库避开 SWE-Bench test；无明确单独训练内 validation/checkpoint selection 方案。当前 C 的 Verified 示例用 test split 前 500 题并要求 official SWE-Bench harness 最终评分；论文表本身未给评测 revision、过滤清单或统一可复刻的评测命令，因此本文不从当前示例追认历史准确任务清单。Lite 的具体消费题量同样应由历史评测记录核实。

在同系列、同参数规模下，32B 相对 SWE-Gym 为 +13.8 **百分点**，相对初始化 +27.4pp；它们是系统配置下报告的成绩差。没有同时固定 SFT 数据量、教师成本、训练 token 和所有 harness 条件，不能将 +13.8pp 单独归因为“合成描述优于真实描述”。

更接近受控的两项消融（§3.1 p.4–5、Figs.2–3）：

- **数据量**：100、200、400、800、1,600、3,200 条轨迹；14B 到约 800 后趋于平台且非严格单调，32B 仍有边际收益，作者解释为更大容量。没有误差/算力匹配信息足以建立普适 scaling law。
- **真实 vs 合成问题**：各 400 条轨迹，28.0% vs 27.8%；支持该设置下相近，不是合成总体严格等效或优越的统计证明，也不能由此推出无需真实测试。
- **Thought 监督**：Fig.3 给 34.4% vs 去 thought 30.4%；相邻正文误写 34.2、并误引 Table 3。本文保留图/正文差异。该对照说明完整 thought/action SFT 有帮助，不证明显式 thought 对所有模型都是必要条件。

### 6.2 推理收益：候选覆盖率与选择能力必须分开

§4.2 p.6–7：编辑 32B 每题采 **26** 条候选，其中 1 条 T=0，余 25 条来自 T=0.8/0.9；两种非零温度各占几条未给。测试 agent T=0.8，采 **7 次测试生成**；结合 C.1 理解为测试 agent rollout/脚本，不是总共七个 unit tests。Fig.4 右图进一步变化测试 agent 0–7 次与编辑 11/16/21/26 次。

- **Pass@26=64.4%**：候选集合至少有一个正确解的 oracle 覆盖（§4.2、Fig.14 p.23）。它需要真实正确性标签识别，不能作为部署时选中率。
- **Best@K**：verifier 从 K 个候选中选出的那一个补丁正确的问题比例。Table 4 的 hybrid Best@16=49.4%、Best@26=51.0%；51.0% 与 64.4% 之间仍有选择损失。
- **单独 EB/EF**：§4.2、Fig.4 约 43.7%/42.8%，继续增加编辑候选的收益趋于平台。Fig.8 柱图写 43.8%/42.7%，§4.4 还出现 42.9%；小幅差异没有被文中解释，不能擅自统一。
- **K=1 图值**：Fig.4/14 曲线从约 32.0（Agentless 图 31.9）起，而 Table 3/4 Pass@1 为 34.4。混合温度采样池/聚合统计与单次评测的关系未完全交代，不能把曲线端点直接替代 Table 3。

评测是 SWE-Bench Verified，训练环境集不是该 benchmark 的随机训练 split；论文也未说明 verifier 分析使用的 Verified 子集准确大小。公开生成测试资产的当前 200 行（§7）不能反推整篇当年只评了 200 题。

### 6.3 Hybrid 消融、成本解释和历史榜单

| 比较 | 成绩/指标 | 可支持的结论与限制 | 原文 |
| --- | --- | --- | --- |
| 只用 regression 的 hybrid vs 加生成测试 | 47.4 → 51.0 Best@26 | 已有回归测试不能替代针对 bug 的测试 | §4.4 / Fig.8 p.9 |
| 官方 Agentless 测试 vs 专门测试 agent | 48.8 → 51.0 | 在该 hybrid 框架/产物下 agentic testgen 更强；不是等教师/训练总成本证明 | §4.4 / Fig.8 |
| 去 Top-n vs 有 Top-n | 49.8 → 51.0 | 预筛候选有益；“减弱毒性影响”是作者解释，未单独测介导因果 | §4.4 p.10 |
| 16→21 编辑 rollouts vs 加 5 测试 rollouts | 共同起点为 1 次测试；编辑方向 47.6→48.4；固定 16 编辑、测试从 1→6 次，正文称 49.3，图中对应点为 49.4（5 次为 49.1） | 保留图文差异；采样预算可分给测试 agent，横轴是 rollout 数，非等 token/GPU-hour | §4.4 p.9 / Fig.4 右 |
| EF 全输入 vs patch-only vs 去 thoughts | accuracy 71.82 / 68.01 / 68.77；Best@26 42.8 / 37.6 / 41.4 | 分别训练对应输入版本的 verifier，并非同一冻结模型推理时删输入；分类准确率与最终选中率不同，去 thought 也不等于删去全部轨迹 | §4.2 p.7 / Fig.7 p.8 |

作者说测试 rollout 通常比编辑便宜（p.9 脚注），但未给逐项 token/时长/美元成本，不能量化节省几倍。26 编辑 + 7 测试还须计算补丁×测试的执行、回归和 14B verifier forward，绝非“26 次总调用”；ReAct 的一次 rollout 本身就包含多轮 LLM/工具交互。

Table 4 是 2025 年不同系统的历史坐标：SWE-Gym-32B Best@16 32.0、SWE-RL-70B Best@500 41.0、DeepSeek-R1/Agentless 49.2、本文 51.0。不同模型、工具、搜索预算和训练方法不相同；“SOTA/与商业模型竞争”仅是作者当时的声明。表中 `Claude-3.6-Sonnet` 的名称与正文 Sonnet-3.5-v2 不一致，不能自行修成另一型号再比较；该论文不建立今天的榜单结论。

## 7. 当前开放资产与论文之外的实现信息

### 7.1 已核可访问资产，不下载权重或整套数据

2026-09-07 通过 HF 官方 API 读取元数据/文件列表，数字是 **当前卡片记录的 train 行数**，没有下载 parquet 逐行核验。完整 revision 与响应保存在 `sources/O03/hf_*.json`，由 SOURCE_RECORD〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/SOURCE_RECORD.md`〕索引。

| 官方资产 | 本次元数据结果 | 与论文的关系 |
| --- | --- | --- |
| [R2E-Gym-Subset](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset) | train 4,578；rev `2e8108ff942f24fcb5686badfaf7f9a8808566d5`；Apache-2.0 | 对应论文主体 Subset 数量；仍未逐行证明内容是原实验集 |
| [R2E-Gym-V1](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-V1) | train **8,101**；rev `903d405799ac435061c41e72260c81ca5100f964`；Apache-2.0 | 与论文 8,135 不同；C README 提到的 `R2E-Gym-Full` API 返回 401，实际组织列表有 V1，未证明二者完全同一集 |
| [R2E-Gym-Lite](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Lite) | train 4,578；另有 9 个 dev split；rev `8d3163011f01f9393bb3dc7700497a79a8686ae5` | 这些 dev split 没有在 v1 论文训练协议中说明，不能倒填；Appendix B 还写 Lite 4,538，见 §8 |
| [编辑 SFT 轨迹](https://huggingface.co/datasets/R2E-Gym/R2EGym-SFT-Trajectories) | **3,231** 行；rev `63ab4eb37668f8be0104133c21d896bedbcf8404` | 论文 3,321；差异原因未知 |
| [测试 agent SFT 轨迹](https://huggingface.co/datasets/R2E-Gym/R2EGym-TestingAgent-SFT-Trajectories) | **2,281** 行；rev `0cfc507e195ff875fa622ab5cd4403d4a7409c46` | 论文 2,203；差异原因未知 |
| [EF verifier 轨迹](https://huggingface.co/datasets/R2E-Gym/R2EGym-Verifier-Trajectories) | **5,750** 行；rev `d8340c4605bb1a00a206a1978813cee35daeff8c` | 论文 5,700；差异原因未知 |
| [生成测试 patches](https://huggingface.co/datasets/R2E-Gym/R2E-TestgenAgent-Patches) | 200 行；rev `005f0eb8c80cb93f3cbfe8699590f752a1c514c3` | 当前执行脚本引用的测试产物；无法据此认定 500 题复现覆盖完整 |
| [32B Agent](https://huggingface.co/R2E-Gym/R2EGym-32B-Agent) | rev `b7b39e295ca764d57ae05b72122da9659e1731b3`；有模型分片、配置和 tokenizer 文件 | 可见权重文件，不等于已运行验证；组织还列出 7B/14B Agent |
| [R2E-TestgenAgent](https://huggingface.co/R2E-Gym/R2E-TestgenAgent) | rev `e91db21ab3069ac8f3fdcdc98c13046c5527be84`；有完整权重分片 | 正确资产名不同于 YAML 本地 output_dir |
| [R2EGym-Verifier](https://huggingface.co/R2E-Gym/R2EGym-Verifier) | rev `623145b2adfdfa3ed59063899480a568811bf5e3`；有 adapter 配置/权重 | 对应 LoRA 形态；并不是名为 `R2EGym-14B-Verifier` 的独立完整模型仓库 |

C 的代码许可证是 Apache-2.0；上述多数轨迹/模型 cardData 没有填写 license，不能把代码许可自动移植给所有资产和原始仓库。论文未逐项交代原始代码/测试授权处理；需要使用时按具体上游许可核对。

### 7.2 当前训练配置与复现入口的增量

以下只陈述 C 的静态文件，不宣称重跑过：

- `train/train_r2egym_32B_agent.yaml`、`train/train_r2egym_32B_testing_agent.yaml`、`train/train_r2egym_14B_verifier.yaml`（目录摘录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/official_repo/train`〕）提供 SFT 入口；对应 `llamafactory-cli train <yaml>`。初始化明确为 Qwen2.5-Coder Instruct；编辑/测试 full，verifier LoRA rank 64、target all。
- 三者均 LR 1e-5、2 epochs、**warmup 0.05**（论文为 0.1）、cosine、BF16、FlashAttention2、Liger、Unsloth gradient checkpointing 开关；编辑/测试 cutoff 20,480，verifier 32,768；每设备 batch 1、accumulation 1。编辑/测试选择 ZeRO-3 offload，verifier ZeRO-3。未给启动 GPU 数/DP 布局，不能凭 batch 8 宣称用了八卡，也不能据开关算实测吞吐。
- `train/dataset_info.json` 是 ShareGPT messages 的 role/content 映射。没有固定 LLaMA-Factory commit，也没有显式 token loss denominator、`train_on_prompt`、packing/长轨迹策略等完整历史证据。
- `src/r2egym/agenthub/run/edit.py` 提供并行采集/评测入口；README 示例 54 workers、编辑采集 T=0.2、40 steps，评测 T=0、40 steps，输出轨迹/patch 后再用官方 SWE-Bench harness 评分。样例 worker 数不等于论文训练资源。
- C README 的 quickstart config 路径仍写缺少 scaffold 子目录的 `src/r2egym/agenthub/config/edit_fn_calling.yaml`；实际相应配置在 `src/r2egym/agenthub/config/r2egym/edit_fn_calling.yaml`。此外文档提到的 `src/r2egym/agenthub/runtime/runtime.py` 已对应到 `src/r2egym/agenthub/runtime/docker.py` 等。复现需按实际文件，不能只复制 README。

### 7.3 环境 reward、推理聚合和静态复现风险

C 的 `src/r2egym/agenthub/environment/env.py::RepoEnv.calculate_reward` 每步返回 0；最终用 `RepoEnv.compute_reward` 调 runtime。`src/r2egym/agenthub/runtime/docker.py::_calculate_reward_r2e` 执行测试、解析并规范化 test-name，再与 `expected_output_json` 比较：长度一致且所有非空解析键的预期状态相符即给 1，否则给 0；缺数据字段时会读容器内 `expected_test_output.json`。函数跳过空字符串键，本身未拒绝双空映射（双空会给 1），也不把返回的 `error_code` 作为独立拒绝条件。这些是静态边界，不表示当前数据实际包含双空记录或论文已发生误奖。该逻辑不等于“所有测试必须 PASSED”，而是匹配期望状态映射；与 SWE-Bench 专门评分分支要区分。这只是当前代码提供的可计算 reward，并非本论文用它完成了 RL。

`src/r2egym/agenthub/verifiers/create_bestofn_aggregate.py::run_hybrid_verifier` 当前确实按 **EF 前 floor(K/2) → 最高 regression → 最高 reproduction → 最高 EF** 过滤；`run_eb_verifier` 则直接从回归分最高候选中最大化 reproduction score。`K=1` 会令 hybrid 的列表为空，因此它不是开箱即用的任意 K 实现；论文 Eq.(2) 本身也没规定单候选特例。

`src/r2egym/agenthub/verifiers/run_reproduction_tests.py::run_test_patch` 先施加测试 patch 和候选 patch，运行 `python3 test_issue.py -v`，以输出中 `resolved` 的出现次数计分；内部异常可返回 0，外层 `process_single_task` 默认最多 3 次总尝试（首次加最多 2 次重试），每次 `join` 超时为 600 s；终止清理与退避另有开销，最终仍可记 0。这种当前脚本行为不能当作论文完整失败过滤协议，也不能直接当在线 RL 的模型失败/infra 失败分类。

同一文件的 `add_reproduction_tests` 把结果按 `(docker_image, test_index)` 存储，未包含候选 patch 身份；**若一次输入含同一环境的多个候选**，后来的候选结果会覆盖前者，然后给该环境轨迹回填同一组分数。这是静态可见的条件性复现风险，本次未运行复现，不声称论文当年数据遭此错误。

`src/r2egym/agenthub/verifiers/run_ef_verifier.py::process_trajectories_to_verifier_format` 两次按 `as_completed` 追加数据/概率，最后与原轨迹 `zip`，没有保留原索引；**并行完成顺序不同**时存在标签错配路径。其 `run_model` 还固定取第 5 个生成 token 的 top-20 logprobs，YES/NO 缺失回填 -10000。若两者都缺失，直接指数运算会下溢并形成 0/0 非有限分数路径，不是稳定的默认概率；这是静态风险，未实测触发。`src/r2egym/agenthub/verifiers/prepare_ef_verifier_input.py::traj2verifier_data` 则使用 `<judgement>` 格式并调用 `deepswe_condense_thoughts`。这些是当前版本的概率位置、输出格式、长上下文与候选身份检查点，不应省略成“公开脚本保证复现”。无需据此扩展为完整源码审计或修改外部实现。

### 7.4 成本口径

| 成本项 | 已有证据 | 尚不能得出的结论 |
| --- | --- | --- |
| 环境生产 | 半人工历史依赖搜索；当前 README 称单镜像约 300–500 MB | 没有全流程 CPU/人工/API/存储账，也未实测镜像大小/层共享 |
| 教师轨迹 | 上述三类保留样本数和部分采集上限 | 无失败尝试分母/总 token/美元成本，不能由成功条数算总预算 |
| SFT | epochs、batch、LR、context；当前优化配置 | 无 GPU 型号、数量、时长、训练 token；不构成八卡低成本复现证明 |
| 推理扩展 | 26 编辑/7 测试和 EF 排序机制，部分减少 rollout 的对照 | 没有等 token/等 GPU-hour 的端到端成本曲线，不能将 Best@26 当 Pass@1 成本 |

## 8. 未披露项与文本矛盾汇总

| 关键问题 | 查阅范围与结论 |
| --- | --- |
| 4,578 vs 4,538 | §2–3、Table 1/2 是 Subset 4,578；B p.19 称 Lite 4,538。TeX `appendix/training.tex` 也写 4,538，非 PDF 解析错误；当前 Subset/Lite train 元数据都是 4,578，仍不擅改历史正文 |
| 3,321/2,203/5,700 vs 3,231/2,281/5,750 | 原文 B/C 与当前三个 HF 卡片不一致。已分别记录，未有逐行差异或发布说明可解释变化 |
| 8,135 vs 8,101 vs >8.7K | 分别是 PDF 完整集、当前 V1 card、arXiv 摘要网页。没有证据把它们视为相同口径 |
| warmup 与 thought/EF/EB 数字 | PDF 0.1 vs 当前 YAML 0.05；thought 34.2 vs 图 34.4；EF/EB 的 42.7/42.8/42.9 和 43.7/43.8；追加测试采样正文 49.3 vs Fig.4 对应点 49.4；均保留各自位置 |
| 生成/验证漏斗 | §2、A、当前生成指南：未给原始 commit 总数、各过滤损耗、生成测试比例、judge 准确率、每任务重采次数、失败成本；Appendix A 的 issue backtranslation 和 gold-conditioned reproduction testgen 也未披露实际模型/每 commit 采样预算，不能把 Sonnet 轨迹教师或当前指南 o1-mini 移植过去 |
| 长轨迹与 SFT 实际消费 | B/C 与三个 YAML：32K 采集到 20K 编辑训练怎样截断/拆分、mask、loss 分母、实际消费 token/轨迹缺失；不能由当前框架默认推回 |
| Benchmark 选择与误差 | §3.1/§4/图表、B/C：未完整说明 checkpoint selection、±/阴影定义、seed/重复、子集名单、混合温度分配、Top-n 历史实参 |
| 评分可信与失败类别 | §2、A–D；静态 runtime/verifier 路径：缺全库替代解、重复稳定性、隐藏材料/测试控制面审计；当前脚本会混合部分错误与零分，但非论文明确 RL 处置 |
| 通用 RL/OPD infra | 全文与全部附录没有自身在线 RL、OPD、异步训推、版本/staleness 实验；README 的 DeepSWE 指引属于后来的独立工作，不回填 |
| 资源与可复现性 | 全文、附录、当前配置/资产：缺论文训练硬件、总时长、API 总成本、原训练框架 pin；本次没下载镜像/权重、没运行训练/benchmark |

原文有数处交叉引用笔误：Subset 分布写 Fig.2，实在 Table 2；§4.4 多处写 Fig.5(right)，实际消融位于 Fig.8；Fig.7 总图注误写 execution-based，分析对象是 execution-free。本文按真实图内容定位，不沿用错号。TeX 包含已注释的旧配置/标题，不把这些当额外正式结果。

## 9. 旧稿更正与证据界限

旧稿的环境链、SFT 与 51% 区分可以保留；此次不是把旧稿推翻，而是补足可查证的训练与评测细节：

1. 补充 **测试 agent 2,203 条正负轨迹的 full SFT** 与 **EF 5,700 条平衡数据、LoRA rank 64**，以及各自不同的 context/timeout。旧稿只写编辑 SFT 容易让人忽略两个训练产物。
2. “多数测试无区分、个别 toxic 约 10%”必须带 Appendix C.3 的 max 公式和每问题测试分母，不能当全库审计率；也不能据此直接推断某题对 GRPO 有学习收益。
3. 旧稿“Prime 重新验证只保留 4,522/4,578、镜像测试可读”属于**后续外部审计**，不是 R2E-Gym 论文事实。本次没有独立复核该 Prime 来源，不在本文把这个数升级为已核结论；可保留为另查线索。
4. 当前公开资产的行数、路径与训练配置差异已实查；旧稿没有这些复现限制，不能凭原论文数字假定下载所得就是原训练数据。

## 10. 对 RepoHarness 项目一的有限映射

映射日期 2026-09-07；读取主资料目录实际 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`，miles 集成目录实际 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`。参考 CURRENT-STATE-BRIEF〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`〕（2026-09-05）和 项目一建议〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`〕（建议而非批准）；后者补充 09-06 审查所指出的 token 覆盖、失败归因和当前消费正确性缺口，不能只依据旧简报说链路已经全闭合。没有以本 worktree 默认分支替代 miles 当前状态。

只核对相关实际文件：`rh2/src/repoharness2/envpack/training_view.py` 的 `TrustedTaskController/RolloutTaskView`，`rh2/src/repoharness2/grading/trusted_projection.py` 的评分控制面说明，`rh2/src/repoharness2/adapters/miles/group_admission.py` 的组准入职责；没有做全仓审计。

| 候选借鉴 | 来源依据 | 上游已有/我方增量/暂不适用 | 最小验证与成本 |
| --- | --- | --- | --- |
| 优先复用现成环境，再做小规模 commit→F2P→反译补充 | §2/A 的生产链及半人工限制 | 任务来源/开源环境是外部资产；rh2 增量是目标执行环境与评分边界适配，不先重建 SWE-GEN 平台 | 少量跨仓库任务跑真实 no-op/gold/重复测试，记录可构建、可评分和失败成本；无效环境不能按模型失败记账 |
| 把完整数据记录拆成公开问题、私有评分与金标材料 | 生产阶段可见 gold，HF 含 `parsed_commit_content/prompt/expected_output_json` | rh2 已有 `training_view.py` 的公开/host 视图理念；当前 source 类型仍是 `swe_gym_lite`，**不是已支持 R2E ingestion** | 若采用 R2E，明确字段语义和测试控制文件，真实检查 solver 可见面；沿用现有控制器，不另建资格证书系统 |
| 评分检查关注错误补丁与合法替代解，而非只看 gold | Eq.3–6、D.2 的异常反例 | 属 rh2 应用层质量验证；fresh grader 已有，但 `trusted_projection.py` 明示通用 pytest/plugin 控制面尚有边界 | 小批 no-op/gold/alternate/不完整修复，在固定测试集分别报 survival、区分与毒性，勿将测试通过冒充需求完整 |
| 完整轨迹 SFT 可作有竞争力初始化/对照 | §3/B 的单候选改进 | 训练内核归上游；是否需要 SFT 取决于目标模型工具能力与失败诊断 | 固定 checkpoint/harness/预算比较初始化与 SFT；若后续 RL，增量从直接 SFT 初始化计，不能把 SFT+搜索收益全归 RL |
| 测试 agent/EF 只作条件性的评测候选 | §4 的混合排序提升与局限 | 暂不应替代首训终局可执行 reward，更不直接把 EF 分数塞入 GRPO | 若确需提高推理选择质量，在 dev 比较等预算编辑重采与测试重采；新增 32B/14B 服务和执行交叉成本要入账 |
| 不从“有正负”推出必须保留所有失败进任何目标 | 编辑成功 SFT、测试含负 SFT、EF 平衡数据的差异 | rh2 `group_admission.py` 的 GRPO 组准入不是 SFT 标签过滤；staleness 仍由 miles consume-time 承担 | 按目标分别统计环境/系统失败、模型失败、实际消费；论文不支持新增 RL group filtering 或 staleness 定案 |

本项目历史 prefix 检查〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze/r2e_prefix_check.md`〕只在 2026-07-07 核了 orange3、coveragepy、numpy 三个镜像的 Git/文件状态：数据 commit 指修复提交，镜像工作区是父提交；没有运行项目测试，且记录修复提交在 Git 历史中存在。它支持“字段语义需查实”，**不证明全库 F2P、隐藏答案不可读或当前 target Linux 可评分**；本次没有重跑该检查。

简历可借该论文解释环境生产与评分质量为何重要，以及为何要区分 SFT、RL 和推理预算。RepoHarness 自身贡献必须由自己的真实评分、训练消费、成本和 held-out 实测支撑；不能把 34.4%/51% 或论文 8,135 题写成本项目成果。

## 11. 快速定位与关联阅读

- 环境和漏斗 → §2；原文 §2、A p.15–18。
- 三个训练模型/失败保留 → §3；原文 B、C.1–C.2 p.19–21。
- reward/reranking 公式 → §4；原文 Eqs.1–6 p.5、8、22。
- rollout、所有案例 → §5；原文 B、C.1、D、E，尤其 p.26–27 图像。
- 训练与搜索增益 → §6；原文 Tables 3–4、Figs.2–8/14。
- 资产/配置差异 → §7–8、来源记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/SOURCE_RECORD.md`〕。
- 关联：O02（SWE-smith，任务 11，尚不链接未交付稿）；已完成的 CalibForge〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md`〕可比较离线 SFT 和任务校准，miles〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕可区分上游 rollout/消费能力；本篇不替代它们。

## 12. 独立检查与修订记录

本任务主线程 `01a07827-1e42-70f2-ac37-48ca0e1af7a7`，实际 GPT-6 Astra / high（主线程已核验配置）。唯一审查子 agent `01a0782e-169c-7b10-939b-bff6f99d0f9a`，canonical `/root/review_o03`，调用参数 GPT-6 Astra / high / `fork_turns="none"`。原文为 arXiv v1（2025-04-09）；被审固定副本 O03_r2e_gym.draft_20260907.txt〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/sources/O03/O03_r2e_gym.draft_20260907.txt`〕 在审查期间未改动。

2026-09-07 已收到完整独立审查：12_O03_review.md〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/reviews/12_O03_review.md`〕。审查者先读原文全部正文/A–E 附录，再对照初稿、关键原图和当前代码/HF 元数据；确认覆盖充分，提出四项必改、两项建议，均已处理：

- **R1**：§6.3 明确 EF 输入消融分别重训模型，而非同一冻结 verifier 的输入删除干预。
- **R2**：§6.3/§8 补 Fig.4 与正文差异：测试从 1→6 次，正文 49.3、对应图点 49.4。
- **R3**：§7.3 修正为最多三次总尝试，每次 join 600 s；清理/退避开销另计。
- **R4**：§7.3 精确描述 reward 非空键匹配、双空映射和未独立使用 error_code 的静态边界。
- **S1/S2**：补 EF YES/NO 同时缺失的非有限概率风险；集中补生成模型和每 commit 预算未知。

同日由同一审查者完成六项定点复核，确认均准确落地且未发现新问题；这不是第二次全文审查。

这些修订没有改变三种 SFT/推理扩展的核心结论。残余未披露项见 §8；对当前代码的条件性路径没有冒称运行复现或论文历史错误。附件比对、相对链接和发布一致性另作交付检查，不替代技术审查。
