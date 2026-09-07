# R2 Nemotron 3 Ultra: Open, Efficient Mixture-of-Experts Hybrid Mamba-Transformer Model for Agentic Reasoning：后训练与项目一精读

Nemotron 3 Ultra（550B 总参数、55B 激活参数）采用两阶段通用 SFT、统一多环境 RLVR、轻量 MOPD warmup、两轮异步多教师 on-policy 蒸馏，最后冻结主干、仅强化 MTP 草稿头。其价值不仅是 SWE：报告完整讨论办公、搜索、终端、工具、安全、聊天、事实性、数学证明和多语言。MOPD 在 agentic 行为上的恢复较强，在 HLE 上只恢复教师差距的 16.9%；多数 agentic MOPD 使用单轮 rollout，而 SWE 教师另有多轮端到端 RL。报告给出 sampled-token 蒸馏公式、部分预算与工程负结果，但没有完整 SWE 环境漏斗、失败样本组统计和 loss 分母，不能据此复现生产训练或推出八卡成本。

导航：[来源与覆盖](#source) · [阶段与数据](#pipeline) · [教师与环境](#teachers) · [目标与训练语义](#objective) · [系统与评测](#infra) · [边界、项目映射与审查](#limits)

<a id="source"></a>
## 1. 来源、版本与覆盖

- 正式标题如上；署名机构 NVIDIA；封面日期 **2026-06-09**；阅读日期 **2026-09-07**。这是技术报告，没有在封面注明 v1/v2。
- 主资料：[原本地 PDF](../../NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf)。[官方 PDF](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf) 于本次下载后与本地 `cmp` 相同，均 65 页、3,876,804 bytes；未静默换版本。[本次固定来源副本](sources/R2/online_20260907.pdf)。PDF 元数据创建/修改时间为 2026-06-09 18:49:09 UTC（与封面日一致），不是另一个发布日期。
- 本文 **p.n 是从 1 起算的 PDF 物理页，也等于报告印刷页 n**；封面无页码，但下一页印刷为 2。文本内部分图形字体含控制字符，按 `\f` 分割会错误地产生超过 65 个片段，不能拿该片段序号作页码。本次按 `pdftotext -f/-l` 物理页分块读；关键公式和图像回原页核对。
- 正文 §1–6、唯一附录 A.1/A.2 和图 1–17、表 1–18 均纳入覆盖；§3 全文与附录精读。作者/参考文献 p.51–63 用于确认来源结构及相关引用身份，不另精读所有被引论文。无网页动态案例需要补开。
- 官方资产入口：[Nemotron 仓库](https://github.com/NVIDIA-NeMo/Nemotron)、[Evaluator 的 Ultra 复现目录](https://github.com/NVIDIA-NeMo/Evaluator/tree/9758d8d5508e0d1bea79cb99ed56d595a1c3acdc/examples/nemotron/nemotron-3-ultra)。实际只核验入口与复现说明，不把当前仓库默认配置当作 6 月报告的训练配置。资产查阅范围见 §9。
- 阅读原文、建立覆盖后，才查旧稿：[重定位审核](../../repositioning_design_review.md) §2.3/T3/T4、[训练配方矩阵](../agentic_rl_training_recipe_evidence_matrix.md) §7.2。旧稿纠错见 §10；未修改旧稿。

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

<a id="pipeline"></a>
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

<a id="teachers"></a>
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

<a id="objective"></a>
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

<a id="infra"></a>
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
| [Base BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-Base-BF16)、[posttrained BF16](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16)、[NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-NVFP4)、[GenRM](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-GenRM) | p.2的发布声明与PDF超链接；2026-09-07实际查询四模型HF metadata，均public、non-gated；[各模型revision及访问状态](sources/R2/model_metadata_20260907.json) | 未下载权重、未验完整tensor/许可证条款（metadata license标签为other）；发布模型不等于十余teacher全部checkpoint公开 |
| [Posttraining-v3 collection](https://huggingface.co/collections/nvidia/nemotron-post-training-v3) | p.3入口；原文仍使用proprietary/vendor数据和商业许可筛选 | 不证明所有SFT/RL/pivot/hidden tests可取得，未批量下载数据 |
| Nemotron recipe repo | 2026-09-07入口可达，HEAD `907d408c67cb70e9f1ed28fb67702e7bd36e3239` | 本次未追训练代码；不能以main框架默认值补本文未给配置 |
| Evaluator Ultra recipe | HEAD `9758d8d5508e0d1bea79cb99ed56d595a1c3acdc`；读 `examples/nemotron/nemotron-3-ultra/reproducibility.md`，[固定远端](https://github.com/NVIDIA-NeMo/Evaluator/blob/9758d8d5508e0d1bea79cb99ed56d595a1c3acdc/examples/nemotron/nemotron-3-ultra/reproducibility.md)、[读取快照](sources/R2/evaluator_reproducibility_20260907.txt) | 当前说明分v0.2 instruct/Gym与v0.3 native SWE/terminal；不是六月所有评测配置的冻结证明 |

当前Evaluator说明还同时写Tau2/TauBenchV3 recipe与“TauBench3未onboarded”，terminal标Hard/2.0，而PDF主表为2.1；default instruct max_new_tokens262144、temperature1、top_p0.95是**后续入口说明**，不能移作Ultra SWE训练192K的解释或补全6月PDF评测预算。仅核入口未运行复现实验。

<a id="limits"></a>
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

映射日期2026-09-07；使用主资料checkout HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`，实际 `reference/miles-rh2-integration` HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`，未用本任务worktree默认分支代替。[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)更新于09-05，[项目一建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)09-07强调已有真实链与实际消费缺口优先；建议不是C包批准。只做窄读取，没有重新全仓审计。

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
- 关联已存在笔记：[R1 MAI-Thinking-1](R1_mai_thinking_1.md)、[N01 KAT-Coder-V2.5](N01_kat_coder_v2_5.md)、[N11 miles](N11_miles_agentic_rollout.md)。R1的SFT专家合并不能填作本篇MOPD事实；其他第二批尚未完成任务仅以编号参考。

独立审查与修订于 **2026-09-07完成**，记录见 [07_R2_review](reviews/07_R2_review.md)。

- 主任务ID `01a07827-1e2f-78c3-8c14-1d222dda34c7`；子任务ID `01a0782d-89ca-7723-ac6f-947eb979e7d7`，agent path `/root/r2_independent_review`。两者session turn_context均核实际 `gpt-6-astra / high`；唯一审查者以 `fork_turns="none"` 创建，无递归扩团队。
- 原文为2026-06-09的65页报告；被审版本 [固定初稿](sources/R2/R2_nemotron_3_ultra_draft_20260907.md)（385行），审查期间及修订后均保持不变。该副本按原笔记位置解释相对链接，最终导航以本正文为准。
- 审查者先读原文全部§3和A，再核相关§2/4/5并逐项对照初稿；关键教师箭头、公式、harness图回原页。结论为没有重大训练语义错误或整块主题遗漏，实际发现F1已处理：§3.2 Safety撤回未披露的“先回应/后推理”顺序，改为回应与推理的两阶段生成（p.16）。未另声称审查者对修订后全文二次复审。
- 作者另将审查期间完成的四模型HF metadata查询纳入§9，并为§11的miles符号补完整路径及实际读取依据；不是为报告训练配置补默认参数。
- 未披露项仍见§10。正文、审查与来源附件的本地链接按最终主资料位置核验；只发布本任务专属文件，没有修改共享索引、旧稿、训练代码或实验定案。
