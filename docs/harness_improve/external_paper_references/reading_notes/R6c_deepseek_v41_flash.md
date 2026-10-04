# R6c DeepSeek-V4.1-Flash：任务生产、异步后训练与长上下文部署精读

这份报告把两条进展放在一起：一条是 CED、CSA2、FP4 KV 和 SWA Bounded Replay 的架构／部署协同；另一条是在既有 SFT→RL→OPD 范式下，扩大任务生产、质量复审、跨 scaffold 训练和最终能力整合。对 RepoHarness 最直接的增量，是“问题—环境—验证系统”的联合生产、真实失败驱动的复审、共置时分且允许跨 checkpoint 续写的异步训练，以及按 `(prompt, effort)` 分组的成本控制。报告确实提供实际训练、曲线和多 harness 评测，但没有完整任务漏斗、训练预算、RL loss 或数据策略的等预算消融。**不能将“作者归因于数据”写成已排除架构、模型合并、额外计算和推理预算的普遍因果定律，也不能将复用 KV 后的续写称为精确 on-policy replay。**

导航：[来源与覆盖](#source) · [架构与通用 infra](#architecture) · [任务与环境](#tasks) · [DSec／异步训练](#async) · [effort 公式](#effort) · [评测与多 agent](#evaluation) · [证据边界](#limits) · [A/B 两线启示](#project)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**正式标题：** *DeepSeek-V4.1-Flash: Pushing the Limits of KV Cache Compression*。团体作者 DeepSeek-AI；完整作者名单在 Appendix A。主来源为用户上传的 **`DeepSeek_V41_Tech_Report.pdf`，51 页，1,809,802 bytes**。文件 SHA-256 为：

```text
ba68e2e40408125ae6d2f63a9a241b61c73910691c74ec1a2a7023c851eac08d
```

阅读日期 **2026-09-10**。PDF 创建／修改 metadata 均为 `2026-09-10 05:49:49 UTC`；正文 §5.1.4 提及 2026 年 9 月生产部署。**metadata 不是独立验证的正式发布日期，本稿不虚构 arXiv 编号、v1 标记或 HF revision。** 用户提供的官方托管入口见 [P]。本轮网页与容器联网未能取得 HF 在线正文／model metadata，因此不能证明上传文件与此刻 `main` 逐字节相同，也不能据此判断官网没有开放模型、代码或数据。上传文件自身完整可读，全文分析不受在线获取失败限制。

原文件 PDF 印刷页码与物理页一致。下文 `P, p.29, §5.1.4, Eq.(8)` 均指这一上传版本；所有事实可按页节回到原文，`P` 链接只是用户给出的官方定位入口，不代替本次文件身份。

**完整阅读与视觉检查。** 已读摘要、§1–6、Appendix B/C；浏览 References 和 Appendix A 以确认来源关系与尾部完整性，不逐篇扩读引用文献、不抄作者名单。全部 51 页由 PyMuPDF 提取原生文本并渲染，12 幅图、5 张表、Algorithm 1 和 Eq.(1)–(17) 均结合原图核对；未使用 OCR。纯架构／预训练部分读全后按与 agent 成本、训推一致性和训练阶段的关系压缩总结，不只看 §5。

**项目映射基线。** 读取 `Rogerffff/RepoHarness@miles-migration` 的 `2e1e857fe3b8b0b84305ef5a5ed03d98d5927951`，沿用 [NOTE_TEMPLATE.md](NOTE_TEMPLATE.md)。新建独立文档分支 `research/deepseek-v41-flash-20260910`，不改共享索引、代码和实验定案。当前简报本身仍标 2026-09-05；本文不把它当作所有后续 A/B 实现的实时审计。项目建议只在 §13 出现，明确是设计候选。

### 1.1 按原文目录的覆盖

| 原文范围 | 实际内容与阅读深度 | 本笔记 |
| --- | --- | --- |
| p.1 摘要、p.2–3 目录、p.4–7 §1 | 全读；全局／持久 KV、agent 成本、能力概括和限制 | §2、§12 |
| p.7–14 §2.1–2.4 | 全读；CED、CSA2、multimodal、mHC、Engram、DSpark、FP4 | §3 |
| p.14–16 §2.5、Algorithm 1 | 全读并核公式；参数类别、Nesterov、Sinkhorn 更新 | §3.5 |
| p.16–20 §3 | 全读；多模态并行、共享状态、Engram、EPD、KV 生命周期与 bounded replay | §3.4、§4 |
| p.20–25 §4 | 全读；数据、优化配置、vision 两阶段、全部 base 评测 | §5 |
| p.25–26 §5.1.1 | 全读；任务三元组、生成／检查模型、两类任务生产 | §6 |
| p.26–28 §5.1.2 | 全读并核 Fig.7/8；scaffold 扩展、worker/sandbox、model merging | §6.4、§7 |
| p.27–29 §5.1.3 | 全读；DSec 调度、密度、评测隔离、agent 导致的崩溃 | §7.1 |
| p.29–30 §5.1.4 | 全读并核 Eq.(8)–(10)、Table 2 | §8 |
| p.30–32 §5.2.1–5.2.4 | 全读；dispatch、长度偏置、stale mask、状态重用、40+ teacher OPD | §7.2–7.6 |
| p.32–35 §5.3.1–5.3.4 | 全读；完整 Table 3/4、effort、scaffold 结果与脚注 | §9–10 |
| p.35–36 §5.3.5 | 全读；Agent Team 训练、DAG 延迟 reward、两项评测 | §11 |
| p.37 §6 | 全读；饱和 benchmark、困难任务和新架构鲁棒性边界 | §12 |
| p.38–47 References、Appendix A | 核验文献身份和附录连续性；不扩写人物信息 | §1、§14 |
| p.47–50 Appendix B | 全读；版本、工具、重复数、Claude 对照及 Fig.11/12 | §9–10 |
| p.49–51 Appendix C | 全读；Eq.(11)–(17)、内点／未封顶假设和最终限制段 | §8.3 |

**原图检索表。** Fig.1 p.1（能力／KV）；Fig.2 p.5（加权 decode FLOPs）；Fig.3 p.7（架构）；Fig.4 p.10（CSA2 三模式）；Fig.5 p.11（层级索引）；Fig.6 p.25（内部 BPB）；Fig.7 p.27、Fig.8 p.28（RL 曲线）；Fig.9 p.35（effort）；Fig.10 p.36（多 agent）；Fig.11 p.49、Fig.12 p.50（effort 分解）。Table 1 p.24、Table 2 p.30、Table 3 p.33、Table 4 p.35、Table 5 p.48；Algorithm 1 p.16。

## 2. 总体问题与证据层次

报告的出发点不是“增加输出速度”一个指标。长程 agent 不断增加输入，cache miss 后的 prefill、运行时 HBM、持久 KV 的 SSD／host memory、跨机器传输都可能成为瓶颈。作者同时改变模型结构、低精度缓存、状态恢复和部署系统，最后通过后训练获得 agent 能力。（P, §1, pp.4–7）

| 报告要证明的事情 | 本篇给出的直接证据 | 不应外推为 |
| --- | --- | --- |
| KV 存储显著缩小 | global KV 890 bytes/token；相对 V4-Flash 约 1/4；持久 KV 约 1/8 | 整模型内存缩小 4×/8×，或相同硬件上训练更快 4×/8× |
| 既有优化范式也能继续提升 agent | 实际数据／环境生产流程、多个 RL run 曲线、最终评测 | 已用单因素消融证明全部收益只来自数据 |
| 多 scaffold 训练与运行可行 | 多 Claude Code 版本、多异质 scaffold 联合训练曲线，8 配置评测 | 未见 scaffold 泛化已被隔离验证，或各种工具面语义等价 |
| effort 可以控制成本与质量 | 条件化 reward、固定 checkpoint 的 effort 扫描 | 任意任务、任意相邻 effort 都单调改善；effort 是硬 token 上限 |
| 大规模 agent 运行能够被工程支持 | DSec、共置时分、跨版本续写、routing replay、OPD 描述 | 已公开可复现生产实现和八卡等价配方 |

报告 §5.1 明确将后训练增益主要归因于数据／环境，而不是新的优化算法。这是作者对自己开发过程的总结。本篇没有公开足以独立排除 base 更新、训练计算量、model merging、context 与推理 effort 的完整配对矩阵。应该保留作者判断，同时保留其因果证据边界。（P, pp.6、25–28）

<a id="architecture"></a>
## 3. 模型架构：哪些变化真正影响 agent 后训练和推理

### 3.1 参数规模与 CED：prefill 和 decode 的激活不是同一个数

模型是原生图文输入、文本输出的 MoE。语言 backbone **40 层，20 encoder + 20 decoder，552B backbone 参数**；另有 **196B Engram 参数**。prefill 激活 **8B/token**，decode 激活 **16B/token**。552B 不是包含 Engram 的完整存储规模，8B/16B 也不是模型全部参数，不能按一个 8B dense 模型估算本项目训练成本。（P, §2.1, pp.7–8；§4.2.1, pp.21–22）

CED 的 encoder 仍是因果模型，不是看到未来的双向编码器。上半部 decoder 的 global KV 直接从最后一层 encoder 输出投影，而不必先完整计算对应 decoder hidden states：

$$
C_l=H_{L/2}W_l^{KV},\qquad Z_l=H_{L/2}W_l^Z,\qquad l>L/2.\tag{P1}
$$

对应原文 Eq.(1)，$C$ 为 KV entries，$Z$ 为压缩权重。SWA 的 KV 仍依赖每层自身 hidden states，因此不能无条件跳过整个 decoder；需要后述 decoder bounded replay。原文给出在 $N\gg n_{win}$ 且采用该恢复路径下的复杂度近似：$O(NL/2+n_{win}L/2)\approx O(NL/2)$。这是架构计算量解释，不是完整服务 wall-clock 加速实测。（P, §2.2, p.9）

### 3.2 CSA2：共享缓存、重选索引和复用索引是三件事

所有模式都计算本层 main Q 和 SWA KV。模式按层静态指定，不是 agent 按任务选择。（P, §2.3、Fig.4, pp.9–11）

| 模式 | main KV / indexer K | indexer Q / Top-K | 保留的自由度 |
| --- | --- | --- | --- |
| Full | 当前层产生，decoder 源于 encoder 最终输出 | 当前层评分并选择 | 新缓存与新选择 |
| Reindex | 复用最近 Full 层的缓存 | 当前层生成 indexer Q，重选 Top-K | 共享缓存但可改变关注位置 |
| Reuse | 复用 main KV / indexer K | 复用最近 Full/Reindex 的 Top-K，不再评分 | 本层 Q、SWA 和 attention 输出仍不同 |

相对 V4，CSA2 移除压缩窗口重叠与压缩器绝对位置 embedding；indexer K 由 main KV 投影，不再独立压缩 hidden states。采用纯 CSA2，而非 CSA–HCA 混合。（P, §2.3, p.10）

**Hierarchical Sparse Indexer 只用于 CED decoder，并在后训练引入、训推采用相同限制。** 首个 Full 层仍扫描全部因果可见位置，自己取 Top-512，并按 block 内最大分数挑候选块；例子为 2,048 块×8 个位置=16,384 候选。后续 Reindex 只在这个池内各自选 Top-512；Reuse 沿用选择。后续 indexer 的搜索量可不随上下文增长，但**首层扫描没有消失，整个系统并非严格常数复杂度**。（P, §2.3.2、Fig.5, pp.11–12）

### 3.3 mHC、Engram、DSpark 与 FP4：不能全部称为无损 serving 优化

**Single-Pass mHC。** 原始 mHC 以 $X_l\in\mathbb R^{n\times d}$ 表示多条 residual stream，Eq.(2) 为 $X_{l+1}=B_lX_l+C_lF_l(A_lX_l)$，$(A_l,B_l,C_l)=\mathcal H(X_l)$。Eq.(3)–(5) 展开 residual 更新、系数生成、input mixing；input mixing 必须等当前系数，阻止单次遍历融合。Eq.(6) 改为使用上一块的 $A_{l-1}$：

$$
X_{l+1}=B_lX_l+C_lF_l(A_{l-1}X_l),\quad (A_l,B_l,C_l)=\mathcal H(X_l).\tag{P6}
$$

这是计算图变化，不只是写一个等价 kernel。Mega-mHC 将部署时的 activation 读写量从原实现 $(4n+4)d$ 降至 Single-Pass 的 $(2n+2)d$；中间的普通两遍融合为 $(3n+2)d$。这个 2× 是特定 residual 计算的内存流量，不是全模型吞吐。预训练仍使用多 kernel 实现；作者报告系数位移的质量影响可忽略，但未给完整独立数表。（P, §2.4.1, pp.12–13）

**Engram。** 沿用条件记忆的 tokenizer compression、多头哈希、上下文 gating 与多分支注入，去掉收益不足以抵消复杂度的短因果卷积。196B 均分两个模块，放在零起始层 1、14；n-gram 阶数 {2,3,4}，每阶 8 hash heads，总 embedding dim 2048，每 head 约 16M entries 且表大小取不同质数。embedding 和 key/value projection 使用 FP8。地址只依赖 token，允许预取。它是参数化 n-gram 记忆，不是 agent 可读写的个人长期记忆。（P, §2.4.2, p.13）

Engram 的存储位置必须分场景：部署可从 host memory 后台 RDMA 预取；训练按行分片并分摊 optimizer states；**RL rollout 时 embedding tables 留在 GPU**，以降低 host memory 碎片/OOM 压力。不能由“可 CPU offload”推出 RL 使用的就是同一放置。（P, §3.1.3, p.18）

**DSpark。** 三层 drafter、128-token SWA，一次 forward 并行给出 5 个位置的 base logits，再由 Markov head 建模 draft 间依赖。confidence head 估计接受和前缀存活概率，结合实际 engine 吞吐曲线按负载选验证长度。backbone 预训练不使用原 MTP；其后先冻结 backbone 单训 DSpark；后训练期间二者都更新，但 **DSpark loss 不向 backbone 回传梯度**。服务、RL、OPD rollout 均可用其加速。本文没有公布接受率、完整校验分布或端到端 speedup；引用 DSpark 原作不等于本轮又完整审计了其精确采样算法。（P, §2.4.3, pp.13–14）

**FP4 main KV。** indexer Q/K 延续 MXFP4 QAT；main KV 在后训练增加 QAT，采用 E2M1 + 每 16 channels 一个 E4M3 scale，省略第二级 global scale。KV 在 RoPE 之后量化，SWA KV 因敏感性保留 FP8。main KV 的目的主要是存储压缩，attention 前反量化，不依赖其格式的原生矩阵乘法支持。原文给出量程 448×6=2688、512-channel norm 上界约 22.6、观察值约 10 的理由。**不能把这些格式、精度与位置互换后仍称“复现 V4.1”。**（P, §2.4.4, p.14）

### 3.4 KV 生命周期和 SWA Bounded Replay：省下的是哪些状态

Fig.1(b) 的 global KV 分别为 V1 389,120、V3.2 48,068、V4-Flash 3,514、V4.1-Flash 890 bytes/token。890 仅为 global KV 的斜率，不包括模型权重、SWA、allocator、workspace 或并发请求。按十进制恰好 1,000,000 token 算，global KV 约 0.89 GB；这是本文算术，不是完整 1M 请求显存测量。（P, Fig.1, p.1）

旧部署把 global KV 与 prompt/output 端点的 SWA KV 分开 LRU 存在 SSD，典型保留超过 72 小时。但 SWA 主要在同个活跃 session 的分钟窗口复用，持久化后约占一半容量。新部署保留 global KV 至少 72 小时，将 SWA 移至每机 **10% host DRAM** 构成的短 TTL 池，分钟级失效复用；decoder SWA 从不作为 prefix cache 持久保存。persistent 约 1/8 来自“global 约 1/4 × 不再持久存 SWA 约 1/2”的工作负载级组合，不是所有请求恒定比例。（P, §3.2.1, p.19）

缺失 SWA 的 fallback 不是全量精确重建。理论上 L 层精确恢复要重放约 $L n_{win}$ tokens；bounded replay 只重放最后 $n_{win}$，在重放起点 $s$ 处截断本地注意力范围：$[\max(s,i-W+1),i]$。（P, §3.2.2, p.20）

| 路径 | 触发／过程 | 是否精确 |
| --- | --- | --- |
| Encoder bounded replay | global 命中、encoder SWA 缺失时，重放缓存前缀末尾 128 tokens，再处理新增 suffix；重放段只重生 SWA，既有 global 不重算、不覆盖 | 近似；新 suffix 的 global/SWA 可依赖 cache-hit 位置 |
| Decoder bounded replay | 每次 prefill 将 prompt 最后 128 tokens 的 encoder outputs 送入 decoder，产生供 decode 使用的 SWA | 近似；不同于完整 decoder forward；后训练模拟该路径做适应 |

**这是原文主动承认的非等价，不应整理成“完全无损 KV 恢复”。** 作者报告在内部测试里响应质量影响很小，并在结论保留未测边界风险；没有给完整 cache-hit 位置、长程检索或任务级质量消融。§3 的同 checkpoint 近似 SWA 恢复，与 §5.2 的跨 checkpoint 复用在途 KV 是两类不同问题，见 §7.5。

Fig.2 另报告 4K→1M 的 256× 长度扩展仅约增加 1/4 decode FLOPs，但以 BF16/FP8/FP4 的 **1/0.5/0.25 权重**计量。这不是未加权 FLOPs，更不是硬件无关的 latency 保证。（P, p.5）

### 3.5 优化器 Eq.(7) 与 Algorithm 1：是参数类别配方，不是本文 RL loss

线性矩阵采用 Muon；Q/K 按 head 处理；RMSNorm 与其他非矩阵参数用 AdamW；大 embedding、Engram 表及 prediction head 用 Nesterov momentum 后的 Sinkhorn balancing，只维护 momentum 而不采用 Adam 的完整状态。Engram projection 和 vision-language projector 的线性矩阵仍用 Muon。（P, §2.5, pp.14–16）

Algorithm 1 先更新 $M_t=\beta M_{t-1}+(1-\beta)G_t$，再形成 $\widehat G_t=\beta M_t+(1-\beta)G_t$；按行 norm 与均值阈值屏蔽近零行；执行奇数次行／列交替 L2 归一化，最终 $\Delta_t=\sqrt n U^{(K)}$，以 $\widetilde\eta_t=\gamma\eta_t$ 更新权重。Eq.(7) 用左右对角 scaling 表达该过程，使未屏蔽部分的行／列 update RMS 近似均衡。最终 $\sqrt n$ 与 $\gamma$ 的职责分别是 RMS 尺度与相对 Adam 学习率尺度，不是两个可交换常数。（P, Algorithm 1, p.16）

作者称 head-wise Muon／Sinkhorn 优于比较对象，但未在本篇展开足够受控结果。不能把 §4 的预训练超参复制成其 RL/OPD 训练超参。mHC 的 20 次 Sinkhorn-Knopp 与 optimizer 的 $K=11$ 也不是同一过程。

## 4. 通用训练与推理基础设施

**视觉训练的通信重叠。** 在对比学习中，文本 feature 梯度只依赖 gathered visual features，反之亦然；因此 visual all-gather 与 text forward 重叠，text all-gather 与 text backward 重叠。原文给出明确的依赖次序，而非笼统称 all-gather 无开销。其“完全隐藏通信”属于该调度和负载条件下的报告。（P, §3.1.1, p.16）

**多模态训练解耦。** vision encoder 在 LLM parameter tree 外复制；每 step 分为 vision forward、LLM forward/backward、vision backward，视觉负载平衡不打扰 LLM 主并行。长序列的图片按 CP rank 平衡分片，每张只加载一次；rollout 增量传图，CPU decode／preprocess 产物存在分布式文件系统供后续 rollout 与训练复用。（P, p.17）

原文 I/O 条件 $N\rho/B_{IO}<NC/B_{GPU}$ 消去 $N$，得 $\rho<(B_{IO}/B_{GPU})C$。这是“每张图只加载一次、可重叠”等假设下的模型；不证明 arbitrary CPU、共享存储或八卡任务也一定 compute-bound。

**共享 attention 状态的分布式所有权。** 不同 PP stage 用 shadow indexer 执行副本，只有一个逻辑 owner 负责优化和 checkpoint；同步参数、聚合梯度。已有 P2P payload 携带中间状态和 Top-K，并按 CP 切分；按 microbatch 跟踪 forward、recompute、backward 的最后消费者再释放。它解决的是架构共享参数／状态跨 stage 的生命周期，不能直接等同于环境 episode 的 owner 或恢复协议。（P, §3.1.2, pp.17–18）

**Engram 训练。** 专门进程组按行切分 lookup table，副本间再切 optimizer states；pipeline 开始前预取本 batch 的 deterministic lookup；梯度先 buffer，backbone backward 后返还 owner，并与视觉计算重叠。Sinkhorn 实现保存行列 scale vectors，避免反复写完整矩阵。（P, §3.1.3, p.18）

**部署。** 采用 Encoder–Prefill–Decode（EPD）解耦以分别扩展视觉编码、prefill 和 decode；融合 FlashMLA、DeepGEMM、TileKernels、DeepSelect 等路径，使 Reuse 层 prefill/decode 各执行 15/11 个 kernel。15/11 是单类层的 kernel 数，不是模型端到端性能指标；本轮未审上述代码库。（P, §3.2, pp.18–19）

## 5. 预训练：它改变了后训练起点，不能从收益归因里消失

### 5.1 数据与视觉两阶段

文本侧强调跨语料信息增益、专家质量维度和参数／数据 scaling ladder，过滤低能力模型输出、低质量机翻等“信息上隐式重复”，并增加新的代码、commits、库与框架。多模态侧主要保留网页原生图文而非大规模合成：重新从 Common Crawl 启动采集，先做低成本去重／过滤，再下载图像、再次图文筛选，最后用 SmolVLM 严格打分；部分被滤文档可回收为图文对。另含 pointing/OCR、长尾知识、image-code 与 computer-use 轨迹。（P, §4.1, pp.20–21）

两个数据通道合并时，重叠项以多模态版本替换文本版，取二者较大的 epoch 配置；最终 **text-only : multimodal token = 7:1**。长文确定性预切片、联合样本分配，best-fit packing 的 padding rate 报告不超过 $10^{-4}$。这些是预训练数据做法，不与 §5 大量合成 agent 任务矛盾，也不能把“过滤低信息机翻”变成所有合成数据无价值。（P, p.21）

DeepSeek-ViT 先做约 **47B image-text pairs** 的 SigLIP 式对比训练，最大 224×224；再接临时 **4B MoE LLM**，在 **236B tokens** 上做自回归训练，使用约 544×544–1344×1344 分辨率范围，最后丢弃该 LLM、保留 encoder。更高的对比预训练分辨率虽改善中间指标，作者发现对最终模型贡献小、成本高，这是明确的负向取舍。（P, §4.2.2, p.23）

### 5.2 关键配置与训练日程

| 类别 | 报告配置 | 定位 |
| --- | --- | --- |
| backbone | hidden 5120，40 层；前两层纯 SWA | §4.2.1, pp.21–22 |
| encoder CSA2 | 18 层分三组，每组 1 Full + 5 Reuse；压缩率 2 | p.22 |
| decoder CSA2 | 20 层分五组；首组 1 Full + 3 Reuse；后四组 1 Reindex + 3 Reuse；压缩率 1 | p.22 |
| attention | 64 query heads，head dim 512，query 压缩 dim 1280；indexer 32 heads、dim 128；Top-K 512；SWA 128 | p.22 |
| MoE | 每层 1 shared + 384 routed experts；每 token 激活 6 routed；expert intermediate 2304；SwiGLU clamp 10 | p.22 |
| mHC／视觉 | mHC expansion 4，Sinkhorn-Knopp 20；ViT 32 层、hidden 1024、16 heads、patch 14；两层 projector hidden 5120 | p.22 |
| AdamW | β1=.9，β2=.95，ε=1e-20，weight_decay=.1 | §4.2.2, p.22 |
| Muon／表更新 | momentum=.95、Muon's weight_decay=.1、update RMS=.18；Sinkhorn K=11、τ=1e-3、ε=1e-20；Engram LR 5× | p.22 |
| 规模与 batch | backbone 多模态预训练 45T tokens；固定 100.6M tokens/batch；作者报告无训练不稳定 | p.22 |
| LR | 前 2,000 steps warmup；2.6e-4 维持至 28T；28–40T cosine 到 2.6e-5；40–45T 维持 | p.22 |
| context | 从头 64K sparse，无 dense warmup；34T 时扩至 1M | p.22 |
| routing 与 masking | 图／文各自 bias update .001；sequence-level balance loss 1e-4；sample-level attention mask | p.22 |
| vision 冻结 | LLM 训练初期冻结 ViT，final norm/projector 可训练；LR decay 开始时解冻 encoder，较小 LR | §2.5, p.15 |

这些资源数字不能与后训练 batch、task 数或 rollout 数互换。报告没有完整 GPU 型号／数量、总 wall time 或 GPU-hours，无法从 45T 或 100.6M/batch 唯一恢复训练账单。

### 5.3 Base 结果：完整 Table 1 与内部 BPB

三个 base 使用作者内部同一评测设置；表注将差距≤0.3 视为同水平。下面保留全部任务行，不重制粗体排名。（P, Table 1, p.24）

| Benchmark | 指标 | Shots | V4-Flash Base | V4-Pro Base | V4.1-Flash Base |
| --- | --- | --- | --- | --- | --- |
| AGIEval | EM | 3–5 | 83.9 | 84.4 | 83.4 |
| MMLU-Pro | EM | 5 | 68.3 | 73.5 | 74.1 |
| C-Eval | EM | 5 | 92.1 | 93.1 | 92.1 |
| MultiLoKo | LLM-Judge | 5 | 42.6 | 50.9 | 45.5 |
| Simple-QA verified | EM | 25 | 30.1 | 55.2 | 42.3 |
| SuperGPQA | EM | 5 | 46.5 | 53.9 | 53.1 |
| BBH | EM | 3 | 86.9 | 87.5 | 86.1 |
| BBEH | EM | 1 | 25.4 | 29.8 | 27.2 |
| DROP | F1 | 1 | 88.6 | 88.7 | 87.9 |
| HellaSwag | EM | 0 | 85.7 | 88.0 | 87.2 |
| BigCodeBench | Pass@1 | 3 | 56.8 | 59.2 | 60.6 |
| HumanEval | Pass@1 | 0 | 69.5 | 76.8 | 79.4 |
| GSM8K | EM | 8 | 90.8 | 92.6 | 93.0 |
| MATH | EM | 4 | 57.4 | 64.5 | 61.1 |
| MGSM | EM | 8 | 85.7 | 84.4 | 80.2 |
| LongBench-V2 | EM | 1 | 44.7 | 51.5 | 45.2 |
| MMMU-Pro | EM | 4 | — | — | 56.5 |
| CVBench | EM | 4 | — | — | 77.9 |
| DocVQA | LLM-Judge | 4 | — | — | 95.6 |
| RefCOCO-avg | Acc@0.5 | 0 | — | — | 86.0 |

并非所有任务都提高：V4.1-Flash-Base 的 MGSM 为 80.2，低于 V4-Flash-Base 85.7；LongBench-V2 45.2 仍低于 V4-Pro-Base 51.5。知识、推理、编码、长上下文的不同变化不能压成“base 全面领先”。模型体量、数据和架构同时变化，也不是单因素架构消融。

Fig.6 则给三类内部 held-out 语料 BPB（越低越好）：

| 内部语料 | V4-Flash-Base | V4-Pro-Base | V4.1-Flash-Base |
| --- | --- | --- | --- |
| Internal Docs | 0.617 | 0.59 | 0.564 |
| Internal Code Repos | 0.1562 | 0.1494 | 0.1443 |
| Academic Materials | 0.4929 | 0.4677 | 0.4305 |

这些是内部文档、内部代码和学术材料的 token likelihood 派生指标，**不是研究任务完成率，也不证明消除了所有数据重叠**。作者 p.6 的“5%–10% improvements”是概述；不同基线和分母会得到不同相对比，不从中外推用户真实任务成功率。（P, §4.3.2、Fig.6, pp.24–25）

<a id="tasks"></a>
## 6. 后训练流程与任务／环境生产

### 6.1 已知阶段关系，以及没有披露的连接

```text
多模态 backbone 预训练完成
    → SFT（本篇未给具体训练数据规模和完整配方）
    → 多类 RL 运行：单 scaffold / 同族多版本 / 异质 scaffold
         ↳ 不同 run / 配置的 checkpoint merging → 重新初始化后继续 RL
    → 最后阶段：全领域、40+ teacher、full-vocabulary OPD

并行相关工作：生成/验收任务的模型能力迭代；DSec 环境与执行服务。
后训练内另加入：main-KV QAT、hierarchical indexer、decoder replay 适应；
DSpark 随 backbone 变化继续训练，但其目标不反传 backbone。
```

这是对 §2、§3、§5 已披露关系的重建，不是报告明确给出的每个 checkpoint 时间表。没有各 domain expert 的完整分叉树、SFT 角色、merging 方法／权重、训练混合比例、蒸馏后额外 RL 阶段或能力保持阈值。（P, pp.12–14、20、25–32）

### 6.2 任务定义与全生命周期质量复审

作者把任务定义为 **`(problem, environment, verification system)`**，质量分为 **difficulty** 与 **correctness**：不能过于简单，同时三者不能存在关键缺陷。报告明确说以这两类信号迭代训练模型的任务构造能力；不是只让固定教师生成题目。**生成模型是谁、是否等于最终 solver、其优化器、reward 公式、独立训练成本均未给出**，不能补成某种 proposer–solver 自博弈算法。（P, §5.1.1, p.25）

每当任务用于新的 RL run，新的求解轨迹都会成为质量重审证据。原文因此支持“复审与当前模型行为有关”，但没有给一个逐 step 在线修改 taskset 的算法、单一通过率阈值或完全自动的难度控制器。

### 6.3 两种生产管线：一般 agent 与 coding agent

**General Agent。** 内部员工和外部合作方自愿回传实际工作交互与反馈。基于接口构造 mocked tools，复现输入格式、输出结构、API schema 和行为约束，覆盖常见 SaaS、企业应用与专业后端。内部失败和负反馈用于重建工具上下文、用户交互模式与失败条件，生成单／多轮可重放环境，再针对薄弱点 RL。它是现实工作驱动的模拟环境，不等于训练时对真实企业系统执行任意操作。（P, p.26）

**Coding Agent。** 来源一为复杂或模型表现差的内部／合作方 coding sessions，并做 trajectory dedup；来源二为满足 star 阈值的 GitHub 仓库，阈值数未给。构建流程如下：（P, §5.1.1, p.26）

| 阶段 | 负责动作与产物 | 原文边界 |
| --- | --- | --- |
| 可执行／可验证检查 | agent 判断项目能否在容器完整构建和运行、能否自动验证 | 没有公开仓库清单、成功率、资源阈值 |
| 选择起点与设计任务 | 选特定 turn 或 commit，设计数个复杂实现方向、F2P 与 P2P evaluation points、construction report，可取网络资源 | 不只是把已有 PR 文本翻成题面；也没有披露每题都对应真实历史修复 |
| 独立环境搭建 | 另一 agent 安装依赖、准备初始工作目录、测试与题面，自测、清掉泄漏解法的痕迹，打包新 image layer | 新层不等于每题从零构建整张镜像；也不证明通用 anti-hack 完成 |
| 多求解器试做 | 多个不同 agent 尝试任务 | 不同 agent 是否必然不同底座／家族未说明，数量和预算未给 |
| 独立质检 | 检查环境、事实、题面—评价点错配、hackability，并读取 solver 轨迹 | 质量检查 agent 与 solver 分角色；具体可见信息和接受阈值未给 |
| 修复与再验证 | repair agent 修缺陷、调整太易或太难的评价点，重新进入验证 | 改 evaluation points 可能改变任务含义，原文未给版本／替代解完整审计 |
| 实际训练与重审 | RL run 产生的新轨迹再次用于审查 | 没有公开逐轮任务 lineage、采样权重或生成成本 |

**重要缺口。** 原文没有 MAI 式的候选数→构建数→gold/no-op 通过数→最终题数漏斗，也未给可信 task 数据集、镜像 digest、train/dev/test 清单。描述 F2P/P2P points 和 self-test，不能自动补写“每题原作者 gold 与 no-op 均独立重跑 N 次”。

“百万并发 sandbox”属于执行容量，而不是一百万唯一任务、仓库或镜像。难度与正确性作为生成奖励，也不意味着终局 solver 奖励包含同样两项。

### 6.4 跨 scaffold 的实际训练，以及 merging 混杂

§5.1.2 和 Fig.7/8 明确报告：单一 DeepSeek Minimal、多个 Claude Code 版本、OpenCode/Pi/DSH Standard/PTC 等异质 scaffold 都参与了 RL。worker container 是 scaffold-agnostic 控制层，将交互规范到公共 trajectory schema；agent sandbox 运行 scaffold 和工具。两者都运行在 DSec，独立于可被抢占的 GPU pool，支持暂停／offload／恢复。（P, pp.26–28）

图的横轴是 **cumulative RL steps**，不是 GPU-hours、唯一题目数或恒定 token 量。曲线断段表示不同 run 的 checkpoint 经过 merging 后重新初始化；图7右下还把最大 context 从 512K 扩到 1M，任务是 **Terminal-Bench 3.0 no-gpu 子集**。其他面板标 512K。图8浅线代表个别版本／scaffold，深线是平均；两条主图对应不同训练系列，不是单模型始终连续的一次 run。

这些是真实多 scaffold 训练证据，但不是固定计算／数据／初始化的“单一 vs 多样化”完整消融。没有未见 scaffold 的明确 split，评测中的若干 scaffold 已经出现在训练描述。**“跨 scaffold 有较强表现”与“训练获得未见接口不变性”必须分开。**

<a id="async"></a>
## 7. DSec 与异步后训练：调度、状态和优化语义

### 7.1 DSec 的扩展对象与故障责任

DSec 的设计从 V3→V4 阶段开始，服务多环境、镜像分发、多隔离后端、资源密度、command 记录和可抢占恢复；V4.1 对其提出百万并发 sandbox 的需求。（P, §5.1.3, pp.27–29）

| 设计 | 披露细节 | 本篇没有证明的事情 |
| --- | --- | --- |
| scale units | compute nodes 分 shard，减少实验间 blast radius | 任意共享服务故障都被隔离 |
| placement | 多个不强同步的 placement replicas 基于近期测量估算资源；最终由每节点硬 admission 拒绝超过本地阈值的放置 | reward、训练样本身份和 checkpoint 发布也只需最终一致 |
| 节点密度 | hardware sub-NUMA；worker VM 绑定 NUMA domain；容器限制在 VM 本地 CPU/内存 | 2,500 容器各自独占足够核心、任意重任务都可同密度 |
| 报告收益 | 相似 workload 下，单物理节点从约 1,000 到超过 2,500 live containers 才出现可测端到端退化 | learner throughput 提升 2.5×，或八卡工作站适用相同数字 |
| latency-sensitive class | 非 LS 用 SCHED_IDLE；core scheduling 避免不同优先级任务共享 SMT siblings | 消除了所有内存／I/O／网络干扰 |
| agent misbehavior | 每 sandbox AppArmor 与细粒度 eBPF 网络策略；agent 弄坏环境算失败 trajectory，并向 RL 返回 repercussion 信号 | 所有环境 crash 都是 infra 故障应 DROP；完整 signal 数值/权重已披露 |

原文提到利用内核／权限问题、package mirror 泄漏和删除关键文件等现象。本文只记录威胁类型和防护责任，不扩写 exploit 步骤。**特别需要保留：agent 自身导致的环境崩溃被视为训练中的失败，而不是自动过滤成“无效样本”。** 其他平台故障的完整重试／评分规则未披露。

### 7.2 训推共置、时分，但样本可以跨 checkpoint

真实时序如下：（P, §5.2.1–5.2.3, pp.30–31）

```text
同一组物理 GPU：rollout phase
   → 达到训练所需样本量
   → 在途生成于 token 边界快速暂停，保留 KV/routing
   → training phase（抢占 rollout 使用同一资源）
   → 更新 checkpoint
   → 恢复未完成样本并继续生成
```

因此它同时具有 **共置／时分执行** 与 **跨版本异步样本**。不能因训练阶段暂停生成就说它严格同步 on-policy；也不能因允许 stale 数据就称 trainer 与 rollout 在两套 GPU 上一直并行。DSec worker／sandbox 与 GPU pool 分离，是另外一层生命周期解耦。

### 7.3 sample-level 补位，不是把任意完成样本拼成一个 GRPO 组

每 task 配 in-flight 上限。报告比较了三个补位粒度：batch-level 在起初多派若干 batch、每次训练后补一个，出现严重指标振荡；prompt-level 等某个 GRPO 组全完成才派下一题，被组内长尾卡住；最终改为 **新完成样本计数达到下一 prompt 的 GRPO group size，就派发该 prompt，不要求这些完成样本来自同组**。（P, §5.2.1, p.30）

这里描述的是**释放的容量怎样触发新任务派发**。没有说把不同题的完成样本混成优势计算组；也没有给 learner 是否只消费完整原组、零方差组补采、过滤后重建组等完整规则。

可用一个示意理解：若下一题要 8 个 rollout，8 个释放槽位可以来自多个旧组；由此触发下一题的 8 个 rollout，与后续把不同题 reward 共同中心化是两回事。8 是示意，本篇没有披露统一训练 group size。Table 4 的评测 N=8 同样不能充当训练 G。

### 7.4 长度偏置与 off-policy 分开治理

| 问题 | 报告的处理 | 未披露与可能代价 |
| --- | --- | --- |
| 早完成短序列挤占前期 batch | per-dataset in-flight 上限；可丢弃 early-returned short samples 平滑启动 | 长短判据、丢弃比例、持续时段、原任务组成；不是任意终局长度惩罚 |
| 数据偏離当前策略 | 联动 dispatch 与训练等待条件限制最大 off-policy ratio | ratio 的准确分母、允许版本差和阈值 |
| 部分 token 太 stale | loss mask 去掉这些 token 的梯度贡献 | staleness 定义、是否同时排除组统计、分母、reward 与 prefix 影响 |

这是有明示实际采用的系统处理，不是完整理论证明。（P, §5.2.2, p.31）

**读者推论：** per-dataset 并发限额是控制分布的手段，不等于最终消费比例已固定。用简单稳态近似，完成速率受并发、平均耗时、失败／丢弃率共同影响；课程、难度和服务长尾会改变它。原文没有给逆概率权重或精确无偏保证。应测实际消费分布，不从配置额度直接推出。

同样，token 不更新只消除自身梯度的一条路径；它仍可能参与其他 token 的上下文或原组 reward 统计。具体是否如此必须由原实现决定；本篇没有披露，不能借 SAO/SkyRL 或 rh2 默认行为替作者补完。

### 7.5 routing 拼接与 KV 重用：保存了执行事实，不等于重算一致

对于跨多个 checkpoint 的样本，训练使用 **concatenated routing-replay**：拼接各 rollout segment 当时产生的 expert routing，而不以新 checkpoint 丢弃重算。token-level interrupt 支持在任意生成边界暂停；KV cache/routing 也按 token 记录，后续直接用新 checkpoint 继续，无须重新 prefill；样本完成后按 sample 回收其状态。这还用于响应集群抢占。（P, §5.2.1、5.2.3, p.31）

需要同时保留两句话：**作者确实报告这种路径能运行；原文没有证明它等价于把完整历史在新 checkpoint 上 fresh recompute。** KV 是旧权重产生的状态，routing replay 只固定专家选择，不会自动把所有 activation 变成新权重对应值。这里与 §3.2.2 的同权重 bounded replay 近似还可能叠加，但作者没有给完整组合消融。

本篇未给实际 rollout logprob 如何捕获、policy ratio 的分布对象、允许的 cache age、重放哪套 attention index、prefix state 与 stale mask 的交互、完整 numerical tolerance。**不要据此宣称该路线错误；也不要用“继续原进度”宣传措辞当作数学等价证明。** 它提供的是一个需要在本项目工作负载下衡量质量—计算折中的系统候选。

### 7.6 全词表 OPD 与异步配置变更

最后阶段覆盖所有领域，采用 **超过 40 个教师**，可来自不同开发阶段，架构也可彼此不同并不同于 student；执行 full-vocabulary OPD，rollout 同样异步。原文声称教师数在架构上基本不受限制且切换成本很低；没有对应 teacher placement、forward、通信或总资源表，不能解读成无限教师没有资源成本。（P, §5.2.4, pp.31–32）

训练期间持续监测能力，可改变 dataset mixture、per-dataset concurrency 和 active teachers。异步下旧配置样本可能仍在途，系统支持一致切换。**这里有很具体的问题披露，但没有给具体实现语义**：何时给样本绑定 teacher／config，旧数据 drain/relabel/discard 哪一种，教师缓存怎样失效，未完成分组怎样处理。

同样，full-vocabulary 不等于已披露 KL 方向、温度、logit 精度、教师更新规则或 tokenizer 映射。架构异构不自动等于 vocabulary 异构。本文只说这些字段未披露，不根据 OPD 术语或 V4 引用补成 reverse-KL 公式。

<a id="effort"></a>
## 8. Reasoning effort：训练条件、reward 与 Appendix C 推导

### 8.1 同一 prompt 的不同 effort 不能直接共用 reward 均值

在 system prompt 中给 `Reasoning Effort: {effort}`，$b\in\{1,\ldots,100\}$。训练只使用有限集合 $\mathcal B$；对每个 $x,b$ 采 $M_b$ 个 response：

$$
z_{b,j}\sim\pi_\theta(\cdot\mid x,b),\quad b\in\mathcal B,\quad j=1,\ldots,M_b.\tag{P8}
$$

**共享 `(x,b)` 才构成一个 subgroup**，组内 reward mean-centering 得到 relative advantage；不同 effort 不直接互相比较。报告没有说 finite training levels 是全部 100 档，也没有列出 $M_b$ 和实际 $\mathcal B$。没有披露是否另做 std normalization、critic、KL、PPO clipping 或训练分母。（P, §5.1.4, p.29）

长度部分加到 trajectory reward：

$$
r^{len}_{b,j}=-\min\left\{C_{max},\; k(b)\frac{\ell_{b,j}}{L_{norm}}\right\},\qquad
k(b)=k_0\exp\left(-\frac{b-b_{min}}{\tau}\right),\quad\tau=\lambda\Delta b.\tag{P9–10}
$$

$\ell$ 按正文是 **reasoning tokens**；$L_{norm}$ 为参考长度，$C_{max}$ 是最大扣分，$\Delta b$ 为训练 effort levels 的平均间隔。正文对 $k_0$ 的措辞较笼统，Appendix C Eq.(12) 明确它是最低 effort 的 penalty coefficient。较高 $b$ 减弱长度压力；$b$ 增加 $\tau$，$k$ 乘 $e^{-1}$。这是**封顶的长度扣分与行为条件化**，不是每次执行都严格限制在给定 token 数。

Fig.9/11 的 output tokens 则是评测输出统计，agent 场景可覆盖多轮。不能不经说明把图中的整个 output token 数等同于 reward 的 reasoning-token 计数，也不能等同于 prefill、工具返回字节或总墙钟。

### 8.2 API preset 与实际训练超参的区别

Table 2 的映射为 **low=50、high=75、max=100**，同一 checkpoint 和 decoding configuration，不换模型权重。论文还评测 25、40、60、80 等值，但不表示生产 API 暴露任意数值。真实 API 现状本轮未单独取得；本文只是记录报告。（P, p.30）

$k_0,L_{norm},C_{max},\lambda,\mathcal B,M_b$ 的具体训练值、终局 task reward 尺度、失败是否同样扣长、多 agent／多轮长度怎样合并，都未披露。没有这些值，不能称为可直接运行的训练配方。

### 8.3 Appendix C Eq.(11)–(17)：局部动机，不是全局保证

Eq.(11)/(12) 重述上面的封顶扣分与指数 schedule。原文随后在**未封顶**区间，对固定问题 $x$，以 $p_x(\ell)$ 表示使用 $\ell$ reasoning tokens 后的解决概率，定义：

$$
\ell_x^*(b)\in\arg\max_{\ell\ge0}\left[p_x(\ell)-k(b)\frac{\ell}{L_{norm}}\right].\tag{P13}
$$

对**内点最优**，Eq.(14) 为 $p_x'(\ell_x^*)=k(b)/L_{norm}$。再假设相关局部区间的边际收益近似指数递减：

$$
p_x'(\ell)\approx a_x e^{-\ell/s_x},\quad a_x,s_x>0.\tag{P15}
$$

代入得：

$$
\ell_x^*(b)\approx C_x-s_x\log k_0+\frac{s_x}{\tau}(b-b_{min}),\quad C_x=s_x\log(a_xL_{norm}),\tag{P16}
$$

以及 $\ell_x^*(b_2)-\ell_x^*(b_1)\approx(s_x/\tau)(b_2-b_1)$，即 Eq.(17)。$k_0$ 主要平移长度压力，$\tau$ 改变 effort 敏感性。（P, Appendix C, pp.49–50）

**必须读到 p.51。** 作者明确限制：这是 reward-level 的局部近似，不保证实际平均长度线性或逐点单调；effort 指令本身可改变策略，采样有随机性，多轮长度与 subgroup normalization 也改变结果。扣分达到上限后边际 penalty=0，要另行讨论。它不是证明“无限提高 effort 总能提高准确率”，也没有证明这个 reward 对真实工作全部合理。

### 8.4 一处原文范围张力

§5.1.4 称机制用于单轮 reasoning 和多轮 agentic 任务；§5.3.2 又将结果描述为单响应 reasoning 中学到的控制向 agentic trajectory 转移。两段没有给拆分训练细节。**不能据此断言“agentic 训练从未使用 effort，只靠零样本迁移”。** 笔记保留两处表述与未知，不自行调和。（P, pp.29、34）

<a id="evaluation"></a>
## 9. 评测设置与完整结果

### 9.1 不是同一个 harness 跑所有 benchmark

reasoning 使用 temperature=1、top-p=1。通常的 code agent 使用 DSH Minimal、1M context、temperature=1、top-p=.95；DeepSWE v1.1 特意改 mini-SWE 对齐官方要求。SEC-Bench Pro 用 Claude Code 的 session compaction；visual agent 用 Claude Code、512K、temperature=1、top-p=.95。ALE 与 AutomationBench 用各自官方 scaffold。（P, §5.3.1, p.32）

版本／集合包括 SEC-Bench Pro **260505**、AutomationBench **v1.0.6 public evaluation set**、ALE-CLI、ZeroBench **main set**。HLE 的 text-only 与完整多模态必须分开；DeepSWE 是 **DataCurve 的 v1.1 benchmark，不是 Agentica 的 DeepSWE 训练模型**。

评测限制互联网、去掉 Git histories，并清理 go/mod、node modules 依赖产物、jar、pycache 等 transient cache。作者仍观察到 exploit-seeking 行为，说明这些不是完整防作弊保证。也不应由此推导本项目可直接删除全部依赖缓存而不重验环境可执行性。（P, pp.32–33）

### 9.2 Table 3 全量转录

以下模型列全部标 Max；`†` 为 HLE text-only，`—` 是原表缺报，不是零分。表格是报告内比较，不代表本轮重新运行的排行榜。（P, Table 3, p.33）

| Benchmark | 指标 | Opus-5 | GPT-5.6 Sol | K3 | GLM-5.3 | V4-Pro | V4-Flash | V4.1-Flash |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPQA Diamond | Pass@1 | 93.4 | 94.1 | 92.9 | 88.1 | 92.4 | 89.9 | 90.9 |
| HLE | Pass@1 | 56.3 | 44.5 | 43.5 | 42.0† | 42.7† | 37.8† | 36.8（39.1†） |
| Codeforces | Rating | — | — | — | — | 3348 | 3289 | 3471 |
| MathArena Apex | Pass@1 | — | — | 65.6 | — | 65.3 | 58.6 | 65.6 |
| Terminal-Bench 2.1 | Pass@1 | 89.1 | 88.8 | 88.3 | 88.2 | 87.9 | 82.7 | 90.6 |
| Terminal-Bench 3.0 | Pass@1 | 43.3 | 34.4 | 17.7 | 28.3 | 11.8 | 7.6 | 30.0 |
| Terminal-Bench 4.0 | Pass@1 | 51.8 | 39.9 | 12.6 | 37.9 | 12.4 | 7.0 | 31.2 |
| DeepSWE v1.1 | Resolved | 74.0 | 73.0 | 67.5 | 66.9 | 62.7 | 54.4 | 74.2 |
| ProgramBench | Almost@1 | 37.0 | 23.0 | 17.5 | 19.0 | 15.5 | — | 20.3 |
| NL2Repo-Bench | Score | 75.3 | 56.8 | 58.0 | 58.0 | 61.5 | 54.2 | 65.4 |
| CyberGym | Pass@1 | — | 84.5 | 80.0 | 84.5 | 83.3 | 76.7 | 88.1 |
| SEC-Bench Pro | Pass@1 | — | 74.3 | — | — | 56.4 | 30.9 | 62.8 |
| ExploitGym | Pass@1 | 22.1 | 33.7 | — | 15.0 | 5.4 | 1.8 | 15.3 |
| HLE w/ tools | Pass@1 | 63.6 | — | 59.8 | 62.5 | 60.0 | 51.5 | 63.9 |
| Automation-Bench | Pass@1 | 50.3 | 45.8 | 46.7 | 48.8 | 43.2 | 37.7 | 54.8 |
| Agents’ Last Exam | Pass@1 | 28.6 | 26.7 | 27.6 | 28.5 | 25.7 | 25.2 | 31.8 |
| Chartography w/ tools | Pass@1 | 84.0 | 79.9 | 68.1 | — | — | — | 78.9 |
| BabyVision w/ tools | Pass@1 | 94.1 | 88.9 | 85.7 | — | — | — | 89.6 |
| ZeroBench-main w/ tools | Pass@5 | 52.0 | 53.0 | 41.0 | — | — | — | 49.0 |

**可直接看到的进步。** 相对 V4-Flash，DeepSWE +19.8 pp，TB2.1 +7.9 pp，TB3 +22.4 pp，TB4 +24.2 pp，Automation +17.1 pp，ALE +6.6 pp；这些是表值算术，不是独立后训练归因。V4.1 与 V4-Flash 的 base、架构、数据和可能的预算都变了。

**同样重要的不足。** TB4 为 31.2，低于表内 Opus-5 51.8 和 GLM-5.3 37.9；ExploitGym 为 15.3，低于 GPT-5.6 Sol 33.7；完整 HLE 36.8 不能与前代 text-only 37.8 直接相减。同表“74.2 vs 74.0”没有配套置信区间，不能直接声称统计显著领先。

作者在结尾提到 Fable-5、GPT-6 Astra 的困难任务差距，但 **Table 3 不包含这两个模型列**。也不能把该表改写成“与今天全部最新模型统一测过”。Table 3 的竞争值来源、全部重复与运行配置并未逐项披露。（P, pp.33、37）

### 9.3 Table 4：同 checkpoint、8 种配置，仍有可见 harness 差距

| Benchmark / 指标 | Claude Code | Codex | OpenCode | Pi | mini-SWE | DSH Minimal | DSH Standard | DSH PTC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepSWE v1.1 / Resolved | 69.8 | 65.6 | 65.5 | 66.2 | 74.2 | 72.6 | 70.5 | 67.6 |
| Terminal-Bench v2.1 / Pass@1 | 88.0 | 84.1 | 85.0 | 86.1 | 90.3 | 90.6 | 85.8 | 85.8 |

共同设置：Linux 容器、temperature=1、top-p=.95、1M context、每 agent `max_steps=500` **模型生成轮次**；DeepSWE 每题 N=8，TB2.1 每题 N=3；TB2.1 无网络。Claude 列是 **v2.1.251**，不是四版本平均值。（P, Table 4 脚注, p.35）

这里的 N 是评测重复采样数量，不是训练 group size，也不是 `Pass@8`/`Pass@3`。原表保持 Resolved／Pass@1；不能把“8 次之一成功”拿来解释其分数。完整聚合、未完成 run 和重试规则仍需资产核查。

按表计算，DeepSWE 八配置范围 **65.5–74.2，差 8.7 pp**；TB2.1 范围 **84.1–90.6，差 6.5 pp**。作者将其称为 transfer well／robust，表格也显示它不是严格的不变性或可忽略差距。没有任务配对误差条，不能进一步判断每项差异显著性。

### 9.4 Appendix B.1 的 scaffold 版本与工具条件

所有场景从 benchmark task description 开始，沿用 runtime／integration 自带 prompts、templates、tools，不增加实验性 system prompt。它不表示所有系统提示都相同。（P, pp.47–48）

| scaffold | 明确版本／模式 | 关键差异 |
| --- | --- | --- |
| Claude Code | 2.1.105、2.1.238、2.1.251、2.1.259；Agent SDK | 原生工具接口；Table 4 只用 2.1.251 |
| Codex | 0.147.0，app-server | adapted tool schemas，不能忽略 adaptation |
| OpenCode | 1.18.15，build agent | shell/file tools + native task delegation |
| Pi | 0.84.2，RPC | shell/file + search/open_page/find_in_page extension |
| mini-SWE | mini_swe_v2 port；commit 04d809ceab9d | 单 bash；每 turn 必须 tool call；submission marker 结束 |
| DSH Minimal | 本文未给单独完整 commit | 单 bash |
| DSH Standard | 0.1.1+custom.202609011522 | full sdk profile，26 initial function tools，含 web search/fetch |
| DSH PTC | 同上 | run_code 执行 TypeScript，24 underlying tools |

这些配置改变工具能力、信息取得、turn-taking 和 delegation，不只是给等价 JSON 换名字。报告声明 checkpoint/decoding/taskset 相同，不等于把全部系统条件控制为同一语义工具面。

### 9.5 Claude 版本结果：Table 5

| Benchmark / 指标 | 2.1.105 | 2.1.238 | 2.1.251 | 2.1.259 | 原文 Average |
| --- | --- | --- | --- | --- | --- |
| DeepSWE v1.1 / Resolved | 68.4 | 68.7 | 69.8 | 68.6 | 68.9 |
| Terminal-Bench v2.1 / Pass@1 | 87.3 | 88.4 | 88.0 | 87.6 | 87.8 |

Average 按未四舍五入的原始分数计算，不能用已展示一位小数强求完全一致。四版本的表值范围分别是 1.4 pp、1.1 pp，明显小于 Table 4 跨家族范围；这只是该模型、任务与配置的描述统计，不是“Claude 升级不影响评测”的普遍结论。（P, p.48）

## 10. RL scaling 与 effort 曲线：趋势、缺口和原文张力

### 10.1 Fig.7/8 不应读成单条严格单调训练曲线

图7四面板是 DSH Minimal 下 code benchmarks；图8左为 Claude 多版本联合训练，右为异质 scaffold 联合训练，均在 DeepSWE v1.1 评测。实线是 Pass@1，虚线是 output tokens，横轴累计 RL steps，断段有 merging/reinitialization。图中可见局部回落和 run 重启时 token 使用变化；不从像素自行生成精确 step→score CSV。（P, pp.27–28）

这支持“作者实际持续扩展训练并获得总体改善”，不支持每一步都有收益，也不能把步数与完整 GPU 成本或固定数据量等同。512K→1M 的右下变化还改变了任务执行预算，不能单独归为训练优化器更好。

### 10.2 Fig.9 与 Appendix B.3：端点改善不等于逐点单调

正文给出 effort 25→100 的端点：八项 reasoning 平均 **67.1→76.3**，DeepSWE **66.0→74.2**，TB2.1 **82.4→90.6**，并概括 output tokens 约增加 2.5×。八项包括 AIME 2026、Apex 2025 Shortlist、GPQA Diamond、HLE、IMO-AnswerBench、LiveCodeBench、MathArena Apex、SimpleQA-Verified；Fig.12 的 HLE 面板明确标 **HLE-Text**，所以不能把该曲线直接当完整多模态 HLE 的 effort 扫描。（P, pp.34–35、48–50）

Appendix B.3 另给 AIME 输出 4.6K→11.4K、MathArena Apex 29.1K→86.1K，以及对应准确率端点等。本文没有每个 benchmark 每个 effort 的原始数表，仅保留原文明确数字，不把曲线近似读数当精确结果。

**必须保留的张力：** §5.3.3 和 B.3 使用 accuracy monotonic／no benchmark ever degrading 等强表述；但 Fig.9 的 DeepSWE/TB、Fig.11 多个 panel，以及 Fig.12 的 GPQA、SimpleQA 等曲线均存在局部回落。B.2 反而明确承认跨 scaffold 的 Pass@1 不单调、有平台和下跌。B.2 对 output tokens“每对条件都单调”的概括也比部分虚线局部走势更强。

因此本文结论为 **effort 与输出长度存在明显总体关系，常见端点质量改善，但不是逐点保证**。不能擅自把图或文字其中之一改成另一方；没有重复结果和误差条，也不对局部变化给显著性解释。（P, §5.3.3 p.34；Fig.9 p.35；B.2–B.3 pp.48–50）

### 10.3 相同 effort 不等于相同实际成本

Fig.11 在同一 checkpoint 比较 Claude、DSH Minimal、mini-SWE：DeepSWE 上 Claude 曲线较平，DSH 从较低点提升且消耗更多 token；TB2.1 接近饱和后 harness 排序与 effort 相互作用。正文关于“60–80 恢复大部分准确率、少于一半 token”的概括不能变成每个 harness 的固定折扣。agent 总成本还包含 prefill/cache、工具时长、重试和外部服务，而不只是 output token。（P, pp.34、48–49）

## 11. Multi-Agent：有实际 RL 描述，但不是严格等算力的因果对照

### 11.1 Agent Team 的状态与权限

lead 可用 `spawn_teammate` 创建命名且持久的 teammate；fresh 不带 lead 历史，fork 带完成 turns 的一次性快照。全部 agent **共享同一 checkout**，更改立即彼此可见，并非独立 worktree。durable mailbox 的消息在运行者下一 step boundary 到达，对 idle 开新 turn，对 inactive 触发恢复。lead 用 list/wait 监视状态；task board 记录 ownership、dependencies 与 **advisory write scopes**，更新有 revision check；只有 lead 能 interrupt teammate 当前 turn，最后由 lead 检查、测试和交付。（P, §5.3.5, pp.35–36）

advisory scope 不是内核强制的文件隔离，revision check 也不自动消除代码编辑冲突。原文描述的是工作协议，没有给所有 race／恢复的实现和测试。

### 11.2 训练 reward 与 derived latency

Agent Team 模式训练 reward 包含 task performance、鼓励 delegation/communication 的 collaboration bonus，以及 derived-latency penalty。延迟将执行事件与依赖画成 DAG，节点成本按固定 prefill/decode rate 的 token 成本加实测 tool time，以关键路径长度计，减轻服务端 batching/queue 波动影响。（P, p.36）

这不是每调用一个 teammate 自动得正收益的完整公式；系数、角色信用、不同代理 token 如何进 loss、并发上限都未披露。derived latency 也不是实际 wall-clock，更不是所有代理计算量之和。它鼓励有用并行，但能否避免无效 delegation reward hacking 需要另外验证。

### 11.3 Fig.10 的真实评测条件

ProgramBench 只保留 reference solution 在 hidden suite 通过率≥95% 的 **172 个 golden tasks**；每配置计划每题最多 3 rollouts，即 **516 个 planned rollouts**。Almost@1 是单条 rollout 的 score≥0.95 的比例，不是 Pass@3。FrontierSWE v2 只用当前 public 任务中不要求 GPU 的子集，报 Mean@5，题目数本篇未给。ProgramBench 墙钟 deadline 1–12h，FrontierSWE 1–20h，在 deadline 时根据当时可用输出计分。（P, p.36）

| 指标 | 报告数值 | 解释边界 |
| --- | --- | --- |
| ProgramBench MA | 1h 13.59%，8h peak 30.04% | 12h 曲线不高于 peak，长时间不保证更好 |
| ProgramBench SA | 1h 12.79%，对照 peak 20.39% | 与 MA peak 差 9.65 pp，是算术，不是等 token 改善 |
| FrontierSWE v2 no-gpu MA | 1h 13.50%，20h 32.90% | 比较的是 wall-clock deadline |
| 同集 SA | 1h 10.50%，20h 28.20% | 20h 差 4.70 pp，未控制总代理算力 |

作者明确称结果 **preliminary**，比较 strongest observed multi-agent configs 与 strongest available single-agent baselines。没有等总 token、GPU cost、完全相同训练历史、同量探索调参的完整对照。不能把它改写成“只打开多 agent 工具就提升 9.65 pp”，也不能将特殊 golden subset 的 20.39 与 Table 3 的 20.3 当同分母结果。

<a id="limits"></a>
## 12. 成本、开放资产、未披露项与最重要的限制

### 12.1 四种成本不能混写

| 成本面 | 已披露 | 缺口 |
| --- | --- | --- |
| 数据／环境生产 | 多角色流程、任务三元组、difficulty/correctness 与重审 | 题目／仓库数量、通过漏斗、generator/solver 成本、人工量、镜像存储 |
| 训练 | 45T 预训练、100.6M tokens/batch；RL steps 曲线；40+ OPD teacher | GPU 型号／数量、wall time、RL/OPD 总 tokens、任务 mixture、失败作业成本 |
| serving | global/persistent KV 比例、局部 kernel 数、prefill 复杂度与加权 decode FLOPs | 完整硬件拓扑、并发、延迟／吞吐对照、真实费用 |
| 评测 | 关键 harness 版本、部分 N、token/step/墙钟条件 | 全任务清单、全部重复／seed／重试、置信区间、环境和 API 成本 |

不能把 1/4 global KV、1/8 persistent KV、2× residual memory traffic 和约 2.5× container density 相乘，生成一个原文没有的“整体加速”。

### 12.2 开放资产：报告指针不等于本轮验证

报告给出 HF 模型入口，并引用 DeepSeek Harness、FlashMLA、DeepGEMM、TileKernels、DeepSelect 等仓库。这些是可继续核查的原始指针，本轮未读取其源码或下载 checkpoint；DSec、任务生产、RL/OPD trainer 的完整代码和环境资产在本篇没有提供可复现清单。

只记录上传报告中的能力与工程披露，不把其他 DeepSeek 发布的许可证或开放状态自动套用到全部资产。HF 在线核验失败属于**访问缺口**，不是“作者没有发布”；RL 任务数／完整 loss 未在已读 51 页出现属于**原文未披露**。二者分开。

### 12.3 主要证据边界

| 容易写过头的结论 | 本篇实际支持的较窄结论 |
| --- | --- |
| 数据工程已被证明普遍比算法更重要 | 作者总结自己在既有配方上的边际收益；无跨资源／模型的普遍定律 |
| 本版所有代际提升都是 post-training | base 也变了，预训练数据、架构、上下文、merging 和预算均参与 |
| 跨 scaffold 分数接近，证明未见接口泛化 | 多种 scaffold 实际训练和测试；未见 split 与隔离消融缺失，且仍有 8.7/6.5 pp 范围 |
| KV 恢复精确，routing replay 已解决全部训推差异 | bounded replay 主动接受近似；跨权重 KV 续写也未给 fresh-recompute 等价性 |
| 100% effort 必然更准 | 端点总体更好，原图局部回落；Appendix C 只是局部 reward 动机 |
| “能做 >95% 真实任务”是实测通过率 | p.6 有该概括性主张，但无对应真实任务总体、样本和计分分母，不作为实验结果 |
| 百万 sandbox 等于百万环境／任务 | 是并发执行容量主张，没有唯一任务数 |
| agent 把 sandbox 弄坏应统一丢弃 | 原文将 agent-caused crash 作为 failed trajectory 与 repercussion signal |
| 40+ teacher 是可随意拼接的 40+ 外部 API | 架构异构和全词表支持有披露，tokenizer/teacher prob API/placement 成本未披露 |
| Table 3 已比过全部最新旗舰 | 表中模型固定；结尾点名的新模型没有对应表列，不添加未报告分数 |
| 多 agent 提升就是等成本方法收益 | 是初步最强配置、按 wall-clock deadline 的系统结果 |

### 12.4 原文自己的限制与负向取舍

除了上述阅读边界，报告明确保留：视觉对比预训练增分辨率成本不值；Engram 短卷积移除；batch-level dispatch 指标振荡、prompt-level dispatch 遇组长尾；持久保存 SWA 与真实访问寿命不匹配；exact reconstruction 太贵；极难 science/security/visual 任务仍落后；sparse selection 与近似 cache reconstruction 在未测边界可能退化；公共 benchmark 饱和不代表困难现实任务已解决。（P, pp.13、19–20、23、30、33–37）

这份报告的工程价值不只在正结果，也在它明确接受了哪些折中。它并没有宣称所有改动数学无损，或完全消除了评测与鲁棒性问题。

<a id="project"></a>
## 13. 对 RepoHarness 的 A/B 两线：哪些值得吸收，哪些暂不复制

**这是 2026-09-10 的来源驱动建议，不是新分支的实现批准。** 用户约定 A 负责训练 infra，B 负责数据／环境／评测；设计基线仍为 miles + SGLang + 外部 coding harness，八卡约 30B-A3B。未在本轮审计 A/B 最新代码，不把下面候选指向某个尚未核验的函数。

### 13.1 给 B：任务三元组与“使用后复审”比单纯增加题数更直接

| 候选借鉴 | 来源依据 | 在现有项目上的最小动作／实验 |
| --- | --- | --- |
| 问题、环境、验证共同审查 | §5.1.1 | 在候选样本中核原始／gold/no-op、合法替代解、题面评价点一致性；这些本项目测试是我方建议，不声称报告逐项做过 |
| 从目标模型失败回到任务质量 | 新 RL run trajectory 用于 re-audit | 对失败样本区分环境错、题意缺口、过窄 tests、工具问题和真正能力失败；修订任务需重验，不能把修题收益当权重收益 |
| 真实仓库不只等于历史 PR 修复 | 选 turn/commit 设计新的 implementation directions | 仅在现成任务供给确实不足时，用少量稳定仓库测试新任务路线；不先复制多 agent 生产平台 |
| 质量与难度分开 | correctness 与 difficulty | 先可执行可评分，再测目标模型机会；强模型通过并不能证明弱模型现在可学 |
| 训练／评测信息边界 | 清理 solution traces、Git histories 和 cache | 记录 grader 私有材料与合法开发测试；任何 cache 删除都重验可运行性，避免把依赖破坏当模型失败 |

报告最有力地支持的是“训练任务持续接受求解行为的检验”，但没有给我们选择 SWE-Gym、R2E-Gym、ScaleSWE 或自产任务的直接排序，也没有让现成环境资格作业失去价值。

### 13.2 给 A：优先读清三个消费边界

**容量补位与统计组分离。** 可以在固定逻辑组的前提下改善任务补位；先离线模拟延迟或做 CPU 测试，检查成员身份、派发配额和 drop 分布。不要因为 completion 计数跨组，就允许 reward baseline 跨题。

**实际行为条件与重算条件分离。** 固定 token／checkpoint 对照 fresh prefill、同版本 cache resume、跨版本状态 resume，并记录 routing、attention 路径和概率定义。报告接受的近似应先成为诊断条件，不直接成为项目默认；也不需要马上建立通用 KV lineage 平台。

**训练配置与在途样本分离。** 若将来真的启用 OPD 或在线改 mixture，给样本明确其生效配置与 teacher 选择条件；先用少量有控制的 config switch 测试发现交界问题。当前没有动态重配置需求时，不为 40+ teachers 提前建设复杂服务。

### 13.3 一个跨 A/B 的低成本研究候选：effort 与任务预算

本篇给出可解释的 conditional reward 思路，但参数缺失且有非单调现象。对当前模型可以先不训练，只比较固定任务、不同合法提示／预算下的结果、output/input tokens、工具时间和失败类型。若“低 effort 无谓停止／高 effort 重复循环”确为可复现瓶颈，再讨论按 `(task, effort)` 分组的训练与强 SFT 基线；不要把长度奖励当作所有长尾问题的通用解。

### 13.4 暂不建议直接实现的东西

CED/CSA2/FP4-main-KV/Engram/SWA replay 均强依赖底座架构与训练，不能在现有 Qwen checkpoint 上用一层 adapter 等价取得。DeepSeek 552B backbone +196B Engram 也不是八卡小模型训练替换项。百万容器 placement、sub-NUMA VM 密度优化、40+ teacher 全域整合和 Agent Team 专项 RL 都不应只因报告采用，就列成项目一必要范围。

**对项目叙事的支持。** 这份报告与“复用成熟优化范式，把任务生产、执行、评分和训练消费做扎实”的研究工程路线相容。但只有本项目自己的有效任务率、错误 reward 减少、有效吞吐和独立学习结果，才能成为简历成果；不能拿 DeepSeek 的规模或分数替代。

## 14. 快速回查与进一步资料边界

| 想查什么 | 本笔记 | 原文位置 |
| --- | --- | --- |
| “无新后训练算法，重点数据”到底说了什么 | §2、§6、§12 | §1 p.6；§5.1 p.25 |
| coding 生产：来源、多个 agent、F2P/P2P、重审 | §6.2–6.3 | pp.25–26 |
| 训练过哪些 scaffold，曲线为什么断开 | §6.4、§10 | Fig.7/8、pp.26–28 |
| 共置时分为何仍产生 stale samples | §7.2–7.5 | pp.30–31 |
| 用完成样本数补位是否改变 GRPO 组 | §7.3 | §5.2.1 p.30 |
| KV 接续和 SWA replay 的近似 | §3.4、§7.5 | p.20、p.31 |
| full-vocab OPD、教师与配置转换 | §7.6 | pp.31–32 |
| effort reward、subgroup 与所有公式 | §8 | p.29、Appendix C pp.49–51 |
| 比分、harness 版本、N=8/3 | §9 | pp.32–35、47–48 |
| “单调提升”与原图是否相符 | §10、§12 | pp.34–35、48–50 |
| Agent Team reward 与特殊评测子集 | §11 | pp.35–36 |

报告引用的 DeepSeek-V4、DSpark、Engram、mHC 与各 benchmark 原作是进一步补读入口；本轮只核参考文献身份，不因继承关系替本篇增加未披露配方。项目中此前的 ScaleSWE 与其他来源也没有被用来填补此报告的数据数量、cost 或 scoring 协议。

## 15. 自查与交付状态

已完成上传版本的正文、附录 B/C、全部数表和原图阅读；没有 ScaleSWE 那一轮的 PDF／附录访问缺口。完整覆盖并不意味着验证了作者所有实验：本轮无 GPU／sandbox 训练复现，无模型权重下载，无代码 audit，也没有独立 reviewer。审查状态是 **作者自查完成、待独立复核**。

正文原文转录、公式推导、算术差值和适用性推论已分开。数表和 derived values 用本地脚本复算；正文链接、锚点、数学分隔符与文件编码已检查。具体自查清单见 [R6c 检查记录](reviews/R6c_self_check_20260910.md)。仅交付本稿与自查，不覆盖其他线程文件或将未实现建议写成系统能力。

[P]: https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/DeepSeek_V41_Tech_Report.pdf
