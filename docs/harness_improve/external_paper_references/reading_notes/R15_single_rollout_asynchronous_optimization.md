# R15 SAO：单轨迹异步优化、DIS 与价值模型训练

SAO 不是把 GRPO 的 group size 改成 1，而是将每题单轨迹采样、直接使用 rollout 概率的双边硬屏蔽、强化 critic 训练和 Skip-Observation token-level GAE 组合起来。原文在 Qwen3-30B-A3B-Thinking-2507 上报告了数学工具推理、SWE 与写作偏好变化三个实验分支：SWE-Bench Verified 为 23.0 → GRPO+DIS 27.0 → SAO 29.8；更完整的稳定性、critic 和动作粒度消融主要来自数学分支。**每批 128 条轨迹相同，不代表 prompt 覆盖、token 或算力相同。** 原文没有披露完整 SWE 数据生产、训练硬件与成本，也未写清 DIS 的 stop-gradient 和最终归一化。本文保留这些实现缺口、表格异常和在线实验的非单调结果，不用项目 faithful DIS 或第三方复现补成作者配方。

导航：[来源与覆盖](#source) · [训练分支与数据](#pipeline) · [DIS 与 critic/GAE](#method) · [配置、评测与消融](#experiments) · [系统、资产与缺口](#assets) · [项目判断与复核](#project)

<a id="source"></a>
## 1. 来源、版本与本次覆盖

**主来源 P**：Zhenyu Hou、Yujiang Li、Jie Tang、Yuxiao Dong，*Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning*，Tsinghua University。前两位等贡献，首页注明相关工作在 Z.AI 实习期间完成。[arXiv 元数据][P-abs] 首次提交为 **2026-07-08 15:02:19 UTC**；2026-09-07 本次查询只列 **v1**。固定 [PDF][P] 与 [HTML][H]；原文以 CC BY 4.0 发布。本稿为中文解读与分析，不是原文译本。

**已读范围**：全部 14 个 PDF 物理页的正文、附录 A.1/A.2/B 及参考文献，核对全部 **5 张表、6 幅编号图、5 个编号公式**。不是只读 coding 或摘要。正文到 p.10，参考文献延续到 p.12；附录在 p.13–14。图表与公式通过 PDF 原页目视核验，重要曲线保留近似量级但不伪造精确日志。首页页脚另印有 `Under review, Feb 2026`，本稿采用 arXiv 提交历史记录版本日期，不据模板页脚判断实际送审／录用状态。

HTML 与 PDF 的表值、公式在本次关键核对处一致。带 v1 的部分截图请求失败后，通过无版本 PDF 入口补看 p.7、13、14；该入口当时同为 14 页 v1 内容。网页 TeX 入口未成功读取，容器直连下载因网络解析失败而未取得本机 PDF/TeX。**这属于本轮未取得，不是作者未公开，也不阻止已取得的 HTML 与 PDF 页完成全文阅读。** 不向仓库上传来源 PDF 或第三方代码缓存。

项目读取基线：`Rogerffff/RepoHarness@miles-migration`，**`f5d373b566244ddc02b53b881e773257511820fd`**。复用 [旧独立摘要](../../../../knowledge/summary_single_rollout_asynchronous_optimization.md) 和 [算法讨论稿](../../../agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md) 的问题骨架，事实逐项回原文核验；两者不充当作者实现证据。按 [Codex 对 O01 的质量反馈](reviews/15_O01_codex_quality_review_20260907.md)，本轮只维护本稿和专属自查文件，不改共享 README/catalog、其他作者笔记或训练实现。

### 1.1 原文章节覆盖表

| 原文位置（PDF 物理页） | 内容与阅读深度 | 本稿位置 |
| --- | --- | --- |
| p.1 摘要、Fig.1 | 全读；核五项指标、各自 baseline 与 GLM-5.2 应用声明 | §2、§6 |
| p.2–3 §1 Introduction、Fig.2 | 全读；区分组等待、单条轨迹完成与 optimizer batch | §2、§8 |
| p.2–3 §2 Preliminaries | 全读；标准 clipped surrogate、critic MSE、GAE 背景 | §4–5 |
| p.3–4 §3.1 DIS、Eq.1–3 | 全读并核原公式；概率身份、硬屏蔽、端点与梯度缺口 | §4 |
| p.4–5 §3.2、Eq.4–5 | 全读；K=2、冻结 attention、跳过 observation、value pretraining | §5 |
| p.5–6 Table 1–2、§4.1–4.2、Fig.3 | 全读；TIR SFT、RL 初始化、全部表值、重复评测与曲线 | §3、§6 |
| p.7–8 §4.3–4.4、Table 3–4、Fig.4 | 全读；critic 消融、running mean、EV、gradient norm、clip ratio | §7.1–7.2 |
| p.8–9 §4.5、Fig.5 | 全读；偏好阶段、judge、候选风格变化、128-reward baseline | §7.4 |
| p.9–10 §5.1–5.2、§6 | 全读；作者的相关工作定位和结论边界 | §2、§8–9 |
| p.10–12 References | 检查尾部与引用身份；不扩展为每篇被引文献全文阅读 | §1、§9 |
| p.13 A.1、Fig.6、Table 5 | 全读；step average/last-token、长度自适应、400-step 比较 | §7.3 |
| p.14 A.2、B | 全读；SPO 与 running mean 的主张；适用性、在线部署与双重用途限制 | §7.5、§9 |

后文 `[P §x, p.y]` 链接对应固定 v1 的物理页。论文事实、作者解释、读者推导和项目候选分别标出；当前实现不替历史实验补参数。

## 2. 作者解决的问题，以及 SAO 不是什么

原文把异步 agentic RL 的困难分成两个方面：一条多轮轨迹可能经历多个 rollout 权重版本；组相对方法又要求等齐同题的多条轨迹，快成员因此额外等待，进入训练时进一步偏离当前策略。SAO 的目标是**改善这种异步场景中的学习稳定性与效果**，而不是只优化生成吞吐。[P §1–3, pp.2–4][P2]

方法的分工是：DIS 处理 token 级策略差异；single-rollout 去掉同题组的等待需求；critic 提供不依赖同题多样本的基线；critic 更新与 GAE 设计使这种基线足够有用。原文 Fig.2 展示完成顺序不同的 rollout 进入训练的示意，不是实测队列时延或吞吐图。[P Fig.2, p.3][P3]

**Single-rollout = 每次采样每个 prompt 一条轨迹，不等于 optimizer batch size=1。** 实验仍有 128 条轨迹的训练 batch。原文的“完成即可用于训练”首先表示不必等同 prompt 的其他成员，不能读成每个结果回来都立刻独自执行一次梯度更新，也不意味着一个 prompt 在全训练期间只出现一次。

DIS 也不专属于 critic：Table 1–2 明确包含 **GRPO+DIS**。反过来，PPO/critic 本身也不自动成为 SAO：vanilla VAPO 在这里是会失败的对照之一。[P §4.1–4.4, pp.6–8][P6]

§5 将 PPO/RLHF、GRPO/RLOO、sequence-level weighting、adaptive clipping 与异步系统分开讨论；引用 AReaL、ROLL Flash、异步 RLHF 和 MobileRL 是说明研究背景，**不能据此推断 SAO 实验使用其中某个后端**。论文自述 SAO 已用于 **GLM-5.2（750B-A40B）** 的 agentic RL；本文保留为作者的生产采用声明，不当成该 750B 模型上的独立消融。[P 摘要、§5, pp.1,9–10][P1]

<a id="pipeline"></a>
## 3. 后训练分支、数据与环境：三个实验不能连成一条流水线

### 3.1 工具数学推理分支

起点是 **Qwen3-30B-A3B-Thinking-2507**。作者先使用 **GPT-OSS-120B 生成的 Tool-Integrated Reasoning（TIR）数据做 3 epochs SFT**，使模型能交错自然语言数学推理与 Python 调用；该 SFT 模型用于初始化 policy 和 value model，然后进入异步 RL。[P §4.1, p.6][P6]

这里 GPT-OSS-120B 是离线轨迹生产者，不是披露过逐 token 概率监督的 OPD 教师。不能将整条 TIR 路线称作从原始基座直接 pure RL；也没有证据把这 3 epochs 自动解释为 critic 的专门 return regression 预训练。

TIR 的原始题源、SFT 轨迹数、保留率、RL 题数、验证器实现、Python 沙箱版本、数据去重与污染检查均未给出。4 个数学 benchmark 是评测对象，不是原文披露的 RL 训练数据清单。

### 3.2 Coding/SWE 分支

作者直接使用 **Qwen3-30B-A3B-Thinking-2507** 进行 coding agent RL，不经过上面的 TIR SFT。§4.1 称“almost all”超参数与 TIR 相同，明确列出的差异是 DIS 阈值。[P §4.1, p.6][P6]

**OpenHands** 被明确写为 SWE-Bench Verified 的 scaffold；相关预算为 **300 interaction turns、128k context**，评测段再次说明 300 turns。这些是可核实的 benchmark/harness 条件。原文没有提供足够独立的训练环境描述，不能进一步认定训练一定使用相同 OpenHands commit、工具表或所有评测配置。

| 数据／环境对象 | 本篇实际披露 | 复用所需而未披露的部分 |
| --- | --- | --- |
| 原始 SWE 来源 | 未列训练任务集名称及数量 | 仓库/PR/issue 清单、时间、授权与切分 |
| 环境构建和任务筛选 | 未给生产漏斗 | 镜像、依赖、gold/no-op/替代解、flakiness |
| 工具与可见性 | 明确 OpenHands 评测入口 | 训练工具 schema、reference/test 隔离、网络规则 |
| Reward | 结果表评价修复准确率 | RL reward 精确函数、尺度、partial credit、hacking/格式惩罚 |
| 失败与终止 | 披露长度/turn 预算 | wall-clock timeout、环境错误、截断评分、补采、丢弃与 bootstrap |
| 最终实验 | SWE-Bench Verified 23.0/27.0/29.8 | 逐题日志、重复运行数、checkpoint 选择、精确训练步数 |

**本篇不能被用作 SWE 环境生产配方，也不能从其他报告继承 R2E-Gym、SWE-Gym、二元测试 reward 或 golden patch 检查。** 这些缺项在 §4 和附录没有补齐。

### 3.3 在线写作模拟分支

这是受控改变 reward 偏好的写作实验，使用 GLM-4.7 作为 judge，见 §7.4。附录 B 将实验总体定位于 Qwen3-30B-A3B backbone，但写作段没有单独写出初始化 checkpoint、是否经过 TIR SFT、数据量或全部超参数。不能把数学设置逐项继承过去。[P §4.5、B, pp.8–9,14][P8]

没有披露将数学、SWE 和写作混训成同一个最终模型，也没有单列 OPD、安全对齐或部署压缩阶段。

<a id="method"></a>
## 4. DIS：直接 rollout ratio、双侧屏蔽，以及不能静默补齐的梯度定义

### 4.1 三个概率身份

§3.1 先描述 decoupled PPO 的三种策略：当前训练策略 $\pi_\theta$、用于比较的旧策略 $\pi_{\theta_{\rm old}}$、生成器上的 $\pi_{\rm rollout}$。原文将 current/old 关联于 staleness correction，将 old/rollout 关联于训推不一致。SAO 去掉单独 old-policy 推理，直接使用真实生成阶段记录的 token logprob。[P §3.1, pp.3–4][P3]

为免与环境 reward 混淆，下文把论文 Eq.2 的 $r_t(\theta)$ 记为 $\rho_t$；**这是符号重命名，不是改算法**：

$$
\rho_t(\theta)=\exp\big(\log\pi_\theta(a_t\mid s_t)-\log\pi_{\rm rollout}(a_t\mid s_t)\big). \tag{P2}
$$

一条轨迹跨多个 rollout 版本时，每个 token 需要它自己的生成概率，而不是把整个轨迹随便绑定到最后一个版本再重算 old logprob。原文解释这样做接受一定 off-policy bias，换取不维护历史 checkpoint 集合的实用性；**没有证明这些 token-level 权重给出全轨迹／状态分布的无偏校正**。

以下是实现推论而非作者额外保证：必须同时保留实际上下文、action token 与对应概率；仅有版本号不能代替概率。反过来，不再调用旧模型也不代表轨迹身份、版本和恢复来源记录都失去用途。原文没有规定 raw-vocabulary 与采样处理后 logprob 的口径、top-p 支持集重放或 MoE routing replay，因此这些不能直接归入“论文 DIS 已覆盖”。

### 4.2 原文 Eq.1–3 的准确形式

原文最大化方向的目标写为：

$$
L(\theta)=\hat{\mathbb E}_t\left[f(\rho_t(\theta);\epsilon_\ell,\epsilon_h)\hat A_t\log\pi_\theta(a_t\mid s_t)\right], \tag{P1}
$$

$$
f(x;\epsilon_\ell,\epsilon_h)=
\begin{cases}
x,&1-\epsilon_\ell<x<1+\epsilon_h,\\
0,&\text{otherwise}.
\end{cases} \tag{P3}
$$

以上重排展示顺序但保留原编号关系。**区间内保留比例权重 $x$，不是仅乘一个 0/1 mask；区间外整个 token 的这项梯度被屏蔽，不是把 $x$ clamp 到边界。** 双侧与优势符号无关，这是其相对普通 PPO sign-dependent clipping 的关键区别。[P Eq.1–3, p.4][P4]

§3.1 的文字写闭区间 $[1-\epsilon_\ell,1+\epsilon_h]$，Eq.3 写严格不等号。因此恰等于端点的 token，**按公式应被屏蔽，按文字无法唯一确认**。实现必须记录选择，不能将一个版本悄悄作为作者全部实现的确定行为。

实际公开参数转成 ratio 区间后是：

| 设置 | 原参数 | 按 Eq.3 换算的严格区间 |
| --- | --- | --- |
| TIR/math RL | $\epsilon_{\rm low}=0.3,\epsilon_{\rm high}=5.0$ | $0.7<\rho<6.0$ |
| coding RL | $\epsilon_{\rm low}=0.8,\epsilon_{\rm high}=3.0$ | $0.2<\rho<4.0$ |

**不能把数学实验的区间写成 `[0.3,5.0]`。** “strict/aggressive”指两侧都屏蔽的机制，不代表数值区间对称或很窄。[P §4.1, p.6][P6]

### 4.3 Stop-gradient 与最终 loss 分母未被原文完整定义

Eq.1 对 $f(\rho)$ 没有 `stop_gradient` 标记；正文也没有明确说 ratio 权重是否 detach，$\hat A$ 的反向边界和负号约定同样未提供代码。**不能直接把惯用的 surrogate 实现当成原文明确披露。**

为什么这不是无关细节？下面为读者代数推导，限定在区间内部、固定行为概率与 advantage 的情形。令 $\ell=\log\pi_\theta$：

- 将 $\rho\hat A$ 当作固定权重时，梯度为 $\rho\hat A\nabla\ell$。
- 若按 $\rho(\theta)\hat A\ell(\theta)$ 字面同时求导，梯度为 $\rho\hat A(1+\ell)\nabla\ell$。

两者一般不同。此推导只说明复现前必须确认计算图，**不宣称作者真的采用第二种方式，也不把缺少记号判成已运行的算法错误**。本项目 faithful DIS 的 detach、数值裁剪和 reduction 约定属于我方定义，不能反过来填入 P1。

另一个缺口是 $\hat{\mathbb E}_t$：原文没有解释它在变长轨迹、并行 microbatch 和被屏蔽 token 下，最终按原始 action token、保留 token、trajectory 还是固定 batch 常数平均。§2 的通用 PPO 预备公式含 $1/|y|$，不能因此认定新 Eq.1 和分布式实现必然继承相同分母。

### 4.4 屏蔽 token，不是排除全部环境作用

Eq.3 限制的是 policy loss 中 sampled token 的贡献。它未说明该 token 对 critic target、后续 action context、advantage 递推及分母是否同时被删除。也没有规定 all-masked trajectory/batch 的补采与停止策略。将 DIS 解读为“整条轨迹过期就丢掉”，会混淆 token ratio 与轨迹生命周期两种控制。

## 5. Single-rollout 的 critic、更新频率和 Skip-Observation GAE

### 5.1 K=2：更快追踪 policy 的价值基线

原文解释 single-rollout 的主要困难是基线质量不足：critic 误差变成高噪声 advantage，随后影响 policy，二者相互作用。其方案是每个 policy 更新配置 **K=2 个 value update**；§4.1 又表述为每 batch 两次 value update，§4.3 用 `critic-train-epoch=1` 描述单次更新消融。[P §3.2、§4.1/4.3, pp.4,6–7][P4]

因此可以确认相对频率与实验开关，不能进一步恢复未披露的 microbatch 梯度累积、每个 critic epoch 的 optimizer step 数、两次 target 是否重新计算、最终 advantage 在何时重算。这里的“faster”是频率更高，不是另一个经证明更快的 critic kernel。

### 5.2 Frozen Attention：冻结的是 critic，不是 policy

作者的 pilot 观察称 critic 的大梯度主要来自 Full Attention，而 MoE 相对稳定；方案是在 RL 中冻结 $V_\phi$ 的 attention 参数，优化 MoE projections。作者提出的解释是，预训练 attention 已具备有用的语义关注能力，冻结能正则化 value learning。[P §3.2, pp.4–5][P4]

原文没有公布完整参数名过滤器，也没有逐项说明 value head、router、embedding、norm 是否更新。不能概括成“只有随机 value head 被训练”，或“policy attention 也冻结”。同样，少训练一部分参数不等于不需要 critic 的前向和相关反向计算；没有公开资源剖析支持 critic 成本近似免费。

### 5.3 Value pretraining 与 10-step warmup 是两项不同信息

§3.2 的末段强调扩大 value pretraining corpus、改善冷启动，并称实验说明其重要性；但正文及 A/B **没有给出该语料的名称、数量、回归目标细节或数据规模消融表**。§4.1 明确给出 TIR SFT 初始化和 value 的 10-step warmup，却未说明 warmup 期间 actor 是否冻结、是否为独立离线预训练。[P pp.5–6][P5]

因此本篇支持“作者重视良好 value 初始化”这一方向，**不支持复现者按原文直接恢复一套完整 critic 预训练流程**。

### 5.4 Skip-Observation GAE：跳过估计链里的观测位置，不从上下文删除观测

原文令轨迹为 $[a_0,o_0,a_1,o_1,\ldots]$，每个 $a_i$ 是模型 action 序列，每个 $o_i$ 是外部反馈。普通相邻 token 递推跨到 observation 起点时，引入作者认为不合适的 value 差。SAO 在当前 action 末 token 与下一 action 首 token 之间直接连接：[P Eq.4–5, p.5][P5]

$$
\hat A(a_{i,N})=\delta+\gamma\lambda\hat A(a_{i+1,0}), \tag{P4}
$$
$$
\delta=u_t+\gamma V(a_{i+1,0})-V(a_{i,N}). \tag{P5}
$$

为避免与 ratio $r_t(\theta)$ 混淆，此处将 Eq.5 的环境即时 reward $r_t$ 另记为 $u_t$。下一 action 的 value 仍建立在已见 observation 的上下文上；**skip 不等于不读工具输出，也不等于消除了环境本身的随机性**。作者“filtering out stochasticity”的解释，直接证据是避免将 observation token 作为递推中间位置，而非环境噪声被理论消除。

若一段 action 末尾与下一段首部之间插入 10 或 100 个 observation token，按 P4–P5，这个桥接本身仍只有一次 $\gamma\lambda$，不是按观测 token 数再做 10 或 100 次衰减。这是公式的直接含义；其他位置的完整实现、终端 bootstrap、因外部上限截断的 value target 未给出。

论文没有提供独立的 “token-level with-skip vs without-skip、其他完全不变”结果表。附录 A.1 测的是更大的 **token-level vs step-level** 设计变化，不能把全部差值归给 skip 这一行代码。

### 5.5 长度自适应与 state 索引边界

§4.1 给出 policy advantage 的长度自适应参数：

$$
\lambda_{\rm policy}=1-\frac{1}{\alpha l},\qquad\alpha=1.5,
\qquad\lambda_{\rm critic}=1.
$$

$l$ 在正文没有进一步定义成含 observation 的 flattened length、仅 action token 数还是分段长度。$\gamma$ 的数值也未列出。不能默认 $\gamma=1$，或将 $\lambda_{\rm critic}=1$ 单独解释成无折扣 Monte Carlo target。

$V(a_{i,N})$ 是原文的 token 位置记法，不表示 value 只依赖该孤立 token 字面。next-token shift、value 取 prefix-before-action 还是其他张量位置，需要实现再核；不能用一张通用 transformer 图替代这个缺项。

<a id="experiments"></a>
## 6. 实验配置与主结果

### 6.1 公开训练配置：相同轨迹数，不同 prompt 覆盖

| 项目 | TIR/math | coding | 原文定位 |
| --- | --- | --- | --- |
| 输入 policy | 2507 thinking 模型经 3-epoch TIR SFT | 直接使用 2507 thinking 模型 | §4.1 p.6 |
| SAO batch / group | 128 / 1 | 称几乎与 TIR 相同 | §4.1 |
| GRPO 对照 | 16 prompts × 8 rollout = 128 | 没有另列独立完整参数表 | §4.1 |
| 最大训练长度 | 128k tokens | 称几乎相同；SWE 另写 128k context | §4.1 |
| policy lr | 1e-6 | 未另列改变 | §4.1 |
| critic lr / 更新频率 | 5e-6 / K=2 | 未另列改变 | §4.1 |
| value warmup | 10 steps | 未另列改变 | §4.1 |
| actor λ / critic λ | 长度自适应，α=1.5 / 1 | 未另列改变 | §4.1 |
| DIS ε_low / ε_high | 0.3 / 5.0 | **0.8 / 3.0** | §4.1 |
| 训练 top-p / temperature | 未单独披露 | 未单独披露 | eval 的值不能自动移用 |
| optimizer、KL、entropy、value loss 具体实现 | 未完整披露 | 未完整披露 | §2 是背景定义而非完整 recipe |

按论文采样设计，同样的 128 条轨迹对应 SAO 每批 **128 个 prompt 抽样位置**，GRPO 为 **16 个**。不据此保证跨 batch 的 128 个题目都唯一，但一次更新覆盖的 prompt 数确实不一样。SAO 还增加 critic 及其额外更新；轨迹长度和生成内容也会变化。**所以这是 matched trajectory-count batch，不是 matched unique prompts / tokens / FLOPs / GPU-hours。** [P §4.1, p.6][P6]

### 6.2 评测协议

数学评测是允许 Python 工具的 TIR setting，原文报告 **Pass@1 accuracy**。所有评测设 **top-p=1.0、temperature=1.0、最大 generation length=128k**；数学最多 **50 turns**，SWE 最多 **300 OpenHands turns**。AIME2025、HMMT、IMOAnswerBench 对 **16 次评测运行取均值**，BeyondAIME 为 **4 次**。[P §4.1, p.6][P6]

这里不是 pass@16 / pass@4，也不是训练种子数。原文未给 SWE 重复次数、误差条、逐题结果、精确 harness commit 与完整任务 manifest。128k 同时出现在 max-length、generation length 和 SWE context 的表述中，不能相加成 256k，或推定每次工具调用都允许重新生成 128k。

### 6.3 Table 1：数学全部表值与原标签

下表忠实保留 PDF Table 1 的行名与数字；没有因数值看起来反常而调换 `w/` 与 `w/o`。[P Table 1, p.5][P5]

| 模型/设置 | AIME2025 | BeyondAIME | HMMT Nov 2025 | IMOAnswerBench |
| --- | ---: | ---: | ---: | ---: |
| Claude-Sonnet-4.5 | 87.0 | 62.0 | 81.7 | 65.8 |
| GPT-5 High | 94.6 | 74.0 | 89.2 | 76.0 |
| GLM-4.7 | 95.7 | — | 93.5 | 82.0 |
| Qwen3-30B-A3B w/ python | 14.6 | 10.5 | 17.3 | 7.8 |
| Qwen3-30B-A3B w/o python | 85.0 | 63.0 | 76.7 | 55.3 |
| SFT (w/ python) | 80.4 | 53.3 | 75.2 | 53.3 |
| SFT (w/o python) | 14.6 | 46.8 | 17.3 | 42.0 |
| GRPO (w/ python) | 84.2 | 54.8 | 76.0 | 55.8 |
| SAO (ours) | **97.3** | **74.8** | **88.3** | **74.0** |
| SAO (w/ DIS only) | 94.2 | 71.5 | 86.7 | 71.3 |
| GRPO (+ DIS) | 93.5 | 70.8 | 84.0 | 70.0 |

**需要保留的解释边界。**

首先，未 SFT 模型的工具开启结果明显更低；SFT 去掉工具后的 AIME/HMMT 又回到 14.6/17.3。原文没有完整解释这些大幅变化，且 PDF 与 HTML 一致。可把它们记录为 protocol-sensitive / 待作者澄清，不能自行纠错，也不能直接宣布一般意义的“加工具伤害推理”或“SFT 毁掉裸模型能力”。

其次，`SAO (w/ DIS only)` 没有一份逐项开关表，不能确定该行究竟关闭了哪些 critic／GAE／pretraining 改动；特别不能因 only 一词便写成没有 critic。Table 3–4 的具体消融更适合解释单项变化。

最后，闭源/其他 GLM 行没有在本篇交代与作者实验完全相同的工具、prompt 和预算来源；SAO 也并未在四列都高于这些模型。因此“consistently outperforms all baselines”应限制于所讨论的自家算法对照，不能扩成全表、所有模型、所有预算。

同一表内对 GRPO+DIS 的算术差是 **+3.8 / +4.0 / +4.3 / +4.0 个百分点**；对 SFT(w/ python) 是 **+16.9 / +21.5 / +13.1 / +20.7 pp**。前者更接近增量算法比较，但仍包含采样组织与 critic 改动，不能称为仅“取消等待”的因果收益。

### 6.4 Table 2：SWE 的直接证据

| Qwen3-30B-A3B 设置 | SWE-Bench Verified accuracy (%) |
| --- | ---: |
| 输入模型 | 23.0 |
| GRPO (w/ DIS) | 27.0 |
| SAO | 29.8 |

SAO 相对输入模型 **+6.8 pp**，相对已经稳定化的 GRPO+DIS **+2.8 pp**。[P Table 2, p.6][P6]

这是本文最直接的 coding 学习结果，但没有 SWE 的独立 critic 消融、staleness 分布、训练成本表或多 harness 迁移表。**不是“超过稳定 GRPO 六个点”**；数学分支的 400/1000-step 曲线也不能直接移到这张表上。

Fig.1 用同一个 `GRPO` 图例画五项指标，但数学四柱对应 vanilla GRPO 的 84.2/54.8/76.0/55.8，SWE 柱的 27.0 对应 Table 2 的 **GRPO+DIS**。不能把整张 overview 当成跨领域同一对照开关。[P Fig.1, p.1][P1]

## 7. 消融、训练动态和在线模拟：重要负结果也进入正文

### 7.1 Table 3–4：频率与冻结的实际效果

Table 3 明确列出训练策略与 critic frequency；Table 4 重列其中结果并增加 VAPO/running mean，两个表不能算两套独立重复实验。[P Table 3–4, p.8][P8]

| 方法 | critic 参数/频率 | AIME2025 | BeyondAIME |
| --- | --- | ---: | ---: |
| SAO | Frozen Attention / 2 | 97.3 | 74.8 |
| Single-step-update | Frozen Attention / 1 | 95.00 | 69.75 |
| Full-Parameter Value Training | Full / 2 | 90.62 | 74.50 |

Table 4 将中两行按较低精度写成 **95.0/69.8、90.6/74.5**，另外给出 **Vanilla VAPO (w/o DIS)=91.3/69.0、Running mean=79.8/55.3**。不把 69.75 与 69.8 的舍入当成实验冲突。

单次 critic update 的下降在 BeyondAIME 上较明显；冻结 attention 的收益在 AIME2025 更大，在 BeyondAIME 只有约 **0.3 pp**。作者用这些结果支持各设计，但没有误差条，不能说每个组件在每个任务上都具有统计显著且同样大的收益。

数学 running mean 保存的是 **每个 prompt 最近 8 个 reward**，用均值作基线；不是在线模拟的全局 128-reward 窗口，也不是当前批次 8 条同策略 rollout。[P §4.3, p.7][P7]

### 7.2 Fig.3–4：记录坐标与量级，不把曲线当精确日志

以下近似值来自 PDF 图像目测，通常只保留到两个有效数字；没有像素级数字化或作者日志，不能用于显著性检验。

| 图 | 轴、比较与近似量级 | 可支持的结论／限制 |
| --- | --- | --- |
| Fig.3, p.6 | 三面为 AIME2025/BeyondAIME/HMMT；x 为 training step，至约 1000；vanilla GRPO 在约 160 步附近急降；另两条继续 | 原文称约 400 步后差距明显，但曲线有交叉；不是所有时点 SAO 都高，也不是 SWE 曲线 |
| Fig.4(a), p.7 | EV 对 training step；后段 SAO 约 0.60，single-update 约 0.50；后段差距总体扩大 | 诊断 critic 对 return 的拟合；没有独立校准/泛化证明 |
| Fig.4(b), p.7 | critic gradient norm；full 参数后段约 10–11，frozen 约 5，x 约到 650 | 参数集合不同，梯度范数较低不单独证明因果；需结合结果表 |
| Fig.4(c), p.7 | clip ratio；SAO 约 0.0004–0.006，VAPO 约 0–0.0004 | 这是比例，约 0.04%–0.6% 与 0–0.04%，不是 0.6 或 60%；具体分母未定义 |

EV 定义在 §4.4 为：

$$
EV=1-\frac{\operatorname{Var}(R-V(s))}{\operatorname{Var}(R)}.
$$

作者把 full-parameter 的大范数解释为 critic 优化不稳，将 VAPO 近零 clip ratio 与约 **90 步**崩溃联系起来。图 4(c) 未提供足够可恢复的 x 轴数值刻度，因此 90 步来自正文，不是假装由图精确读出。[P §4.4, pp.7–8][P7]

**160 步是 vanilla GRPO 的这次实验，90 步是 VAPO，400 步是数学训练分化的描述。** 都不是通用阈值，也不是用户旧项目约 90 步问题的根因诊断。对崩溃模型，§4.2 说明表中采用崩溃前最后有效成绩，而非与 SAO 相同终点的稳定模型。

图 3 HMMT 的最右端目测超过 90，而 Table 1 SAO 为 88.3；本篇未解释二者的 checkpoint/运行对应关系。笔记保留**表值作为作者数表结果，曲线作为轨迹观察**，不任选一个替换另一个。

### 7.3 附录 A.1：step-level 简化没有优于 token-level

作者试图缓解 token value 的高方差，令一个 conversation turn 为 $S_i$，尝试两种 step value：

$$
V(S_i)=\frac{1}{n}\sum_{j=1}^{n}v_{i,j}\quad\text{(Average)},\qquad
V(S_i)=v_{i,n}\quad\text{(Last-Token)}.
$$

Average 用该步全部 token 的 value prediction，critic 也在这些 token 上训练；Last-Token 只让每步最后 token 产生 critic loss。随后用 $\delta_i=R_i+\gamma V(S_{i+1})-V(S_i)$ 做 step-wise GAE，将同一 $\hat A_i$ 广播给该步全部动作 token。**Last-Token 的 critic mask 不等于 policy 只训练最后 token。** 长度自适应改为：

$$
\lambda_{\rm policy}=1-\frac{1}{\alpha\cdot\text{step number}}.
$$

[P A.1, p.13][P13]

Table 5 固定 **400 training steps**：

| 动作/value 粒度 | AIME2025 | BeyondAIME |
| --- | ---: | ---: |
| Step-level (Average) | 85.8 | 60.5 |
| Step-level (Last-Token) | 87.3 | 62.8 |
| Token-level | 89.8 | 66.8 |

Fig.6 的 training reward 后段，token-level 约 **0.54**，两种 step-level 约 **0.50**。这是一项重要负结果：较平滑、较粗粒度的 baseline 不保证更有效。但该比较同时改变 value aggregation、critic mask、advantage 粒度和 λ 的长度单位；不能称作只改变 action 名字或只关闭 Skip-Observation 的单因素消融。

400-step 表中的 89.8/66.8 不能与 Table 1 最终 97.3/74.8 直接作为相同训练终点比较。这个附录也没有证明 step-level 在所有 agent 环境中都差。

### 7.4 在线写作偏好模拟：有适应结果，不是持续生产学习证明

偏好依次奖励 **Cute → Chuunibyou（中二风格）→ Classical**。原文先描述四种总候选：Academic、Cute、Chuunibyou、Classical；实际前两阶段提供前三种，末阶段改为 Classical、Cute、Chuunibyou。**第三阶段既改变 reward，又更换了 system prompt 中的可选风格集合**，并非全程输入完全固定。[P §4.5, pp.8–9][P8]

GLM-4.7 judge 分别判回答质量与风格一致性：

$$
r=r_{\rm quality}\,r_{\rm style},\qquad
r_{\rm quality},r_{\rm style}\in\{0,1\}.
$$

这是模型 judge 的二元乘积，不是客观执行测试，也不是纯风格分类即可满分。原文提到 held-out test set，但没有给数量、prompt/judge 模板、切分方法或 judge 准确率审计。

对照使用最近 **128 个 reward** 的滑动窗口：$\hat A=r-\mathbb E[r_{\rm window}]$。这里没有像 §4.3 一样说“每个 prompt 的 8 个历史 reward”，两者必须分开。SAO 与此 baseline 都允许 single-rollout，因此该实验主要比较基线估计及适应行为，而不是与必须重复用户交互的 GRPO 做现实在线试验。

Fig.5 记录到约 420 步，偏好切换区目测在 **150 与 300 步附近**。左图中占优风格随阶段变化：Cute 峰值约 65%–70%，随后 Chuunibyou 达约 75%–80%，末段 Classical 约 65%–70%；曲线明显非单调。右图的关键信息如下：[P Fig.5, p.9][P9]

- **第一阶段 running mean 反而更高**，后段约 0.70–0.75，SAO 约 0.60。
- 后两阶段 SAO 的恢复后水平较高；最终约 0.65–0.70，对照约 0.55–0.60。
- 第二次切换后 SAO 也发生更深的短暂下跌，最低约 0.08，而对照约 0.19；不能写成每个时点或每次切换都更优。

这些为目测近似值，不是作者精确日志或带置信区间的估计。正文将总体结果解释为状态相关 critic 能更快追踪新分布；图像支持后两阶段更高平台，但不支持“始终压过 running mean”。没有测试大量用户、长期技能保持、隐私隔离或安全发布。附录 B 明确指出真实在线适应仍需更强 safeguards、监测与隐私审查。[P B, p.14][P14]

### 7.5 附录 A.2：有相关方法讨论，没有完整 SPO 数表

A.2 提到 **SPO（Single-stream Policy Optimization）** 和历史 running mean 也是 single-rollout 路线，并声称依赖先验难度、性能较弱。全文实际有 running-mean 的 Table 4 与在线图，但没有标为 SPO 的独立行或完整配置。**保留作者主张，不能补成 SAO 在本篇已经做了可恢复的 SPO head-to-head 实验。** [P A.2, p.14][P14]

<a id="assets"></a>
## 8. Infra、成本与开放资产：不要用后来代码填补原论文

### 8.1 作者披露的是优化组织，不是完整系统配方

原文支持：异步生成与训练、每题单样本解除组等待、rollout logprob 直接用于 current/behavior ratio、value 模型与不同更新频率。没有给出可还原的训练系统后端、队列实现、并发数、发布频率、staleness 上界、样本复用次数、取消／resume 协议或实际多版本轨迹分布。[P §1–4、B][P2]

Fig.2 是方法示意；Fig.3–6 的横轴是 **training step**，没有真实 wall-clock、GPU utilization、吞吐曲线或 time-to-score 表。**本文不能作为 SAO 在八卡上更快、节约某个百分比算力的证据。** 缩短同题等待是结构上的动机；是否抵过额外 critic 更新、内存和数据移动成本仍需实测。

| 成本项目 | 原文给出的锚点 | 无法据此估算的内容 |
| --- | --- | --- |
| TIR 生产/SFT | GPT-OSS-120B；3 epochs | API/GPU 用量、轨迹数、token、清洗成本 |
| Value 初始化 | corpus scaling 主张；10-step warmup | corpus 规模、回归标签、独立预训练费用 |
| 主要 RL | batch 128；K=2；128k 上限；数学曲线约 1000 步 | GPU 型号/数量、拓扑、总 GPU-hours、墙钟、FP32/BF16/FP8、actor/critic 布局 |
| SWE 环境 | OpenHands benchmark 与预算 | 构建/镜像复用、CPU/RAM、执行与评分成本 |
| 评测 | 数学 16/4 次运行 | 总推理 token、API、SWE 重复成本 |
| 在线写作 | GLM-4.7 judge | 请求规模、judge 费用、真实用户部署开销 |

### 8.2 本轮检索到的公开实现：有第三方，不等于作者实验可复现

2026-09-07，以准确标题、arXiv ID、DIS/Skip-Observation 等词检索，并核主文全部链接与两个实际 GitHub 入口。**未确认原作者对应 SAO 实验的完整代码、数据 manifest 或中间 checkpoint 公开入口。** 这是限定本轮范围的检索结论，不宣称互联网上不存在代码。

实际取得第三方 `fooSynaptic/Single-rollout-async-Optimization` 的 [README][C-readme] 与 [sao/dis.py][C-dis]，固定 **`ac2728149041b5f15ceb75413f467ce0659179cf`**（2026-07-27）。README 明确自称 unofficial、与原作者无隶属／背书关系，采用 AReaL、MATH、Qwen3-4B-Instruct-2507；不是本文 30B-A3B TIR/SWE 配方。

它的 README 把 ratio band 写作 `[0.3,5.0]`，`dis_token_weight` 则接受直接的 `lower/upper` 并用 `>=/<=` 判断。这与 P3 加上数学参数得到的 **`(0.7,6.0)`** 不是同一表示。这里只核对 README 与 helper，不将其扩展为实际全部运行配置已审、独立训练结果已验证，也不把 helper 是否 detach 推定为最终调用栈行为。这个差异说明，不能为填补原文缺项直接引用名为 SAO 的第三方实现。

还读取了 [TRL #6473 的实际讨论][C-trl]。贡献者讨论新增实验 trainer，维护者建议隔离实现；**讨论或 feature request 不是合并、训练成功或作者发布证明**。没有继续做通用框架整库审计。

上述第三方内容只支撑其自身声明和代码事实，不承担 SAO 原文事实。本轮不授予“独立复现已验证”标签，不根据 README 的训练曲线声明改变本文主结果。

## 9. 关键披露缺口、内部差异与适用限制

| 问题 | 状态 | 已查位置／处理 |
| --- | --- | --- |
| DIS stop-gradient、advantage 反向边界、最终分母 | **未披露完整实现** | Eq.1–3、全文及 A/B；项目习惯不补空白 |
| ratio 恰好等于端点 | **原文文字/公式不同** | §3.1 闭区间 vs Eq.3 严格不等式；保留两者 |
| 128k、$l$、$\gamma$、value tensor shift | **粒度不足／值未给** | §3.2、§4.1、A.1；不默认 gamma=1 |
| value pretraining 扩大规模的量化证据 | **提出重要性但未给可核数据表** | §3.2 最后一段；不能伪造规模消融 |
| `SAO (w/ DIS only)` 的具体开关 | **未完整枚举** | Table 1、§4.3–4.4、A；不假设无 critic |
| Table 1 Python/no-Python 大幅变动 | **原表如此，原因不明** | PDF/HTML 已对照；不互换标签 |
| 图3 HMMT 最后点与 Table 1 数字 | **对应关系未给** | 图约 >90 vs 表88.3；保留不同出处 |
| 在线模拟全程输入不变 | **不成立** | §4.5 明写末阶段更换 candidate set |
| SAO 在线训练始终优于 running mean | **图不支持这种强表述** | Fig.5 第一阶段对照更高，后两阶段 SAO 更高 |
| SPO 独立结果 | **正文作比较主张，未找到专属数表** | A.2、Table 1–5 |
| SWE 数据、reward、grader、成本、staleness、后端 | **未披露** | §4.1 及全部附录；不继承其他论文 |
| 官方 source archive / 本机 PDF | **本轮未取得** | 网页和容器访问失败；不等于无公开来源 |
| 代码与训练复现 | **仅第三方小范围静态核查；未运行** | C-readme/C-dis/C-trl；不提升为原作者或独立复现实验 |

附录 B 主动限制结论：Qwen3-30B-A3B 的 agentic reasoning、coding、模拟写作不一定迁移到小模型、非 agentic RLHF、密集奖励或短 rollout；依赖可靠 value model 与 token-level 行为概率；真实在线学习需要额外治理，方法也可能降低优化有害目标的门槛。[P B, p.14][P14]

总体证据是**作者训练结果与部分受控算法消融**，不是完整系统因果分解、全域能力保持或低成本复现证明。没有公开的 error bars / 多训练种子，也不能因重复评测就声称训练稳定性已经跨种子验证。

<a id="project"></a>
## 10. 对 RepoHarness 项目一的简短判断

映射日期：**2026-09-07**；依据本次固定基线的 [当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)。当前候选仍是 miles + SGLang + 外部 coding harness、rh2 负责可信环境/评分/样本消费；本轮没有审计本项目 loss 全代码，也没有修改算法定案。

**SAO 支持把“组等待是否值得保留”作为算法—系统联合问题，却不支持现在直接宣布 GRPO 过时或必须改用 SAO。** 最有辨识度的对照是与已经带有效 off-policy 稳定化的 GRPO 比，而不是只与会在本设置中崩溃的 vanilla GRPO 比。SWE 直接增量为 **+2.8 pp**，其总成本未知。[P Table 2, p.6][P6]

只保留三个候选验证：

| 候选 | 为什么值得做 | 最小验证与边界 |
| --- | --- | --- |
| 明确当前 faithful DIS 与 P1–P3 的关系 | 原文 ratio/硬屏蔽清楚，detach/分母不清楚 | 固定少量 token 对拍端点、权重、梯度与分母；声明我方选择，不自称已恢复未披露作者计算图 |
| 在正式资源投入前检查 critic 代价和质量 | single-rollout 的新增依赖是 value，不只是 n=1 | 小规模 frozen/full、K=1/2 对照，记录 EV、真实开销及学习；不把同模型参数量当八卡预算证明 |
| 若组等待与 stale 消费成为主要损耗，再比较采样组织 | 去掉组依赖可能减少陈旧，但也改变 prompt 覆盖 | 对 GRPO+DIS 与 single-rollout 分别报告轨迹数、prompt 覆盖、action tokens、critic计算和独立质量；不能只固定 batch=128 就声称等算力 |

旧摘要里“约400步才拉开”应收紧为**数学曲线的运行观察**，不是 SWE 或所有短实验必须跑到400步。旧稿“现有字段已足够”“slime 缺某模块”“开 compaction 后应转 SAO”属于历史设计判断，本篇不确认它们仍然成立。

尤其是 **Skip-Observation 只讨论外部反馈间的 action-to-action 递推，不等于已经解决 compaction 重建上下文的跨 segment 信用**。本线程后续分别阅读 R14 CompactionRL、R5b GLM-5.2、R5c GLM-5.3，再检查组合方式；本轮不把任何一篇提前标为已读或组合目标已成立。

对简历叙事的支持是：能准确识别并验证采样组织、行为概率与优势计算之间的关系，体现后训练系统理解。是否真正改善本项目有效训练成本和独立 SWE 能力，仍需我方受控实验，而不是引用 SAO 的成绩代替。

## 11. 快速查阅与关联来源

| 要查的问题 | 本稿 | 原文 |
| --- | --- | --- |
| single-rollout 与 batch size 是否相同？ | §2、§6.1 | §4.1 p.6、Fig.2 p.3 |
| DIS 的区间、权重、detach、分母 | §4 | Eq.1–3 p.4；参数 p.6 |
| critic 更新、冻结、warmup | §5.1–5.3、§7.1 | §3.2 pp.4–5、§4.1 p.6、Table3–4 p.8 |
| observation skip、lambda、action 粒度 | §5.4–5.5、§7.3 | Eq.4–5 p.5、A.1 p.13 |
| 全部数学/SWE 表值与评测协议 | §6 | Table1–2 pp.5–6 |
| 90/160/400/1000 步分别指什么？ | §7.2 | §4.2/4.4、Fig.3–4 pp.6–8 |
| 在线偏好改变是否始终优于简单基线？ | §7.4 | §4.5、Fig.5 pp.8–9 |
| 代码、成本和适用性缺口 | §8–9 | 全文、B p.14 |

已存在的关联笔记：[SkyRL-Agent](O01_skyrl_agent_sa_swe.md)、[miles 接入专题](N11_miles_agentic_rollout.md)。前者的 horizon masking 不是 SAO 自动继承的处置；后者的实现能力也不等于 SAO 原始实验采用了 miles。原文提及的 VAPO、IcePop、SPO 仅恢复本文引用关系，本轮未分别全文精读。

## 12. 作者自查与交付状态

**完成：SAO v1 全文及 A/B 附录精读；5 表、6 图、5 个编号公式核对；全部训练分支及负结果覆盖；专属作者自查。** [自查记录](reviews/13_R15_self_check_20260907.md) 列实际检查、修正、数学小测试和待独立复核点。

**未完成：独立 reviewer、GPU/环境训练复现、官方原始 recipe 恢复、完整第三方实现审计。** 本会话没有可用的独立子 agent 工具，不虚构线程 ID、effort 配置或审查通过。没有修改 O01、共享索引、其他并行任务文档或项目实现。正文是 R15 的后续维护入口；旧稿保留作历史线索。

## 一手定位链接

[P-abs]: https://arxiv.org/abs/2607.07508
[P]: https://arxiv.org/pdf/2607.07508v1
[H]: https://arxiv.org/html/2607.07508v1
[P1]: https://arxiv.org/pdf/2607.07508v1#page=1
[P2]: https://arxiv.org/pdf/2607.07508v1#page=2
[P3]: https://arxiv.org/pdf/2607.07508v1#page=3
[P4]: https://arxiv.org/pdf/2607.07508v1#page=4
[P5]: https://arxiv.org/pdf/2607.07508v1#page=5
[P6]: https://arxiv.org/pdf/2607.07508v1#page=6
[P7]: https://arxiv.org/pdf/2607.07508v1#page=7
[P8]: https://arxiv.org/pdf/2607.07508v1#page=8
[P9]: https://arxiv.org/pdf/2607.07508v1#page=9
[P13]: https://arxiv.org/pdf/2607.07508v1#page=13
[P14]: https://arxiv.org/pdf/2607.07508v1#page=14
[C-readme]: https://github.com/fooSynaptic/Single-rollout-async-Optimization/blob/ac2728149041b5f15ceb75413f467ce0659179cf/README.md
[C-dis]: https://github.com/fooSynaptic/Single-rollout-async-Optimization/blob/ac2728149041b5f15ceb75413f467ce0659179cf/sao/dis.py
[C-trl]: https://github.com/huggingface/trl/issues/6473#issuecomment-5062522221
