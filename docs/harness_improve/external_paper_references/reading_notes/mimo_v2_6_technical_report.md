# MiMo-V2.6：Scaling Reinforcement Learning Towards Self-Improvement 全文精读

MiMo-V2.6 将 agentic RL 的扩展对象从采样和训练计算，推进到任务环境、harness 与 grader 计算：Pro/Flash 以 1,568 个 prompt、每题 16 条轨迹进行混合 RL，单步消费约 2.7B–3.7B tokens。报告的重要内容是环境监督的准确性／稳定性审计、两种不同的组内评分机制、变长轨迹的优化语义，以及面向异构长任务的调度和数据运输。大模型在混合 RL 后还进行 MOPD2；开放的 Qwen3.5-9B 衍生模型则先做大量轨迹 SFT，再开展四域独立 GRPO 和另一项多 harness coding 实验，不能合成一个阶段或一个模型成绩。本稿完整覆盖 44 页、17 图、7 表、7 个编号公式及附录 A；来源事实、作者解释、补查资料和项目建议分层。**稿件状态：全文与图表精读、作者自查完成；未独立审查、未复现实验。**

导航：[来源与覆盖](#source) · [模型与训练阶段](#stages) · [数据环境与监督](#environments) · [评分与优化公式](#learning) · [系统与结果](#systems) · [9B 与开放资产](#open) · [证据边界及项目映射](#boundaries)

<a id="source"></a>
## 1. 来源、版本、阅读范围

### 1.1 本稿的主证据是用户上传 PDF

正式标题为 **MiMo-V2.6: Scaling Reinforcement Learning Towards Self-Improvement**，首页作者为 **LLM-Core Xiaomi**。主来源简称 **P**：用户上传的 `MiMo_V2_6_technical_report.pdf`，44 个物理页，正文页码与物理页一致。PDF 的创建时间元数据为 `2026-09-22 03:46:37 UTC`；这不是独立核实的首次发布时间或正式版本号。阅读日期 **2026-09-23**。

原件指纹（用于区分用户上传版本，不构成额外实验准入制度）：

```text
SHA256 fb81e6e083801b3358f084ed6be953dc23b0d2e434690f4541d5eae03e01e7af
```

文件具备可提取文本。本次提取了全部页的文本，渲染全部 44 页，再逐图／表／公式核对对应页；**没有使用 OCR**，也没有用图注猜测未看到的图片。全部 17 图、7 表和 7 个编号公式均可读。Fig.17 的任务 prompt 在原图本身标为 truncated，并非本次提取丢失；静态截图也不能用于复验生成网站的完整交互功能。

没有为本报告虚构 arXiv 编号。官方发布入口是 [MiMo-V2.6 公告][release]；PDF 给出的训练日志入口为 [mimo-v26][logs]。本轮网页工具未取得二者的完整正文／动态日志，故**用户上传 PDF 是唯一主版本**。本稿不上传第三方 PDF、渲染图或模型权重，也不建立假定原件已入库的相对附件链接。

### 1.2 仓库与写入边界

阅读规范依据本库 [NOTE_TEMPLATE.md](NOTE_TEMPLATE.md)。项目映射基线固定到 `Rogerffff/RepoHarness@0554dafd633cd982288bd60a54f75da65e5c54d4`，即 `codex/project-status-20260923` 同步快照。本文在新分支 `pro/mimo-v2-6-reading-20260923` 独立成文；不修改同步分支的实现、不批准新数据集或算法。

本文不是 MiMo-V2-Flash、MOPD、MiMo Sparse Attention 的更新版笔记；不把这些旧工作的配方默认继承到 V2.6。必要关联工作仅作定点补查，范围与访问状态见 §14。

### 1.3 按原文目录的覆盖记录

| P 的位置 | 主题与本次阅读 | 本稿定位 |
| --- | --- | --- |
| p.1–3 摘要、目录、§1 | 全读；Fig.1 六域曲线；研究定位与 self-improvement 的范围 | §2、§9 |
| pp.4–6 §2.1–2.4 | 全读；混合 SWA、ViT、音频和 speculative decoder；Fig.2、Table 1 | §3 |
| p.7 §3.1–3.2 | 全读；text→omni、mid-training、Muown、MXFP4 QAT | §3.3 |
| pp.8–9 §4.1 | 全读；大 batch、成本、partial rollout、Eq.(1)、Fig.3 | §4、§8 |
| pp.9–11 §4.2.1 | 全读；五条 coding 合成路线、四次求解审计、八次执行稳定性；Fig.4 | §5.1–5.3 |
| pp.11–12 §4.2.2 | 全读；可重置一般工作环境、multi-agent 合成、rubric；Fig.5 | §5.4 |
| p.13 §4.2.3 | 全读；开放视觉设计与参考复现两类 reward | §5.5 |
| pp.13–14 §4.2.4 | 全读；目标漏洞重现、sanitizer 规则与环境信息 | §5.6 |
| p.14 §4.2.5 | 全读；对直接训练生产 harness 的保留、可组合 mini-harness | §6 |
| pp.14–16 §4.2.6 | 全读；mid-training 纠错、环境清理、hack agent、在线审计；Table 2、Fig.6 | §5.7 |
| pp.16–18 §4.3.1–4.3.2 | 全读；GRS 与 GAR 是不同子集；Eq.(2)(3)、Fig.7 | §7.1–7.3 |
| pp.18–20 §4.3.3 | 全读；GAR 消融、长度与行为塑形；Eq.(4)(5)、Fig.8 | §7.4–7.6 |
| pp.20–21 §5.1 | 全读；混合比例、Muown、prompt-mean、stop-gradient IS 和四边界 mask | §4、§8 |
| pp.21–23 §5.2–5.3 | 全读；评测协议与全部任务类别、曲线与跨 harness；Fig.9–10 | §9.1–9.3 |
| pp.23–25 §5.4–5.5 | 全读；冻结 router 的受控比较、全部故障类型；Fig.11–12 | §9.4、§10 |
| pp.25–26 §5.6 | 全读；MOPD2 教师和 prefix 分支、最终全表；Fig.13、Table 3 | §11、§9.5 |
| pp.26–29 §6.1–6.2 | 全读；四级轨迹、Penalty Module、多租户、数据与控制面；Fig.14 | §12.1–12.3 |
| pp.29–31 §6.3 | 全读；Sample Mixer 四项机制、Eq.(6)(7)、Fig.15–16 | §12.4–12.7 |
| pp.32–33 §6.4 | 全读；QDQ、R3、top-p support、KV、DFlash、CP、offload/fusion | §12.8–12.10 |
| pp.33–36 §7.1–7.2 | 全读；9B SFT、开放任务、四域独立 RL、多 harness 独立实验；Table 4–7 | §13 |
| pp.36–37 §8、Fig.17 | 全读；结论及三个案例的九张截图 | §2、§13.5 |
| pp.37–43 References | 检查全部条目与关键依赖身份；不是每条引用都扩展为全文阅读 | §14–15 |
| p.44 Appendix A | 全读；贡献与致谢，Fuli Luo 标为通讯作者；没有新的技术附录 | §1、作者自查 |

<a id="stages"></a>
## 2. 核心命题及几条不能混并的训练线

作者将 self-improvement 作为扩展 RL 的研究方向，实际展示的是在人工组织的环境、grader、混合比例和训练系统下，模型通过 RL 与蒸馏改善 agent 表现。**报告没有证明一个可自行设定目标、反复修改自身算法与基础设施、无人管理闭环的递归自我改进系统。** [P, 摘要、§1、§8]

核心投入有三维：更多 rollout／训练计算；更多真实且可复现的环境与 harness；更多 grader 计算，使二元成功之外的实现质量与行为也产生监督。规模本身不保证正确，因此报告同时处理环境漏解、测试误杀、hacking、训推差异、专家负载和长尾。[P, §4]

### 2.1 大模型与 9B 开放实验的关系

```text
MiMo Pro / Flash 各自的 text pretraining
  → omni joint pretraining
  → agent-centric mid-training（256K→1M、Muown、MXFP4 QAT）
  → short SFT
  → mixed-task RL（主实验，GRS/GAR 等）
  → MOPD2（多教师、标准 OPD + prefix-conditioned OPD）
  → Table 3 最终模型评测

MiMo 生成的多领域轨迹
  → Qwen3.5-9B 的 SFT
  → MiMo-V2.6-Distill-Qwen-9B（公开起点）
       ├─ coding GRPO（单 harness）
       ├─ cyber GRPO
       ├─ general GRPO
       ├─ visual GRPO                    → Table 6 各领域对应 checkpoint
       └─ 独立 coding multi-harness RL   → Table 7
```

§5 标题 **You Only RL Once** 描述大规模混合 RL 这条主线，**不能据此删去它前面的 short SFT 和后面的 MOPD2**。四域小模型训练也不是一份“一个 9B 混合模型同时提高十一项指标”的证明。[P, §4开头、§5.6、§7]

MOPD2 中还存在为不同任务训练的 mixRL teachers，以及为开放领域训练的 SFT teachers。这些教师训练与主学生的时间、资源、冻结策略未完全展开，不应自行画成所有专家都从完全同一 checkpoint 并行训练的严格时间图。用于 9B SFT 的 MiMo-generated 数据也没有完整披露各教师版本和抽样权重。

## 3. 架构、预训练与 mid-training：后训练的前提不是同一个 30B 模型

### 3.1 主干配置（Table 1，pp.4–6）

MiMo 使用全局注意力（GA）与 128-token 滑动窗口注意力（SWA）混合的 MoE 主干。第一层使用 GA 与 dense FFN，其余层按混合布局使用 sparse MoE；没有 shared experts。视觉、音频经各自编码器投影到同一 token 序列。[P, §2.1、Fig.2]

| 主干项 | Flash | Pro |
| --- | ---: | ---: |
| 总参数（P 的口径） | 310B | 1.02T |
| 激活参数 | 15B | 42B |
| 总层／SWA／GA | 48 / 39 / 9 | 70 / 60 / 10 |
| hidden size | 4,096 | 6,144 |
| SWA Q/KV heads | 64 / 8 | 128 / 8 |
| GA Q/KV heads | 64 / 4 | 128 / 8 |
| QK / V head dimensions | 192 / 128 | 192 / 128 |
| SWA window | 128 | 128 |
| 总 experts／每 token 激活 experts | 256 / 8 | 384 / 8 |

主干层数不含 MTP。以上是上传 PDF 的配置，不能用网页 packed 权重计数或本项目的 30B-A3B 激活量替换。其万条轨迹级并行和优化器选择是在大模型、大集群前提下讨论的。

### 3.2 视觉、音频与 speculative decoder

**MiMo-ViT。** 28 层，其中 24 SWA、4 GA，hidden 1,280、Q/KV heads 32/8、head dim 64；patch 为 $2\times16\times16$，左右窗口各 64，空间 merge $2\times2$，681M 参数。采用带 attention sink 的局部注意力，行／列优先扫描相交替，再结合 GA。它与一个可训练的小型预训练 LLM 从头联合学习视觉表示，使用超过 4T image tokens 和多模态语言建模交叉熵，而不是先加入一套未披露的 contrastive loss。[P, §2.2、Fig.2、Table 1]

**音频。** Audio Tokenizer 先将 log-mel 特征经两层卷积减帧率，再用因果 SWA/GA Transformer 和 20 层 RVQ 编码；训练语料为约 20M 小时的语音、音乐和一般声音。输出 25Hz、每帧 20 个离散 token。其配置为 24 层（12 SWA/12 GA）、hidden1,024、16/16 heads、head dim64、128 mel bins、窗口128、308M 参数（不含 EMA codebooks）。Audio Patch Encoder 将同一时刻各 codebook embedding 求和，每四帧一组做局部双向处理，拼接并投影为单个主干 token，因此进入主干的速率降为 6.25Hz；它有 6 层、hidden1,024、16 heads、group4、127M 参数。编码器参数口径含 embedding、不含 projector。[P, §2.3、Table 1]

**Speculative decoder。** 采用 DFlash 式 block diffusion MTP：5 层 dense FFN Transformer，全部 SWA，窗口1,024；hidden4,096/6,144，Q/KV 为64/8、128/8，QK/V dim128/128。条件包括主干 hidden features 与一个 anchor token，一次预测其后七个 token，draft block 内双向关注，回看主干最多1,024位置。Table1还列 GA heads 字段，但层计数显示 GA=0，本文照录结构，不据该字段构造额外 GA 层。[P, §2.4]

这里的“架构可以预测七个后继 token”与 §6.4 实际 RL 默认 **block-6** 是不同层次的配置，不应擅自改成同一个数字。DFlash 的外部原论文只作术语补查，见 §14。

### 3.3 预训练、mid-training 和 short SFT 的披露范围

| 阶段 | 已披露数据／目标／配置 | 没有披露的关键量 |
| --- | --- | --- |
| Text pretraining | 公共网页、书籍、论文、code、STEM；Flash26T、Pro27T tokens | 全部来源构成、去重与许可清单、运行成本 |
| Omni pretraining | 整合自建 ViT/audio encoder 后全模型联合训练；Flash22T、Pro3T tokens | 各模态比例与逐阶段优化配置 |
| 预训练总量 | Flash48T、Pro30T；AdamW；32K 逐步扩为256K | 不能把 total tokens 当独立语料或后训练消费 |
| Mid-training | coding/general/visual/research agent 轨迹，加文本、repo代码、图像视频音频；先256K占多数计算、最后1M；MXFP4 QAT | mid tokens、SFT前模型表现、量化影响的匹配消融 |
| Short SFT | §4明确在主RL之前存在；RL继承SFT的FP32 master与Muown row state | 任务数、token数、教师、学习率、训练时长；不是§7的77.4B小模型SFT |

视觉预训练数据包含 caption、grounding、OCR、GUI、对话、视频和 visual coding；音频分成 speech-text interleaving、ASR 与 general audio captioning。[P, §3.1, p.7]

作者在 mid-training 将 hidden weight matrices 从 AdamW 切换至 **Muown**：它在 Muon 矩阵正交化更新之外显式控制 row norm。embedding、LM head、router 继续用 AdamW。理由是前期实验观察到 AdamW 的大 batch 数据效率递减；文中引用已有 optimizer mismatch 风险，同时报告自身 mid-training 未出现 loss spike。**未发生 loss spike 不是同预算 Muown 优于 AdamW 的完整 RL 消融。** [P, §3.2]

## 4. 主 RL 规模、成本与训练设置

### 4.1 先明确计数对象

每步抽 **1,568 prompts**，每 prompt 生成 **G=16** 个 sequence，名义总数为 **25,088**（文中约25K），消费 **2.7B–3.7B training tokens/step**，约 **110K–150K tokens/sequence**。这不是1,568条轨迹，也不是每条序列都达到1M；1M是训练支持的上下文上限。任务数、序列数、跨 context 的 token 数和过滤后训练消费应分开。[P, §4.1、§5.1、§6.1]

在数千GPU上运行，Pro/Flash的**RL post-training**预算分别为 **$2.6M / $0.9M**。Fig.3按累计该预算绘制 DeepSWE v1.1 average@3：Pro58.4→72.6（图标72.57），Flash48.7→65.7（图标65.68）。两条曲线有波动，不应把“随投入整体上升”解释为每一步单调改善或与另一个配方的因果比较。

| Fig.3 成本组成 | Pro | Flash |
| --- | ---: | ---: |
| Rollout | 43.8% | 44.9% |
| Training | 43.5% | 40.9% |
| Grader | 12.7% | 14.2% |

grader 是可见的大项，但这不是从零开发模型的总成本：预训练、mid-training、short SFT、离线环境生产／审计、教师生产和后续MOPD2的完整成本未一并披露。也没有完整列出GPU型号数量、小时单价和环境CPU费用。不能将百万美元成本按激活参数线性缩小成八卡预算。[P, Fig.3, pp.8–9]

### 4.2 主混合比例与优化器

主任务混合为 **agentic + competitive coding 68%、general tool use12%、aesthetic design13%、context following3%、cybersecurity4%**。68%不等于68%的数据都是 SWE 仓库修复。§4的四种环境描述也不是所有源的逐个清单；§6 profile的25个source不等于25个任务。[P, §5.1, pp.20–21]

主算法GRPO，异步partial rollout，**staleness=4**。采满一批时中断在途序列，在下一rollout阶段续跑；每次策略更新后续跑要重新prefill。大batch与partial rollout联合选择以摊销重建成本，不是无成本消除长尾。文中没有完整定义“4”的起算、跨token/sequence阈值与过期回收细节。[P, §4.1、§5.1]

Muown学习率 **3e-6**，**无weight decay、无warmup、grad clip=1.0**。Muon部分momentum0.95，Nesterov开启，Newton–Schulz10次，额外update scaling0.5；Adam部分betas0.95/0.95、epsilon1e-8。继承SFT的FP32 master weights和Muown row state，RL阶段冻结MoE router。这里的已给值只属于主大模型实验，不能填入9B未披露配置。[P, §5.1]

<a id="environments"></a>
## 5. 环境与数据：构建更多任务之前，先保证监督含义

### 5.1 Coding 的五条合成路线及补充来源

| 路线 | 输入与生成过程 | 任务含义与泄漏边界 |
| --- | --- | --- |
| GitHub PR／issue | 拉取PR和关联issue，启发式＋模型筛重复、格式错误和不可复现候选；issue充分则直接用，否则结合reference patch和repo重构需求 | 重构明确要求省略暴露解法的implementation细节；是否实际做到仍靠后续检查 |
| 日常开发工作流 | 收集组织内部员工真实请求，包括vibe coding、功能、refactoring、debug、maintenance；agent生成测试 | 不限于现成bugfix；员工请求数与公开许可未给 |
| Specification-driven coding | 生成详细、多约束规格及测试，要求将复杂规格转成可执行实现 | 密集规格不自动等于长程；需要核要求与测试一致 |
| Source-code-driven synthesis | 使用CodeMidas，从代码已有功能的observable behavior构造题面与环境 | 不依赖issue/PR，因此来源覆盖更广；外部CodeMidas总量不是本篇实际训练量 |
| Long-horizon SWE | 迭代细化需求、扩大变更范围、引入组件依赖，并补对应测试 | 新增复杂度应反映真实目标，不能只拉长轨迹 |
| 另外的来源 | 筛选public sources与licensed vendor data | 属五条生成路线之外的补充；Fig.4画出vendor框不表示正文改为“六条同类生成算法” |

共同输出是任务spec、可执行环境和verifier。原文声称覆盖多语言、开发语境、实现复杂度与时程；**没有给整个大模型私有coding池的候选仓库数、环境构建通过率、各路线任务数、人工比例、成本漏斗或最终manifest**。[P, §4.2.1, pp.9–11, Fig.4]

### 5.2 Accuracy of supervision：题面／测试对齐与四次真实求解互补

第一步是校准行为范围：测试应接受满足规格的实现、拒绝违反规格的实现；不强制参考解的偶然细节。覆盖不足或过度限制的题应复查；强迫实现题面没有的额外要求时，修改或删除相应测试。[P, p.10]

随后**每题做四次coding agent求解**。auditing agent的共享工作区含：题面、测试、reference patch、四条submitted patches、测试输出、完整conversation logs。它先陈述正确解需要满足什么，再看测试是否覆盖这些要求，之后逐个判断候选并与实际reward对照：

| 观察 | 报告给出的解释 | 本稿保留的证据边界 |
| --- | --- | --- |
| 测试通过，但auditor认为不正确 | 潜在false positive：验证不完整 | 是进一步复查线索，不把审查模型判断自动升级为真值 |
| 测试失败，但auditor认为正确 | 潜在false negative：测试过严或执行失败 | 需要分清规范冲突、环境失效与模型实际错误 |

**reference、完整日志对auditor可见，不代表它们对训练solver可见。** 四次自然候选是探测真实误接收／误拒绝的一种方法，不是证明覆盖了全部替代解或全部失败模式。[P, p.11]

### 5.3 Robustness of supervision：八次重跑检测另一种问题

对**有reference patch的任务**：应用前F2P失败、P2P通过；应用后两者通过，要求这些结果在**八次reruns**保持稳定。原文没有精确拆出八次是否分别作用于每种补丁条件，不能自行换算成某个总尝试数。目的在于flaky tests与环境引入的reward波动，与题意正确性不是同一维度。[P, §4.2.1, p.11]

同一rollout审计还检查如何取得reward，为hacking清理提供实际patch和行为证据。三类证据互补：**规格／测试校准检查目标含义；重复执行检查稳定性；自然轨迹检查两者在真实求解中是否一致。** 这不要求所有未来领域都有gold patch，也不等于本文公开了每步筛选率。

### 5.4 General agent：可重置的工作世界，不是线上SaaS无限调用

真实专业工作既依赖文件，也依赖复杂软件状态。作者将真实文件资料与真实软件的本地mock结合，在sandbox内提供支持范围明确的操作、状态、格式和错误行为，并通过MCP/API/CLI/GUI暴露。可离线执行的工具直接集成；mock服务实现局部重置，降低网络与外部服务限流的影响。**这是可控制的任务环境，不等于逐项复制真实SaaS全部功能。** [P, §4.2.2, pp.11–12]

Fig.5的环境侧流程是：规划agent指定workspace结构、工具、文件、数据库；web检索为计划提供现实依据，确立文件与表之间的关系；多个agent并行生成和填充；review agent做局部／全局一致性检查，包括实体名称、数值核对、时间线、引用关系；发现问题后迭代修复。每个场景的工作区和工具配置可不同，而不是不断往同一巨型环境堆全部接口。

任务侧由agent探索已有环境，用职业任务与一般题目作种子，构造目标和**atomic binary rubric items**。文件格式、数据库值等用代码判；开放内容用LLM判。重复同一judge及跨judge一致性可以提示歧义，但作者**明确说一致性不足以证明rubric真正衡量任务完成**。因此再用不同能力模型的rollout、结果和rubric判断复查，改过严／过宽条目，加入无关文件／数据库不应变更的负约束，并构造貌似正确却未完成任务的反例。训练时，该类任务使用自托管 **MiMo-V2.6-SFT** grader。[P, p.12]

未披露各mock的完整兼容范围、最终任务量、rubric汇总权重、审查通过率、每题judge预算和独立人类标注的误差率；不能用“多模型一致”填补这些缺口。

### 5.5 Visual agent：开放创作和目标复现使用不同评分依据

任务工件包括网站、互动应用、游戏、3D、slides、SVG、视频和Figma。开放设计先稳定pointwise rubrics：runtime正确、遵循用户需求、布局完整与基本美学，再对同题组内的**渲染工件**做比较，判断相对优劣。高保真复现则有明确视觉参考，主要用rule-based相似度（例如pixel similarity），辅以LLM整体判断。[P, §4.2.3, p.13]

不能把两类任务都简化为“图片打分”，也不能把它们的groupwise scoring直接称为§4.3.2的同一套coding GAR公式。原文没有给视觉rubric各项权重、渲染视口、交互覆盖或独立人类评测的完整协议。静态精选截图也不证明交互功能正常。

### 5.6 Cybersecurity：目标漏洞与任意crash不同

报告训练目标是现实项目中的**指定漏洞重现**，不是只触发一个崩溃。作者以OSS-Fuzz的大量已确认样本作为候选来源，但这个来源的“数万”不等于本篇最终训练量或公开1k集合。[P, §4.2.4, pp.13–14]

作者认为仅用有漏洞／修补后二进制的crash差异，可能受不完整patch或无关commit变化干扰；随机LLM判定也不适合稳定reward。其方案从ground-truth sanitizer报告提取**漏洞类型＋最上层project-level stack frame**，要求候选执行同时匹配二者；题面由同一报告产生，明确类型和函数，减少目标与判定的来源错位。环境提供对应commit源码和已构建的harness binary，以支持真实运行反馈。

这是作者对任务定义和自动验证的设计；二字段确定性匹配不构成对所有安全任务完整语义的证明。报告对CyberGym原设置的比较应按作者陈述记录，而不是未经复核宣称全部原数据无效。更关键的是§5.2脚注明确：**作者修订了CyberGym评测环境**。Table3成绩必须带这个条件，不能无提示地替代官方原协议分数。

### 5.7 多层反hacking：纠正策略、清理材料、攻击式筛查和持续审计

**Mid-training示范。** 根据早期不当行为合成纠错轨迹：保留原错误可辨识，模型反思、修改相关turn，再继续遵循任务spec执行。作者报告alignment改善，但没有单独的等量数据消融或精确增益。[P, §4.2.6, p.14]

**环境清理。** gold构建可能残留build logs、verifier outputs、patch、项目generated binaries或bytecode；清理repo内外可能泄解的缓存，同时**保留离线重建需要的第三方依赖**。Git保留base及更早历史，移除后续commit和ref；容器网络限制阻止取得上游修复与其他版本答案，辅以明确指令。不能转述成删除全部历史、缓存、依赖或普通开发测试。[P, pp.14–15]

Table2给出五种真实轨迹的模式：pytest安装较新版本读已修文件；Astropy取上游实现；Matplotlib克隆上游查代码；Django查对应ticket／changeset；Sphinx枚举版本以寻找现成修复。本文仅概括其证据性质，不将示例变成可执行作弊手册。[P, Table2, p.15]

**Hack Agent。** 用早期已知路径引导专门agent搜索残留泄漏和新捷径；每次发现后修环境、限制访问，再测试。作者称最终该agent未能在这些环境中成功，但这是给定搜索预算与攻击者的结果，**未找到攻击不等于不存在可利用路径**。[P, pp.15–16, Fig.6(a)]

**训练期间审计。** 定期离线检查真实策略轨迹，发现训练前未想到的捷径后继续修环境；GAR对确认借助外部／泄漏答案的轨迹先将effective reward置0，再重算组统计。Fig.6(b)上半图画不同数据源随清理轮数变化的被攻破比例；下半图画训练中**检测且确认**的hack轨迹比例，作者报告两模型均低于2%。它不等于独立估计的所有潜在hack发生率，也不能由此算环境审计召回率。[P, p.16]

## 6. Multi-harness：原文主张与我们生产harness路线的真实分歧

报告**不推荐直接把多个生产harness原样放入RL**。作者给出两个理由：生产系统的保障、工作流和大量约束提示未被task-completion reward覆盖，会使信用分配不可靠；模块紧耦合，不便隔离一个机制或受控重组。[P, §4.2.5, p.14]

其替代路线是共同的最小agent loop，保留system prompt、tools、context management等完成任务所需模块，再独立实现／重组，形成Code/General/Visual/Cyber的mini-harness。训练分布因而可变但更可控。不能为了贴近RepoHarness当前采用Claude Code而把这段改写为“作者支持直接训练所有生产harness”。

反过来，这仍是作者的方法判断：报告没有给所有生产harness方案的全面控制变量实验。它不自动批准我们弃用CC或再写一套通用harness。公开mimoagent代码同时支持black-box CLI，并不矛盾：**接口能够接入，与主实验实际采用什么是两件事**。当前代码和论文证据分开见§14。

每个prompt group内部使用相同harness配置，这与每组advantage的相对比较有关；harness代码库、行为和环境设置是分开配置的。实验中的四个mini-harness与三个held-out生产harness结果见§9.3、§13.4。

<a id="learning"></a>
## 7. Groupwise Agentic Grading：不是一个统一的“LLM reward”

### 7.1 GRS 与 GAR 的适用子集不同

GRS用于**部分高通过率coding任务**：离线比较多条解生成rubrics，训练中逐轨迹用这些rubrics打分。GAR主要用于**其余coding任务的mixed-outcome组**：在线联合看全组，在通过候选中重分配正优势。Fig.7画的是两条互补流程，不能默认每条轨迹依次跑GRS、GAR、所有惩罚，或将其合成权重编造成原文配方。[P, §4.3, pp.16–18]

### 7.2 GRS：先离线形成监督标准，再在线逐条检查

离线工作区给agent同题多条rollouts、题面和repo，以比较解法、重复错误和有效工作方式。输出solution rubrics和behavior rubrics。解法标准包括满足需求、边界条件和repo约定；行为标准包括搜集相关证据、检查修改效果。标准以题意为准：所有示例遗漏的明确要求仍可加入；某个成功解的风格不能强加给其他合法解。[P, §4.3.1, p.17]

训练中grader进入各rollout的执行环境，检查实现、执行结果和交互证据，给$S_i^{sol}$与$S_i^{beh}$。最终reward为：

$$
R_i=R_i^{test}\,S_i^{sol}\,S_i^{beh}.\tag{2}
$$

这里$R_i^{test}$为原二元测试奖励；失败仍为0。即使原始全组通过，rubric乘积差异也能产生信号。**它不能仅靠该乘法让全失败组产生非零奖励差异。** 原文没有给两种score的取值刻度、rubric汇总或grader成本上限，不能自行假设都已校准到[0,1]。[P, p.18]

§4.1概括dynamic sampler过滤all-pass/all-fail，§4.3.1又保留全raw-pass组的rubric信号。语义上必须区分raw test outcome与最终训练score，但原文没有完整公开各分支的过滤callback顺序。**本稿记录这个待核接口，不擅自填成“必先rubric再过滤”的已实现事实，也不直接判为论文bug。**

### 7.3 GAR：保留二元结果，改变通过解之间的正优势权重

在线grader是SFT-trained agent，可访问全组的题面、repo、patch、测试输出，能够读代码并运行targeted tests。比较维度为：解决路线、实施精确性（不漏要求、不加不必要fallback）、必要改动范围、任务之外影响、代码库惯例。证据不足允许并列。确认借助外部／泄露答案时先更正effective reward为0。[P, §4.3.2, p.18]

令更正后的二元reward为$R_i$，组均值$\bar R$，$A_i=R_i-\bar R$，$\mathcal P=\{i:R_i=1\}$。质量因子$f_i\in(0,1]$先降低相对差的通过解，再用公共系数恢复通过解的正优势总量：

$$
\lambda=\frac{\sum_{j\in\mathcal P}A_j}{\sum_{j\in\mathcal P}f_jA_j},\qquad
A'_i=\begin{cases}\lambda f_iA_i,&i\in\mathcal P,\\A_i,&i\notin\mathcal P.\end{cases}\tag{3}
$$

**未截断版本**保持$\sum_{i\in\mathcal P}A'_i=\sum_{i\in\mathcal P}A_i$，且失败解不变。作者希望避免仅压低正优势、相对加重负压力而推动entropy异常增长。

**实际实现描述多了两步**：先限制$\lambda$上限，再对通过与失败的全部优势减组均值，得到最终零均值的$A_i^{new}$，广播到该轨迹response tokens。因而不能继续声称实际版本总是保持原正优势质量或“失败优势完全不变”。rank→$f$映射、cap值、混合reward的完整执行顺序未披露。[P, p.18]

一个仅用于解释的手算例：$R=(1,1,0,0)$，$A=(.5,.5,-.5,-.5)$，通过解$f=(1,.25)$，未cap时$\lambda=1.6$，得$(.8,.2,-.5,-.5)$。若假设cap为1.2（**不是论文超参数**），cap后为$(.6,.15,-.5,-.5)$；再中心化得到$(.6625,.2125,-.4375,-.4375)$。它直观展示了cap＋中心化为什么会改变失败优势。

原文开头限定mixed-outcome groups，因此全raw-pass导致$A=0$、Eq3成为0/0的情形不能仅用“$\mathcal P$非空”放行。hack更正后若全部失败的处置、grader不可用时“original advantages”是否在更正前后，未完全指定。已明确的是grader异步运行，不能使用的输出退回原优势，不应把这等同于任务环境失败。[P, p.18]

### 7.4 GAR 消融：非常有用，但不是主混合实验的全部收益解释

Fig.8比较Flash的**code-only RL、batch128、token-mean loss**，开／关online GAR，指标是DeepSWE v1.1 avg@3、平均总turns和总token。没有GAR时后期turns/token增长快、更多碰长度上限、passrate改善难持续；有GAR时收益延续到step52，turns相对稳定，token仍逐渐增多。[P, Fig.8, pp.18–19]

它不证明GAR让所有阶段的绝对token数都更低，也不是主实验1,568 prompts、prompt-mean与跨领域混合的同一设置。维护者导向审查还观察到不使用GAR的策略更常加入投机兼容分支、广泛导出、吞异常、放松校验或评测特定配置；文中没有该审查的样本量、盲评或误差条，保留为作者的定性发现。

### 7.5 Group-relative length penalty：只在相对易组的成功轨迹上扣分

令$\ell_i=|o_i|$为**生成token数**，$\mathcal P_q$为prompt $q$的成功轨迹，$A\in[0,1]$是通过率阈值、$B\in(0,100)$是成功长度百分位（此$A$不是优势$A_i$）。仅当$|\mathcal P_q|/G>A$时，取
$\ell_q^\star=\operatorname{Quantile}_{B/100}\{\ell_j:j\in\mathcal P_q\}$，然后：

$$
\widetilde R_i=R_i-\mathbf1[i\in\mathcal P_q]X\left[\operatorname{clip}\left(\frac{\ell_i/\ell_q^\star-1-\delta}{s-\delta},0,1\right)\right]^\gamma.\tag{4}
$$

$X\ge0$是最大扣分，$\delta\ge0$容忍相对超长，$s>\delta$是饱和位置，$\gamma\ge1$控制增长形状。比值达到$1+s$时扣满$X$；低于或等于$1+\delta$不扣。失败轨迹不因该项扣分，不达通过率门槛的组保留原reward。作者明确用调整后的reward计算outcome advantage，借门槛为难题保留探索空间。[P, Eq4, pp.19–20]

没有给实际$A,B,X,\delta,s,\gamma$值、与GRS/GAR所有分支的完整组合顺序，也没有这一项独立的充分对照。它不同于统一按长度惩罚所有序列，更不同于把外部超时认作模型失败。

### 7.6 Segment behavioral penalty：正轨迹错误token归零，负轨迹错误token更负

$h_{i,t}=1$标记被规则识别的格式或tool-call错误token；$H^\pm,C^\pm$分别是**整个training batch中、loss mask=1**的被标记／未标记token集合，正负取所属轨迹的$A_i$符号。各求和按token计数，不是按轨迹计数：

$$
\widetilde A_{i,t}=\begin{cases}
\alpha(1-h_{i,t})A_i,&A_i>0,\\
[\beta(1-h_{i,t})+\kappa h_{i,t}]A_i,&A_i<0,\\
0,&A_i=0,
\end{cases}\qquad \kappa>1,
$$
$$
\alpha=\min\!\left(\alpha_{\max},1+\frac{\sum_{H^+}A_i}{\sum_{C^+}A_i}\right),\qquad
\beta=\max\!\left(\beta_{\min},1-(\kappa-1)\frac{\sum_{H^-}|A_i|}{\sum_{C^-}|A_i|}\right).\tag{5}
$$

$\alpha_{max}\ge1$，$0<\beta_{min}\le1$。正轨迹被标记token是**零优势而非负优势**，其余正token适度放大；负轨迹被标记token乘$\kappa$，其余负token向零缩小。分母为零时相应scale设1；触发clip或零分母时不再保证质量守恒。原文未给具体阈值、错误检测误差率或所有segment规则配置。[P, Eq5, p.20]

所谓各符号总优势质量守恒，是按该公式定义的token求和；**不自动保证加入每token IS ratio、各prompt不同loss分母之后，梯度向量或参数更新保持不变**。这属于本稿的数学边界解释，不是报告另外给出的定理。检测到“工具不可用”也需要区分模型编造工具与环境供给错误，不能据关键词统一惩罚。

## 8. 主优化目标：prompt-mean、真实行为概率和四个解耦边界

### 8.1 Eq.(1) 与样本权重

报告的基础目标为：

$$
\mathcal L(\theta)=-\mathbb E_{q\sim\cup_d\mathcal D_d,\{o_i\}_{i=1}^{G}\sim\mu_{\theta_{old}}(\cdot|q)}\left[
\frac{1}{\sum_{i=1}^{G}|o_i|}\sum_{i=1}^{G}\sum_{t=1}^{|o_i|}
 r_{i,t}M_{i,t}A_i\log\pi_\theta(o_{i,t}\mid q,o_{i,<t})\right].\tag{1}
$$

组内按response token长度归一化，外层对prompt聚合，即**prompt-mean**，不是把全batch所有token一起求均值，也不是每条sequence先均值再等权。作者说这有助于抑制response长度增长；没有提供同条件完整消融证明所有情况下优于token-mean。[P, p.8、§5.1]

§6只有model-generated segments参与loss。展示公式分母写为$\sum_i|o_i|$，不明确写成 surviving-mask-token 数；对被屏蔽样本、多context重复前缀以及零有效token组，不能用框架默认实现填补分母语义。Eq5用token-level调整优势替换Eq1的$A_i$；以上不是宣称所有其他reward分支的组合顺序都已给全。

### 8.2 IS ratio 与 clipping 实际为mask

§5.1明确逐token计算
$r_{i,t}=\operatorname{sg}[\pi_\theta(o_{i,t})/\mu_{\theta_{old}}(o_{i,t})]$。
分子来自当前训练模型，分母是token生成时的rollout概率；partial rollout**不重算旧的推理概率**。`sg`阻止对ratio本身回传梯度，再以其加权$\nabla\log\pi$。[P, p.21]

四个独立边界分别作用于正／负优势的下界与上界：

$$
M_{clip}=\mathbf1\{(A\ge0\land\epsilon_+^\ell\le r\le\epsilon_+^h)
\lor(A<0\land\epsilon_-^\ell\le r\le\epsilon_-^h)\}.
$$

两侧初始区间都是 **[0.2,5.0]**，是ratio本身的界，不是PPO的$1\pm\epsilon$偏移；区间外token以mask去掉，不是传统PPO的`min(rA, clip(r)A)`展示式。entropy太低时放宽正界、收窄负界，太高反向；具体调节规则和后续值未披露。训练监测两方向token clipping率。[P, §5.1]

源文Eq1将$M$泛称token-level mask，p.21又用$M$写clip mask，§4.3.3还以loss-mask集合定义行为塑形。本文分名以解释这些职责，但不捏造其未公开代码的精确布尔组合或执行顺序。也没有据“GRPO”自行加上参考模型KL系数、entropy bonus或std normalization；这些未披露不等于为零。

<a id="systems"></a>
## 9. 大模型评测、收益和主要负结果

### 9.1 评测对象与条件

§5.2按Code、Cyber、General、Visual四类组织。Code使用DeepSWE v1.1、ProgramBench和内部MiMo Code Bench；ProgramBench要求从binary和文档重建程序行为，不等于普通单函数编程。Cyber包含目标重现与更复杂漏洞利用阶段的不同bench，不能汇成一个安全“准确率”。General涵盖模拟SaaS跨应用、MCP工具、职业交付、终端与桌面；Visual为内部开放设计和参考复现任务。[P, pp.21–22]

基线模型若可配置reasoning effort，均用其最高max设置，但这不表示总token、工具调用、时间或硬件相同。正文缺少许多benchmark的实际题目数、重复次数、执行harness revision、完整budget、污染切分与置信区间。运行曲线明确的DeepSWE avg@3不能自动赋给最终表全部行。

### 9.2 训练曲线与“效率”的限定

Fig.1展示六个域的曲线；Fig.9进一步将DeepSWE、AutomationBench、视觉任务的分数和总token曲线配对。两模型总体进步，**通常伴随更多token使用**。报告“更token-efficient”的机制动机与GAR小实验，不能被改写成最终所有任务用更少token取得更高分。[P, pp.1、22]

### 9.3 跨harness迁移

Fig.10跟踪四个训练mini-harness与held-out Codex、Claude Code、mini-swe-agent在DeepSWE v1.1的pass@1。后者均改善，平均约50%→66%，两组均值差距缩小。这支持学习结果能够迁移到未参与训练的执行面。[P, Fig.10, p.23]

但是没有完整的**等数据／等预算single-harness RL，在同七个harness评测**的竞争基线，不能由图单独得到“多样性是唯一原因”或“越多harness越好”。代码实现能力、训练数据变化与更强初始化都需分开。小模型也有独立实验，见§13.4。

### 9.4 Router freezing：有较明确的受控对照，但范围是给定模型层

Fig.11比较两个只在router是否冻结上不同的Pro训练，展示**decoder layer9、384 experts**。router可训练时，前20步load CV从约0.78升到2.0，peak/mean从6到16，低于0.1×mean的cold experts从0.5%到22%。将step20模型的router恢复到最初pre-RL值、其余权重不变后，负载恢复，作者报告benchmark不变，因而将崩塌归因为router漂移。[P, §5.4, pp.23–24]

正式训练冻结router后，该层CV约0.7、峰值约5.5、cold约1%，benchmark仍能改善。没有全层、全模型、全microbatch的统一保证，也未公布替换router前后的详细score表。冻结router**不等于冻结每个token的routing结果**：hidden states与数值运算仍能改变top-k，因此R3仍有独立用途。

### 9.5 Table 3 全表：最终 MiMo-V2.6，不能与RL曲线终点混用

表列来自mixed RL后的MOPD2最终模型；对照名称依原表。`—`表示未报告，不是零分。除明确标注的指标外保留原值，不将GDPval1673写成百分比，亦不替作者补设具体标度。

| Benchmark | V2.6 Pro | V2.6 Flash | V2.5 Pro | Claude Opus5 | GPT-5.6 Sol | Claude Fable5 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DeepSWE v1.1 | 71.9 | 67.9 | 19.0 | 74.0 | 73.0 | 70.0 |
| ProgramBench | 26.5 | 26.0 | 12.5 | 37.0 | 25.0 | 33.0 |
| MiMo Code Bench | 63.2 | 61.2 | 40.4 | 68.6 | 59.3 | — |
| AutomationBench v1.0.6 | 53.1 | 52.3 | 16.0 | 50.3 | 45.8 | 46.2 |
| Toolathlon-Verified | 76.9 | 73.6 | 49.1 | 80.6 | 74.9 | 77.9 |
| GDPval-AA 2.1 | 1673 | — | 1107 | 1708 | 1588 | 1595 |
| Agents’ Last Exam | 31.6 | 27.6 | 13.2 | 31.6 | 30.8 | 25.7 |
| Terminal Bench4.0 | 34.9 | 28.8 | 1.5 | 49.0 | 39.9 | 42.4 |
| Terminal Bench2.1 | 89.9 | 87.6 | 65.2 | 89.1 | 88.8 | 84.3 |
| OSWorld-Verified | 82.0 | 80.8 | — | 83.4 | 83.0 | 86.0 |
| JobBench | 62.0 | 61.2 | 25.0 | 65.7 | 45.4 | 57.4 |
| CyberGym（作者修订环境） | 94.0 | 95.1 | 40.1 | — | — | — |
| MiMo Cyber Bench | 80.2 | 77.2 | 0.0 | — | — | — |
| ExploitGym | 17.8 | 6.0 | 0.2 | 22.1 | 30.3 | 28.4 |
| ExploitBench | 47.9 | 25.3 | 16.6 | 70.0 | 78.5 | 78.0 |
| SEC Bench Pro | 66.3 | 47.5 | 17.7 | — | 79.1 | — |
| MiMo Visual Coding | 72.3 | 71.5 | — | 70.0 | 73.4 | 69.1 |

[P, Table3, p.26]。CyberGym V2.5值按原图 **40.1**；不要沿不精确摘录改成40.0。Fig.3的72.57/65.68与本表71.9/67.9属于不同阶段／报告位置，不能择高拼表。MOPD2增量没有同样的完整独立表，也没有隔离每个环境审计步骤的质量收益。

## 10. 系统失败是结果的一部分，不应从总结中删除

Fig.12把30个training steps按真实elapsed time排列：Pro **123.1小时**、Flash **81.8小时**，包含失败与恢复间隔。没有全GPU型号／数量的完整配置，不能简单乘成精确GPU-hours。[P, §5.5, pp.24–25]

| 故障层 | 报告中的实际观察 | 处理或尚未解决的边界 |
| --- | --- | --- |
| 基础设施 | GPU memory double-bit errors；Flash15–16步之间Cyber K8s pods故障；Pro14步后grader网络不可达 | 重启／恢复计入时间线，不宣称系统从未中断 |
| Rollout预测 | startup先完成短轨迹，长度先验偏小，同时耗尽HBM与pinned-host KV池 | 预测只看已完成轨迹的偏差被真实暴露 |
| Harness异构 | 某harness平均长度不到同代码来源其他harness的一半，重启后第2、3步重复出现问题 | 仅按粗source均值不一定足以建模分布 |
| 训练MoE | full batch相对均衡，某microbatch单个EP rank却承担超过mean30×的token，GPU OOM | 调整parallelism降低activation峰值；冻结router并未消除所有局部失衡 |
| Driver／packing | Flash长序列使prefetch量超过host内存；已做跨节点packing，仍可能本地CPU OOM中断 | 数据面分离降低瓶颈，不自动提供无限容量 |

这些是特定运行的故障记录，不应外推为所有实现的常见失败率。它们恰好约束§6的宣传性措辞：高并发、预测、offload和distributed packing是机制，效果仍受统计偏差、峰值与生命周期影响。

## 11. MOPD2：完成混合RL后，通过不同前缀和教师拓展能力

**Multi-Prefix Multi-Teacher On-Policy Distillation** 保留MiMo-V2-Flash的多教师思想，并区分三类学生访问状态。[P, §5.6, pp.25–26, Fig.13]

| 分支 | 学生从哪里出发 | 谁提供监督 | 与普通示范模仿的区别 |
| --- | --- | --- | --- |
| Standard MOPD | 给task prompt，让学生完成整条自主rollout | 适合该可验证领域的mixRL teacher | 教师在学生访问的历史上监督 |
| Teacher-Prefix OPD | 从teacher rollout中取完整历史prefix，停在一个assistant动作之前 | 该领域mixRL teacher | 学生自己生成下一turn，教师对同history＋学生已生成token给token-level监督 |
| SFT-Prefix OPD | 从SFT示范取相同形式的prefix | 在高质量合成示范上训练的SFT teacher | 示范提供状态，目标不是简单复制原示范的固定下一句 |

一条有$k$个assistant-turn决策点的源轨迹可以形成$k$个prefix训练起点。prefix保留完整此前交互；它不是任意截取一段文本就能恢复合法环境状态。对开放领域，教师在学生长时间偏离后的历史上覆盖可能不足，固定示范前缀限制了偏离范围；在单turn上学生仍生成自己的动作。[P, p.25]

该阶段扩展到较难定义训练时验证器的任务，包括长程游戏开发、scientific research和embodied intelligence。**报告没有给这些分支的完整任务集、mix ratio、teacher冻结／更新规则、KL方向、full-vocab或top-k监督方式、异tokenizer映射、单turn长度或总成本**。Eq1是RL目标，不是MOPD2蒸馏损失公式。不能从旧MOPD或ReOPD自动继承这些缺项。

外部ReOPD补查有助于理解prefix replay和教师在off-distribution历史上的局限；其具体schedule与实验数字不是MiMo-V2.6本篇已采用的证据，见§14。

## 12. Infra 全链：逻辑轨迹、错误责任与物理数据分别管理

### 12.1 四级轨迹身份

| 层 | 本篇定义 | 对训练／缓存的责任 |
| --- | --- | --- |
| Sample | Mixer派发的一个prompt | 组算法产生一组Sequences，组整体接受／拒绝 |
| Sequence | 一次Agent Loop执行 | 持有environment lifecycle，可有多并发contexts |
| Context | 一条对话branch | prefix matching、KV复用和训练数据export单位 |
| Segment | 一次system/user/model/tool turn | 只有model-generated段产生loss |

Agent Loop负责setup、interaction、reward evaluation、cleanup，向外部agent暴露请求endpoint；外部agent按需调用inference。每个对话同时维护string prefix与实际token序列；匹配已知prefix后只tokenize新suffix。[P, §6.1, p.27]

不能从接口设计推出任意生产harness的历史改写都自然满足append-only条件；同时，Context是export单位并不等于每个export row成为独立GRPO样本。如何在具体代码中保持这些身份，需要另做静态／运行核查。

### 12.2 Penalty Module：检测与动作分开，不把所有失败都叫坏样本

Rule可用规则或模型judge在segment/context/sequence上检测infra故障、乱码、不存在工具、重复等。Strategy决定mask、set/scale/subtract advantage或仅monitor。Composite early stop会停止rollout、置outcome reward为0，对触发turn与更早turn分别处置，mask sibling contexts。[P, §6.1]

层级升级：无存活model turns的context删除；无存活context的sequence优势为0；无存活sequence的sample拒绝。**这与“其中任意一个sequence失败，就丢全组”不是相同规则。** 具体哪些条件被视为模型可归因错误、哪些重试／恢复，本篇没有公开完整规则表，不能把同名错误跨系统照搬。

### 12.3 Harness Pool 与 Payload Porter

大batch若每个agent/harness instance都用一个独立Ray actor，会放大GCS/FD与进程开销。作者采用固定数量的persistent host actors，每个host多租户共享一个event loop，各租户有自己的状态，按in-flight实例数平衡；模型侧共享endpoint、proxy和tokenizer，环境侧共享加载的harness代码；阻塞环境操作和tokenization放后台线程。[P, Fig.14、§6.2, pp.27–29]

不同harness代码库放不同pool；pool的host预算比例在启动时配置，**不等于Mixer每个step动态选择的数据比例**。同一个prompt group用共同配置，以保证group-relative比较的语境一致。

序列结束时，将tokens、行为logprobs、routing IDs、采样候选集及多模态数据写入分布式KV store（例如Ray object store/TransferQueue），driver只保留reward、长度和key等轻量metadata。grader完成后改变reward，sampler按分布和有效性筛选，hook进行长度／优势塑形；per-token advantages仍回存数据面，默认排除最终全零优势的组。OPD同样可以将teacher监督作为异步产物消费。[P, §6.2, pp.28–29]

packing规划只看元数据；每个training TP group用一个packer，按需要拉unpadding rows或CP窗口涉及数据，再提供共享只读副本。大型多模态payload在环境侧保留、按delta传输；图像item在TP ranks上先独立负载均衡地跑复制的ViT，再按text token所在rank重分配embedding。不能把“写入一次”理解成整个系统绝无后续复制，也不能据此假设host峰值已完全受控（§10有反例）。

### 12.4 Sample Mixer：接受率不是模型通过率

跨25个source，mean generated tokens与active rollout duration分别相差 **90×和66×**。Fig.15用log坐标，起点为steps1–5均值、终点为26–30；tokens按各context求和、在text filtering之前；时间是**已完成rollout的活跃时间，不含training pause**。[P, §6.3, Fig.15, pp.29–30]

令$B_i$为每step希望保留的组数，$r_i$为**group acceptance rate**，$t_i$为模型＋环境的活跃时长，则需求$m_i=B_i/r_i$。这里$r_i$不是task pass@1，接受率还受全零组、有效性和过滤影响；与Eq1的IS ratio $r$也不同。

### 12.5 自适应并发与派发：Eq.(6)(7)

慢source需要更大并发以贡献同样多的训练组。其额外采样比例与source预算为：

$$
p_i=\operatorname{clip}(ct_i-1,p_{\min},p_{\max}),\qquad
\frac{\sum_i m_ip_i}{\sum_i m_i}=\bar p,\qquad
\text{budget}_i=(1+p_i)m_i.\tag{6}
$$

$c$依据近期时间／接受率校准，使需求加权平均oversampling等于全局$\bar p$；边界、零接受率处理和不可行目标的fallback未给。稳态所需并发与$t_i m_i$成比例，不是给所有来源相同slots。

如果本batch已有$A_i$组被接受（此处$A_i$是**count不是advantage**），用目标需求和当前缺口混合：

$$
w_i=\alpha\frac{B_i}{r_i}+(1-\alpha)\frac{(B_i-A_i)^+}{r_i},\qquad(x)^+=\max(x,0).\tag{7}
$$

smooth weighted round-robin按$w_i$选择source。$\alpha=0$纯deficit，1纯target；作者考察0.5混合，steady-state startup还让初始并发按$t_i m_i$分配。这里$\alpha$与Eq5行为正优势scale没有同一含义。[P, pp.30–31]

Fig.16的六源输入原值：

| Source | 每步目标占比 | mean active duration | group acceptance |
| --- | ---: | ---: | ---: |
| Chat | 7.0% | 16.4 min | 64.1% |
| Visual | 9.0% | 12.1 min | 100.0% |
| General | 7.0% | 14.2 min | 61.5% |
| Cyber | 14.3% | 50.7 min | 89.0% |
| Code1 | 34.1% | 24.1 min | 99.5% |
| Code2 | 28.6% | 37.2 min | 71.0% |

**这是trace-driven simulation，不是完整RL四组训练消融。** 固定并发、source预算不构成约束，时长按profile末期校准；图注明确**排除training time、credit-assignment latency、staleness expiry和replay**。它支持混合方案在这个仿真里改善occupancy与collection balance，不直接给完整time-to-score加速比。

### 12.6 Predictive Dispatch 与启动／恢复 replay

根据各source已完成序列的input＋generated tokens、所有contexts总长估算KV需求；安全系数放大后必须能放入target rank剩余GPU KV。层级cache还含pinned host pool，已准入状态可在两层保留。环境等待时间比例将rollout concurrency折为预期inference concurrency，限制不超过CUDA graph capture对应的max-running-request；放置时在可行rank中取剩余容量较大者，容量为并发slot和KV容量（都换成sequence单位）的较小值。[P, p.31]

此估计真实遇到过“已完成短轨迹偏差”并OOM，不能把算法描述视为可靠容量保证。安全系数、层级缓存预算和异常分布fallback仍需具体实现验证。

作者测到初始采集约为连续稳态时长的 **1.8×**。replay只在**启动／checkpoint恢复后的第一次collection**补慢source缺口：fresh start要求存量来自run starting policy；恢复要求在该source staleness内。之后回到正常rollout，不是全程无界经验回放。[P, §6.3]

保持source配额只维持了一个分布维度；并不能单独证明同source内部不会偏向快题／短轨迹。原文已经指出初次采集存在这种偏差，本文不把source quotas等同完整无偏采样。

### 12.7 四种时间不要混为一个指标

代码／报告中应区分环境active rollout、等待grader／credit、training pause、完整step／恢复时间。Fig15和Eq6用active时长；Fig16删去部分真实开销；Fig12则包含失败恢复。它们并不互相矛盾，也不能选一个最好看的分母代表全部系统。

### 12.8 训推一致性：权重、离散routing、概率支持集分别对齐

主大模型系统继续使用 **SGLang inference＋Megatron-LM training**。rollout experts为MXFP4；每次参数更新后按Humming GEMM的数字约束做quantize–dequantize，使两端看到一致的专家权重。即使权重一致，数值差异仍可能改变离散expert选择，故用R3记录rollout expert IDs并在训练回放。[P, §6.4, p.32]

对top-k/top-p采样，训练logprob必须在**当时采样的候选集**内重新归一化：不能重新计算当前top-p集合，也不能直接用全vocab概率冒充行为概率。GPU→CPU先传固定full-vocab宽度bitmap，避免依赖动态长度的同步并确保不截断大集合；之后改稀疏表示。作者观察典型top-p0.97时平均候选少于5，但这不是所有token都有最多5个候选的保证。

R3与候选集payload被作者描述为很小、移出关键路径，但本篇没有完整单项延迟表。相同QDQ专家权重＋这些replay机制也不保证所有kernel、batch形状和硬件完全逐位一致。

### 12.9 Context Cache 与 DFlash：状态复用、搬运和真实吞吐

每个context有persistent key；同一policy版本中缓存包括generated tokens，下一轮只prefill新suffix。routing记录、候选集**在最终rollout收集时返回**，不逐turn碎片化传输。多模态输入只发送新图像，policy更新或cache miss再发送完整输入。[P, p.32]

KV在generation时驻HBM，工具等待时进入pinned-host池，side CUDA streams执行offload／restore。原文说不阻塞generation，是作者设计与运行描述；不能不经目标机测量就为本项目承诺零延迟。

实际RL默认 **DFlash block-6**，替换从SFT继承的 **MTP-3**；先在SFT策略上训练draft，再用early-RL logs按实际训练分布重采样微调。默认条件下accepted length比MTP高 **31.3%**；block6相比block8的global average throughput约高 **6%**、accepted length近似；RL-adapted FP8 draft在长上下文负载上per-node throughput约高 **10.3%**。[P, pp.32–33]

三项分母和基线不同，不能相乘，也不能把accepted-length增长当作整体训练加速。draft训练的全部数据量、硬件与成本未披露。

### 12.10 Trainer：SWA CP、optimizer offload 和 fused loss

训练context达1M，而SWA窗口只有128。CP下SWA只交换query可见的window范围KV，其每层通信不随全序列长度同比增长；GA仍有自身成本。optimizer states常驻CPU，参数更新时回GPU；融合policy-gradient（有／无top-p renormalization）、OPD及可选entropy、label logit、top-p mass计算到一个kernel，减少memory和step time。[P, p.33]

这些机制未给各自完整性能消融。参数、routing和多模态payload的真实格式、CP packing、更新同步细节也没有在报告中公开到可以重写同等系统的程度。不能用后面的开源verl通用README补出这套大模型内部Megatron实现。

<a id="open"></a>
## 13. 9B 开放实验：更接近可复用起点，但成本与训练分支必须说清

### 13.1 Table4：Distill-Qwen-9B 是 SFT 蒸馏，不是直接OPD结果

从**Qwen3.5-9B**开始，在MiMo-generated coding/general/visual/cyber轨迹上SFT，得到MiMo-V2.6-Distill-Qwen-9B。数据共 **77.4B total tokens、27.2B loss tokens**，表caption明确是weighted SFT composition，数值四舍五入一位。[P, §7.1, pp.33–34]

| Source | Total tokens(B) | Token share | Loss tokens(B) |
| --- | ---: | ---: | ---: |
| Code | 23.2 | 29.9% | 7.3 |
| Cyber | 11.0 | 14.2% | 4.8 |
| General | 22.0 | 28.5% | 5.7 |
| Visual | 21.2 | 27.4% | 9.4 |
| Total | 77.4 | 100.0% | 27.2 |

表内百分比由未round的原始总数算，不能因显示小数复算略不同就判错误；token不等于独立实例、独立字节或可下载的同量语料。不能把这一大SFT预算称为“直接用免费小基座就能做纯RL”，也不能将这段SFT推定为MOPD2同一目标。

### 13.2 Table5：公开约7k是task IDs，不是主大模型所有环境

| 开放领域 | Task family | 近似训练任务数 | Verifier |
| --- | --- | ---: | --- |
| Code | Software engineering | 3k | executable tests |
| Cyber | Vulnerability reproduction | 1k | rule checks |
| General | Knowledge work | 1k | rubric judging |
| Visual | Web development | 2k | visual grading |

数字按各training set的distinct task identifiers计数，合计约7k。另有约1k music-generation任务资源，未在Table5四行中；是否与其他集合／release清单交叠未逐项核实，不能一口气宣布“精确8,000个独立镜像”。[P, §7.2, p.34]

主Pro/Flash环境生产的完整规模未给，**不能用公开3k coding反填主RL任务数**。数据卡revision、镜像、test/gold、训练／评测切分、许可证和下载体量仍要查实际资产；本轮未下载数据或镜像运行。

### 13.3 Table6：四个独立GRPO模型，不是一列统一的全域checkpoint

从同一个SFT起点，对coding、cyber、general、visual分别用对应开放集做GRPO；四个internal mini评测与其training set来自相同task distribution。这不是公开的详细split／去重证明。[P, pp.34–35]

| Benchmark | 原表metric | Qwen3.5-9B | SFT | 对应领域RL |
| --- | --- | ---: | ---: | ---: |
| SWE-bench Verified | avg@3 | 60.0 | 61.1 | 66.2 |
| SWE-bench Pro | avg@3 | 32.0 | 44.6 | 47.6 |
| MiMo Code Bench mini | avg@3 | 19.5 | 51.6 | 59.9 |
| MiMo Cyber Bench mini | avg@3 | 5.7 | 31.3 | 47.0 |
| AutomationBench v1.0.6 | avg@1 | 5.0 | 30.3 | 33.1 |
| Terminal Bench2.1 | avg@1 | 27.0 | 37.1 | 52.8 |
| Toolathlon-Verified | avg@1 | 25.9 | 35.2 | 38.0 |
| OfficeQA Pro | avg@1 | 9.0 | 19.5 | 24.8 |
| JobBench | avg@1 | 2.6 | 18.3 | 25.2 |
| MiMo General Bench mini | avg@1 | 28.5 | 62.2 | 70.6 |
| MiMo Visual Coding mini | avg@1 | 61.7 | 64.0 | 72.4 |

11行在对应RL后均高于SFT，但不存在由这张表证明的“一个checkpoint无领域回退”。**avg@3不是pass@3**，不能解释成三次中至少一次成功。正文另报internal music score45.7（SFT）→52.5（RL），没有该任务的完整协议或数据划分。

9B的每题采样数、batch、RL steps、optimizer、GPU数量、实际context/turn预算与各损失开关，在本段没有完整列出；不能从主大模型1568×16、Muown或1M填进去。code列是**single-harness RL**，下一表另开训练。[P, Table6、§7.2]

### 13.4 Table7：独立多harness coding实验，全表与归因限制

同一9B SFT起点，四个mini-harness联合训练，三个held-out为Codex、Claude Code、mini-swe-agent。Mean是七列**不加权均值**，一位小数。[P, Table7, p.36] 以表内已round的七列复算，SWE-Pro的multi-harness RL均值为46.4429，原表Mean为46.5；可能涉及未round底层值，本轮未取得底表，因此保留原表并说明，不静默改成46.4。

| Dataset / model | mini1 | mini2 | mini3 | mini4 | Codex | Claude Code | mini-swe | Mean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Verified / Qwen3.5-9B | 58.4 | 36.4 | 54.8 | 57.8 | 48.6 | 54.8 | 60.6 | 53.1 |
| Verified / SFT | 61.7 | 63.9 | 61.7 | 63.1 | 58.5 | 61.7 | 65.3 | 62.3 |
| Verified / +multi-harness RL | 67.9 | 65.1 | 66.6 | 67.2 | 61.1 | 65.3 | 66.7 | 65.7 |
| Pro / Qwen3.5-9B | 33.5 | 15.2 | 31.1 | 31.1 | 23.1 | 26.9 | 31.6 | 27.5 |
| Pro / SFT | 45.2 | 46.6 | 45.1 | 45.5 | 40.3 | 42.2 | 45.6 | 44.4 |
| Pro / +multi-harness RL | 48.5 | 46.9 | 47.6 | 48.0 | 42.6 | 43.1 | 48.4 | 46.5 |
| Code mini / Qwen3.5-9B | 19.0 | 7.5 | 16.5 | 22.5 | 10.5 | 13.5 | 17.5 | 15.3 |
| Code mini / SFT | 53.2 | 56.7 | 51.5 | 56.3 | 46.0 | 51.2 | 56.8 | 53.1 |
| Code mini / +multi-harness RL | 62.5 | 64.5 | 57.0 | 63.3 | 50.7 | 53.0 | 62.0 | 59.0 |

SFT相对原模型的21个dataset×harness格子全改善，multi-harness RL再全部改善；Code mini较SFT各列为 **+1.8～+9.3pp**。**但缺少等预算single-harness RL在同七列上的完整对照**，所以不能把全部增量归因于harness diversity，更不能拿Table6不同执行条件的单个值直接构造这个缺失实验。

### 13.5 Fig17网站案例与结论边界

图展示三种prompt的三个模型产物：Momentum Software Studios首页、Ethiopia文化网站、HR Internship管理界面。可见布局、图片和信息组织从原Qwen到SFT/RL更丰富；作者以这些例子解释美学和功能完整度提升。它们是精选静态展示，prompt原本截短，缺少完整代码与交互回放，因此**本轮可核视觉差异，不声称独立验证全部功能或统计代表性**。[P, pp.35–37]

## 14. 配套资产与必要外部补查：不替主报告填缺项

### 14.1 实际可访问的官方项目

本轮通过GitHub连接器核对官方组织，未找到以`MiMo-V2.6`命名的独立repo；这不表示没有开放代码。实际取得的三个fork如下：

| 资产与固定commit | 实际读取范围 | 可以确认／不能确认 |
| --- | --- | --- |
| [XiaomiMiMo/mimoagent][mimoagent] `467f0a19016f0ac4d63b8d17a1f0da9ba07f232c` | 完整README | agent/model/environment/dataset四层；原mini-swe-agent fork；原生白盒工具与多CLI黑盒，三种SDK协议，多后端，数据grader入口。未跑代码，不等于各接口全部验证 |
| [XiaomiMiMo/uni-agent][uniagent] `c63e0b01c375ebede95e01fe92bc367df24e5bf3` | 完整README | 长程代理接入及训练入口；README大部分为上游说明，其结果不能充当本篇9B／大模型实验复现 |
| [XiaomiMiMo/verl][verl] `e2b9fc03c6e01247f5d93c44201b068ea320b7de` | README前180行请求；返回有截断，只有已见部分使用 | 可确认fork与训练后端接口背景；没有审计整库、特定MiMo recipe或私有Megatron实现 |

mimoagent当前README区分`cc-agent`（原生loop＋Claude工具目录）与`claude-code`（实际black-box CLI），这一区别非常重要。它还注明CLI setup需要网络，可改用离线payload；局部judge可进入环境评分。**不能由通用README推定主RL采用所有这些配置，也不能把其中顺序与GRS/GAR原文强行合并。**

其开源许可在README标为MIT，uni-agent标为Apache2.0；本轮未做全部依赖／数据／模型许可证审计，不将代码许可覆盖到训练数据和权重。官方模型入口 [Distill-Qwen-9B][model9] 及 [Flash-RL][modelflash] 有搜索索引，完整页面获取失败，未下载weights、验证revision或确认每种领域RL权重均已发布。报告“open-source”与本次“已实际验证可用的资产”分别记录。

### 14.2 相关工作定点补查

| 外部来源 | 实际补查与用途 | 不继承的内容 |
| --- | --- | --- |
| [Muown: Row-Norm Control for Muon Optimization][muown]，`2605.10797` | 取得arXiv v1摘要／版本信息，理解Muon的 row norm与矩阵方向更新分开、谱范数漂移问题 | 其小至中型预训练验证不自动证明V2.6大batch RL收益；不补主文缺失优化器消融 |
| [Multi-Turn On-Policy Distillation with Prefix Replay][reopd]，`2607.04763` | 取得arXiv v3摘要／版本信息及作者／微软入口；理解teacher-prefix和长程历史偏移 | 不据该论文替MOPD2指定KL、step schedule、mix或资源配置 |
| [DFlash: Block Diffusion for Flash Speculative Decoding][dflash]，`2602.06036` | 取得arXiv v2摘要／版本信息，理解block diffusion draft与目标hidden conditioning | 不把外部单独速度倍率写成MiMo RL的吞吐；实际MiMo数值取P §6.4 |
| CodeMidas，P 引`2609.22068` | 已核P中的引用位置，外部一手全文／摘要入口本轮未成功取得 | 不导入搜索／第三方所称任务数、语言数或合成效果，五路线中的描述只依据P |

上表是术语与关系核验，不是又完成四篇独立精读。Muown、ReOPD和DFlash的相关方法仍需从各自原文范围理解；本稿不会让外部一般知识替上传报告“纠错”。

### 14.3 仍未验证的开放复现链

未访问成功的正式动态训练日志；未下载约7k任务及music资产；未核镜像registry、运行成本、完整dataset split；未检查9B全部recipe与report数据版本对应；未运行训练／评测。**这些缺口不影响本篇PDF完整阅读，但限制“可直接复现”的表述。** 主报告可用于设计参照，实际引入新资产必须另做短而具体的接入核验。

<a id="boundaries"></a>
## 15. 证据边界、内部张力与最影响项目决策的缺项

| 问题 | P能确定什么 | 不能自行补全什么 |
| --- | --- | --- |
| 私有环境漏斗 | coding五路线、四次rollout审查、八次稳定性；四域方法 | 全部候选数、失败率、人工成本、语言／repo占比、完整manifest |
| 监督审查正确性 | auditor标潜在FP/FN；多judge一致性不足 | 不能当独立人类真值或完整召回率 |
| GRS与dynamic filtering | GRS可区分all-raw-pass；动态sampler概述all-pass/all-fail过滤 | 各分支实际callback顺序、raw与finalscore过滤时点 |
| GAR的数学与实际实现 | Eq3未cap守恒；实践cap并对全组中心化 | rank→factor、cap值、全失效fallback细节；最终失败优势不能说保持不变 |
| 行为塑形 | Eq5按full-batch有效token统计，零分母有fallback | 不等于IS和prompt分母加权后的梯度守恒；规则误检率未知 |
| 全部优化模块组合 | 分别有reward／advantage／mask定义 | 不存在完整公开的GRS/GAR/长度/行为/筛选执行配置表 |
| 预算与成本 | 主RL成本、每步大batch、1M训练上下文、30step时间线 | 全生命周期费用、完整硬件、9B成本、每域评测预算 |
| 多harness作用 | 跨未训练harness改善；四mini上的训练可运行 | 没有同条件single-vs-multi完整矩阵，不宜宣称多样性的独立因果收益 |
| Figure8与主实验 | 前者Flash/code-only/batch128/token-mean；后者mixed/1568/prompt-mean | 不能合并设置或把所有主成绩归给GAR |
| Table3与Fig3 | 主RL曲线和后MOPD2最终表数值各自有效 | 不择高拼接、不假定为同checkpoint或同统计口径 |
| 小模型RL列 | 四域单独训练＋另一项multi-harness | 不是一个统一9Bcheckpoint无能力回退的证明 |
| 表中CyberGym | 明确修订评测环境 | 不能冒充canonical原环境分数 |
| 大系统与open framework | 主文指定SGLang/Megatron；官方有verl/uni-agent/mimoagent | 开源存在不证明已公开并验收全部私有优化路径 |
| Qwen书目 | 正文明示Qwen3.5-9B，表与模型名称同向 | `Qwen Team, 2025`对应参考条目是Qwen3-Next，这是书目对齐问题；不据它更改输入模型 |

没有把上述未披露项都当作论文缺陷：技术报告本来并非完整复现包。关键是后续决策不能用框架默认值、同家族旧报告或我们自己的实现来静默补齐。

## 16. 对 RepoHarness 的设计层映射（2026-09-23，不是实施定案）

当前同步包记载：已有216题noop/gold对照、164题修订组合证据、40题静态质量复核、8题67次实际求解；但求解使用诊断条件，训练捕获与正式预算没有全部对齐，A线数据表示优化的目标GPU收益仍待验证。这里只复用[同步包](../../../agentic_RL/repo_harness_rh2_workstreams/project1_execution/external_sync_20260923/README.md)，没有重新审完全部运行或修改项目代码。

### 16.1 对B：最直接的借鉴是审计顺序与证据，而不是照抄规模

报告与当前自然候选处置的交集很强：**先定义期望行为，审test覆盖，再用真实候选暴露误接收／误拒绝，最后把重复运行稳定性作为另一维度。** gold通过并不能排除actor开发条件问题、漏测或合法替代解被拒绝。四次求解和八次重跑是作者选择，不是本项目每题必须机械达到的新门槛。

对Conan等已有自然部分修复，优先复用当前patch和公开spec做独立测试／行为裁定，比先生成更多同类题更能定位reward是否有辨识力。对范围争议保留原始分数和版本，避免为了获得mixed reward而放宽grader。此处只提供问题组织方法，不代替逐题裁定。

### 16.2 对A：大payload与逻辑身份，比重新造一个系统更直接

Sample→Sequence→Context→Segment的分层，有助于检查现有logical group与I01分行是否保持优化单位；Payload Porter与延后routing/candidate回收，则可作为E3/E3b重对象传输的参照。**来源机制不等于本项目尚未具备，阅读不要求重写已通过的路径。** 应比较实际pin、表示开销、按需读取与取消／恢复生命周期，再选择有限增量。

冻结router、R3、候选集概率归一化是不同层次；不要用其中一个通过来代替另外两个的训推检查。原文已经报告full-batch均衡而microbatch30×偏载，更说明要看真实消费布局而非单个平均指标。

### 16.3 对训练选择：区分全pass与全fail，再讨论grading

GRS直接针对all-test-pass但质量不同的组；GAR针对mixed groups，重分配成功候选的优势。二者都不是为同题全失败自动创造可靠成功信号的万能办法。当前候选模型未观察到mixed格子的事实，仍需先核预算、接口、任务与评分；不能因为这篇新增GAR就立刻替换主配方。

9B开放SFT起点和3k coding集合可以成为**另一个实验候选**，其77.4B SFT消费表明强初始化成本真实存在。不要据9B名字简单称为低成本纯RL复现，也不应在资产、许可与当前harness条件未核之前决定替换本项目基座。

### 16.4 最小辨识实验候选

| 候选 | P支持的机制 | 我方最小检查 | 不应提前承诺 |
| --- | --- | --- | --- |
| 自然patch审计 | spec/test/rollout三路对照 | 选已出现不同实现质量的几题，审查者先定公开行为，再对照原分数和补测 | 每题都新建judge平台或强制八次重跑 |
| 原始pass内的质量区分 | GRS或GAR | 冻结已有轨迹，测judge一致性、替代解误杀和额外成本，再看是否需训练 | “加LLM评分就提高真实性” |
| advantage参考计算 | Eq3/5与实际cap/fallback | 固定小组做reference，核组身份、分母、全零处理与并行消费 | 仅凭代数守恒保证训练稳定 |
| payload与cache生命周期 | §6数据面、最终统一回传 | 延续E3/E3b，检查真实CC改写、长context下内存与延迟 | 将千万token批次上的设计倍率搬到八卡 |
| 多harness迁移 | Fig10/Table7 | 先固定主harness训练条件，增加一个评测面，区分信息变化和格式变化 | 重建四个mini-harness，或立即弃用生产CC |
| 混合调度 | Eq6/7与失败分析 | 多source真的出现成本／接受率差异时做trace replay，并统计source内偏差 | 仿真收敛等于完整time-to-quality收益 |

这些候选中，前几项可以主要复用现有探针和数据，不需要等待完整模型重训；会改变任务分布、reward或梯度的改动则仍需要学习层证据。**本篇最有价值的贡献不是提供更多组件名称，而是把环境监督、样本消费和实际运行成本连接成可以检查的具体关系。**

## 17. 快速查阅与交付范围

| 要回答的问题 | 本稿 | 原文 |
| --- | --- | --- |
| 如何从PR/源码/真实工作生产任务？ | §5.1 | pp.9–10，Fig4 |
| 四次求解和八次重跑各检验什么？ | §5.2–5.3 | p.11 |
| 一般环境怎样mock、重置与审rubric？ | §5.4 | pp.11–12，Fig5 |
| 是否建议直接训练生产harness？ | §6 | p.14 |
| all-pass与mixed组怎样产生质量信号？ | §7 | pp.16–20，Eq2–5 |
| loss分母、概率和mask是什么？ | §8 | p.8 Eq1、p.21 |
| 真实故障和router负载如何变化？ | §9.4、§10 | pp.23–25，Fig11–12 |
| MOPD2哪些是prefix，哪些是目标？ | §11 | p.25，Fig13 |
| Sample Mixer的实际证据范围？ | §12.4–12.7 | pp.29–31，Eq6–7、Fig15–16 |
| 训推一致性与投机采样优化？ | §12.8–12.10 | pp.32–33 |
| 9B、7k任务、四域RL是否同一模型？ | §13 | pp.33–37，Table4–7 |

本次仅新增本文与[作者自查记录](reviews/mimo_v2_6_self_check_20260923.md)，使用语义文件名避免与多人维护的编号冲突。原始PDF不随笔记上传。没有运行GPU、Docker、模型或grader，也没有独立子agent；作者自查不能冒充独立审查。后续精读其他来源、外部代码审计或具体实验可以直接引用本稿页节，不必从头重复这44页。

## 来源链接

[release]: https://mimo.mi.com/docs/en-US/news/latest/v2-6
[logs]: https://mimo.xiaomi.com/rl/mimo-v26
[model9]: https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Distill-Qwen-9B
[modelflash]: https://huggingface.co/XiaomiMiMo/MiMo-V2.6-Flash-RL
[mimoagent]: https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/README.md
[uniagent]: https://github.com/XiaomiMiMo/uni-agent/blob/c63e0b01c375ebede95e01fe92bc367df24e5bf3/README.md
[verl]: https://github.com/XiaomiMiMo/verl/blob/e2b9fc03c6e01247f5d93c44201b068ea320b7de/README.md
[muown]: https://arxiv.org/abs/2605.10797
[reopd]: https://arxiv.org/abs/2607.04763
[dflash]: https://arxiv.org/abs/2602.06036
