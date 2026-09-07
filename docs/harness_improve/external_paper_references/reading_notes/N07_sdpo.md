# N07 SDPO：将环境反馈转成自蒸馏信号的完整方法、实验与实现边界

**SDPO 的关键不是再生成一条更好的教师答案，而是让同一模型在看到反馈后，重新评价学生已经采样的回答，并把条件分布差异变成训练信号。** 本篇覆盖 v2 全部 50 页，包括科学推理／工具调用、丰富代码反馈、逐题测试时权重更新，以及 A–F 附录。作者报告 Qwen3-8B 在其 LiveCodeBench v6 设置中从 GRPO 的 41.2% 提升到 48.8%；但这里训练与验证使用同一批 131 道题，按测试用例而非题目划分，不能等同未见题目或真实 SWE 泛化。SDPO 不需要额外强教师生成，却仍支付反馈条件化 forward、教师状态和损失计算成本；弱模型、误导反馈、不受约束的自教师以及部分能力回退是必须保留的限制。详见 §5–9。

导航：[来源与覆盖](#source) · [目标与梯度](#objective) · [科学／工具实验](#scalar) · [代码反馈与消融](#rich) · [测试时训练](#ttt) · [实现与项目判断](#implementation)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**论文 P。** Jonas Hübotter、Frederike Lübeck、Lejs Behric、Anton Baumann、Marco Bagatella、Daniel Marta、Ido Hakimi、Idan Shenfeld、Thomas Kleine Buening、Carlos Guestrin、Andreas Krause，*Reinforcement Learning via Self-Distillation*。首页机构为 ETH Zürich、Max Planck Institute for Intelligent Systems、MIT、Stanford。初版 **2026-01-28**，本次主读 **`2601.20802v2`，2026-02-16**；2026-09-07 查询 [arXiv 版本历史][P-abs]，最新仍为 v2。[PDF][P] / [HTML][H] / [作者代码][C0]。论文登记 CC BY 4.0；本文是带出处的中文分析，不分发原论文、图页或第三方代码副本。

**正式术语。** 论文使用 **Self-Distillation Policy Optimization（SDPO）**，并将问题设置称为 **Reinforcement Learning with Rich Feedback（RLRF）**。当前仓库 README 使用 Self-Distilled Policy Optimization 这一措辞；本文以论文名称为准。它不是另一个来源 N08 的 OPSD，也不是 E7 的 MOPD；不将这些名称合并成一种算法。

**代码 C。** 官方 `lasgroup/SDPO`，固定提交 **`7c457fc1b1f636ae794eb0362ba37d4743b06fbc`**（2026-07-01），基于 verl。实际查阅入口及符号见 §10。此版本晚于论文，未恢复历史实验逐 run 的原始代码 revision；代码事实不能倒填论文未披露的配置。

**项目映射。** RepoHarness 读取基线为 `miles-migration@f0eaf0df1f27bb08c6254edb0346e11cd6479a9c`。已读 [O01 的 Codex 质量复核](reviews/15_O01_codex_quality_review_20260907.md)、[笔记模板](NOTE_TEMPLATE.md)、[第三批准备中的任务 16](BATCH3_PLAN.md) 与 [当前状态简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)。没有独立 SDPO 旧稿需要覆盖；此前会话建议只作为问题线索，不作为论文证据。项目判断集中在 §12，不改代码、算法或任务集定案。

### 1.1 按原文建立的覆盖表

| 原文范围（PDF 物理页） | 实际内容与阅读深度 | 本文定位 |
| --- | --- | --- |
| p.1–3，摘要、§1 | RLRF 动机、三组主张、Fig.1–3、Table 1，全文 | §2、§5–7 |
| p.3–6，§2–2.3 | Algorithm 1、Eq.1–2、Table 2、Fig.4–5，计算与稳定化，全文 | §3–4、§8 |
| p.6–8，§3–3.3 | 科学／工具、选择规则、Table 3、Fig.6–7，全文 | §5 |
| p.8–13，§4–4.6 | LCB、模型尺度、信用粒度、教师、遗忘、混合目标、反馈消融；Fig.8–11、Table 4–6，全文 | §6 |
| p.13–16，§5–5.2 | discovery 定义、逐题训练、筛选和多轮基线、Fig.12–13，全文 | §7 |
| p.16–18，§6–7 | RL、反馈、蒸馏谱系；限制与未来工作，全文 | §2.3、§9、§11 |
| p.18–26，贡献、致谢、参考文献 | 检查尾部范围与引用身份；不逐篇扩读全部参考文献 | §1、§9 |
| p.27–28，Contents | 核目录；发现其部分标题／编号未随正文同步，不以目录替代实际覆盖 | 本节 |
| p.29，A.1 | frozen-prefix 与 sequence-level gradient estimators，Eq.5–8、Fig.14，全文 | §3.2 |
| p.30–31，A.2–A.4 | 教师正则、top-K+tail、PPO/TIS 的 logit 扩展，Eq.9–13，全文 | §3.3–3.4、§4 |
| p.32–33，B.1–B.2 | Proposition 2.1 与 trust-region teacher 推导，Eq.14–16，逐式阅读 | §3.2、§4.2 |
| p.34–35，C/C.1 | 价值函数、过程奖励、部分可观测、TTT；最大熵解释 Eq.17–19，全文 | §9.1 |
| p.36，D.1 | 个别任务最优超参数 Table 7、长度 Table 8，完整读取 HTML 与 PDF 提取文字；本轮此页截图反复失败 | §5.3–5.4 |
| p.37–39，D.2 | 难度、batch、Qwen2.5、稳定性、基线；Fig.15–18、Table 9，全文与图表核查 | §6.2、§6.7 |
| p.39–41，D.3 | 首次成功、初始教师、TTT 消融、19 题曲线；Table 10–11、Fig.19–20，全文 | §7 |
| p.42–45，E.1–E.3 | 硬件、Table 12–13、搜索网格、Listing 1–3 模板，全文 | §5、§8.1、§9.2 |
| p.46–50，F.1–F.4 | advantage 可视化、完整失败代码实例、错误反馈 Listing 4–6、set/dict 示例 Fig.21–22，全文 | §9.3 |

**图表核验边界。** 全文与所有附录已读；关键公式和除 p.36 外的表／图页已通过 PDF 截图目视核查。p.36 Table 7–8 的文字／数值可从原文 HTML 及 PDF 提取文本取得，但本轮不能宣称该页 raster 已成功查看。其他页也曾发生截图缓存错误，使用可用 PDF 入口补核；没有用旧摘要替代未取得内容。未取得本机 PDF/TeX，不表示作者未公开。详细过程见 [本次作者自查](reviews/16_N07_review.md)。

**编号约定。** 统一使用 PDF 的物理页与印刷编号。HTML 在 A.2 之后有重复多行公式计数，例如网页 Eq.14/15 实为 PDF Eq.12/13；网页 Eq.19–21 对应 PDF Eq.17–19。PDF Contents 中部分 A 节标题也过时，应按正文 A.1–A.4 阅读。作者致谢提及他人指出初始梯度估计中的错误；本次以 v2 为准，未进行 v1→v2 的完整差分，不推测旧版具体错误。

## 2. 核心问题与三个独立训练实验

### 2.1 从“是否成功”到“哪里可能错了”

普通二元 RLVR 把一次回答压成 pass/fail，组内全同分时 GRPO 的相对优势为零。代码执行实际还会返回异常类型、行号、失败输入及期望输出。SDPO 的假设是：模型即使暂时不能从头生成正确答案，也可能在看过这些信息后改变某些下一 token 的判断。把这种条件分布变化反向写入权重，有机会比只重复终局奖惩更有效。[P, §1–2, pp.1–4][P3]

实际学习循环是：学生在原始题目上采样 → 环境提供评分和反馈 → 对同一回答构造反馈知情的教师条件 → 教师只做概率评估 → 更新学生 → 继续采样。它**不要求常规每步都额外生成一条教师修复答案**。评价教师本身、对照 SFT 或多轮基线时，论文另外进行了教师／后续回答生成，不能混进标准 SDPO 的 sampling 成本。[P, Algorithm 1、Table 2, pp.4–5][P4]

### 2.2 不是一条“科学训练→代码→TTT”的串行模型流水线

| 独立实验 | 输入模型与对象 | 反馈／学习目标 | 验证对象 |
| --- | --- | --- | --- |
| §3 无丰富环境反馈 | Qwen3-8B、Olmo3-7B-Instruct；五类科学／工具任务分别训练 | 同题组内成功学生回答作为额外信息；主要用 JSD 自蒸馏 | 按题切分的域内泛化，avg@16，训练墙钟预算 |
| §4 丰富代码反馈 | 默认 Qwen3-8B，另做尺寸／模型家族消融 | LeetCode 风格执行反馈与同组成功解；主要 reverse-KL | 同一批 LCBv6 题目的更完整测试，avg@4；附加能力保持集 |
| §5 测试时自蒸馏 | 每个困难问题上运行 Qwen3-8B 的适应实验 | 单题失败反馈驱动实际参数更新 | 该题首次成功的概率与生成次数，不是未见下一题的零样本表现 |

模型是已有 checkpoint，不在此重新预训练。主 SDPO 路线没有追加“先从外部强教师 SFT”这一必要阶段；§4.4 的教师回答 SFT 是比较方法。三组实验的 divergence、EMA、学习率、mini-batch 和采样设置不同，见 §8；不能从“SDPO”名称推出唯一通用配方。[P, §3–5、Table 12][P42]

### 2.3 Table 1 的定位与边界

作者将 SFT/传统蒸馏、外部教师 on-policy distillation、RLVR、SDPO 按采样来源、信号稠密度和反馈来源比较。SDPO 的区别是**学生自己的轨迹 + 环境信息条件化的自教师**，而不是拥有一份更强专家权重。[P, Table 1, p.3][P3]

这张动机表不表示所有 SFT 必须由强教师生产，也不表示普通 RLVR 在任何设置下只有一 bit 信息；它针对本文选择的基线与问题定义。论文 §7 将长程／agentic 环境、大规模多任务和非可验证开放任务明确列为未来工作。因此，ToolAlpaca 的工具调用结果和 LCB 的程序生成结果，不是已在 Claude Code、真实仓库修复、GUI 或多 agent 任务上训练的证据。[P, §7, pp.17–18][P17]

<a id="objective"></a>
## 3. 目标、概率身份与梯度：不能只写“换一个 advantage”

### 3.1 同一组参数，两种不同的条件分布

为简洁，记学生在原始条件下的下一 token 分布为

$$p_{\theta,t}(v)=\pi_\theta(v\mid x,y_{<t}),$$

反馈知情分布为

$$q_{\theta,t}(v)=\pi_\theta(v\mid \operatorname{reprompt}(x,f),y_{<t}).$$

$x$ 是题目，$y$ 是学生已经采样的完整回答，$f$ 是环境反馈或该题的学生成功解，$v$ 遍历词表。基础 Eq.1 为

$$\mathcal L_{\mathrm{SDPO}}=\sum_t \operatorname{KL}\!\left(p_{\theta,t}\,\|\,\operatorname{stopgrad}(q_{\theta,t})\right).$$

方向是 **student→teacher 的 reverse KL**。stop-gradient 阻止教师被同一 loss 拉向学生、通过忽略反馈降低差异。后文可用 EMA／trust-region 替换 $q_\theta$，也可改用 JSD；这些是明确的实际变体，不应把 Eq.1 当成所有实验原样使用的 loss。[P, Eq.1、§2.3, pp.4–6][P4]

重要的是：教师的额外信息可以包含完整任务后果，但其被评分的 assistant continuation 仍是**原来那条 $y$**。没有把反馈文本或示范解直接当作新的学生 action token；也没有默认在额外条件下采一条修复解，再对它做 SFT。

### 3.2 Proposition 2.1、A.1 和 B.1：冻结什么决定“梯度等价”的范围

对于固定的 $x,f,y_{<t}$，B.1 将局部梯度写为

$$\nabla_\theta \mathcal L=\sum_t \mathbb E_{v\sim p_{\theta,t}}\left[\log\frac{p_{\theta,t}(v)}{q_{\theta,t}(v)}\,\nabla_\theta\log p_{\theta,t}(v)\right].$$

改写成最大化 policy-gradient 的符号时，隐式优势为

$$A^{\mathrm{SDPO}}_t(v)=\log\frac{q_{\theta,t}(v)}{p_{\theta,t}(v)}.$$

教师更倾向该 token 时为正，反之为负。论文的 GRPO 对照采用 $r_i-\mathrm{mean}(r)$，**不除以组内标准差**；它对该回答的所有采样 token 使用同一标量，而 SDPO 可以给一个位置上的多个候选 token 不同方向的信号。[P, Eq.2、§2.1, pp.4–5；B.1, p.32][P32]

B.1 的关键化简是 $\sum_v p(v)\nabla\log p(v)=\nabla\sum_vp(v)=0$。所以将 log-ratio 构成的优势 detach，可以保留这一局部梯度。它**不是**“自教师信号无偏等于真实任务 reward-to-go”的证明：反馈质量、教师判断、被采样前缀和后续泛化仍是经验问题。

A.1 将实际采用的目标进一步写清：

$$\mathbb E_{y\sim\operatorname{stopgrad}(\pi_\theta(\cdot\mid x))}\left[\sum_t\operatorname{KL}(p_{\theta,t}\|\operatorname{stopgrad}(q_{\theta,t}))\right].$$

这意味着采样得到的前缀分布在一次更新中作为固定数据。A.1 还给出对整条序列分布求导的估计器，其中增加“前缀出现概率的梯度 × 该位置 KL”的项（PDF Eq.7–8）。作者测试后没有发现可衡量收益，选择较简单的 per-token estimator。[P, A.1, Eq.5–8, p.29][P29]

Eq.2/B.1 针对上述 reverse-KL 目标；JSD 的分布梯度不能不加推导地直接替换成同一个 $\log(q/p)$ advantage。代码可直接计算 JSD 的梯度，这是另一种实现路径。

**两个“sequence-level”不要混淆。** A.1 的 sequence-level estimator 指是否对前缀访问分布求导；§4.2 的 sequence-level credit 消融则将逐 token 信号平均成整条回答的一个标量。它们不是同一个开关。

### 3.3 Top-K + tail：压缩的是词表分布，不是只取教师最喜欢的 K 个字

令 $S_t$ 是该位置**学生**概率最高的 K 个 token。分别保留学生、教师在同一 $S_t$ 上的概率，并将其余词表压成一个 tail bucket：

$$P_t=\big(\{p_t(v):v\in S_t\},\;1-\sum_{v\in S_t}p_t(v)\big),$$
$$Q_t=\big(\{q_t(v):v\in S_t\},\;1-\sum_{v\in S_t}q_t(v)\big).$$

对 $K+1$ 维分布计算 KL/JSD。教师必须在**学生选择的同一组 token ID**上给出概率，不能把两者各自 top-K 列按排名直接相减。保留 tail 也不同于把 top-K 内重新归一化；后者丢失了学生和教师给尾部多少总概率这一信息。[P, A.3, Eq.11, p.31][P31]

这是对分布的合并近似，不是全词表精确 KL；合并后看不到 tail 内部差异。本文用小型概率向量验证了归一化与一个 KL 合并示例，但没有复现作者大模型显存或精度实验。

文中有三种 K 口径：§2.2 举例 K=100；Table 12 的无丰富反馈实验 K=100，丰富反馈与 TTT 默认 K=20；§4.2 稠密信用消融的 logit-level 使用 K=100。**不能把消融参数写成默认代码主结果的参数。** “full-logit distillation”在代码中表示多候选分布目标，可启用 top-K，并不总是保存全部词表。

### 3.4 Off-policy 扩展：两种概率比、两种 clipping 与一个真实分母

A.4 定义：$\pi_\theta$ 为当前训练模型，$\pi_{\theta_{old}}$ 为生成批次对应权重在训练端的概率，$\pi^{rollout}_{\theta_{old}}$ 为高效推理引擎实际返回的概率。更新差异与训推差异分别是

$$w_{i,t}=\frac{\pi_\theta(y_{i,t}\mid x,y_{i,<t})}{\pi_{\theta_{old}}(y_{i,t}\mid x,y_{i,<t})},\qquad
w^{\mathrm{TIS}}_{i,t}=\frac{\pi_{\theta_{old}}(y_{i,t}\mid x,y_{i,<t})}{\pi^{rollout}_{\theta_{old}}(y_{i,t}\mid x,y_{i,<t})}.$$

论文 token-level 扩展（PDF Eq.12）是

$$\mathcal L_{token}=-\frac{1}{D}\sum_{i,t}\min(w^{\mathrm{TIS}}_{i,t},\rho)
\min\big(w_{i,t}A_{i,t},\operatorname{clip}(w_{i,t},1-\epsilon_{low},1+\epsilon_{high})A_{i,t}\big),\quad D=\sum_i|y_i|.$$

TIS 的上界截断用于训推偏差；PPO 双侧 clipping 用于当前／旧策略的更新幅度，且有 advantage 符号相关的 min。两者不能统称同一个“clip=2”。原文将归一化称为 fixed length normalization，但写出的分母是**该组实际回答 token 数之和**，不是固定最大 response length。[P, A.4, p.31][P31]

Eq.13 再显式对候选 token $v$ 求和：原来的概率权重变为 $\min(p_{old,t}(v),\rho p^{rollout}_{old,t}(v))$，再乘候选相关的 PPO surrogate。A.4 写可使用旧策略的 top-K，而 A.3 使用一般当前学生记号；多次更新时应保留这种支持集身份，不默认为相同。**作者随后明确说明实际 SDPO 实验用 token-level TIS，而不是逐 logit 的 TIS。**

这些是论文给出的广义扩展，不能据公式就声称其处理了任意陈旧轨迹、数百轮异步版本或多 harness。当前公开代码也没有原封不动实现 Eq.13 的 PPO min 形式；它采用 detached clipped ratio 乘 divergence，详见 §10.3。

## 4. 自教师、反馈、mask 与稳定化

### 4.1 Table 2 的原始 reprompt 逻辑

教师输入按原文包含：原始题目；可用时插入学生同题成功回答；无成功解且原回答失败时插入执行反馈；最后要求解决原题。教师 assistant 段放原回答，用来重算概率。Table 2 特别写到：**原回答本身成功时，可将它自己作为正确示范**。[P, Table 2, p.5][P5]

成功回答来源是当前学生，而不是外部专家。没有丰富反馈的 §3 中，若一组全失败，便不存在这一成功示范通道；SDPO 不会仅凭“更密集的 loss 名称”创造不存在的信息。丰富反馈情形则不同：全组失败时仍可能有可解释的错误输出，因而可以形成非零自蒸馏信号。

§4.6 对“加入原回答”的消融，指在教师**额外 prompt 中再放完整失败回答 $y$**。它不是取消教师评分时必需的 $y_{<t}$；也不表示去掉了原始 response 的 teacher-forcing 概率评估。完整失败文本可能令教师锚定原错误，见 §6.6。

当前代码默认排除“用自己的成功回答指导自己”，和 Table 2 存在区别；不要把现代默认 silently 代替论文模板。实际消费与 mask 见 §10.2。

### 4.2 三类教师状态：不能都叫 EMA

| 教师 | 参数／分布如何构造 | 额外成本与含义 |
| --- | --- | --- |
| 当前模型、无正则 | 直接用当前参数，但反馈不同；teacher 分支 stop-gradient | 当前一次更新不反传 teacher，不表示跨更新 teacher 不变化 |
| 冻结初始教师 | 初始 checkpoint 在反馈条件下评分 | 固定权重仍能因每条反馈不同给不同监督；不是固定答案库 |
| EMA | $\theta_T\leftarrow(1-\alpha)\theta_T+\alpha\theta_S$ | 增加教师参数状态；这一步权重平均不需要再自回归生成教师答案 |
| Trust-region | 初始与当前的**反馈条件化分布**做几何混合 | 通常需额外参考 forward；不是直接平均模型参数或概率 |

A.2/B.2 的 trust-region 目标限制 $q$ 偏离初始反馈教师 $q_{ref}$ 的 KL，并最大化 $\mathbb E_q[\log(q_{current}/q_{ref})]$。拉格朗日一阶条件得到

$$q^*(v)\propto\exp\big((1-\alpha)\log q_{ref}(v)+\alpha\log q_{current}(v)\big),\qquad\alpha=1/\lambda.$$

这与归一化后的 logit 插值等价。参照对象是**也看了反馈的 $q_{ref}$**，不是没有反馈的原始 policy $\pi_{ref}$；B.2 说后一种参照在其观察中更差，但未另列完整对照表。[P, A.2, Eq.9–10, p.30；B.2, Eq.14–16, pp.32–33][P33]

A.2 所说 EMA 不增加额外运行开销，针对其与另一种教师正则机制的比较；不能读成“SDPO 相对 GRPO 没有 teacher forward／参数存储开销”。同理，KL/JSD loss 的插值系数与教师 EMA 更新率是不同参数，即便当前代码都曾使用 alpha 字样也不能混用。

### 4.3 信号有效性与训练消费要分开

SDPO 不必依赖 outcome reward 的组内方差：同组全零 reward，只要反馈改变了教师分布仍可训练。但是没有有效反馈、没有成功示范，或者自教师根本不能利用信息时，密集目标不保证有用。

这也不取消环境与评分责任。正文的反馈示例包含错误行号、失败输入及 expected output，信息强度高于一句“失败”；这些来源是否可信、是否只使用训练允许的内容，决定学生被教会什么。论文没有完整研究误导反馈、可攻击 verifier、真实仓库评分隔离或异步错误恢复；§7 将反馈质量列为限制。**不能把 private grader 的任意信息自动当成可交付给学生或教师的训练材料。**[P, §7、F.3][P17]

<a id="scalar"></a>
## 5. 无丰富环境反馈：科学推理和工具调用的完整结果

### 5.1 任务、划分与基线选择

四个科学任务来自 SciKnowEval 的 L3 reasoning 子集：Chemistry、Physics、Biology、Materials，作者称本科级推理。ToolAlpaca 要求将 API specification 与用户要求映射成正确调用；不是在真实 API 服务中执行长程任务。论文按题做 train/test split，验证**域内未见题目**；本篇未给每个任务最终题数、完整题单或精确拆分比例。[P, §3.1, p.6][P6]

Qwen3-8B 与 Olmo3-7B-Instruct 分别训练。指标 avg@16 是每题 16 条回答的平均正确率，不是至少一条成功的 pass@16。报告“前 1h／5h 内达到的最高验证成绩”，墙钟计时排除初始化及 validation，因此不是预先冻结单一终点的盲测。

基线 GRPO 已加入不对称 clipping、去除 std normalization、训推 IS 修正，另比较每生成批只更新一次的 on-policy GRPO。通常 GRPO 每批 4 个 mini-batch 更新，SDPO 与 on-policy GRPO 每批一次。E.2.1 从学习率、mini-batch 和 divergence 网格按**所有任务×模型的 5h 表现**为各方法选择一份全局配置；D.1 另外给每任务／模型分别调参的结果。不能只把 baseline 当未经调优的 vanilla。[P, §3、E.2.1][P43]

### 5.2 Table 3：全局选择超参数，数值均为百分比

每个单元格是 **1h / 5h**；基座只有一个无训练值。原表没有给逐格误差条。

| 模型／方法 | Chemistry | Physics | Biology | Materials | Tool use |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3-8B 基座 | 41.2 | 59.2 | 30.8 | 58.9 | 57.5 |
| + GRPO | 65.9 / 74.5 | 63.8 / 72.7 | 35.1 / 59.9 | 74.3 / 77.1 | 64.9 / 67.7 |
| + GRPO on-policy | 63.3 / 63.4 | 63.6 / 63.6 | 49.8 / 49.8 | 73.9 / 74.1 | 60.2 / 65.7 |
| + SDPO on-policy | 73.2 / 80.9 | 66.6 / 75.6 | 50.6 / 56.8 | 72.1 / 78.4 | 68.0 / 68.5 |
| Olmo3-7B-Instruct 基座 | 22.8 | 37.7 | 16.2 | 36.7 | 39.3 |
| + GRPO | 39.7 / 56.7 | 55.3 / 63.3 | 35.6 / 55.8 | 70.9 / 75.0 | 56.4 / 65.0 |
| + GRPO on-policy | 51.4 / 57.5 | 62.7 / 62.7 | 49.8 / 49.8 | 73.3 / 73.5 | 56.8 / 60.6 |
| + SDPO on-policy | 68.0 / 80.0 | 59.9 / 66.1 | 48.0 / 52.8 | 73.7 / 79.1 | 60.8 / 62.1 |

来源：[P, Table 3, p.7][P7]。SDPO 不是每格最优：两模型 Biology 的 5h 均不及通常 GRPO，Olmo Tool use 也较低。论文引言汇总为 70.2% vs 66.6%；直接平均本表十个 5h 单元格却得到 SDPO 70.03%、GRPO 66.77%。未找到足以恢复引言聚合的权重／checkpoint 口径；**保留作者汇总与表格，不擅自改数，也不将差异当作已定位的错误。**

### 5.3 Table 7：每个模型／任务独立选择超参数

同样为 1h / 5h、avg@16。这个结果集合的选择自由度更大，不能与 Table 3 交叉挑最好格后再声称统一配方。

| 模型／方法 | Chemistry | Physics | Biology | Materials | Tool use |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen + GRPO | 65.9 / 74.5 | 62.9 / 74.5 | 35.1 / 59.9 | 74.3 / 77.1 | 61.7 / 68.1 |
| Qwen + on-policy GRPO | 52.2 / 71.6 | 62.9 / 74.8 | 49.8 / 49.8 | 73.3 / 75.8 | 61.7 / 68.1 |
| Qwen + SDPO | 73.2 / 80.9 | 70.6 / 80.6 | 50.6 / 56.8 | 72.1 / 78.3 | 56.4 / 68.5 |
| Olmo + GRPO | 53.1 / 67.7 | 55.3 / 63.3 | 35.6 / 55.8 | 73.8 / 78.1 | 56.4 / 65.0 |
| Olmo + on-policy GRPO | 47.1 / 65.4 | 62.7 / 62.7 | 49.8 / 49.8 | 67.9 / 74.4 | 56.0 / 61.3 |
| Olmo + SDPO | 68.0 / 80.0 | 60.3 / 71.4 | 48.0 / 52.8 | 75.3 / 79.2 | 57.3 / 62.5 |

来源：[P, D.1, Table 7, p.36][P36]，该页图片获取缺口见 §1。E.2.1 将 individually optimal 结果误指向 Table 3；D.1 的 Table 7 标题和说明明确是独立选择。本文按实际表内容解释，不沿用错误跳转。

### 5.4 速度、长度和具体行为

Fig.6 在 **Olmo3-7B-Instruct / Chemistry / 各任务适合的 GRPO 超参数**下报告 3 seeds，阴影是 **standard error（SEM）**；SDPO 约 50 分钟达到 GRPO 的 5h 准确率，作者据此称 6×。同图某些训练阶段 response length 相差可达 11×。这是一个任务和选定性能目标下的结果，不是所有任务、所有 checkpoint 的统一时间／token 减少。[P, Fig.6、§3.2–3.3, p.6][P6]

Table 8 则在**两方法都 on-policy**的设置下跨任务平均：

| 模型 | GRPO 平均回答 tokens | SDPO | 原文缩短倍率 |
| --- | ---: | ---: | ---: |
| Qwen3-8B | 820.8 | 255.8 | 3.2× |
| Olmo3-7B-Instruct | 1095.4 | 343.9 | 3.2× |

来源：[P, Table 8, p.36][P36]。不要拿它与 Table 3 通常 GRPO 的四次 mini-update 混成同一性能条件。

Fig.7 选取 Qwen3-8B 第 50 步的化学题：GRPO 用 5,549 tokens，重复推理后答错 B；SDPO 用 764 tokens 答对 C。作者展示循环、反复“Wait”等行为，并将较短推理归因于细粒度信用。**这是一对定性样例，不是对思维忠实性、所有解法长度或通用效率的因果证明。**[P, Fig.7, p.8][P8]

<a id="rich"></a>
## 6. 丰富代码反馈：LCBv6 设置、消融与负结果

### 6.1 首先固定比较对象：同题训练，按测试用例验证

§4 使用 **2025 年 2–5 月的 LCBv6 子集，共 131 道题**。从原 private tests 随机取 50% 作为训练可用的 public tests；论文称以 private tests 验证。**没有将这 131 道题划成训练题与未见验证题。** 当前公开 `data/split_tests.py` 更明确：训练 JSON 保留一半 tests，验证 JSON 保留原完整 tests，因此验证还包含已经暴露的那一半，而不是严格互斥的剩余半套，详见 §10.1。[P, §4 脚注 5, pp.8–9][P9]

默认 Qwen3-8B，non-thinking，验证每题平均 4 条回答，3 个训练 seeds。程序在 LeetCode 风格的执行环境中评分；反馈包含编译／运行错误、失败输入、预期结果，不是模型可以自己任意查询整个 hidden grader 的真实 SWE agent 场景。

| 主结果 | LCBv6 (%) | 解释 |
| --- | ---: | --- |
| Qwen3-8B 基座 | 27.9 | 无本专项训练 |
| + GRPO | 41.2 | 作者改进的 RLVR 基线 |
| + SDPO | 48.8 | 比 GRPO 高 7.6 个百分点 |
| Claude Sonnet 4，原文引用榜单 | 40.5 | 公共 leaderboard，非本篇同题适应训练协议 |
| Claude Opus 4，原文引用榜单 | 39.7 | 同上 |

来源：[P, Fig.1、§4、Table 5][P1]。作者称达到 GRPO 最终准确率所需 generations 减少 **4×**。这不是更新次数、GPU-hour 或所有任务上四倍效率；外部模型成绩也不能支持“8B 通用 coding 能力超过 Claude”的表述。SDPO 与本文 GRPO 的对照仍有价值，因为它们共享本文的数据／反馈设置。

### 6.2 模型强弱与任务难度并非同一个变量

Fig.8 比较 Qwen3-0.6B、1.7B、4B、8B 在 **step 80** 的最终验证，3 seeds 的 **SEM**。较大模型 SDPO 相对 GRPO 的差距更明显，0.6B 收益很小。目视图中的 1.7B 约 29%→33%、4B 约 40%→45%；仅作量级帮助，不是另有精确数表。8B 的 41.2→48.8 由正文与 Table 9 支持。[P, Fig.8, p.9][P9]

D.2 的 Fig.17 将 Qwen2.5-Instruct 与 Qwen3 比较，但统计量变成**训练期间平均准确率**：Qwen2.5 到 step 65，Qwen3 到 step 80。Qwen2.5-1.5B 中 SDPO 低于 GRPO，3B 大致相当，7B SDPO 较好。正文 §4.1 将中间模型写成 Qwen2.5-8B，而图轴是 **3B**；本稿保留该源文不一致，不新增一个“8B 实验”或用外部知识替作者修正。[P, Fig.17, p.38][P38]

Fig.15 使用 LCB 自身 easy/medium/hard 标签，统计 **到 step 80 的训练期平均准确率**，误差是 3 seeds 的 **standard deviation（SD）**：

| 难度 | GRPO (%) | SDPO (%) | 算术增益 |
| --- | ---: | ---: | ---: |
| Easy | 90.1 | 91.7 | +1.6 pp |
| Medium | 37.8 | 46.6 | +8.8 pp |
| Hard | 11.6 | 18.9 | +7.3 pp |

图中的约 +2%/+23%/+63% 是**相对增幅**，不是百分点；也不是 §5 根据基座 pass@64 定义的 hard/very hard 分组。[P, Fig.15, p.37][P37]

### 6.3 丰富反馈与信用粒度：两个因素都有证据

§4.2 明确区分三种目标：logit-level 在学生 top-100 候选上分配信用；token-level 原文措辞是“每个位置最可能的 token”；sequence-level 将原生成各 token 的 SDPO advantage 平均为一个标量。三者都可以利用丰富反馈，只有信用粒度不同。[P, §4.2, p.10][P10]

Fig.10 左显示 logit > token > sequence > GRPO；约 20K generations 附近，图上分别接近 49%、48%、46%、41%（**目视近似**，不是精确终点表）。误差为 3 seeds 的 SEM。结果支持“只改善反馈、仍用序列标量也有收益；更细信用另有增益”，不支持所有环境都必须全词表蒸馏。[P, Fig.10, p.11][P11]

**实现边界。** 当前公开 non-full-logit 分支计算的是实际 `responses` 中采样 token 的 log-ratio，不是另取 argmax token。本文没有运行论文的该项 ablation 或恢复其历史脚本，因此不将现有实现静默改写成原文“most likely”的精确复现。Fig.4/9 的代码边界修正示例说明教师能局部改变某些 token 偏好，但不证明 log-ratio 等价于真实的因果首次错误标签。

### 6.4 教师会改善，但不受约束的自举会发散

Fig.10 右为了分析教师，额外生成反馈条件下的回答，报告当前训练 batch 的正确率与 5-step rolling average；学生最终点来自 step 80，误差是 3 seeds 的 **SD**。学生后来超过初始教师，说明最终成绩不必受初始 teacher 的一次性生成正确率约束；不代表模型能在没有可靠外部信息时无限自举。[P, §4.3、Fig.10, pp.10–11][P11]

Table 4 对正则机制比较的是 **到 step 90 的最高／平均准确率，3 seeds 的 SEM**：

| 教师 | 最高准确率 (%) | 期间平均 (%) |
| --- | ---: | ---: |
| 当前教师，无正则 | 36.1 ± 1.6 | 29.8 ± 1.3 |
| 冻结初始反馈教师 | 48.8 ± 0.7 | 44.4 ± 0.2 |
| Trust-region，α=0.01 | 50.6 ± 0.9 | 45.6 ± 0.2 |
| EMA，α=0.01 | 49.3 ± 0.3 | 45.3 ± 0.2 |

原文明确无正则教师的训练最终 diverges。冻结教师已经有效，缓慢更新／分布约束进一步改善。因此既不能说“共享当前模型无需额外稳定机制”，也不能说“必须不断更新教师才有任何收益”。表里的 48.8 与主结果同数值，但实验条件及 checkpoint 口径不同，不据巧合合并。[P, Table 4, p.10][P10]

### 6.5 能力保持与教师回答 SFT：相对退化较小，不是完全不遗忘

Table 5 的 final checkpoint 结果如下；Avg 只平均四个 **holdout** 指标，不包括 LCB。

| 方法 | LCBv6 | IFEval | ArenaHard-v2 hard | ArenaHard-v2 creative | MMLU-Pro | Holdout Avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 基座 | 27.9 | 83.9 | 14.0 | 13.7 | 62.5 | 43.5 |
| SFT on self-teacher | 42.7 | 83.7 | 11.2 | 8.9 | 61.9 | 41.4 |
| GRPO | 41.2 | 82.2 | 12.0 | 10.8 | 62.3 | 41.8 |
| SDPO | 48.8 | 83.2 | 12.3 | 11.1 | 62.9 | 42.4 |

来源：[P, Table 5、§4.4, p.11][P11]。标题宣称避免 catastrophic forgetting；实际表明 SDPO 相对 SFT 和 GRPO 有较好的收益—保持折中，**但 holdout 均值仍比基座低 1.1 点**，IFEval 与两项 ArenaHard 也下降。不应推广成“on-policy 天然不遗忘”。ArenaHard 为 LLM-judged benchmark，本篇没有逐项公开本次评测的 judge revision、完整运行配置与误差条。

SFT 基线使用反馈教师生成的成功回答，论文说加入学生原始成功回答反而较差，因而报告 teacher-success-only。它每步需要学生和教师都生成，作者称相同 step 下 generations 为 SDPO 的 2×。Table 5 caption 指向 **initial self-teacher**；正文更一般地称 self-teacher。保留这个来源限定，不把它描述成已证明的最强动态 repair-SFT 配方，也不能据“同 step”推定两者总 token、墙钟或教师成本已完全匹配。

### 6.6 混入 GRPO，以及不同反馈组合

Eq.3 以 $\lambda A^{GRPO}+(1-\lambda)A^{SDPO}$ 混合优势。Fig.11 使用 **λ=0.9**，即权重主要来自 GRPO，报告 step 80、3 seeds 的 SEM。混合明显帮助弱 Qwen3-0.6B，相对纯 SDPO 则在较强模型略降。作者解释为弱模型的 self-teacher 不可靠、scalar 信号可稳定它；强模型时 scalar 信号可能有害。后一项是**该固定 λ 和实验条件下的解释**，不是“任何 GRPO 辅助必然损害大模型”。[P, Eq.3、Fig.11, p.12][P12]

Table 6 比较反馈来源，到 step 60，误差均为 **3 seeds 的 SD**：

| 教师额外信息 f | 初始教师生成正确率 (%) | Same output (%) | SDPO 学生正确率 (%) | 平均 entropy |
| --- | ---: | ---: | ---: | ---: |
| 仅环境 output | 32.5 ± 0.5 | 13.7 ± 0.6 | 39.9 ± 1.1 | 0.40 ± 0.0 |
| 仅 own solution | 42.4 ± 1.0 | 12.1 ± 0.7 | 42.6 ± 1.3 | 0.41 ± 0.0 |
| output + own solution | 42.5 ± 1.2 | 10.1 ± 0.2 | 48.3 ± 1.4 | 0.38 ± 0.0 |
| 再加入完整原始失败回答 y | 39.3 ± 0.8 | 30.0 ± 0.9 | 44.5 ± 1.3 | 0.23 ± 0.0 |

来源：[P, Table 6, p.13][P13]。`own solution` 是学生同题采样成功解，不是 gold reference。`Same output` 指教师新回答得到**与原失败回答相同的环境输出**，不是文本逐字相同。两种反馈互补；简单加上全部失败文本反而提高锚定、降低 entropy 与成绩。因此“更多 hindsight 信息总更好”不受支持。这里语法模板变动被作者称为不敏感，但没有充分支持任意长度、任意错误日志或长期上下文管理都不敏感。

### 6.7 D.2 的其余消融和训练稳定性

**Fig.16** 比较 question batch size 4/8/16/32 与每题 rollouts 4/8，横轴主要是累计 generations。多种配置趋势相近，说明该任务上不只一个 batch 设置可用；不代表任意微批、DP 分片或有效样本比例下梯度都数值等价。[P, Fig.16, p.37][P37]

**Fig.18** 给出 Qwen3-8B/LCB 的 loss、entropy、gradient norm、response length。图示 loss 从较高初值下降，entropy 未在主配置中迅速归零，gradient norm 有波动，回答长度维持数百 token 量级（约 700–900，**目视范围**）。这些是特定配置的健康观察；不能抵消 Table 4 已报告的无正则发散，也不构成长期稳定性保证。[P, Fig.18, p.38][P38]

**Table 9** 对通常 GRPO、只训练高熵 token、GSPO、CISPO 与 SDPO 的比较为 **step 80 / 到 step 80 期间平均，3 seeds 的 SD**：

| 方法 | Step 80 (%) | 期间平均 (%) |
| --- | ---: | ---: |
| GRPO | 41.2 ± 0.8 | 38.2 ± 0.0 |
| GRPO + only high-entropy tokens | 37.8 ± 2.2 | 35.9 ± 0.1 |
| GSPO | 40.1 ± 2.3 | 37.7 ± 0.1 |
| CISPO | 41.2 ± 1.8 | 37.8 ± 0.1 |
| SDPO | 48.8 ± 0.6 | 43.8 ± 0.0 |

来源：[P, Table 9, p.39][P39]。表支持本设置下不是随便换一个常见 RLVR 目标就得到相同收益，且只训练高熵 token 的基线更差；这不是提高 entropy bonus 系数的消融。±0.0 是原表舍入值，不是确定性运行或零真实方差；本文未逐一审计全部基线代码来认证其达到各算法最优。

<a id="ttt"></a>
## 7. 测试时自蒸馏：逐题更新权重，而非普通多轮推理

### 7.1 指标与三个比较对象

定义首次成功的 trial 编号为 discovery time，Eq.4 的 $\mathrm{discovery}@k=\Pr(\text{前 }k\text{ 次至少成功一次})$。对固定模型的独立采样，它等于通常 pass@k；对参数或上下文随反馈变化的算法，它允许 trials 非独立同分布。[P, §5、Eq.4, p.13][P13]

| 方法 | 每次失败后改变什么 | 额外计算 |
| --- | --- | --- |
| Best-of-k | 不改权重，不积累反馈；从基座反复独立生成 | 原文用 2,944 条独立 rollout 估计 pass@k |
| Multi-turn | 把过去反馈放进上下文，保留权重 | 40K context 中 prompt 上限 32K，FIFO 删除最早反馈；选择只留反馈这一较强模板 |
| Test-time SDPO | 用当前题的反馈更新模型权重，再生成 | 教师 forward、反向／优化器、教师状态；默认每轮 1 题×16 rollouts |

Fig.12 的“batch size 1”指单题适应的概念，不是实际所有更新都只用一条 rollout。正文与 Table 12 的采样 batch 是 16。所谓将交互历史压进权重，是机制解释；它不是已验证的跨用户长期记忆、任意 session 恢复或低成本 checkpoint 系统。[P, §5.1、Fig.12, pp.13–14；Table 12][P14]

### 7.2 难题集合带有明确的事后可解性筛选

先按 Qwen3-8B 的能力定义 **hard：pass@64<0.5；very hard：pass@64<0.03**。再仅保留三种方法中**至少一种**在 512 steps、5 seeds 内找到过一次解的题，得到 **19 hard，其中 9 very hard**。D.3 另说明删除 Q9，因为环境中的 rounding 验证问题会拒绝逻辑正确的解。[P, §5.1, p.14；D.3, p.39][P39]

这里不是从所有 LCB hard 题中无条件估计总体可解率。筛选利用了被比较方法的成功情况，会偏向这组三种方法至少能解决的题；不能把之后 78%/53.2% 的数值当作整个真实困难问题分布的绝对能力。标签也与 Fig.15 的 LCB 官方难度不同。

### 7.3 主结果与“3×”的真实含义

Fig.13 比较累计生成预算，5 seeds／题，报告均值与 bootstrap **90% CI**：

| 题集 | SDPO discovery@2750 | Best-of-k | Multi-turn |
| --- | ---: | ---: | ---: |
| Very hard（9 题） | 53.2% | 41.5% | 35.6% |
| Hard（19 题，含上述 9 题） | 78.0% | 72.3% | 68.4% |

在 very hard 上达到约 **22% discovery** 的交叉点，SDPO 所需 generations 约少 3×；hard 上达到约 **67%** 时约少 2.4×。这些是同一目标成功概率的样本效率，不是总体均值加速，也没有比较三者全部 GPU、反向、teacher 或 token 成本。[P, Fig.13、§5.2, p.15][P15]

多轮上下文达到上限的时点，原文给 hard 837±466 steps、very hard 1007±349 steps，作为高预算收益减缓的一种可能解释；该 ± 的统计定义在相邻正文未进一步说明。不要直接将其当作已隔离的上下文截断因果消融。

### 7.4 Table 10：逐题平均首次成功，不隐藏不利结果

每值为 generations；未成功情况在 **2750** 预算处截断参与平均，`≥2750` 保留原表符号。星号为 very hard。下面不重抄由比值舍入的 Speedup 列，避免把 censor 后的比值解释成未截断期望。

| Q | SDPO | Best-of-k | Multi-turn |
| --- | ---: | ---: | ---: |
| 1 | 104 | 98 | 59 |
| 3* | 1987 | ≥2750 | ≥2750 |
| 10* | 938 | ≥2750 | 1706 |
| 43 | 111 | 109 | 111 |
| 46* | 1852 | 1466 | 1315 |
| 59 | 172 | 123 | 76 |
| 69 | 280 | 134 | 134 |
| 74* | 1948 | 1466 | 2405 |
| 86 | 85 | 421 | 335 |
| 91* | 1360 | ≥2750 | 2384 |
| 92* | 1575 | ≥2750 | 2203 |
| 95* | 1948 | 1466 | 1794 |
| 100 | 277 | 294 | 1596 |
| 103* | 2246 | ≥2750 | 2210 |
| 111 | 85 | 95 | 39 |
| 120 | 24 | 327 | 70 |
| 125* | 1795 | 1466 | 2320 |
| 127 | 28 | 368 | 61 |
| 129 | 168 | 173 | 104 |
| Hard 平均 | 894 | 1145 | 1141 |
| Very hard 平均 | 1739 | 2180 | 2121 |

来源：[P, Table 10, p.39][P39]。按表中精确均值算，Best-of-k/SDPO 约为 **1.281×、1.254×**，原表 Speedup 列写 1.3×、1.2×。保留原始均值与原文舍入，不把任一值改写成“平均 3×”。多个题上 best-of-k 或 multi-turn 更快；Fig.20 也显示某些题的固定预算发现概率不利于 SDPO，均值优势不等于逐题支配。

Q3 的“321 attempts 后首次发现”是某次观察到的第一次成功，约经历 20 轮×16 条；Table 10 的 1987 则是跨运行且带 censor 的均值，两者不冲突。作者在这组有限预算下只有 SDPO 找到 Q3，不能推成基座真实概率严格为零。

### 7.5 初始教师、batch 与多轮模板的附录结果

Table 11 测初始模型仅通过一次反馈 reprompt 后的生成正确率。在 19 题中 **15 题为 0.00%**；非零项是 Q43 6.25%、Q69 3.12%、Q127 1.23%、Q129 0.06%。这些是有限采样估计，不是数学上的零支持。它支持“初始教师不能直接可靠给整题答案，但局部信号仍可能有效”，不支持“不需要任务信息或有效反馈”。[P, Table 11, p.40][P40]

Fig.19 左比较 batch 8/16/32：较小 batch 可能较早发现，较大 batch 在后期更稳，默认取 16。右图在**部分 hard 题**上比较“只累积反馈”和“完整 attempts+feedback”，前者更好。这里是上下文模板基线优化，不是 SDPO 另一种优化器。Fig.20 完整列出 19 题的 discovery 曲线、5 seeds 的 90% CI；Q46/74/95/125 等题提醒不能只展示 Q3/Q120/Q127 的突出案例。[P, Fig.19–20, pp.40–41][P41]

## 8. 可恢复的训练配方、计算与未计入成本

### 8.1 Table 12：三个 SDPO 配方并列

| 参数 | §3 无丰富反馈 | §4 丰富反馈 | §5 TTT |
| --- | --- | --- | --- |
| 模型 | Qwen3-8B / Olmo3-7B-Instruct | 默认 Qwen3-8B | Qwen3-8B |
| Thinking | False | False | False |
| 原始 prompt 上限 | 2048 | 2048 | 2048 |
| response 上限 | 8192 | 8192 | 8192 |
| Question batch | 32 | 32 | 1 |
| Mini-batch（原表） | 32 | 1 | 1 |
| Rollouts / question | 8 | 8 | 16 |
| 推理后端 / 训练 temperature | vLLM / 1.0 | vLLM / 1.0 | vLLM / 1.0 |
| Validation n / temp / top-p | 16 / 0.6 / 0.95 | 4 / 0.6 / 0.95 | — |
| Top-K | 100 | 20 | 20 |
| Divergence | Jensen–Shannon | Reverse KL | Reverse KL |
| Advantage clipping | — | — | 5.0 |
| Teacher EMA update rate | 0.05 | 0.01 | 0.01 |
| Rollout IS 上限 | 2 | 2 | 2 |
| Optimizer | AdamW | AdamW | AdamW |
| 恒定 lr | 1e-5 | 1e-6 | 1e-6 |
| Warmup steps | 10 | 0 | 0 |
| Weight decay / grad clip norm | 0.01 / 1.0 | 0.01 / 1.0 | 0.01 / 1.0 |

来源：[P, Table 12, p.42][P42]。Table 12 的 prompt 2048 是原题输入限制，不是额外 reprompt 后整个教师序列的总限制；现代配置还提供单独 `max_reprompt_len`。mini-batch=1 的单位也不能由字段名猜为“一条全局 rollout”，需经过实际训练框架的 n 和 DP 转换，见 §10.4。

Table 13 给 §3 GRPO 的 question batch=32、n=8，通常 mini=8/on-policy mini=32；lr 通常 1e-6/on-policy 1e-5，ε-high=0.28、rollout IS clip=2、KL coefficient=0、warmup=10、wd=0.01、grad clip=1，其余输入／生成／validation 设置与该组可比。不要把此表未经核对复制成所有 LCB 对照的唯一配置。[P, Table 13, p.43][P43]

E.2.1 的搜索网格：GRPO 搜 lr∈{1e-5,1e-6}、mini∈{8,32}；on-policy GRPO 固定 mini32；SDPO 额外搜 forward-KL/JSD。Table 3 是每方法统一配置，Table 7 是每模型／任务选择。研究结论中已经包含这些 tuning 成本与验证选择自由度，但全文没有给全部搜索 GPU-hour。

### 8.2 硬件与局部时间开销

E.1 称全部实验运行在**单节点 4×GH200，总 378GB VRAM（沿用作者口径）**；NVIDIA PyTorch 容器 `nvcr.io/nvidia/pytorch:25.02-py3`，CUDA 12.8、PyTorch 2.7.0、FSDP2、verl、vLLM。[P, E.1, p.42][P42]

§3 每次 run 加上初始化和 validation 约 6 小时；4 卡×6 小时约 **24 GPU-hours/run** 是按描述的算术换算，不是整篇所有实验总成本。它也不能推算本项目 30B-A3B、长轨迹、PCIe 无 NVLink 的具体时间。

Fig.5 在 micro-batch=2 的设置比较单步用时：不计代码环境时 SDPO 增加约 **17.1%**，计入环境后约 **5.8%**。图注明确实色／浅色的环境口径；增加 teacher forward 的成本可能被昂贵执行稀释，这与“没有额外 sampling”相容，却不是零成本。[P, Fig.5、§2.2, p.5][P5]

| 成本组成 | 已披露 | 本次不能补出的内容 |
| --- | --- | --- |
| 模型生成 | 每组 n、最大长度；主结果以 generations 或训练墙钟比较 | 完整累计 tokens、每个 checkpoint 的总生成与失败费用 |
| 教师评分 | 一次 feedback-conditioned 概率计算；top-K+tail 减少 logits 储存 | 单独 teacher GPU-hours、长 prompt 前缀缓存收益、30B MoE 可用吞吐 |
| 教师状态 | EMA 需独立参数；trust-region 的参考分布需额外计算 | 所有运行的峰值显存、offload 与通信开销曲线 |
| 执行与反馈 | 代码运行；部分图比较含／不含环境时间 | 隔离方式、完整 CPU-hours、按题 timeout 与异常处理成本 |
| 训练 | 硬件、优化器、主要超参、单 run 描述 | 全部网格／seeds／失败实验总费用 |
| 评测 | avg@16/4、若干 repeats、外部保持集、TTT 预算 | 完整 judge/API 账单、所有权重与结果 manifest |

## 9. 理论联系、模板与定性附录：不能遗漏的非主表内容

### 9.1 §6、Appendix C 与最大熵解释

作者把相关工作分为：从 scalar reward 估计信用的 RLVR；从环境文本、反思或纠错中学习；外部教师蒸馏；同一模型有／无额外上下文的自蒸馏。本文不重新全文阅读这些引用，也不凭相关工作段落裁定并行来源 OPSD/MOPD 的完整方法。

Appendix C 进一步区分价值网络与 Monte Carlo 估值、显式过程奖励模型、部分可观测信息，以及 test-time training。SDPO 的反馈知情分布既不是另训 critic，也不是对每一步调用外部 PRM；作者强调其没有这类额外模型的训练负担。该比较是本文方法定位，不证明在真实 agent 长程信用问题上胜过精确 critic 或 process verifier。[P, §6, pp.16–17；C, pp.34–35][P34]

C.1 的最大熵视角（PDF Eq.17–19）从 $\mathbb E_\pi[\sum_t r_t]+\lambda H(\pi)$ 出发，在原文的均匀响应先验等假设下得到 Gibbs 目标 $\pi^*\propto\exp(\sum_t r_t/\lambda)$。令隐式 reward 为 $\log q(y_t\mid x,f,y_{<t})$、λ=1，就得到朝反馈教师分布拟合的解释。[P, C.1, p.35][P35]

**边界。** 这里的“reward”是由教师定义的隐式信号，不是已证明等于真实任务效用。C.1 的序列分布解释与 A.1 的实际 frozen-prefix 梯度也需要分开；不能借最大熵术语为实际近似补上一项已经省略的前缀访问梯度。

### 9.2 E.3 的任务格式

科学选择题模板明确要求 `<reasoning>...</reasoning>` 与 `<answer>A/B/C/D</answer>`，并另提示逐步思考。因而 Table 12 的 Thinking=False 不表示回答里没有显式推理文本。Tool use 模板提供工具名、功能、参数、返回结构，并要求 Thought / Action / JSON Action Input。文中的 Axolotl 查询仅是格式例子；不是通过这些真实服务训练长期工具交互。[P, Listing 1–3, pp.44–45][P44]

论文没有提供一套完整真实 coding CLI harness 的 system/developer prompt、权限、compaction 和多进程工具运行协议。其程序生成模板要求输出满足规范的 Python code block，和修改已有仓库工件仍是不同任务面。

### 9.3 F.1–F.4 的全部例子与可解释范围

**F.1 / Fig.21（p.46）。** Olmo3-7B-Instruct 的 Chemistry batch 中，各行展示不同生成回答的前段；GRPO 同一行颜色近乎恒定，SDPO 随位置变化。色条范围并不相同（SDPO 约 −15 到 3，GRPO 约 −1 到 1），不同颜色深浅不能直接当成算法梯度强弱的量化比较。它支持信号形式不同，不证明这些位置都是经独立 oracle 确认的真实原因。[P, Fig.21][P46]

**F.2（pp.47–48）。** `maxActiveSectionsAfterTrade` 的完整二进制字符串题、长回答与代码，最后因对字符列表调用 `sum(temp)` 导致 TypeError，反馈定位到行 48、输入 `"11000"`。本例显示实际执行反馈可以指向局部类型错误；原文这里展示的是失败轨迹，没有给该例后续修复通过全部测试的独立结果。也不能认为修掉 TypeError 就证明原算法复杂度和逻辑均正确。[P, F.2][P47]

**F.3 / Listing 4–6（pp.49–50）。** Wrong Answer 反馈包括具体输入、实际输出和 expected output；MemoryError、IndexError 给堆栈、位置和最后执行输入，其中过长输入截断。因此“丰富反馈”同时可能包含错误类型和相当强的答案约束，而不是只有退出码。迁移到 SWE 时应按训练允许的反馈粒度设计，不能笼统称这些信号全部免费且不会泄漏验证信息。[P, F.3][P49]

**F.4 / Fig.22（p.50）。** 从用 `set()` 去重到用保持插入顺序的 `dict()` 去重，图展示反馈如何改变局部候选概率。caption 描述可视化里的 teacher top-K，但算法 A.3 的近似词表是 student top-K；可视化的候选展示不应代替真实训练支持集定义。本例解释局部概率监督，不是长程恢复或跨工具迁移的实验。[P, F.4][P50]

<a id="implementation"></a>
## 10. 官方代码定点核查：从反馈构建到实际 loss

以下全部固定到 **`lasgroup/SDPO@7c457fc1b1f636ae794eb0362ba37d4743b06fbc`**，只做静态查阅。目标是弄清论文关键机制的真实入口、张量与消费，不进行整个 verl fork 的泛化 bug 审计。没有执行真实 GPU、代码沙箱、模型生成或训练；不将当前文件存在认定为历史实验已经可完整重放。

| 来源 | 实际路径／符号 | 核查问题 |
| --- | --- | --- |
| C0 | [README.md][C0] | 官方入口、数据与训练步骤、已公开资源和兼容限制 |
| C1 | [experiments/rich_feedback/run_sdpo.sh][C1] | LCB 实验 override、n、mini、top-K、EMA 和资源声明 |
| C2 | [verl/trainer/config/sdpo.yaml][C2] | 基础配置、teacher reprompt 长度、实际 policy loss mode |
| C3 | [verl/trainer/ppo/ray_trainer.py][C3]：`_collect_feedback`、`_collect_solutions_by_uid`、`_get_solution`、`_maybe_build_self_distillation_batch` | 反馈和示范来源、UID、teacher 输入与 row mask |
| C4 | [verl/workers/actor/dp_actor.py][C4]：`TrustRegionTeacher`、`_forward_micro_batch`、`update_policy`、`_update_teacher` | top-K 身份、stop-grad、micro/mini 更新、教师状态 |
| C5 | [verl/trainer/ppo/core_algos.py][C5]：`compute_self_distillation_loss`、`agg_loss` | 实际 KL/JSD、tail、ratio、mask 与分母 |
| C6 | [data/split_tests.py][C6]：`sample_tests`、`main` | 50% tests 与完整验证 tests 的真实关系 |
| C7 | [verl/workers/fsdp_workers.py][C7]：`ActorRolloutRefWorker.__init__` 的 config normalization | mini-batch 在 n、DP、SP 下的实际单位 |

### 10.1 实验入口与数据划分确证

C1 指定 Qwen/Qwen3-8B、question batch32、n8、lr1e-6、mini1、top-K20、divergence α=1（reverse KL）、EMA update=.01、warmup0、validation n4。它覆盖 C2 中默认 mini32 等值。Slurm 的 1 节点／4 GPU／12h 是**作业资源与上限**，不等于 run 实际执行12h，也不等于本篇所有条件的总成本。

C6 固定 NumPy seed0，按每题 tests 数的50%随机抽取，至少保留1个。它先把完整输入 dataset 存成 `test.json`，再把删减 tests 的版本存成 `train.json`。题目本身不变，验证 tests 包含训练暴露 tests。**这不是题目级的 train/test split，也不是用原 tests 的互斥两半评测。** 此事实可解释论文“public subset of private”的具体复现方式，但未确认每个历史 run 都使用这一 commit 的脚本。

### 10.2 Producer：teacher prompt 与原始 response 怎样绑定

C3 按 `uid` 收集 reward 总和达到阈值的成功回答；反馈只接受非空字符串。选择同 UID 的第一条可用成功回答，代码注释称其等效随机，但本轮没有验证排序如何产生，不把它宣称成显式均匀采样。

`dont_reprompt_on_self_success=True` 时排除当前回答自身；可选去除示范 `<think>...</think>`。若设置 `environment_feedback_only_without_solution=True`，已经取得成功示范时不再加入环境反馈。这些都是输入条件的真实变化，而不只是 loss 配置。

`_maybe_build_self_distillation_batch` 对最后的用户题目构造 reprompt，并保留更早消息；对教师 prompt 应用 chat template 后，**直接拼接原始 `responses` token tensor**。示范内容可由 decode 得到，但被监督的目标回答没有重新生成。teacher attention mask 和 position IDs 重新构建，以适应更长的前缀；这才是源文“重新评分同一回答”的关键实现。

`self_distillation_mask` 在样本层表示该行确实拥有成功示范或实际使用的 feedback；随后与 response mask 相乘。无 feedback、无解的行不进入 SDPO 目标，但有错误信息的全失败组仍可进入。成功／失败、组内 reward 方差和 SD loss 可用性不是同一个标签。

**两项边界。** 其一，默认 self-success 排除与论文 Table 2 自己给自己成功示范不同。其二，row mask 根据模板构建前的反馈可用性决定，随后 teacher prompt 会按 `max_reprompt_len` 截断；这些已查函数未验证关键反馈在截断后仍然保留。这里只指出复用时需要确认的条件，不宣称已测得错误训练或历史结果无效。

### 10.3 Consumer：分布、支持集、ratio 与有效 token

C4 先计算当前学生分布与 top-K indices，再在 `torch.no_grad()` 下用教师前缀对**同一组 indices**评分。C5 用 logsumexp 和 tail bucket 构造 K+1 分布，或在关闭 tail 时重新归一化 top-K。其 divergence 选择为 α=0 forward KL、α=1 reverse KL、中间值 generalized JSD；teacher EMA 的 update rate 是另一个字段。

非 full-logit 分支则对当前采样 response 的 log-ratio 做 `detach()`，再乘 student log-prob；只支持 reverse KL。它没有另取论文 §4.2 描述的 argmax token。full-logit/JSD 分支直接对分布目标求导，不能将“只替换 sampled-token advantage”当作完整实现描述。

当前 loss 的内部 IS 是 detached 当前／old student ratio，上界为 `is_clip`，然后乘逐位置 divergence；另外可以再乘 trainer 提供的 `rollout_is_weights`。它**不是** A.4 Eq.13 的逐 logit PPO min surrogate，也不能不加版本边界地称为原式完全实现。

C5 的 `loss_mask=response_mask×self_distillation_mask`；token-mean 的分母显式传入当前计算张量的有效 mask 和、最少为1。C4 后续按 micro-batch 样本比例或梯度累积次数缩放。**本次没有跨 DP／可变长度 micro-batch 对拍，因此未证明这一路径与单一全局有效-token 分母严格等价。** 配置名称与 generic `agg_loss` 的文档并不能替代实际传参。

全零 SD mask 会使该目标的梯度为零，不自动保证参数完全不动：优化器动量、weight decay 或其他启用目标仍需考虑。当前更新逻辑在有限 grad norm 时会执行 optimizer 并允许教师更新；本文没有运行这一边界案例。

### 10.4 更新次数与教师状态：on-policy 必须限定到实验和调用

C2 仍设置 `adv_estimator: grpo` 来禁用 critic 等通用路径；C4 进入 `loss_mode=sdpo` 后直接调用 C5，**不把预计算 GRPO advantages 用作主 SDPO loss**。因而配置里出现 GRPO，不等于执行了 Eq.3 的混合目标。

C7 将 configured mini-batch 先乘 `rollout.n`，再除以 DP 维度。以 C1 的 question32、mini1、n8、DP4且SP1为例，局部 mini 为2条回答，每卡约64条回答，因而一批生成数据可产生32个 mini 更新（one epoch 的静态推算，未实际执行）。§3 的“每批一次更新、严格 on-policy”不能扩展到全部 LCB／TTT 配置。

C4 将 `on_policy` 判断为一个 mini 且一个 epoch；否则沿用旧 logprob。EMA teacher 的 `_update_teacher()` 在整个 `update_policy` 调用结束、至少一次有限更新后运行，并非每个 mini-step 都运行。teacher forward 使用独立 teacher 模块；TrustRegionTeacher 则对参考／当前的 raw logits 用 `torch.lerp`，与正文几何混合一致。

当前代码对 SDPO 明确拒绝 multimodal inputs，logit distillation 需关闭对应 fused kernels。这些是实际支持边界，不应因为 fork 继承了大量 verl 模块就称“任意 agent、多模态、fully async 均已原生支持 SDPO”。

### 10.5 开放资产与真正的复现范围

官方 README 提供训练与预处理入口、科学任务和 rich-feedback 的 sweep、multi-turn baseline、W&B 链接；实现有实际的反馈构建和 loss，而非空仓库。但本次没有下载权重、冻结数据包 revision、核验 W&B 所有运行配置，或找到可覆盖每张表的历史 checkpoint 清单。

只检查的 `experiments/ttt/` 目录列有 multi-turn launcher，不足以据此认定全部 TTT-SDPO 实验没有实现；反过来，现有通用 loss 也不能充当所有 TTT sweep 已完整核验的证据。README 的安装说明晚于论文：包含 GH200 CUDA13.1 路线和未充分测试的 Blackwell 配置。它们不应覆盖 E.1 的 CUDA12.8/Torch2.7.0 环境记录。

本次代码仅作为配套实现事实；作者实验具有训练与多项消融证据，**没有在本次任务中获得独立复现证据**。论文、代码和数据许可应按各自产物查看，不能由 Apache 代码许可推断所有训练资产同样授权。

## 11. 不确定性、冲突与不能外推的结论

| 问题 | 本次结果 | 已查范围与处理 |
| --- | --- | --- |
| SDPO 是否只处理 outcome 全零？ | 不是；核心取决于反馈改变分布；scalar-only 全失败仍缺示范 | §2–5、C3/C5；不把任何失败都定义成有用反馈 |
| 所有结果是否 strictly on-policy？ | 不能统一称是；§3明确一次，Table12 rich mini1，当前代码可多次更新 | §3、A.4、E、C4/C7，逐实验区分 |
| “换 advantage”是否完整？ | reverse-KL 的局部等价成立；top-K/JSD/teacher-forward/mask 有额外实现 | Eq1–2、A/B、当前 loss，不压成一行替换 |
| 代码主结果是不是题目泛化？ | 131题反复训练，按tests验证；当前test文件为完整suite | §4脚注、C6，不能与未适应的公开榜单等同 |
| Science 汇总70.2/66.6怎么得到？ | 原文有此值；不能由Table3直接无权重平均恢复 | §1、Table3/7、E，保留口径差异而不自造解释 |
| Token-level ablation 是 sampled还是argmax？ | 正文写most likely，当前非full分支评分sampledresponse | §4.2、C4/C5，历史配置未恢复 |
| Own-success 是否给自己作示范？ | Table2说是；当前 rich-feedback 默认排除 | 原文与C3分列，不判历史错误 |
| K=100还是20？ | 不同实验／消融不同 | §2、§4.2、A.3、Table12；支持集也分别注明 |
| Qwen2.5中间模型的名字 | 正文8B与Fig17的3B不一致 | 用图中实际系列说明，保留文字疑点 |
| 3×到底是哪种速度？ | 目标discovery交叉点；均值约1.28/1.25，另有逐题大幅收益 | Fig13、Table10，不当墙钟／费用倍率 |
| “不遗忘” | 相比基线较好，仍有明确heldout下降 | Table5；无长期多域遗忘保证 |
| 反馈是否经过反作弊、噪声质量评估？ | 示例与执行有披露，完整威胁模型／错误反馈压力测试未披露 | §4、§7、F、已查代码范围；不能假设安全隔离 |
| 科学题数与全部成本 | 无足够完整manifest和成本分解 | §3、E、代码入口；不从数据集总量补最终训练量 |
| 长程SWE、多harness、MoE、fully-async收益 | 本篇没有对应训练实证 | §7列为扩展方向；框架继承能力不等于实测 |
| 本轮读取／验证缺口 | p36图片未取得；TeX/本机PDF未取得；无独立review与训练复现 | 不是原文“未披露”；明确与作者的未知项分开 |

## 12. 对 RepoHarness 的条件化启示（2026-09-07）

项目基线仍是 miles+SGLang+真实 Claude Code harness+rh2，约30B-A3B、8×96GB PCIe；本稿不改变 GRPO+faithful DIS 的候选状态，也不将上游 OPD 接口视为 SDPO 已完整接入。

**本篇最值得保留的候选是：减少对已有执行反馈的浪费，而不是仅为增加算法名改训练。** 但 LCB 的公开用例反馈与真实 SWE 中私有评分资产并不相同；先明确允许提供的诊断，再判断模型能否使用它。不能把“重跑 hidden tests 后把失败详情全部传给模型”当成无需审批实验语义的普通实现。

| 候选验证 | 本文证据 | 适合先做什么 | 不应预先承诺什么 |
| --- | --- | --- | --- |
| 反馈是否真的有信息 | Table6信息组合、弱模型负结果 | 在少量固定失败代码／SWE片段上比较同策略无额外信息与合法反馈条件，测完成改善和错误类型 | 得到反馈的教师一次没解出，就判其所有token信号无用；或反过来只因能解就保证蒸馏有效 |
| 是否要反馈自蒸馏而非简单SFT | Table5、Fig10 | 固定来源与预算，比较GRPO、合法修复轨迹SFT、最小SDPO目标；计teacher forward与数据生产 | SDPO天然胜过强SFT；无需运行比较就启动多教师平台 |
| 原始回答与教师上下文是否对齐 | Algorithm1、C3/C4 | 对真实捕获response做学生／教师两种前缀的token与位置对拍；保持target同一份、教师stop-grad | 解码后重分词天然一致；上下文裁剪或subagent分叉可直接套单次LCB recipe |
| 零reward组能否给辅助目标提供信号 | rich-feedback实验、C3/C5 | 区分无可信数据与对GRPO无对比；固定小batch核mask、支持集、有效分母、teacher版本 | 绕过现有可信准入；把环境失败当模型失败；修改冻结loss合同而不做算法决策 |
| 如何证明可迁移收益 | §3题目split与§4tests split的对比 | 预先冻结真正未见的题目／仓库，再单列harness迁移与能力保持 | 仅在训练过的PR或同题私有测试上上涨就称未见SWE能力 |

这是一组可验证的有限改动，不要求建立自动数据策展、通用反馈平台或新异步运行时。**最应由上游承担的仍是分布式训练、推理与权重运输；本项目需要明确的是反馈来源、目标轨迹身份、合法上下文、消费mask及真实结果。** 将EMA状态与异步策略版本连接是否必要，应在确定采用此目标后再做窄设计，不因本次阅读自动扩大范围。

SDPO也为项目方向提供一个反证：代码学习信号不足不一定意味着必须扩充更多任务；另一方面，弱模型和错误反馈下的失败说明它也不是“全零组通用救活器”。它最适合作为与环境生产／系统效率路线并列的候选，由实际探针决定，而不是新的最低交付清单。

## 13. 查阅索引与交付状态

| 后续常见问题 | 笔记位置 | 原文位置 |
| --- | --- | --- |
| 是否采样教师修复答案？ | §2、§4 | Algorithm1、Table2，pp.4–5 |
| teacher/student/old/rollout概率怎样区别？ | §3、§10.3 | Eq1–2、A.4，pp.4–5/31 |
| JSD、reverse KL与top-K+tail？ | §3、§8 | A.1–A.3、Table12，pp.29–31/42 |
| EMA和trust-region有什么差别？ | §4.2、§6.4 | A.2/B.2、Table4 |
| 科学与工具训练是否generalization？ | §5 | §3、D.1、E |
| LCB是否未见题目？ | §6.1、§10.1 | §4脚注5、`data/split_tests.py` |
| 反馈越多越好吗？ | §6.6 | Table6，p.13 |
| 真的不遗忘吗？ | §6.5 | Table5，p.11 |
| 3×与4×分母是什么？ | §6.1、§7.3–7.4 | Fig1/Fig13、Table10 |
| 单题适应是否更新权重？ | §7 | §5、Table12、D.3 |
| 当前代码与论文配方差别？ | §10–11 | 固定C1–C7；不可倒填历史 |

**状态：全文精读完成，作者自查完成，待独立复查。** 有完整覆盖记录、主要表格与图的统计口径、公式和代码身份、局限与负结果。作者自查包括文本链接／数学格式、Table3/7均值与TTT比值的独立算术，以及固定前缀KL梯度、几何教师混合、top-K+tail的小型CPU检查；这些不是论文训练复现。

并行写入范围仅为本稿与 [16_N07_review.md](reviews/16_N07_review.md)，共享README、catalog、batch计划、历史交接包、其他线程文件和训练实现均不修改。没有可用独立子agent工具，因此不编造reviewer身份、线程ID或“独立审查通过”状态。

## 官方来源与版本化代码

[P-abs]: https://arxiv.org/abs/2601.20802
[P]: https://arxiv.org/pdf/2601.20802v2
[H]: https://arxiv.org/html/2601.20802v2
[P1]: https://arxiv.org/pdf/2601.20802v2#page=1
[P3]: https://arxiv.org/pdf/2601.20802v2#page=3
[P4]: https://arxiv.org/pdf/2601.20802v2#page=4
[P5]: https://arxiv.org/pdf/2601.20802v2#page=5
[P6]: https://arxiv.org/pdf/2601.20802v2#page=6
[P7]: https://arxiv.org/pdf/2601.20802v2#page=7
[P8]: https://arxiv.org/pdf/2601.20802v2#page=8
[P9]: https://arxiv.org/pdf/2601.20802v2#page=9
[P10]: https://arxiv.org/pdf/2601.20802v2#page=10
[P11]: https://arxiv.org/pdf/2601.20802v2#page=11
[P12]: https://arxiv.org/pdf/2601.20802v2#page=12
[P13]: https://arxiv.org/pdf/2601.20802v2#page=13
[P14]: https://arxiv.org/pdf/2601.20802v2#page=14
[P15]: https://arxiv.org/pdf/2601.20802v2#page=15
[P17]: https://arxiv.org/pdf/2601.20802v2#page=17
[P29]: https://arxiv.org/pdf/2601.20802v2#page=29
[P31]: https://arxiv.org/pdf/2601.20802v2#page=31
[P32]: https://arxiv.org/pdf/2601.20802v2#page=32
[P33]: https://arxiv.org/pdf/2601.20802v2#page=33
[P34]: https://arxiv.org/pdf/2601.20802v2#page=34
[P35]: https://arxiv.org/pdf/2601.20802v2#page=35
[P36]: https://arxiv.org/pdf/2601.20802v2#page=36
[P37]: https://arxiv.org/pdf/2601.20802v2#page=37
[P38]: https://arxiv.org/pdf/2601.20802v2#page=38
[P39]: https://arxiv.org/pdf/2601.20802v2#page=39
[P40]: https://arxiv.org/pdf/2601.20802v2#page=40
[P41]: https://arxiv.org/pdf/2601.20802v2#page=41
[P42]: https://arxiv.org/pdf/2601.20802v2#page=42
[P43]: https://arxiv.org/pdf/2601.20802v2#page=43
[P44]: https://arxiv.org/pdf/2601.20802v2#page=44
[P46]: https://arxiv.org/pdf/2601.20802v2#page=46
[P47]: https://arxiv.org/pdf/2601.20802v2#page=47
[P49]: https://arxiv.org/pdf/2601.20802v2#page=49
[P50]: https://arxiv.org/pdf/2601.20802v2#page=50
[C0]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/README.md
[C1]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/experiments/rich_feedback/run_sdpo.sh
[C2]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/verl/trainer/config/sdpo.yaml
[C3]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/verl/trainer/ppo/ray_trainer.py#L612-L800
[C4]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/verl/workers/actor/dp_actor.py
[C5]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/verl/trainer/ppo/core_algos.py#L1027-L1205
[C6]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/data/split_tests.py
[C7]: https://github.com/lasgroup/SDPO/blob/7c457fc1b1f636ae794eb0362ba37d4743b06fbc/verl/workers/fsdp_workers.py#L231-L259
