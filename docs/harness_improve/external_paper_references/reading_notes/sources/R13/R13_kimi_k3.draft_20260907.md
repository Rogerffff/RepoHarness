# R13 Kimi K3: Open Frontier Intelligence：后训练与项目一精读

Kimi K3 的主线是 SFT 冷启动、三个领域与三个推理投入档位形成九个 RL 专家，再用多教师在线蒸馏（MOPD）整合为一个可按 effort 控制的模型。报告明确继承 K2.5 的策略优化，并直接给出 MOPD 逐 token 奖励；不能说“算法完全未知”，也不能据此补齐 K3 的跨版本概率、mask 和损失分母实现。其长程方案是同步迭代内的 partial rollout：达到完成比例便暂停生成，未完轨迹下轮优先恢复，同题 K 条全部完成后才送优化。可借鉴的是预算、组完整性、独立评分与状态保留之间的分工；1M 上下文、数千万沙箱和几百卡共置训练不是 RepoHarness 的配置依据。正文同时覆盖通用/视觉/专业工作、偏好式奖励、部署量化及 draft 训练，并保留负结果和复现缺口。

导航：[来源与覆盖](#source) · [训练阶段与算法](#training) · [数据环境与评分](#environments) · [长程系统与模板](#infra) · [评测与负结果](#evaluation) · [旧稿纠错及项目映射](#mapping)

<a id="source"></a>
## 1. 来源、版本与覆盖

- 正式标题 **Kimi K3: Open Frontier Intelligence**，作者 Kimi Team，机构 Moonshot AI / Kimi；技术报告，阅读日期 2026-09-07。
- 主证据：[资料库 PDF](../pdfs/k3_tech_report.pdf)，47 页，无 arXiv 水印，PDF 元数据生成于 2026-07-27。以下 `p.` 指此 PDF 的物理页；封面算 p.1，p.2 起与印刷页一致。
- [arXiv 记录](https://arxiv.org/abs/2607.24653)：v1 提交 2026-07-27，v2 修订 2026-08-07。另保存 [v1 PDF](sources/R13/arxiv_v1.pdf)、[v2 PDF](sources/R13/arxiv_v2.pdf)、两版 TeX 源码。主 PDF 与 arXiv v1 **不是同一个字节版本**：逐页去空白比较，只有 p.1 的水印/版式及 p.41–42 贡献名单不同；p.2–40、43–47 正文和技术附录文本一致。故称“本地报告，与 arXiv v1 技术正文一致”，不直接把其文件身份改成 v1。
- 已逐文件比较两版源码，包括 `4-post-training.tex`、`5-infrastructure.tex`、`6-eval.tex`、`tables/`、`7-case-study.tex`、`appendix.tex` 及附录 F。**后训练、数据环境、全部评测表、案例、技术附录 B–F 均无实质增删。** v2 的相关增量见下表。源码中的注释、`\iffalse` 内容不是已发表正文。
- K3 §4.1.2 明确引用的 K2.5 算法，仅沿这一依赖核对：[Kimi K2.5: Visual Agentic Intelligence v1](https://arxiv.org/abs/2602.02276v1)，[资料库 PDF](../pdfs/R7_kimi_k2_5_2602.02276.pdf) p.8 §4.4.2 Eq.(1)，及 [原 TeX 对应文件](sources/R13/k25_tex/4-pipeline.tex)。这不是 K2.5 全篇精读，也不把其全部配方归入 K3。
- 官方 [Kimi K3 模型卡](https://huggingface.co/moonshotai/Kimi-K3/tree/f831ab66814297da540d832a5235f8e904f29d06)：仅核发布资产与部署入口，查询 revision `f831ab66814297da540d832a5235f8e904f29d06`。AgentENV 只采用 K3 §5.3.2 的依赖说明及官方仓库可访问性，不展开环境系统专题。
- 按原文章节先建立[独立覆盖底稿](sources/R13/coverage_before_old_notes.md)，随后才读[旧相关性笔记](../k3_agentenv_relevance_notes.md)、[旧证据矩阵](../agentic_rl_training_recipe_evidence_matrix.md) §7.1，及[旧 Pro 长文](../pdfs/外部pro探索回答粘贴.md) K3 部分的算法、阶段、预算、系统、继承关系等段落。旧稿不是事实源。

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

<a id="training"></a>
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

但 K2.5 原式/文字存在实现歧义：Clip 写在 ratio 上，文字边界说 log-ratio；平方正则的求和括号不完整；正文称“minimize”而式的符号呈 reward 最大化形态。此处保留[原页](sources/R13/k25_page-08.png)供核对，不擅自修成可运行 loss。旧长文写出的 `m(ρ)ρA−τ(logρ)^2` 只是概念重写；mask 是否也作用于正则、跨 prompt 分母、最终符号不能由它定案。

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

<a id="environments"></a>
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

<a id="infra"></a>
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

<a id="evaluation"></a>
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

负结果需和成功一起保留：top-k蒸馏无明确优势；研究级reasoning与agent纪律仍弱；kernel利用大量题未完成；固定硬件/参数分别优化后cosine优于WSD（预训练§3.2）；SigLIP初始化梯度不稳定（§2.4）；长程容器早期panic/deadlock与高并发KV preemption（§5.3）。均不外推成普遍定律。

## 8. 成本、公开资产与复现程度

§6.4/图13报告的是 **per-task推理美元费用**，非训练GPU-hour或数据生产成本：KCB2.0 K3/Kimi Code相对Fable/Claude Code差4分、38%费用，high约以Opus max三分之一成本接近成绩；BrowseComp91.2%、$2.03/题，约Sol一半；GDPval相对Sol低50Elo、费用低13%，相对Fable约2.6倍便宜；AA-Briefcase第二、约Fable一半。KCB为内部计费，BrowseComp混内部与已发表charts，后两者用AA截至07-23的按token API价格。harness、缓存/价格政策及effort不同，不是等硬件训练成本对照。

图13(b) K3只有红星 **max**；medium/high/max黑线是GPT5.6 Sol，其他medium标记属于Claude系列。**不存在“该图披露K3 medium训练档”的证据。** 图13(a)的K3才是low/high/max。

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

<a id="mapping"></a>
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

映射日期2026-09-07。只读主资料checkout，HEAD **`ce2009f879cf38071d7898a1387e01d4e27741d6`**；其 `reference/miles-rh2-integration` HEAD **`98a0272e4158b2c20e3a34d210c79b50159af0f6`**。以[09-05简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)定位，结合更新的[09-07设计建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)所列未闭合缺口。后者是咨询建议，不替代C包定案。未把本worktree基线当当前miles，未扩为全仓审计。

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
- 已有关联：[miles工程精读](N11_miles_agentic_rollout.md)、[Qwen3-Coder-Next](R3_qwen3_coder_next.md)、[KAT-Coder-V2.5](N01_kat_coder_v2_5.md)。K2/K2.5整体另见来源R7；未完成第二批笔记只按任务编号关联，不造链接。

## 12. 独立检查与修订记录

主任务ID：`01a07827-1e44-7133-85d7-65aee3707e7f`；派工主任务ID：`01a077c4-9f0d-7ef0-a40a-688b42f1b294`。主线程实际配置 GPT-6 Astra / high（派工主线程已核验）；日期2026-09-07。

固定初稿将保存为 `sources/R13/R13_kimi_k3.draft_20260907.md`。独立审查待执行，完成前不标通过；审查记录指定为 `reviews/08_R13_review.md`。交审后正文保持稳定，真实发现收到后逐项修订。
