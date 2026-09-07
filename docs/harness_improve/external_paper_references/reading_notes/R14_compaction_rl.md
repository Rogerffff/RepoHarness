# R14 CompactionRL：可训练上下文压缩、分段权重与跨段信用

CompactionRL 将同一策略生成的任务动作和摘要共同置于终局任务奖励下，用 token-level PPO loss 与跨段 GAE 修正训练压缩后的长程轨迹。最有用的证据不是“窗口变长”，而是训练期压缩、摘要直接训练和评测期压缩被分别比较：30B 模型在 compacted SWE 上达到 56.0%，关闭压缩却为 43.7%，低于其基线 47.5%。106B 实验的输入还经过额外 SFT，不能当作公开 GLM-4.5-Air 原权重的直接 RL。本文恢复全部方法、配置、表图和负结果，区分固定峰值窗口与等计算预算，并说明跨段修正为何只对终奖距离给出精确对应、并非完整轨迹 GAE。**这不是 SAO + compaction 的已披露统一配方，也不是八卡训练成本证明。**

导航：[来源与覆盖](#source) · [阶段、数据与运行过程](#pipeline) · [PPO与跨段GAE](#optimization) · [实验和负结果](#experiments) · [资产与披露缺口](#assets) · [SAO关系与项目判断](#comparison)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**主来源 P**：Yujiang Li、Zhenyu Hou、Yi Jing、Jie Tang、Yuxiao Dong，*CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents*。机构 Tsinghua University；前两位等贡献，前三位相关工作在 Z.AI 实习期间完成。arXiv **2607.05378v1**，提交 **2026-07-06 17:55:12 UTC**。2026-09-07 查询[提交历史][ABS]仍只列 v1；[固定 PDF][P]、[HTML][H]均已取得。首页为 Preprint，不推定录用状态。

**覆盖**：读完 13 个 PDF 物理页，正文 §1–6、Limitations 和 References；逐项核对 **4 张表、4 幅编号图、15 个编号公式**。**此版没有单列技术附录**，正文与限制到 p.10，参考文献从 p.10 延续至 p.13。没有省略某份实际存在的附录，也没有把被引论文自动算作本轮全部精读。

网页文本、公式与 PDF 原页对照使用；HTML 含 `\\rowcolor` 等渲染残留时以 PDF 数表为准。关键公式、全部表图已目视检查。最后一页的带版本截图请求失败后改用无版本 PDF 入口，同为 13 页 v1，末页为参考文献。TeX 网页入口报错，容器直接联网下载 PDF/HTML/TeX 因域名解析失败未取得本机副本；这是**本轮未取得本机来源**，不是论文未公开全文。未向仓库上传原文 PDF、整篇译文或截图。

论文许可为 arXiv perpetual non-exclusive distribution，并非 SAO 的 CC BY 4.0；这里记录科学事实、必要公式与独立分析，不把相邻论文许可套到本篇。

**项目读取基线**：`Rogerffff/RepoHarness@miles-migration`，`681f22f088cdca76eb6e6ac2355d25f633d592a3`。复用[旧 CompactionRL 摘要](../../../../knowledge/summary_compaction_rl.md)及[算法讨论稿](../../../agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md)的问题骨架，逐项回原文；旧稿不是论文实现证据。本轮遵循 [Codex 的 O01 复核建议](reviews/15_O01_codex_quality_review_20260907.md)，只维护本稿及专属自查，不改共享索引或其他线程成果。

### 1.1 原文章节覆盖与快速定位

| 原文位置：PDF物理页 | 实际范围 | 本稿位置 |
| --- | --- | --- |
| p.1–2 Abstract、§1、Fig.1 | 全读；应用动机、两规模效果、GLM-5.2采用声明、与预算有关的限定 | §2、§6–7 |
| p.3 §2 Related Work | 全读；SUPO/ReSum/Context-Folding、group-free及critic路线的作者定位 | §2.2 |
| p.3 §3，Eq.1–5 | 全读并目视核公式；PPO、value regression、TD/GAE/return基础 | §5 |
| p.4–5 §4.1、Fig.2、Eq.6–10、Table1 | 全读；固定触发、原子交互、摘要与resume、段身份、摘要模型替换 | §3–4、§7.1 |
| p.5–6 §4.2、Eq.11–15 | 全读并核公式；组与段计数、全局token分母、位置折扣 | §5 |
| p.6–7 §5.1 | 全读；106B额外SFT、critic预训练、训练与评测配置 | §3、§6 |
| p.7 §5.2、Table2 | 全读并核表注；作者200题子集和引用完整榜单不同，single/compacted区别 | §6.2、§7.2 |
| p.8–9 §5.3、Table3–4 | 全读并核全部表值；长窗口、摘要loss与优化组件消融，保留相反方向结果 | §7.3–7.4 |
| p.8–10 §5.4、Fig.3–4 | 全读并核图上数字/曲线量级；不同模型触发的子集、长度/推理/熵趋势 | §7.5–7.6 |
| p.9–10 §6、Limitations | 全读；无compaction迁移、GAE近似、领域限制 | §8、§10 |
| p.10–13 References | 检查至文件末尾；核SWE-Dev、slime、Terminus-KIRA、Harbor入口身份 | §9 |

只在资产部分加入少量当前仓库检查，固定其提交。没有把 KIRA 当前默认行为或复现仓库选择倒填为作者实验配置。

## 2. 问题与方法的准确边界

### 2.1 学的是摘要内容，不是自由选择“何时压缩”

原文讨论有限上下文下的多轮行动：历史接近窗口上限时，用摘要替换较早信息，再继续同一任务。摘要决定后续策略能看到哪些条件，因此不能只把它视为不影响能力的预处理。方法通过最终结果共同训练 execution 与 summary，处理变长分段引出的权重和信用问题。[P §1、§4，pp.1–6][P4]

但本文的触发阈值、摘要指令与重建模板都是固定规则；保留最近交互数由预算规则调整。**没有训练自由的触发时机策略，也没有独立 memory 工具库或跨任务长期记忆实验。** “trainable compaction”在本篇主要指摘要生成进入策略学习，而不是所有上下文控制动作都可学习。

同样，压缩前后是同一环境任务的继续执行；论文没有在这里引入环境快照、进程恢复、跨用户状态或多 agent 委派。这些是可另行研究的问题，不是本文已经具备的能力。

### 2.2 与相关工作：按作者讨论保留，不补成比较实验

§2 将长上下文、prompt/observation 压缩、外部记忆与 reflection 列为背景；将 SUPO 定位为多轮RL内联合摘要与工具使用，ReSum 为外部周期摘要及摘要条件化训练，Context-Folding 为可训练 branch-and-fold。随后引入 RLOO/GRPO/DAPO 等无critic路线，以及 VC-PPO/VAPO 的 value-learning 经验。[P §2，p.3][P3]

这些是作者的文献定位；本篇没有逐一给出与 SUPO、ReSum、Context-Folding 的同条件成绩表，也没有独立 GRPO 对照。因此不能据相关工作段宣称本方法全面超过上述方案或首先提出可训练摘要。

<a id="pipeline"></a>
## 3. 训练阶段、模型关系与数据环境

### 3.1 两个实验分支并不共用相同初始化过程

| 分支 | RL前的输入与准备 | 后续角色 | 原文依据 |
| --- | --- | --- | --- |
| 30B-A3B | GLM-4.7-Flash；本篇未描述额外actor SFT | actor从该checkpoint开始；对应critic同源初始化，再做50步value pretraining | §5.1，p.6 |
| 106B-A30B | GLM-4.5-Air先用**GLM-4.7生成的轨迹做SFT**，得到GLM-4.5-Air-SFT | actor与critic以该SFT checkpoint初始化；critic再预训练50步 | §5.1，p.6 |
| GLM-5.2，750B-A40B | 摘要称已将CompactionRL用于其RL流水线 | 本篇没有该规模的独立配方、组件消融或资源表 | Abstract，p.1 |

论文正文、图注有时写 GLM-4.5-Air-SFT，表格简称 GLM-4.5-Air。下文保留表名，但讨论增量时按 §5.1 的**已做SFT输入**理解；不要把66.8直接归为从公开原权重开始的pure RL。GLM-4.7是这里的数据生成模型，不应改写成GLM-4.7-Flash，也不是RL阶段的在线OPD教师。[P §5.1；Fig.3，pp.6、9][P6]

主RL中执行和摘要由同一可训练策略生成，没有独立冻结摘要教师或单独摘要质量reward。Table1替换摘要模型是诊断实验，不能把其中Qwen模型画进所有训练分支。本文亦未披露额外数学、安全、偏好、多模态或部署蒸馏训练阶段；不因模板字段而补造。

### 3.2 可恢复的数据链与明确缺项

作者称使用 **SWE-Dev 的开放训练数据**；引用对应 Wang et al. 的 *SWE-Dev: Building Software Engineering Agents with Training and Inference Scaling*。本篇没有提供自己的任务列表、镜像数、最终训练题数或环境生产漏斗。[P §5.1，p.6；References，p.12][P6]

| 对象 | 本篇实际披露 | 未恢复的部分 |
| --- | --- | --- |
| 上游训练来源 | SWE-Dev | 使用哪个release、仓库/提交/任务split、多少实例与镜像 |
| 106B的SFT数据 | GLM-4.7生成的轨迹 | 题源、数量、成功过滤、训练epochs、token与教师成本 |
| critic准备 | 同源checkpoint；50步value pretraining，使用训练数据 | rollout采集策略、return目标、有效样本数、冻结范围 |
| RL反馈 | 由任务正确性决定的终局R，赋予同一rollout的可训练段 | 具体binary/partial尺度、F2P/P2P实现、hacking/flakiness审计 |
| RL消费 | global batch=128、group=1 | 128究竟在分段前还是分段后计数、microbatch、总更新步数、过滤后数量 |
| 外部评测 | SWE-bench Verified随机200题；Terminal-Bench2.0全量 | SWE题单/随机seed、TB精确任务注册版本与题数、逐题输出 |

不能从上游项目总规模推成本篇实际消费量，也不能因为测试是可执行的，就断言已验证gold/no-op/合法替代解、隐藏测试隔离与反作弊。本文没有展示任务修改或持续供给的训练循环；这不是一篇环境合成研究。

### 3.3 Harness身份：评测明确，训练具体接线仍缺

原文明确所有作者评测使用 **Harbor + Terminus-KIRA**，RL使用 **slime**。它没有给出训练入口、harness commit、API捕获、消息转换与评分脚本，因此不能仅据评测配置就认定所有训练也运行同一原生KIRA代码路径。[P §5.1，pp.6–7][P7]

这不否定作者可能采用相同接口；只是原文不足以验证。当前KIRA README的工具与默认上下文行为另外放在§9，不用其补齐历史训练接线。

## 4. Rollout状态变化、段身份与token来源

### 4.1 原子交互与触发规则

原文 Eq.6–9，PDF pp.4–5：

$$
h_t=(s,u,z_1,\ldots,z_t),\qquad z_i=(a_i,o_i),
$$

其中`s`为system prompt，`u`为原始用户任务，`a_i`是一次assistant响应，`o_i`是对应环境反馈。每一完整assistant–observation对被视为原子step，避免在工具调用与其结果之间截断。

设窗口预算为C，当

$$
C-|h_t|<T_{\mathrm{comp}}
$$

时，在当前历史后附加固定总结要求，并采样

$$
S_t\sim\pi_\theta(\cdot\mid h_t\oplus q_{\mathrm{sum}}).
$$

作者描述的总结目标涵盖原任务、已做操作、重要观测、未解决错误、当前状态与后续行动，但未提供`q_sum`的完整可执行文本。随后重建为

$$
\bar h_t=(s)\oplus u_{\mathrm{resume}}(S_t)\oplus(z_{t-k+1},\ldots,z_t).
$$

默认`k=2`，放不下时减小k。原始`u`并未作为独立项再次写入Eq.9；它可能经摘要/模板保留，但**不能擅加原任务完整逐字复制**。固定resume模板本身未公开于本篇。[P Eq.6–9，pp.4–5][P4]

这里保留的是最近完整交互的原貌，不是证明保留了整个外部世界状态。摘要有损、工具观测可能只反映部分环境；不要把context重建写成环境rollback。

触发阈值为剩余10,240 tokens，而不是累计token达10,240。论文没有给大块observation突然挤爆窗口、摘要指令占位、摘要生成超长或连续重压缩的完整处置；不能从这个不等式推得所有请求一定能在C内运行。

### 4.2 一次rollout不等于一个训练sample

Eq.10将一次完整rollout记为有序段序列：

$$\tau=(\sigma_1,\ldots,\sigma_K).$$

段有execution和summary两种。前者包含解题生成，后者包含重建前生成的摘要。两者共享终局`R(τ)`；没有另一个“摘要写得像参考答案”的评分器。[P §4.1，p.5；Fig.2，p.4][P5]

在无异常、每次压缩都产生一个摘要段且继续执行的示意下，压缩m次产生m+1个execution段和m个summary段。因而三次压缩对应至多四个执行窗口，**不等于总共只有四个生成段**；这项计数是按原文定义推导的结构例，不是公开代码的sample数量保证。

### 4.3 Mask：原文能确定的动作集合，与实际实现分开

| token出现位置 | 在本文目标中的身份 | 证据强度 |
| --- | --- | --- |
| execution时新采样的assistant token | 可优化action | §4.1、Eq.12的明确对象 |
| summary首次生成时新采样的token | 可优化action；完整方法直接训练它 | §4.1、§5.3明确 |
| 后续resume中复制的summary | 当前段条件x，不是再次采样的action y | 根据Eq.9、11–12的数学身份推导 |
| 携带的最近历史，哪怕角色仍为assistant | 当前段的已有上下文；不应因角色而二次计权 | 同上；需要实现保证来源而非只看role |
| 工具observation、system/user模板 | 条件信息，不是该目标优化的assistant生成位置 | Eq.6、12及M定义 |
| `w/o sum.`中summary原始响应 | 不进入其直接summary loss | §5.3；critic mask与后续token计数没有逐项说明 |

上述后几项是为了正确实现论文数学定义所需的区分，**不宣称原文发布了逐token mask代码或已验证重分词不会改变token**。也不能把本篇自动等同SAO的Skip-Observation GAE：CompactionRL按optimized-token定义距离，但没有单独给SAO的action-to-action Bellman桥接公式。

摘要loss关掉也不等于摘要模型冻结：主方法是同一套权重，execution更新仍可能间接改变摘要分布。没有独立冻结副本的披露，不能将`w/o sum.`称为fixed-teacher ablation。

<a id="optimization"></a>
## 5. 训练目标：三个不同的计量问题

### 5.1 PPO、critic与局部GAE基础

原文§3，Eq.1–5（p.3）先给标准PPO clipped surrogate、critic MSE、TD residual与GAE：

$$
J^{\mathrm{CLIP}}=\mathbb E_t[\min(\rho_t A_t,\mathrm{clip}(\rho_t,1-\epsilon,1+\epsilon)A_t)],
\qquad
\mathcal L^{\mathrm{VF}}=\mathbb E_t[(V_\phi(x_t)-\hat R_t)^2],
$$

$$
\delta_t=r_t+\gamma V_\phi(x_{t+1})-V_\phi(x_t),\quad
A_t^{\mathrm{GAE}}=\sum_{\ell=0}^{T-t}(\gamma\lambda)^\ell\delta_{t+\ell},\quad
\hat R_t=A_t^{\mathrm{GAE}}+V_\phi(x_t).
$$

真正终态给`V(x_{T+1})=0`。这些是背景公式；不能据此就认定**每个中间compaction边界都是真正终态**。`T`在这里是optimized tokens，不是环境调用数。[P §3，p.3][P3]

### 5.2 为什么作者选择PPO，而非把segment当GRPO成员

如果同题G次执行各自分成K_g段，扁平化后成为`ΣK_g`个sample。把这些段当独立reward样本进行组统计，会使压缩更多的执行重复进入统计。原文也指出，按完整执行做组相对归一化不能直接给出各段不同的value-based advantage，因此采用critic PPO。[P §4.2，p.5][P5]

**读者边界判断**：这是对错误扁平化及细粒度信用需求的诊断，不是“任何GRPO都不能处理压缩”的证明。按原始execution计算一个组优势、再广播到其各段，仍可定义一种目标，只是不等价于本文的token/segment信用估计。原文没有同条件GRPO实验来否定这种替代方案；本笔记不替作者增加该实证结论。

### 5.3 Token-level loss：消除切段计数效应，不让每题等权

Eq.11–12定义当前策略与old策略在**同一段实际上下文**上的概率比：

$$
\rho_{s,i}(\theta)=\frac{\pi_\theta(y_{s,i}\mid x_{s,i})}{\pi_{\theta_{\mathrm{old}}}(y_{s,i}\mid x_{s,i})}.
$$

以batch中全部可优化assistant-token集合M作分母：

$$
\mathcal L_\pi=-\frac1{|\mathcal M|}\sum_{(s,i)\in\mathcal M}
\min\!\left(\rho_{s,i}\widehat A_{s,i},\mathrm{clip}(\rho_{s,i},1-\epsilon,1+\epsilon)\widehat A_{s,i}\right).
$$

这是PPO的`min + clip`，**不是SAO的双边区间外整项硬屏蔽**。原文没有披露ε数值、额外TIS、真实rollout logprob捕获或多版本old-policy重建。§3将ratio描述为current/rollout，§4写作`θ_old`；没有足够系统实现说明来替它区分旧trainer重算概率与推理端行为概率。[P Eq.11–12，p.6][P6]

**独立算例，非作者实验**：9个token各自loss=1，另1个token的loss=9。两段各自平均再平均为5；全局token均值为1.8。把前9个token重分为3个长度3的段，segment均值变为3，token均值仍为1.8。它说明**固定每token项后**，token分母不随任意切段改变。

这不意味着每个rollout等权：生成更多可训练token的rollout占更大计量份额；也不保证每token梯度数值相同。若切段同时改变上下文、advantage或λ，整体目标仍会变。本文的消融不是对所有可能的episode-normalization方案做优劣判定；分布式DP/CP/microbatch如何实现全局分母也没有公开于本篇。

### 5.4 Cross-trajectory GAE：跨的是同一rollout的段

令第s段有n_s个optimized tokens。Eq.13–15为：

$$
A^{\mathrm{loc}}_{s,i}=\sum_{\ell=0}^{n_s-i}(\gamma\lambda)^\ell\delta_{s,i+\ell},
\quad\delta_{s,i}=r_{s,i}+\gamma V_\phi(x_{s,i+1})-V_\phi(x_{s,i}),
$$

$$
N_{>s}=\sum_{j>s}n_j,\qquad
\widehat A_{s,i}=(\gamma\lambda)^{N_{>s}}A^{\mathrm{loc}}_{s,i}.
$$

局部计算若把同一终局奖励放在每个段的末尾，则未经修正时，早期段的action会误以为奖励更近。乘以后续generated trainable token数的折扣后，**终奖项**的系数变为

$$
(\gamma\lambda)^{N_{>s}+n_s-i},
$$

与按同一折扣串联全部段时到终奖的token距离一致。`N_{>s}`不跨无关任务、不等于剩余工具调用数，也不是wall-clock时间。[P Eq.13–15，p.6][P6]

注意乘数作用于整个local advantage，而非仅reward项。它没有显式加入后续段的全部TD residual或跨边界value bootstrap，所以不能把“终奖距离一致”写成“完整轨迹GAE精确恢复”。作者在Limitations明确承认该方法仍是近似。[P Limitations，p.10][P10]

### 5.5 一个可复核的近似反例

**这是读者自行构造的标量例，只解释公式，不评价作者隐藏实现。** 设两个段长度为(2,1)，γ=1、λ=0.8；全局只有最后token得到R=1；各token之前的value为(0.2,0.4,0.6)，真正终态为0。演示local GAE时额外假定每个独立段末端bootstrap为0，并把R放到各段末尾。

| 计算方式 | 三个token的advantage |
| --- | --- |
| 完整串联，一次终奖 | (0.616, 0.520, 0.400) |
| 先局部GAE，再Eq.14修正 | (0.544, 0.480, 0.400) |
| value全为0时：两种方法 | 均为(0.640, 0.800, 1.000) |

非零critic时差异来自局部残差与边界value结构；零critic时只剩终奖距离，两者在这个例子吻合。该算例已用独立Python标量递推检查；不是slime数值对拍，也不证明所有critic选择下差异的方向固定。

### 5.6 Length-adaptive λ与value target仍需明示实现选择

§5.1给出`λ=1−1/(αl)`、`α=1.5`，其中l称response length。但Eq.13–15使用未带段索引的统一λ。**一条执行有多个response和segment时，l按哪一级计算、Eq.14是否沿用当前段λ或跨段乘各自折扣，原文没有交代。** 统一λ下的距离推导不能不加说明地当成变λ实现的等价证明。

类似地，§3的return是`A_GAE+V`，§4只说standard value regression，未明确critic目标采用local advantage还是修正后的advantage、是否使用独立`λ_critic`。不能把SAO的`λ_critic=1`、Frozen-Attention、10-step warmup移入本篇。

`w/o sum.`还留下一个实现问题：关闭summary直接loss后，summary是否仍进入critic目标、n_s/N_{>s}和归一化计数？本篇没有分开说明。因此它是一个有价值的训练干预，但不能宣称已将所有变化严格限于某些actor梯度。

<a id="experiments"></a>
## 6. 配置与比较协议

### 6.1 已披露配置：训练和评测分列

| 项目 | RL训练 | 评测 |
| --- | --- | --- |
| 峰值上下文 | 30B 64k；106B-SFT 80k；另有无压缩128k/160k训练对照 | Single/Comp使用64k或80k；Long使用128k或160k |
| 每题采样 | group size=1 | Pass@1；每实验2次evaluation均值，不是pass@2/best-of-2 |
| batch | global batch=128 | SWE随机200题，TB2.0全量 |
| 更新 | 每batch 2次value、1次policy | 不适用 |
| 初始化 | critic同源checkpoint，预训练50步 | 各对应checkpoint |
| 优化器／LR | policy Adam，2e−6；critic LR 3e−6 | 不适用 |
| GAE | length-adaptive λ，α=1.5 | 不适用 |
| 单次assistant响应 | ≤10,240 tokens | §5.1未独立列此字段的eval值，不用训练值自动补齐 |
| 压缩触发 | 剩余context <10,240 tokens | 使用compaction评测；逐项阈值重申不完整 |
| 压缩次数 | 每rollout至多3次 | 每trajectory至多3次 |
| interaction turns | 未明确列训练上限 | 至多250 |
| sampling | 未独立列训练temperature/top-p | temperature=1.0，top-p=1.0 |
| backend / harness | slime；具体训练harness接线未给 | Harbor + Terminus-KIRA |

来源[P §5.1、Table3，pp.6–8][P7]。critic优化器种类、Adam参数、ε、γ、KL/entropy系数、attention冻结、staleness阈值、总训练步数与并行布局均没有完整披露。**配置表不是可直接执行的训练yaml。**

### 6.2 三种预算：不要把“峰值相同”解释成“总成本相同”

原文Table2–3定义：Single只用一个峰值窗口；Comp允许三次compaction，称有效预算为`4×Peak Length`；Long是不压缩的大窗口参考，大小为`2×Peak Length`。这三个数字分别描述窗口与续跑机制，不是已经匹配过的生成token总数或FLOPs。[P Table2–3，pp.7–8][P8]

压缩触发有预留、summary需要生成、system/resume/tail会重新输入，各段实际未必填满；累计prefill还会重复处理历史。因此“64k×4”等于一个命名上的续跑额度，不等于每条轨迹产生精确256k新action token，也不等于单次持有256k完整历史。三次compaction的推理工作量更不等于single四倍的确定费用。

**作者内部结果**用随机200题SWE子集及TB2.0全量，均值来自两次评测；没有公开任务ID、随机seed、每次原分数、置信区间或多训练seed。不要将200题子集分数写成全500题Verified结果。作者表注称包括Qwen3.5-35B-A3B在内的“our results”使用该200题子集；即使其行排在public-baseline分组，也不能把它误作同一批完整榜单引用。[P Table2注，p.7][P7]

## 7. 完整结果、消融与反向证据

以下数值为百分制Pass@1；差值为读者算术，不是显著性检验。106B表名保留原文简写，初始化按§3.1理解。

### 7.1 Table1：固定executor，更换summarizer

固定execution为GLM-4.7-Flash：

| summary模型 | SWE-Verified | 每trace平均summary次数 |
| --- | ---: | ---: |
| Qwen3.5-27B | 55.5 | 1.010 |
| GLM-4.7-Flash | 50.5 | 1.075 |
| Qwen3-30B-A3B | 49.0 | 1.126 |

[P Table1，p.5][P5]。从最弱到最强summarizer相差6.5pp；相对原生GLM summarizer是5.0pp。它支持固定executor下摘要策略影响结果，不证明存在一个单一、已经量化的“摘要质量”潜变量，也没有比较摘要器API成本。

这个55.5与CompactionRL的56.0很接近，但前者换了外部summarizer，后者同时更新executor和summarizer；没有单独的固定executor训练后summarizer行。**不能把0.5pp解释成强化学习超过强外部摘要器的显著独立收益。**

### 7.2 Table2：同峰值下的主对照

| 模型/训练变化 | Peak | SWE Single | SWE Comp | TB2 Single | TB2 Comp |
| --- | ---: | ---: | ---: | ---: | ---: |
| GLM-4.7-Flash | 64k | 47.5 | 50.5 | 14.6 | 13.4 |
| + RL，无compaction | 64k | 50.0 | 48.0 | 16.9 | 12.4 |
| + CompactionRL | 64k | 43.7 | 56.0 | 16.9 | 20.2 |
| GLM-4.5-Air | 80k | 57.8 | 59.8 | 17.9 | 21.4 |
| + RL，无compaction | 80k | 58.3 | 62.5 | 20.2 | 23.6 |
| + CompactionRL | 80k | 57.3 | 66.8 | 21.4 | 24.5 |

[P Table2，p.7][P7]。compacted评测下，对base的headline增益分别是30B `+5.5/+6.8`、106B `+7.0/+3.1`。**对已经做RL的同峰值对照**则为30B `+8.0/+7.8`、106B `+4.3/+0.9`。不能把两种baseline混用。

single-window不是全面提升：30B SWE比base低3.8pp，比同峰值普通RL低6.3pp；106B SWE为57.3，也略低于57.8/58.3。作者以train–test mismatch和higher overlong rate解释，但没有overlong率的完整数表或配对归因实验。它不是所有静态能力都被遗忘的证明，也不是无条件可忽略的回退。[P §5.2、Limitations，pp.7、10][P10]

原表还列出以下公开参照；其SWE通常是完整benchmark、工具与预算不同，不与上述200题混做排名：

| 原表外部参照 | Peak | SWE Single | TB2 Single |
| --- | ---: | ---: | ---: |
| GPT-5 mini (2025-08-07) | 400k | 72.0 | 31.9 |
| Qwen3-Coder-480B-A35B-Instruct | 256k | 66.5 | 23.9 |
| gpt-oss-120b | 128k | 62.0 | 18.7 |
| Qwen3-Coder-30B-A3B-Instruct | 256k | 51.9 | 14.6 |
| Qwen3-235B-A22B-Instruct-2507 | 256k | 45.2 | 13.5 |
| Qwen3-30B-A3B-Instruct-2507 | 256k | 25.2 | 5.34 |

Qwen3.5-35B-A3B另列64k compacted `58.0/27.0`，Single未给；表注将它纳入作者200题结果。它高于30B CompactionRL的56.0/20.2，但底座不同，不构成训练方法对照。破折号代表未报告，不是0分。[P Table2，p.7][P7]

### 7.3 Table3：训练方式×评测上下文交叉矩阵

这是本篇最值得完整保留的消融。下两表每行是一个训练配置；列是评测方式。关闭summary loss的配置仍在训练时生成并使用summary，不等于关闭compaction。

**30B：Single/Comp峰值64k，Long峰值128k。**

| 配置 | Train Budget | Summary直接训练 | SWE Single | SWE Comp | SWE Long | TB Single | TB Comp | TB Long |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GLM-4.7-Flash | — | — | 47.5 | 50.5 | 53.5 | 14.6 | 13.4 | 16.9 |
| RL，无压缩64k | 64k | 否 | 50.0 | 48.0 | 48.5 | 16.9 | 12.4 | 12.4 |
| RL，无压缩128k | 128k | 否 | 48.3 | 52.5 | 59.0 | 11.8 | 23.6 | 14.6 |
| CompactionRL w/o sum. | 64k×4 | 否 | 52.5 | 54.5 | 50.2 | 9.0 | 12.4 | 11.2 |
| CompactionRL | 64k×4 | 是 | 43.7 | 56.0 | 49.0 | 16.9 | 20.2 | 16.9 |

**106B：Single/Comp峰值80k，Long峰值160k。**

| 配置 | Train Budget | Summary直接训练 | SWE Single | SWE Comp | SWE Long | TB Single | TB Comp | TB Long |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GLM-4.5-Air | — | — | 57.8 | 59.8 | 59.5 | 17.9 | 21.4 | 20.8 |
| RL，无压缩80k | 80k | 否 | 58.3 | 62.5 | 61.8 | 20.2 | 23.6 | 21.1 |
| RL，无压缩160k | 160k | 否 | 63.0 | 64.5 | 64.0 | 20.8 | 23.0 | 23.6 |
| CompactionRL w/o sum. | 80k×4 | 否 | 54.5 | 64.5 | 61.6 | 17.6 | 21.5 | 20.2 |
| CompactionRL | 80k×4 | 是 | 57.3 | 66.8 | 62.1 | 21.4 | 24.5 | 22.5 |

[P Table3，p.8][P8]。四项compact列中，完整方法相对w/o sum.均提高：30B `+1.5 SWE/+7.8 TB`，106B `+2.3/+3.0`。这是直接summary训练的正面证据，但共享权重及未披露mask细节的边界仍见§4.3、§5.6。

**同样需要保留的反例：**30B无压缩128k训练在compact TB得到23.6，高于完整方法20.2；在SWE Long得到59.0，高于完整方法的Long 49.0，也高于其compact 56.0，但后一个比较的评测机制不同。106B无压缩160k在Single SWE的63.0高于完整方法57.3。30B关闭summary直接loss反而在Single SWE为52.5，高于完整方法43.7。

因此作者“较短peak能与长窗口竞争且常超过”的解释可以在部分格子成立，不能升级成**全面超过长上下文训练**。固定peak的Table2主结论不应该被扩大到训练peak不同的Table3全部配置；两者也未匹配GPU-hour或总生成token。

### 7.4 Table4：token分母与跨段GAE消融

所有行是106B-SFT背景下的80k×4 compacted评测：

| 方案 | SWE | TB2 |
| --- | ---: | ---: |
| 基线 | 59.8 | 21.4 |
| 完整CompactionRL | 66.8 | 24.5 |
| 去掉token-level loss | 60.0 | 21.3 |
| 去掉cross-trajectory GAE | 63.0 | 22.5 |

[P Table4，p.9][P9]。相对完整方法，去token分母下降`6.8/3.2pp`，去跨段修正下降`3.8/2.0pp`。前者在本设置下降更大，但它不是对两个组件普遍重要性的排名，也不是可相加的独立增益分解。

没有公开“去掉两项”的完整因子矩阵、精确替换reducer实现或多seed误差；30B上也没有同样的组件消融表。此结果验证一种近似方法在该实验有用，不把§5.4的数学近似变成精确无偏定理。

### 7.5 Figure3：实际行为数字与条件子集

场景为106B、SWE、80k×4。下表数字来自原图柱上标注，不是曲线目测：

| 模型 | Compactions/trace | Tool calls/trace | 触发压缩任务的Pass@1 |
| --- | ---: | ---: | ---: |
| GLM-4.5-Air-SFT | 0.47 | 83.4 | 35.4 |
| RL-80k | 0.21 | 48.2 | 29.0 |
| RL-160k | 0.26 | 63.5 | 45.9 |
| CompactionRL w/o sum. | 0.58 | 90.8 | 42.4 |
| CompactionRL | 0.36 | 60.7 | 47.7 |

[P Fig.3，p.9][P9]。trace是一个任务的完整执行，包含全部压缩段，不是单个segment。完整方法比base及w/o sum.少调用工具、少压缩；**压缩次数多于两个普通RL，但tool calls只多于RL-80k，低于RL-160k的63.5**。正文“比standard RL更多”的概括需要这个限定，不能为了配合叙述改动图值。

第三列限定为“每次评测实际触发压缩的任务”。不同模型行为会改变哪些任务进入这个子集，原文没有共同固定的compaction任务清单。47.7高于35.4是各自条件子集结果，**不自动等于在同一批预定难题上提升12.3pp**；更不是重复运行可靠率。关于减少无效重新探索的解释有整体成功与平均行为支撑，但没有在相同环境边界做成对续跑实验。

工具调用数少不代表更低总费用：摘要和每turn推理都可能更长，latency/prefill/环境时延也不相同，见下一节。

### 7.6 Figure4：训练趋势不只写“变长/变好”

106B训练图横轴约0–80个training steps，末端约75附近。以下为**原图目测近似量级，无精确日志、无误差条**：

| 子图 | 完整CompactionRL | 对照 | 能支持什么／不能支持什么 |
| --- | --- | --- | --- |
| (a) Summary Length | 约2.1k到2.35k，中途有波动 | w/o sum.约2.1k降至1.6–1.75k | 摘要变长；没有独立事实保持率或“更详细”的逐项打分 |
| (b) Reasoning Tokens per turn | 约90到190，早期略降后上升 | w/o sum.与普通RL末段约60–80 | 每turn推理开销上升；不是整条轨迹只用了190tokens |
| (c) Entropy | 约0.38先降到0.31附近，再到0.44 | w/o sum.末约0.48，普通RL末约0.56 | 后期增长更缓；不是全程单调增，也没有因此得到稳定性定理 |

[P Fig.4，p.10；§5.4，p.9][P10]。作者将更长摘要解释为更完整可执行的状态、较缓entropy增长解释为更可控的优化。本稿保留这些**作者解释**，不把长度本身当作质量证据。曲线的80刻度也不是完整训练的总步数承诺，不能用它估算全部样本量或费用。

## 8. 系统、预算和失败处置的证据上限

本文明确slime作为训练框架，但未给出：GPU型号/数量、GPU-hour、wall-clock、TP/EP/CP、精度、训练推理拓扑、weight-sync规则、staleness年龄、partial-rollout策略或logprob一致性结果。**“slime是异步框架”不等于这次实验已验证指定的fully-async时序。** group=1本身也不能给出排队节省量。[P §5.1，p.6][P6]

同样没有完整描述：环境超时、parser错误、窗口溢出、三次压缩耗尽、异常summary、未完成patch分别怎样给reward、mask、保留或丢弃。不能套用SkyRL-Agent的horizon规则，也不能将RepoHarness当前准入语义当成本文方法。

成本应分开看：106B前置SFT与轨迹教师、两模型critic预训练、每batch双critic更新、摘要生成、重复prefill、真实环境执行与两次评测。论文仅有预算配置和部分行为量，没有把这些合成可核算的总成本。降低peak context很可能改善部分显存压力，但**本篇没有给精确显存对照或在8×96GB上完成训练的证明**。

适用性限制有三类：不开compaction时的迁移回退；cross-trajectory GAE近似；主要验证coding/terminal、尚无其他观察结构和reward域的对应实验。[P Limitations，p.10][P10]

<a id="assets"></a>
## 9. 开放资产、当前附查与复现程度

### 9.1 论文关联资产与本轮实际取得

| 资产 | 本轮状态 | 不能推出什么 |
| --- | --- | --- |
| CompactionRL v1正文 | HTML、PDF文本与关键页图完整可读；TeX/本机下载未取得 | 原始训练实现、checkpoint和日志一并开放 |
| SWE-Dev | 原文指明训练数据来源，引用身份已核 | 上游全部数据就是本次训练集 |
| slime | 原文参考文献给通用仓库链接 | 主分支任一PPO/compaction配置就是作者实验revision |
| Harbor / Terminus-KIRA | 原文明确评测面；KIRA关联README已定点读取 | 当前默认提示、工具和overflow行为等于作者定制设置 |
| CompactionRL专属权重/manifest/recipe | 本篇及本轮定向检索未确认一套作者绑定的完整发布 | “互联网上不存在实现”或“作者永久不公开” |

本轮不完整审计slime，不重复此前上游综述；没有取得作者固定实验commit就保留缺口。没有下载模型或执行训练、容器评测。

### 9.2 KIRA只作关联入口，不代替原文算法

固定 **`krafton-ai/KIRA@652dacbf14d29ea93a83c496ee91e0e5ba286721`**，只读[README第1–125行][KIRA]。该README描述native tool calling、`execute_commands`、`task_complete`、`image_read`，以及completion确认和上下文overflow后自动摘要重试；提供`terminus_kira.terminus_kira:TerminusKira`的Harbor调用入口。

这些是当前README自述，不是代码消费路径已审计。特别是原文按剩余预算提前触发，README概括overflow后处理；没有实际实验revision就不能视作完全相同逻辑。`image_read`存在也不能证明CompactionRL做了视觉RL。本文不逐项复述KIRA排行榜，因为它不构成本方法的训练证据。

### 9.3 一个可用的复现线索，但不是作者历史配方

本轮找到 **`ajing/compactionrl-repro`**，固定 **`c7af1ea7f07324cf20d74bf293b5caee7d110d2a`**，只检查[README第1–135行][REPRO]。它自称复现公开算法核心、提供synthetic memory实验和slime接线，并明确**没有复现30B/106B benchmark分数**，提示prompt、resume、训练子集、reward和PPO细节缺失。

该仓库也记录了mask、critic、checkpoint保存与不同seed的失败/修正，并坦言尚无稳定的held-out LLM能力收益。本轮未复核那些实验日志、代码或blog，不能把这些自述登记为本篇结论已获独立复现。它的`lambda_s`、stitched bootstrap和其他扩展同样不用于补齐原论文。

后续真要实现时它可作为问题清单或对照代码来源；本次精读仍以P为方法事实依据，而非用复现者选择消除作者未披露项。

### 9.4 最影响复用的未知项汇总

| 未知 | 类型与已查范围 | 对复现/解释的影响 |
| --- | --- | --- |
| summary/resume逐字模板、工具消息格式 | 原文未披露；§4.1只给目标与结构 | 无法恢复完全一致的训练输入 |
| λ按response/segment/rollout哪一级计算 | 原文不充分；Eq.13–15与§5.1已核 | cross-boundary折扣存在不同合理实现 |
| 中间segment的bootstrap、critic return | 原文不充分；Eq.2–5、13–14及value描述已核 | 不能声称full-trajectory GAE等价 |
| w/o sum.的critic mask与N/M计数 | 原文未逐项列；§5.3及全表已核 | 消融的确切实现干预不完全可恢复 |
| global batch=128在分段前后如何计量 | 原文未明确；§5.1已核 | 不应当作128独立执行或128段的确定消费量 |
| 训练harness与行为概率来源 | 原文未给固定接线；§4–5已核 | 无法验证token fidelity或策略版本合同 |
| dataset/镜像/200题列表/两次原始结果 | 原文未给完整资产 | 难以严格重跑及建立置信区间 |
| 更高overlong率的数值与因果作用 | 只有正文解释，无独立数表 | 不能完全解释single-window退化 |
| GPU/CPU/API费用与实际token消耗 | 原文没有总成本实验 | 固定peak不等于等成本，不能报价八卡预算 |
| TeX与本机原文缓存 | 本轮未取得，非作者未公开 | 不伪装为已读取TeX；现有正文及图页覆盖完整 |
| 原始实现与现代复现对照 | 未做完整源码/实验审计 | 不给未经运行的代码下正确性保证 |

<a id="comparison"></a>
## 10. 与SAO的关系：交集真实，但不能自动合并

SAO本轮只定点回查其§3–4公式与配置，完整笔记见 [R15](R15_single_rollout_asynchronous_optimization.md)。下表是两篇公开内容的对照，不是已经训练过的组合方法。[SAO v1 §3–4][SAO]

| 维度 | CompactionRL v1 | SAO v1 |
| --- | --- | --- |
| 主要问题 | 上下文重建后分段权重与时间信用 | 异步策略漂移、同题组等待、value稳定性 |
| actor目标 | Eq.11–12：old-policy ratio的PPO min/clip，显式全局token分母 | Eq.1–3：current/rollout ratio加双边硬屏蔽，计算图/分母另有缺口 |
| GAE改动 | local GAE乘后续optimized-token距离折扣 | action-to-action的Skip-Observation桥接 |
| critic共同点 | 同源初始化、2次value/1次policy | 同样重视critic质量与2:1更新 |
| critic不同点 | 50步预训练；没有冻结attention声明 | 10-step warmup等配置；明确Frozen-Attention |
| 实验模型/harness | GLM-4.7-Flash、GLM-4.5-Air-SFT；Harbor/Terminus-KIRA | Qwen3-30B-A3B；SWE使用OpenHands |
| compaction训练 | 本文主要干预，summary进入目标 | SAO未给同一套summary联合训练配方 |
| GLM-5.2 | 声称已采用 | 也声称已采用 |

共同用于GLM-5.2，并不补出它们如何合并loss、何时更新critic或怎样处理混合策略版本的算法。GLM-5.2/5.3文章按线程分工另行精读；本轮不把它们标为已完成，也不用尚未读完的博客回填组合公式。

尤其不要把“跨段GAE”解释成跨不同rollout的共享优势，更不要把“skip observation”解释成可以删除工具反馈的上下文。两者关注不同边界。

## 11. 对RepoHarness项目一的条件化意义

映射日期2026-09-07、读取基线`681f22f0…`。已知项目采用miles/SGLang、外部coding harness及rh2接线，目标约30B-A3B、8×96GB；实际taskset、harness工具面与首训配置仍受[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)及权威决策约束。本节只做设计层映射，未重新审计rh2代码，也不把阅读变成更改首训方案的批准。

| 最直接的候选 | 什么条件下值得做 | 复用与新增边界 | 最小有辨识度的检查 |
| --- | --- | --- | --- |
| 区分压缩暴露和摘要直接训练 | 实际任务确实出现窗口耗尽，原生harness摘要影响后续行动 | 复用harness触发与执行；不先自建新memory平台 | 固定任务/峰值，分别测不开压缩、仅推理压缩、训练见过压缩、摘要加入loss；保留Single与Comp两个结果面 |
| 来源与分母验证 | 一次执行投影为多段，可能重复旧assistant/summary | 复用上游捕获；我方只验证精确输入、首次生成、复制和组身份 | 冻结每token loss做切段不变测试；比较全局token均值与原execution均值，别混同目标 |
| 跨段信用候选 | 已有可靠critic且长rollout比例足够，值得支付额外成本 | 优先通过后端扩展点实现；不因论文直接fork核心语义 | 小型标量参考核reward距离、非零critic差异和λ约定，再比较local vs corrected；同时测吞吐与held-out |

**支持的项目叙事**：真实harness会改变训练样本与可见状态，研究工程需要把表示、目标和评测连接起来；这不只是“接入一个compaction开关”。

**尚不支持的项目主张**：八卡一定更省、GRPO必须放弃、摘要越长越好、跨harness可靠接续已解决、终局分数即可证明全部训练mask正确。已有数据若很少触发压缩，先补足基线比接入完整CompactionRL更可解释；这是项目取舍，不是论文结论。

## 12. 旧稿修正、定位与检查状态

旧稿中trigger、k=2、双segment、50-step critic和主要compact分数与本次原文核验相符。需要收紧的地方是：补出106B的SFT初始化；复制token的mask属于数学身份推导而非已发布代码；保留Table3长窗口及无summary的反例；“相同context”改成相同peak；不能以旧日期对slime main的印象断言当前没有任何实现；SAO与本篇关系保留组合未知。

快速查阅：**trigger/resume → §4 / 原文p.4–5；分母/GAE → §5 / p.6；训练配置 → §6 / p.6–7；single/compact/long全表 → §7.2–7.3 / p.7–8；组件消融 → §7.4 / p.9；行为与曲线 → §7.5–7.6 / p.9–10；资产 → §9。**

本轮状态为**全文精读及作者自查完成，未独立审查、未训练复现**。没有可用的独立子agent工具，不填写虚构reviewer、线程UUID或effort记录。图表/公式、独立算例与实际修改见 [R14作者自查](reviews/14_R14_self_check_20260907.md)。后续独立审查可以直接定位上述关键点，不必重新猜测本轮读到哪里。

## 一手链接与固定资产入口

[ABS]: https://arxiv.org/abs/2607.05378
[P]: https://arxiv.org/pdf/2607.05378v1
[H]: https://arxiv.org/html/2607.05378v1
[P3]: https://arxiv.org/pdf/2607.05378v1#page=3
[P4]: https://arxiv.org/pdf/2607.05378v1#page=4
[P5]: https://arxiv.org/pdf/2607.05378v1#page=5
[P6]: https://arxiv.org/pdf/2607.05378v1#page=6
[P7]: https://arxiv.org/pdf/2607.05378v1#page=7
[P8]: https://arxiv.org/pdf/2607.05378v1#page=8
[P9]: https://arxiv.org/pdf/2607.05378v1#page=9
[P10]: https://arxiv.org/pdf/2607.05378v1#page=10
[SAO]: https://arxiv.org/html/2607.07508v1
[KIRA]: https://github.com/krafton-ai/KIRA/blob/652dacbf14d29ea93a83c496ee91e0e5ba286721/README.md#L1-L125
[REPRO]: https://github.com/ajing/compactionrl-repro/blob/c7af1ea7f07324cf20d74bf293b5caee7d110d2a/README.md#L1-L135
