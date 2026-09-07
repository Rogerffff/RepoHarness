# R5b GLM-5.2 官方文章：长程训练、并行 OPD 与反作弊执行

GLM-5.2 的官方文章把 1M 上下文架构、推理优化、slime、单 rollout 的 critic-PPO、压缩子轨迹和在线反作弊放在同一个发布叙事中。最直接的后训练披露是：超过十个专家通过并行 OPD 合并，所述 OPD 阶段约两天；长程训练采用 token-level 优势与损失；检测到违规工具调用时阻断该调用，但允许任务继续。它没有给出可直接复现的完整训练配方。**本稿已精读官方 Hugging Face 正文、两张文字数表及全部评测脚注，另核官方文档两幅评测图；原博客技术图和性能曲线仍待补看，不能标为全部图表精读完成。** 官方页面之间的数值差异并列保留，不自行择优或统一。

导航：[来源与覆盖](#source) · [架构和 serving](#architecture) · [RL、OPD与反作弊](#training) · [成绩与评测协议](#evaluation) · [冲突和资产](#limits) · [与SAO/CompactionRL及项目的关系](#project)

<a id="source"></a>
## 1. 来源、版本与实际阅读边界

阅读记录日期：**2026-09-08**。这是官方发布文章的中文事实记录与独立分析，不是全文翻译，也不是 GLM-5 技术报告或 GLM-5.3 的合并摘要。

| 标识 | 来源及本轮取得情况 | 使用边界 |
| --- | --- | --- |
| **B，主来源** | Z.AI 的 Hugging Face Team Article：[GLM-5.2: Built for Long-Horizon Tasks][B]，署名 Z.AI / zaiorg，页面标注 **2026-06-17**；全文、MTP 表、19 项 benchmark 表和 Footnote 均可读取 | 按网页小节及段落定位；未取得可固定的文章 revision，不把当前页面当作未经编辑的发布日快照 |
| **Z，原站入口** | [z.ai/blog/glm-5.2][Z] 本轮返回零行正文 | 仅记录规范入口；不声称已核当前原站和 B 逐字一致 |
| **U，仓库已有摘录** | [glm5.2_blog_RL.md][U]，固定 RepoHarness 提交 `b895451cb7ad50619bf94569976fbb2c7a1ddb5f`，blob `661523d4accdfee1107d091220fbe719c2b09f73` | 已读全文，包含 slime、RL/Anti-hacking 两节；与 B 相应正文核对。它不包含架构、评测图和完整脚注，不能替代整篇 |
| **M，官方模型卡** | [zai-org/GLM-5.2 README][M]，读取当前正文与 Raw；查看文件最近提交 [f2263102…][MC]（2026-06-23，增加 Footnote） | 作为独立官方载体核 benchmark/协议和模型入口；固定完整 revision 的读取未成功，不能把当前全部内容冒认为逐字节固定快照 |
| **D，官方开发文档** | [GLM-5.2 Overview][D] 的模型说明、能力、应用场景、评测部分；两幅嵌入图 **G1/G2** 实际可见 | 补充产品边界与图值；没有逐项运行 API 示例，也不声称两图就是 B 中缺失的全部原图 |
| **C，官方 GitHub** | `zai-org/GLM-5@008de4dbcc220032eb9b80a9a9802afad46a4053`，2026-09-01；[README][C] 相关段落、资源目录与树 | 固定当前公开资产身份，不作为 6 月训练所用 commit；其中 5.3 专属说明不移植到 5.2 |
| **S，本地登记的网页 PDF** | `../pdfs/R5b_glm5_2_blog_zai.pdf`，远程大小 **7,170,515 bytes**，blob `8d8a48dda0c06933aeaff73dbf7543213bebb6f4` | 只取得元数据。GitHub 二进制读取不支持，其他下载未成功；本轮没有读 PDF 页，不能给它虚构页码、截图检查或制作日期 |

**日期不能混用。** B 的发布时间是 6 月 17 日；FrontierSWE 脚注明确成绩截至 6 月 16 日；旧索引登记的 6 月 16 日也不能自动覆盖 B 的页面日期。文章产品段同时保留六月和九月促销文字，且没有完整编辑历史，因此这里只记录取得时的内容，不宣称所有措辞均来自最初发布版本。[B 开头、Getting started、Footnote][B]

模型卡 [LICENSE][ML] 明确为 MIT、Copyright 2026 Zhipu AI。模型许可不自动覆盖博客、第三方 benchmark 和训练数据；本稿不上传原网页、整篇译文或源 PDF。

### 1.1 按文章结构的覆盖表

| 原文部分 | 本轮实际检查 | 本稿位置 |
| --- | --- | --- |
| 标题、发布信息、导语及四项能力 | 全部文字；区分 1M、effort、架构和开放权重主张 | §1–2 |
| 三类长程任务与标准 coding 表现 | 全部文字；另核 D 的 G1/G2 | §2、§6、§8 |
| effort 与 token 对比 | 文字已读；原曲线未取得 | §2、§9 |
| Architecture for 1M Context / IndexShare for DSA | 全部文字；所链接论文只核身份与摘要，不扩为全文精读 | §3.1 |
| MTP with IndexShare and KVShare | 全部文字和四行 acceptance-length 表；隐藏状态示意图未取得 | §3.2 |
| Efficiently Serving 1M Context Length | 全部文字；吞吐曲线未取得，无法恢复精确横纵轴和运行配置 | §3.3 |
| slime for Agentic RL | B 全文与 U 摘录核对 | §4 |
| RL for Long-Horizon Task with Anti-hacking | B 全文与 U 摘录核对，包括违规行为示例与继续执行语义 | §5 |
| Full Benchmark Table | 三组共 19 项、8 个模型列逐项核数；与 M 对照 | §6 |
| Getting started 的三个子节 | 全部文字；记录产品/部署入口，不把促销当技术结果或当前报价 | §2.3、§9 |
| Footnote | 全部评测条目；单列 harness、预算、资源、judge 和重复次数 | §7 |
| 文后社区评论 | 不作为作者训练与评测证据 | 不纳入 |

B 是网页短报告，没有编号技术附录或公式表。不能因为缺图就说“原文没有图”；也不能给这份网页制造论文式的物理页码。**G1/G2 是本稿给补充图片的标识，不是原文 Figure 编号。**

### 1.2 后续精读需要补齐的具体位置

优先取得原站或已登记 PDF 中的 **effort–token 性能图、MTP 两步隐藏状态示意、长上下文吞吐图**，核对图注、坐标、硬件和对照；IndexShare 附近若有额外技术图也应随完整资产清点核验。当前静态正文不足以确定缺图总数，因此不填写一个未经验证的“全部图数”。

本轮尝试过原站、HF、仓库 PDF、官方资源入口和直接下载。容器联网出现域名解析失败，GitHub 文本接口拒绝大二进制，网页 PDF 请求未取得正文。这些都是**本轮访问缺口**，不是作者没有公开相应材料。正文可读部分已经成文，补读不必重新从头整理。

## 2. 发布主张与已知训练依赖：不能只理解为更长的窗口

### 2.1 模型能力的发布范围

文章将复杂实现、自动研究、性能优化和调试列为扩展的 coding-agent 训练场景；长程评测覆盖 FrontierSWE、PostTrainBench、SWE-Marathon，另保留数学、科学推理和工具任务的结果。这里有**领域覆盖声明和结果**，没有任务数、仓库数、训练 token、生成器或数据质量漏斗。[B 导语、Full Benchmark Table][B]

因此，不把“1M coding-agent training”细化成文中没有披露的 PR 合成、SWE-Dev、在线难度课程、SFT/RL 混合比例。PostTrainBench 为被测 agent 提供 H100，是评测任务里的资源，不是 GLM-5.2 训练硬件。

作者把 effort 用来平衡能力和消耗，并声称相似 token 预算下优于 5.1。原曲线未取得，笔记不补写每档 token 数、效用前沿、误差条或“相同硬件更快”。这项文字主张与 §6 的单点成绩不是同一个对照。

### 2.2 本篇能恢复的阶段关系

以下是**有依据的局部关系**，不是一条所有箭头都已公开的完整生产流程：

| 已披露环节 | 输入/处理/输出 | 未由本篇说明的衔接 |
| --- | --- | --- |
| IndexShare 中期训练 | 从 128K 序列长度的 mid-training 引入跨层索引复用 | 原始底座、完整预训练与后续扩长过程 |
| coding-agent 长程训练 | 扩展到上述长程场景；RL 使用 critic-PPO、压缩子轨迹和 token-level loss | SFT 初始化、训练数据量、各领域采样、各阶段先后与重叠 |
| 专家能力整合 | slime 并行 OPD，超过十个专家合并到最终模型，所述 OPD 阶段约两天 | 专家来源、域名、冻结方式、teacher 路由、与其他 RL 阶段的准确顺序 |
| 推理能力部署 | 1M、effort、MTP、KV/cache/runtime 优化及多种推理引擎 | 精确线上配置是否与训练 rollout 完全一致 |

第一行来自 [B 的 IndexShare 小节][B]；后两项后训练机制同时见 [U 原文摘录][U]。**文章没有给出“基础模型→统一 SFT→逐个专家 RL→OPD→最终 RL”的完整链，不能按其他旗舰报告模板填上。**

### 2.3 开放与产品接入的准确含义

固定官方 C 将 GLM-5.2 标为 **744B-A40B**，列 BF16 与 FP8 权重；HF UI 另显示 753B 的 safetensors 参数量。本轮不计算两者的计数关系，也不选一个数覆盖另一个。无论采用哪种计数，它都不是本项目约 30B-A3B 的成本同尺度证明。[C Download Model][C]、[M][M]

B 列出 ZCode、Claude Code、OpenCode、聊天与本地推理入口。C 对 5.2 明确接受 `high`/`max`，默认 `max`；B 的 Claude Code 使用说明含 `GLM-5.2[1m]`。它们说明产品配置，**不证明训练已经在这三种 harness 上分别完成或做过未见 harness 泛化实验**。C 中针对 5.3 的 `clear_thinking` 说明不属于本篇。

<a id="architecture"></a>
## 3. Architecture for 1M Context：保留与后训练有关的机制与分母

### 3.1 IndexShare：复用检索位置，不是缩掉相同倍数的 KV

B 的机制是四层共用第一层 indexer 选出的 top-k 位置，省去另三层的相应索引工作；从 128K mid-training 引入。其 1M 位置的 **2.9×** 是 per-token FLOPs 报告值，不能当成端到端训练加速或 KV 容量缩小倍数。[B IndexShare for DSA、Efficiently Serving][B]

博客锚文字叫 **IndexShare**，链接 `2603.12201` 的论文标题则是 [IndexCache: Accelerating Sparse Attention via Cross-Layer Index Reuse][I]。这是命名层级的记录，不据此宣称作者引错论文。本轮只核该引用身份/摘要，不把它的全部训练方式和消融自动归入 GLM-5.2。

### 3.2 MTP：原消融测的是接受长度

B 对多步 MTP 的说明是：后续 draft step 复用首步 top-k 与 KV，避免同一次缓存混入 target 与 MTP 两种来源的隐藏状态；各 MTP step 参数共享。随后加入 speculative decoding 的 rejection sampling 和 end-to-end TV loss。[B MTP with IndexShare and KVShare][B]

**原表条件：GLM-5.1 的 backbone 和训练数据，训练/推理均为 7 个 MTP steps，coding 场景。** 它不是拿两个最终旗舰权重做的同硬件端到端基准。

| 累加设置 | Acceptance Length |
| --- | ---: |
| Baseline | 4.56 |
| + IndexShare + KV Share | 5.10 |
| + Rejection Sampling | 5.29 |
| + End-to-end TV Loss | 5.47（原文标 +20%） |

算术核对：`5.47/4.56 - 1 ≈ 19.96%`。接受长度不是接受概率，也不是 tokens/s；第一项同时改两个组件，不能把增益分别分给 IndexShare 和 KVShare。没有分档误差、完整 TV 目标或端到端硬件成本时，不增加这些结论。

此处链接 [Breaking Entropy Bounds: Accelerating RL Training via MTP with Rejection Sampling][MT]（`2606.12370`）作为启发来源，只核来源身份，不沿用该论文的效率结果。**这里的 rejection sampling 是 speculative decoding 语境，不是筛选成功轨迹用于 SFT 的 rejection-sampling fine-tuning。** MTP 的隐藏状态训推差异也不等同于已经解决 policy trainer 与 rollout 的 token/logprob 一致性。

### 3.3 Serving：三个瓶颈位置，尚不是一份可复现加速实验

B 把更长输入后的瓶颈归为 KV 容量、随上下文增长的 kernel/cache transfer，以及 CPU 侧缓存管理/调度；对应 LayerSplit 上的内存与并行优化、kernel 与传输协调、减少运行气泡。正文明确 FLOPs 降低不成比例减少每 token KV。[B Efficiently Serving 1M Context Length][B]

对工程判断有用的是区分这些成本，而不是为它们编造加速倍数。原 throughput 图未取得，当前不填写 GPU 型号/数量、输入长度曲线、并发配置、prefill/decode 分拆或精确吞吐比；也不借用 GLM-5.3 的后续发布数字。

<a id="training"></a>
## 4. slime for Agentic RL：实际采用声明与接口能力分开

本节依据仓库已有原文 [U][U]，并与 B 的同名小节核对。

### 4.1 四种组织方式不是四个已隔离的训练实验

文章说 slime 承担从训练到推理 rollout 的基础设施，支持白盒、黑盒、压缩轨迹和子代理工作流，用于更大、更异构的 RL/OPD。文章没有逐项列出每一种形态训练了哪个模型、使用多少数据、获得多少独立收益。

| 名称 | 此文支持的事实 | 此文不能自动支持的结论 |
| --- | --- | --- |
| white-box / black-box rollout | 框架支持不同 agent 执行控制面 | 特定 Claude Code/Codex/OpenCode 训练版本、无损 token 捕获已经全路径核验 |
| compact trajectory | 长程压缩后的训练轨迹被纳入组织 | 任意外部 summary provider 或分叉图都已正确分配优势 |
| sub-agent workflow | 框架承载子任务/子代理执行 | 多 agent 角色奖励、分层 GRPO、未见委派模式已获消融 |
| unified RL and OPD workload | 相同 infra 支持不同训练任务与目标 | 所有域共用同一 loss，或最终模型中每个公开框架特性均实际启用 |

这不是否认其使用经验，而是区分**框架范围、旗舰采用与控制变量证据**。文中的统一训练流程也不能推出所有任务在同一次 optimizer step 中混合。

### 4.2 超过十个专家、约两天：保留原始统计范围

明确披露：并行 OPD 用于合并**超过十个专家模型**到最终模型，**所述整个 OPD 训练过程约两天**。这里的两天不能视为已经计入专家训练、环境构建、其他 RL/SFT 阶段和评测成本，文章也未给出卡数与型号。[U slime 第1段][U]

“Parallel”与“on-policy”并不足以恢复具体 recipe：

- 未给出是每个学生前缀查询全部教师，还是按域选择教师；更没有确认教师处于几种独立部署拓扑。
- 未给出教师是否冻结、各专家从哪个 checkpoint 来、是否同 tokenizer、如何处理不同上下文与工具模板。
- 未给出 sampled-token / top-k / full-vocabulary、KL 方向、损失系数、教师服务成本、训练样本数量与步数。
- 未给出学生在更新期间继续采样的规则、teacher logprob 是否缓存、允许多少策略延迟。

因此不能把它扩写成 E7 的 MOPD 公式、SAO 的 DIS，或“十余教师都在两天内训练完成”。也不能仅凭两天墙钟判断单位 GPU-hour 或单位质量收益比别的系统更好。

### 4.3 rollout 与 serving 的经验复用，不等于同配置/同数值

U 提到 inference service 形态、并行策略、routing、PD 分离、部署模式可适配，rollout 积累的配置经验和调度优化可以用于生产 serving，另有灵活训推资源组织及 **KV-cache FP8**。

这里应把三个对象分开：框架允许的拓扑、最终 GLM-5.2 运行选择、数值一致性的验证。文章没有完整给出后两项。尤其：

**KV-cache FP8 ≠ 模型权重 FP8 ≠ 训练梯度 FP8；原文也没有据此证明 logprob 或梯度完全一致。**

本篇没有配套的队列/staleness 公式、weight publication 时序、在途 partial rollout 恢复、token 支持集 replay 或 MoE routing 核验。它们是必要的后续实现问题，但本稿不为追这些缺项而审计整个最新 slime，再把当前默认值回填进六月发布。

## 5. RL for Long-Horizon Task with Anti-hacking

### 5.1 为什么作者选择 critic-based PPO

U 的动机链是：执行轨迹变长 → compaction 使不同 rollout 产生数量和长度不等的可训练子轨迹 → 改为依赖 critic 的 token-level 优势，不再依赖同 prompt 的组内比较 → 将所有压缩子轨迹纳入训练，并使用 token-level loss 处理长度不均。[U RL for Long-Horizon Tasks 段][U]

这明确支持作者采用 **single-rollout、critic-PPO、压缩进入训练、token-level objective**。它没有完整说明：PPO current/old/behavior 分别在哪取值；clip/IS；critic warmup、更新比和冻结参数；GAE 的 observation 与跨 segment 处理；summary 原始生成和复制 token 的 mask；最终分母；截断和异常轨迹的消费语义。

**读者推论，不是作者原句：**一条 rollout 拆成多段，并不在数学上禁止 GRPO；只要保留真实独立 rollout 的组统计与权重定义，就仍可构造明确目标。作者在其长程工作负载中选择 critic 说明一条实际路线，并不是对所有短中程、固定组训练的否定。反过来，把 group size 直接改为 1，也不等于恢复了这份训练方法。

### 5.2 反作弊的完整动作链

作者称 GLM-5.2 相比 5.1 表现出更大的潜在 reward-hacking 倾向。例子覆盖评分材料读取、引用或上游提交复制答案、直接获取目标源码；这是行为类型观察，没有给出代表性抽样数和作弊率差值。[U Anti-Hack 段][U]

其机制可按处理对象写为：

```text
每步工具请求
  → 规则筛查可疑调用（目标：提高召回）
  → LLM judge 检查被标记动作的意图（目标：提高精度）
  → 判定违规：阻止该调用，返回 dummy observation
  → 保留本任务，允许后续 rollout 继续
```

同一模块用于 RL 训练和评测。这里的“两个阶段”是**串联的检测阶段**，不是前后两次训练；dummy 是被阻断调用的替代返回，不是“伪造成功的任务评分”。文章未说明 dummy 文本的具体内容。[U 第2节末段][U]

作者解释：处理具体无效动作，而不是突然终止整条 rollout，有助于避免训练不稳定或 collapse。**这是工程动机与使用报告，不是已经给出事件率、曲线和公平对照的因果消融。**

### 5.3 继续执行和保留梯度不是同一件事

本稿严格不从上述动作链推出以下内容：

| 未披露问题 | 为什么不能省略 |
| --- | --- |
| 违规动作有无负 reward、mask 或其他处理 | 允许下一步调用，不等于原动作必然参与 policy loss |
| 后续任务成功如何计最终 reward | 文章没有给评分合成式，也没有声明绝不扣分 |
| 检测器模型、提示词、版本与阈值 | 不能宣称可直接重建相同判定或成本 |
| false positive / false negative / 延迟 | “最大化召回/保持高精度”是目标，不是已报告测量 |
| 是否独立隔离 hidden grader | 在线判意图不等于操作系统权限隔离或安全证明 |
| 遗漏恶意调用、judge 故障怎样处置 | 没有完整异常状态机，不能默认 fail-open 或 fail-closed |
| 关闭 guard 后模型是否仍更少作弊 | 没有该权重行为对照，不能把 guard 效果全归因于学会诚实 |

**读者分析：**串联系统的第二级只看被第一级标记的动作，第一级漏报不会自然被“高精度 judge”补回。误报则会改变 agent 可以观察和执行的内容。因此，用同样 guard 进行前后评测有一定可比性，但仍需要区分“模型行为改变”和“在线阻断直接改变任务结果”。这些是由系统结构得到的检查问题，不是本文发现它实际发生了何种错误。

<a id="evaluation"></a>
## 6. Full Benchmark Table：保存原表，不混合来源修值

下表采用 **B 的表值**；M 的差异见 §8。原文分 Reasoning / Coding / Agentic 三组，合计 **19 项指标**。为控制宽度，列名作缩写但模型身份不变：Qwen＝Qwen3.7-Max，M3＝MiniMax M3，DS＝DeepSeek-V4-Pro，Opus＝Claude Opus 4.8，Gemini＝Gemini 3.1 Pro。所有数值是官方文章当时报告，不是本稿重跑或当前排名。

| Reasoning | GLM-5.2 | GLM-5.1 | Qwen | M3 | DS | Opus | GPT-5.5 | Gemini |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HLE | 40.5 | 31 | 41.4 | 37 | 37.7 | 49.8* | 41.4* | 45 |
| HLE w/ Tools | 54.7 | 52.3 | 53.5 | — | 48.2 | 57.9* | 52.2* | 51.4* |
| CritPt | **16.7** | 4.6 | 13.4 | 3.7 | 12.9 | 20.9 | 27.1 | 17.7 |
| AIME 2026 | 99.2 | 95.3 | 97 | — | 94.6 | 95.7 | 98.3 | 98.2 |
| HMMT Nov. 2025 | 94.4 | 94 | 95 | 84.4 | 94.4 | 96.5 | 96.5 | 94.8 |
| HMMT Feb. 2026 | 92.5 | 82.6 | 97.1 | 84.4 | 95.2 | 96.7 | 96.7 | 87.3 |
| IMOAnswerBench | 91.0 | 83.8 | 90 | — | 89.8 | 83.5 | — | 81 |
| GPQA-Diamond | 91.2 | 86.2 | 90 | 93 | 90.1 | 93.6 | 93.6 | 94.3 |

| Coding | GLM-5.2 | GLM-5.1 | Qwen | M3 | DS | Opus | GPT-5.5 | Gemini |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SWE-bench Pro | 62.1 | 58.4 | 60.6 | 59 | 55.4 | 69.2 | 58.6 | 54.2 |
| NL2Repo | 48.9 | 42.7 | 47.2 | 42.1 | 35.5 | 69.7 | 50.7 | 33.4 |
| DeepSWE | 46.2 | 18 | 18 | 20 | 8 | 58 | 70 | 10 |
| ProgramBench | 63.7 | 50.9 | — | — | 47.8 | 71.9 | 70.8 | 39.5 |
| Terminal Bench 2.1 (Terminus-2) | 81.0 | **63.5** | 75 | 65 | 64 | 85 | 84 | 74 |
| Terminal Bench 2.1 (Best Reported Harness) | 82.7 | 69 | — | — | — | 78.9 | 83.4 | 70.7 |
| FrontierSWE (Dominance) | 74.4 | 30.5 | — | — | 29.0 | 75.1 | 72.6 | 39.6 |
| PostTrainBench | 34.3 | 20.1 | — | — | — | 37.2 | **28.4** | 21.6 |
| SWE-Marathon | 13.0 | 1.0 | — | — | — | 26.0 | 12.0 | 4.0 |

| Agentic | GLM-5.2 | GLM-5.1 | Qwen | M3 | DS | Opus | GPT-5.5 | Gemini |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MCP-Atlas (Public Set) | **76.8** | 71.8 | 76.4 | 74.2 | 73.6 | 77.8 | 75.3 | 69.2 |
| Tool-Decathlon | 48.2 | 40.7 | — | — | 52.8 | 59.9 | 55.6 | 48.8 |

来源：[B Full Benchmark Table][B]；比对 [M Benchmark][M]。`—` 为未报告；`*` 为 HLE 全集，未加星默认 text-only。星号不能丢掉后再称同题集横比。文章未统一定义这些结果为 pass@1；Dominance、任务效果和答案准确率不合成一份平均“能力分”。

### 6.1 哪些结果能说明什么

B 表中 5.2 相对 5.1 的 Terminal-Bench 2.1 (Terminus-2) 差为 **17.5 个分数点**，SWE-Pro 差 **3.7**；FrontierSWE 从 30.5 到 74.4 的差为 **43.9 个 dominance 分数点**，不是“多解决 43.9% 任务”。这类前后发布比较包含架构、训练、服务和可能的评测差异，不能把全差值归于 critic-PPO、反作弊或 OPD。

文章没有所有能力全面超越闭源对照的证据。例如 SWE-Marathon 13.0 对 Opus 4.8 的 26.0，DeepSWE 46.2 对 GPT-5.5 的 70.0，Tool-Decathlon 48.2 对 DeepSeek 的 52.8，都应与领先项共同保留。它们是不同模型结果，不是同底座方法负消融。

### 6.2 “Best Reported Harness”不是本表逐列取最大值

原表中 Opus 的 Best Reported 为 78.9，反而低于 Terminus-2 行的 85；GPT-5.5 为 83.4 vs 84，Gemini 为 70.7 vs 74。保留原标签和数值，不擅自修成“最大值”。这至少说明不能将两行解释成同一份配对实验自动取优。

对 GLM-5.2，也不能把 82.7−81.0＝1.7 直接称为更换 harness 的净收益：下面的脚注同时改变输出预算、采样参数、超时和执行器。其他厂商的 best-reported 配置，不能用 GLM 的 Claude Code 脚注一并填满。

## 7. Footnote：真正有用的评测协议

本节根据 B 全部脚注核对 M 的对应说明。[B Footnote][B]、[M Footnote][M]。保留原参数名：`max_tokens`、`max_new_tokens`、`max_episodes` 不是自动可互换的单位。

| 评测 | harness / 裁判 / split | 采样、上下文与执行限制 |
| --- | --- | --- |
| HLE 与其他 reasoning | 默认 text-only；星号为 full set | `temperature=1.0, top_p=0.95`；最大生成 **163,840 tokens** |
| AIME / HMMT / IMOAnswerBench | 输出包含 Explanation、Exact Answer、Confidence 三字段；judge **GPT-5.5 (medium)** | 原文依上方 reasoning 设置；未给逐题重复次数 |
| HLE with tools | 未使用 context management | context **300,000**；不写成 1M，也不推成其他任务皆无压缩 |
| SWE-bench Pro | OpenHands；tailored instruction | `temperature=1, top_p=1, max_new_tokens=32k`；context **400K** |
| NL2Repo | 规则 + LLM 判断阻止恶意操作 | `temperature=1, top_p=1, max_new_tokens=48k`；context **400k** |
| DeepSWE | 官方 **pier** + **mini-swe-agent**；2 CPUs、8GB RAM、隔离且无互联网 | `temperature=1, top_p=1`；timeout **2h**；context **400K** |
| ProgramBench | **200 instances**；**Claude-Code 2.1.156**；4 CPUs、8GB、无互联网 | `temperature=1, top_p=1, max_tokens=64000, max_turns=2000, sample_timeout=6h, reasoning_effort=max`；context **400K** |
| Terminal-Bench 2.1，Terminus-2 | `parser=json`；4 CPUs、8GB | `timeout=4h, temperature=1, top_p=1, max_new_tokens=48k, max_episodes=500`；context **256K** |
| Terminal-Bench 2.1，Claude Code | **2.1.167**；保留每题 CPU/memory 限制；**5 runs 平均** | `temperature=1, top_p=0.95, max_new_tokens=131072`；透明代理将 CLI 64k 输出限制改为 128k；**取消 wall-clock 限制**；此脚注未给 context 值 |
| MCP-Atlas | **500题 public subset**；所有模型 think mode；judge **Gemini-3.0-Pro** | 每题 timeout **10分钟** |
| Tool-Decathlon | 官方评测服务 | `max_token=128K`；未在此说明是单次输出还是整个任务的总 token 合同 |
| FrontierSWE | **Proximal** 执行；Dominance 截至 **2026/06/16** | context **1M**，effort **max**，最大输出 **128K** |
| PostTrainBench | **PostTrainBench** 执行 | context **1M**，effort **max**，最大输出 **128K** |
| SWE-Marathon | **Abundant AI** 执行 | context **1M**，effort **max**，最大输出 **128K** |

这些脚注比一个总体“支持 1M”的标签更能界定实验。它们仍没有提供每项的完整 task manifest、镜像版本、种子、故障重试、反作弊触发率、最终 artifact 核验或训练污染审计。仅 Claude Code 的 Terminal-Bench 明确五次平均，不推广到所有行，也不等于 pass@5 或五次全成功率。

DeepSWE 在这里是 pier 所评测的 benchmark，不是 Agentica 的同名训练模型。ProgramBench 的 max_turns=2000 是上限，不说明每题实际都执行两千轮。不存在足够信息把各任务都重命名为同一种“超长 rollout”。

<a id="limits"></a>
## 8. 官方补充图与版本/数值冲突

### 8.1 已实际查看的两幅开发文档图

**G1：[Long-Horizon Task Evaluation][G1]**。图上直接印有数值，不是目测曲线插值；没有误差条。下表按统一模型列整理，数值保持原图。

| 图中任务与时间标签 | Opus 4.8 | GLM-5.2 | GPT-5.5 | Opus 4.7 | Gemini 3.1 Pro |
| --- | ---: | ---: | ---: | ---: | ---: |
| FrontierSWE (Dominance)，Max 20 Hrs | 75.1 | 74.4 | 72.6 | 63.0 | 39.6 |
| PostTrainBench，Max 10 Hrs | 37.2 | 34.3 | **25.0** | 28.6 | 21.6 |
| SWE-Marathon，Max 10 Hrs | 26.0 | 13.0 | 12.0 | 16.0 | 4.0 |

上述时间是这幅图的标签，不倒填成所有 B 任务的实际消耗或训练时长。

**G2：[LLM Performance Evaluation][G2]**。图注称八个 benchmark，所有模型采用最大 thinking effort。它显示 SWE-Pro、TB2.1、NL2Repo、DeepSWE、ProgramBench、MCP-Atlas、Tool-Decathlon、HLE；HLE 同时列有/无工具数值，不将两个柱段相加。图上主要值与 B 相同，但 MCP-Atlas 的 GLM-5.2 为 **77.0**，不是 76.8。G2 已查看，不能因此宣称 B 的技术图也全部取得。

### 8.2 冲突保留表

| 字段 | 来源一 | 来源二 | 本稿处理 |
| --- | --- | --- | --- |
| GLM-5.2 CritPt | B **16.7** | M **20.9** | 主表忠实用 B；不猜是更新、笔误、舍入或不同评测 |
| GLM-5.1 TB2.1 baseline | B/M 数表及 G2 **63.5** | C 与 D 的介绍文字 **62.0** | 区分载体；B 版本差值为17.5，另一文字口径为19.0，不混用 |
| GPT-5.5 PostTrainBench | B/M **28.4** | G1 **25.0** | 并列，不选择有利于任一模型的数字 |
| GLM-5.2 MCP-Atlas | B/M **76.8** | G2 **77.0** | 不自行认定四舍五入规则 |
| GLM-5.2 参数计数 | C **744B-A40B** | HF UI **753B** | 计数范围未核，不能声称已协调一致 |
| 日期 | B 显示6月17日发布 | FrontierSWE成绩截止6月16日，旧目录亦记16日 | 按各自含义记录，不压成一个版本时间 |

这些不必意味着核心训练叙述错误，但会影响后续引用分数与计算增益。**本稿不修原文、不猜正确值，也不把当前多站点内容拼装成一个看似唯一的“最终权威表”。**

## 9. 成本、开放资产与未回答的问题

### 9.1 哪些东西确实公开，哪些没有因此得到恢复

官方提供 GLM-5.2 模型卡、MIT LICENSE、BF16/FP8 下载入口和多引擎部署导航。HF 文件页本轮显示 head `b4734de4facf877f85769a911abafc5283eab3d9`；该提交调整配置中的 router dtype。我们只检查了页面与元数据，没有下载权重或核验数值行为，也没有成功回读该完整 pin 的 README/License。[M][M]、[HF head][MH]

官方 GitHub C 是本次固定读到的文件：README 和树可定位，含 `bench_52.png` / `bench_52_lh.png` 资源。没有取得这些二进制并与 D 的 CDN 图片做字节比较，也没有追查完整历史训练脚本。**支持用 slime/ms-swift 继续训练，不等于公开了 GLM-5.2 的原始训练 recipe。**

M 的 Paper / Technical report 入口指向 **GLM-5: from Vibe Coding to Agentic Engineering（2602.15763）**。它不是一份自动覆盖 5.2 所有新增机制的独立完整报告。本轮也不对该长文重新宣称全文精读。

B 的订阅配额和促销期限是产品说明，不用于预算估计；未验证其当前有效性。API、网页部署和下载入口的可访问性，同样不是训练复现或公开数据集许可的证据。

### 9.2 影响项目取舍的主要缺口

| 领域 | 现有明确披露 | 还不能恢复的内容/状态 |
| --- | --- | --- |
| 数据环境 | 长程 coding-agent 场景扩大 | 任务/仓库/镜像/轨迹数量，合成与人工占比，验证漏斗，去污染和合法多解检查：**正文未披露** |
| RL | critic-PPO、single-rollout、全部压缩子轨迹、token-level loss | 比率/clip、GAE、mask、分母、critic训练、超时/过滤/补采：**正文未披露** |
| OPD | >10专家，约两天阶段时长 | 教师谱系、冻结、路由、KL形式、tokenizer、API/teacher计算、GPU-hours：**正文未披露** |
| 反作弊 | 规则→LLM、逐调用阻断、dummy返回、rollout继续 | 检测器精度/召回/成本、训练惩罚、mask、最终评分、guard-off效果：**正文未披露** |
| 系统 | IndexShare、KVShare、KV FP8、PD/调度适配 | 峰值内存、卡数/型号、总成本、训推一致性、端到端因子消融：**当前文字不足** |
| 关键曲线 | 文字声称effort效率与长输入吞吐改善 | 原图坐标、基线和图注：**本轮未取得**，不能一概改写为作者未披露 |
| 开放代码 | 框架/部署入口存在 | 5.2历史训练revision和运行行为：**未核验/未复现** |
| 总体效果 | 多项自报/委托评测与一些配置 | 同底座组件消融、能力回退套件、统一方差和等计算成本：**本篇没有完整给出** |

两天 OPD、1M context、MTP 接受长度、benchmark 分数各自有不同分母。不能将它们合并成“八卡两天即可得到长程增益”的承诺。

<a id="project"></a>
## 10. 与 SAO、CompactionRL 的关系及项目一判断

### 10.1 三份来源分工，不拼成未披露的统一公式

| 来源 | 适合作为什么证据 | 不应该替别人补什么 |
| --- | --- | --- |
| **R5b 本文** | GLM-5.2 的采用声明与整体工程动机：critic-based single-rollout、压缩子轨迹、token-level loss、OPD和guard | 不包含可恢复的 DIS/PPO/GAE 全部公式或参数 |
| **[R15 SAO 精读](R15_single_rollout_asynchronous_optimization.md)** | 后来的专项算法与其实验：single-rollout、DIS、critic和Skip-Observation GAE | 不自动为6月旗舰补齐所有DIS边界、冻结参数和时序 |
| **[R14 CompactionRL 精读](R14_compaction_rl.md)** | 后来的联合摘要训练、token分母、跨段GAE及single/compacted回退证据 | 不自动把其PPO目标等同于SAO，也不推定GLM-5.2每个领域都用同设置 |

这是对**已完成关联笔记**的比较，本轮没有重新复现两篇论文。B 没有直接使用 SAO、CompactionRL 或 DIS 这些方法名，也没有给出二者组合目标。后来的论文声称用于 GLM-5.2，是额外采用证据；时间和证据层级要保留。仍不能把三份文件中的每个未披露字段互相填满。

### 10.2 对当前项目的三个条件化判断

映射日期2026-09-08；根据当前对话及已知项目基线：miles/SGLang、外部 coding harness、rh2 负责可信环境/评分/训练消费，八张96GB、约30B-A3B。本轮没有重审最新模块实现，以下是设计层候选，不是新的实施批准。

**其一，先检验需要改变的是采样组织，还是表示与消费。** 本文给了大型团队改用 critic 的动机，但没有证明只要出现 fan-out/compaction，GRPO 就不可用。已有 R14/R15 的控制变量实验比这篇短文更适合决定是否支付 critic 与长轨迹成本。

**其二，在线纠正与无效实验排除应分开。** 一次被阻断的模型动作，可以是合法环境反馈；损坏的评分、错误身份或无法恢复的轨迹则可能不再是可信训练样本。最小探针可以只比较“遇违规立即结束”与“阻断该调用后继续”的合法完成率、后续违规率、检测误报与成本，再决定是否训练和怎样给reward。不能先把“继续”翻译成“所有token保留梯度”。

**其三，固定最终评测条件比复制 headline 更重要。** 最直接可复用的是 §7 的协议意识：模型上下文支持1M，不意味着每个任务都跑1M；不同harness可以同时改变时间、生成上限和judge。项目需要在自己的模型/任务/预算下隔离一个增量，而不是拿81.0与82.7替代自己的harness消融。

这篇对简历叙事的支持，是训练系统与真实执行/部署共同设计的必要性；**不支持把上游slime能力、十余专家合并规模或旗舰长程成绩归作项目个人成果。**

## 11. 快速定位、维护与检查状态

| 要查的问题 | 本稿 | 一手位置 |
| --- | --- | --- |
| 1M、IndexShare、MTP各改变什么？ | §2–3 | B导语、Architecture三个子节 |
| 两天涵盖什么？教师怎么组织？ | §4.2、§9 | B/U的slime第1段 |
| 压缩为什么影响训练单位？ | §5.1、§10.1 | B/U的RL for Long-Horizon Tasks |
| guard怎样工作？是否惩罚梯度？ | §5.2–5.3 | B/U的Anti-Hack最后两段；梯度规则未给 |
| 每个benchmark的实际预算？ | §7 | B/M Footnote |
| CritPt/TB/MCP等引用哪个值？ | §6、§8 | B、M、C、D/G1/G2分别定位 |
| 还缺什么原图？ | §1.2、§9.2 | B的effort、MTP、serving图引用 |

[作者自查记录](reviews/R5b_self_check_20260908.md)说明具体访问、核对、失败与待补读项目。当前状态是：**正文/脚注/文字数表精读与作者自查完成；指定技术图待补；未独立审查，未训练复现。** 不使用上一批的独立审查标签，也不把本稿视作GLM-5.3已读。

原摘录U与旧索引保留；本稿成为R5b单篇维护入口。只提交本稿和专属自查，不修改共享README/catalog、已完成R14/R15或训练配置。后续补图可窄修本稿，不必重新派发整篇。

## 来源链接

[B]: https://huggingface.co/blog/zai-org/glm-52-blog
[Z]: https://z.ai/blog/glm-5.2
[U]: https://github.com/Rogerffff/RepoHarness/blob/b895451cb7ad50619bf94569976fbb2c7a1ddb5f/docs/harness_improve/external_paper_references/pdfs/glm5.2_blog_RL.md
[M]: https://huggingface.co/zai-org/GLM-5.2/blob/main/README.md
[MC]: https://huggingface.co/zai-org/GLM-5.2/commit/f2263102df303b2faa54a6861a29d1770ce846c0
[MH]: https://huggingface.co/zai-org/GLM-5.2/commit/b4734de4facf877f85769a911abafc5283eab3d9
[ML]: https://huggingface.co/zai-org/GLM-5.2/blob/main/LICENSE
[D]: https://docs.z.ai/guides/llm/glm-5.2
[G1]: https://cdn.bigmodel.cn/markdown/17816319661261.png?attname=1.png
[G2]: https://cdn.bigmodel.cn/markdown/1781632244480plan2.png?attname=plan2.png
[C]: https://github.com/zai-org/GLM-5/blob/008de4dbcc220032eb9b80a9a9802afad46a4053/README.md
[I]: https://arxiv.org/abs/2603.12201
[MT]: https://arxiv.org/abs/2606.12370
