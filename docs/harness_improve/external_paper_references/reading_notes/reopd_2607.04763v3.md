# ReOPD v3：多轮前缀重放、教师可靠性与真实训练实现

ReOPD 重用教师的历史动作和观察，只在抽中的位置让学生生成一个新动作，并由固定教师评分；该动作不在环境执行，也不接上教师原来的后续结果。它节省的是学生训练期的环境交互，仍需要教师推理、可信轨迹池和在线评测。论文把历史分布偏移与教师监督可靠性分开，用按 turn 衰减的采样作为实用近似；数学平均分改善，搜索及双域平均分接近 OPD，但并非所有任务都不回退。本稿完成 v3 HTML 全文及关键源码阅读；v3 PDF 未取得，v2 图页仅作有版本标记的辅助检查，不冒充 v3 全图核验。

导航：[来源与覆盖](#sources) · [训练流程与数据](#pipeline) · [理论与目标](#theory) · [实验与成本](#experiments) · [实现追踪](#implementation) · [差异与未知](#unknowns) · [项目映射](#project) · [检查与交付](#review)

<a id="sources"></a>
## 1. 来源、版本与完成边界

阅读日期：**2026-09-24**。本稿属于项目后续阅读任务五，不变更项目的算法、环境、预算或实现定案。

**主来源 P3**：Baohao Liao、Hanze Dong、Christof Monz、Xinxing Xu、Li Dong、Furu Wei，*Multi-Turn On-Policy Distillation with Prefix Replay*。机构为 Microsoft Research 与 University of Amsterdam；前两位等贡献，Liao 的部分工作在微软实习期间完成。[arXiv 记录][ABS]：v1 2026-07-06，v2 2026-07-16，**v3 2026-07-26**。本次主读 [v3 HTML][P3]，包含摘要、§1–6、命题及证明、Algorithm 1、Tables 1–7、Figures 1–8 图注和参考文献。该 HTML **没有独立技术附录**；参考文献后的内容是 arXiv 页面帮助，不是论文附录。参考文献只用于确认依赖身份，不表示逐篇扩读。

**辅助来源 V2**：网页工具可取得的无版本 PDF 实际水印为 **v2，16 Jul 2026，共 25 页**。查看了技术正文全部相关图表页及尾页。该文件与 v3 存在真实差异，不能将其页码或表值写成 v3 事实。下文“V2 p.N”只用于复核旧版图示；**P3 的主要定位采用节、表、图和公式编号，不伪造 v3 物理页码**。精确 v3 PDF、HTML 图像直链及 TeX 本轮未能取得；v3 排版级与图中独有数值复核仍待补。

**官方补充 W**：[作者项目页][WEB]，读取方法、结果、资源和模型／代码入口。它是持续更新网页，没有独立版本承诺；其中 headline 和图表说明不能覆盖 P3 的限定与负结果。

**代码 C**：官方 [BaohaoLiao/ReOPD][REPO] 固定提交 **`7a499d29ab07ff50dfde039f9d7a44dfe313b95e`**；其 submodule 是 **`BaohaoLiao/slime@26525f97179afc47c9ef6fff045dbc28d79f1875`**，不是读取时任意最新版 slime。下文给出具体路径／符号。只做静态调用链核查，没有安装整个栈或重现论文训练。

**项目基线**：`Rogerffff/RepoHarness@0554dafd633cd982288bd60a54f75da65e5c54d4`，`codex/project-status-20260923`。前三项阅读在各自 Pro 分支，本任务不自动合并它们。当前同步包的已提交实现基线为 `d4a11940…`；未发布的本地修复不视作本稿已验证内容。

### 1.1 原文结构覆盖

| P3 原文范围 | 本次处理 | 本稿位置 |
| --- | --- | --- |
| 摘要、§1、Figs.1–3 | 完整正文；区分学生当前动作与教师历史；V2 原图辅助 | §2、§6 |
| §2 五组 related work | 全读；保留 distillation、RL、self-training、agent 与双侧偏移的区别 | §2.3 |
| §3 Eqs.(1)–(6)、Assumption 1、Proposition 1 及证明 | 全读 HTML 公式；V2 排版辅助；独立核简化代数 | §4 |
| §4 Eq.(7)–(8)、未编号 KL 目标、Algorithm 1、Fig.4 | 全读；区分理论桥分布、位置采样及实现估计器 | §4–5、§8 |
| §5 模型、数据、基线、Tables 1–3 | 逐项核 v3 HTML；记录相对 V2 的实质变化 | §3、§6.1 |
| §5.1 Tables 4–6、Fig.6 | 全部任务结果与平均口径；不省略回退 | §6.2–6.4 |
| §5.2 Fig.5、Fig.7、Table 7、Fig.8 | 全读正文和图注；图中独有数值只作 V2 辅助，不回填 P3 | §7 |
| §6 限制与未来工作 | 全读；不把未来可靠性估计写成已实现模块 | §9–10 |
| References 至末尾 | 检查完整性、引用身份与有无附录 | §1、§2.3 |

### 1.2 本次已识别的版本差异

| 项目 | 辅助 V2 PDF | 主读 P3 HTML | 本稿采用 |
| --- | --- | --- | --- |
| Table 1 冷启动 | 5 epochs | **3 epochs** | P3 |
| Table 1 Search 教师 GRPO batch | 表内只有统一 `32×8` | 明列 **Search `128×4`**，Math `32×8` | P3 |
| Table 6 双域 OPD 数学 | 32.5 / 35.4 / 75.9 / 43.5 / 57.4 / 86.7，Avg 55.2 | **34.2 / 29.6 / 79.7 / 44.5 / 57.1 / 87.3，Avg 55.4** | P3 |
| Table 6 双域 ReOPD 数学 | Avg 55.3 | Avg **55.3** | 不再沿用旧版的“55.2→55.3 提升” |

没有完整 v2→v3 原始文件差分，因此不声称只改了以上三处。文中方法、结果和成本的优先级均是：明确版本的正文／表格 > 未绑定版本的网页 headline；代码事实另列，不替历史配方补空白。

<a id="pipeline"></a>
## 2. 方法到底做了什么

### 2.1 一条轨迹怎样变成多条训练输入

设教师记录了 `问题 → 动作1 → 观察2 → 动作2 → 观察3 → …`。训练第三个动作时，学生读取的前缀仍是教师的前两个动作及相应观察；学生生成自己的第三个动作，固定教师对它的 token 条件概率提供监督，然后这一条训练样本结束。[P3 §1、§4、Fig.2、Algorithm 1]

**不会发生的步骤**：不执行学生的第三个动作，不取得新观察，不把教师原记录的第四轮观察接在这个不同动作之后，再让学生继续跑。抽到第四个位置时，输入重新来自教师记录，里面仍是教师原来的第三个动作。

因此要区分三层：

| 层次 | 来源 | 是否 student-on-policy |
| --- | --- | --- |
| 当前 turn 之前的外部动作及观察 | 固定教师轨迹池 | 否 |
| 当前 action 内的自回归 token 前缀 | 当前学生采样 | 是，针对采样学生版本 |
| 参数更新时使用的条件概率 | 被更新的学生与固定教师 | 需区分采样版本和更新版本，不能仅凭名称消除偏差 |

这是 **off-environment student training**，不是全程无环境、全历史 on-policy，也不是将历史轨迹当作可执行世界模型。教师仍要对新生成动作评分，测试时仍要使用真实 Python／搜索环境。

### 2.2 教师在评分什么

教师条件是 `历史 h_t + 当前学生动作的 token 前缀 a_t^{<j}`。因此它对学生真实生成的第 j 个 token 提供信息，而不是只复制教师旧动作。若此前只保存了教师原轨迹上所选 token 的 logprob，这些概率不足以评分学生新 token。[P3 §4 “Off-environment prefix construction”]

论文的“dense supervision”指比整题一个终局标量更密集的 token 条件监督，不表示方法证明每个 token 都承担正确的环境信用分配。教师在这些新条件下也可能判断错误，正是本文试图讨论的另一侧分布偏移。

### 2.3 与近邻方法的区别

按作者 §2 的组织：传统 sequence distillation/SFT 模仿教师动作；OPD 让学生生成再获取教师概率；RL 的相关例子通过标量反馈优化；self-training/rejection sampling 从成功或高分轨迹中训练；DAgger 等则处理由学生偏离引起的访问分布变化。本篇的区别在于：**从固定教师历史池选择监督位置，同时让学生在该位置生成新动作**。

作者将方法称为与 PPO／GRPO 等优化器家族正交，并强调不使用环境标量 return 作为学生目标。公开代码仍通过策略损失实现蒸馏，见 §8，不能据此把论文文字改写为“学生也是标准 outcome-GRPO”。

原文 §1 将 RL 概括为 on-policy，§4 又把桥参数描述成 RL 与蒸馏之间的滑块。这是作者对本问题的叙述框架；本稿不将其推广为所有强化学习的定义。本文的桥参数控制的是**历史分布**，并不是一般的 reward/distillation loss 混合系数。

## 3. 训练阶段、模型和数据

### 3.1 依赖关系，而不是误读成四阶段串行训练

```text
已有 Qwen3 模型
  └─ 冷启动 SFT
       ├─ 教师：在相应环境上 GRPO → 最终冻结教师
       │         └─ 保留训练过程中的多版本轨迹 → 前缀池
       └─ 学生：从冷启动 checkpoint 分别进行
                 SFT 基线 / 在线 OPD 基线 / ReOPD
```

ReOPD 和 OPD 是对照分支，不是 ReOPD 后必须继续 OPD。公开脚本的 “Stage 3 / Stage 4” 只是执行入口编号。学生默认从冷启动模型开始，不从最终 GRPO 教师开始；最终教师为固定目标，而池内可包含教师早期 checkpoint 的行为。[P3 §5 Models、Baselines；C1、C2]

教师：Qwen3-4B-Instruct-2507、Qwen3-8B、Qwen3-30B-A3B-Instruct-2507。学生：4B，另有 30B-A3B→8B 的数学实验。论文简称 Qwen3-8B，公开脚本说明其部分路径实际以 **Qwen3-8B-Base** 加非 thinking 模板为基础。保留两者来源，不在本稿默默合并为完全相同的初始化。

### 3.2 两种任务环境

| 域 | 冷启动 | 教师 GRPO／学生蒸馏问题 | 工具及观察 | 外部评测 |
| --- | --- | --- | --- | --- |
| 数学 | ReTool 来源的约 2K 教师轨迹 | DAPO 来源的约 **6.4K prompts** | Python code interpreter | AIME24/25、AMC23、Minerva、Olympiad、MATH500 |
| 搜索 | 从 NQ+HotpotQA 训练集取约 2K 问题，由 Qwen3-30B-A3B-Instruct-2507 生成轨迹 | 另取约 **6.5K prompts** | 2018 Wikipedia，E5，top-3 检索段落 | NQ、TriviaQA、PopQA、HotpotQA、2Wiki、MuSiQue、Bamboogle |

两域都先冷启动，教师再 GRPO。数学冷启动轨迹的具体生成 checkpoint，本篇没有进一步固定；不从 ReTool 引文自动补写。搜索不是实时互联网浏览，也不是 BrowseComp。论文没有 SWE 仓库修复、terminal 或生产 Claude Code 的结果。[P3 §5 Datasets & environments]

原文未提供完整逐题 manifest、重复轨迹处理、污染审计或本地镜像 hash。6.4K/6.5K 是问题数，不是实际训练行、独立环境数或工具调用数。默认池来自教师 RL 期间的记录，而不只来自最终教师重新采样。

### 3.3 单域与双域不是同一个模型

Tables 4/5 分别训练数学和搜索学生。Table 6 则是**一个 Qwen3-4B 学生**同时训练两域；冷启动和蒸馏数据合并、打乱，教师仍是两个单域训练的 Qwen3-4B 模型，按任务路由。不是一个教师同时掌握全部环境，也不是在同一 token 上融合两个教师概率。[P3 Table 6、§5]

### 3.4 公开前缀资产：数量不等于题数或质量承诺

| 域／教师 | 官方 README 登记的 prefix rows | 格式 |
| --- | ---: | --- |
| Math / 4B | 81,936 | JSONL |
| Math / 8B | 53,762 | JSONL |
| Math / 30B-A3B | 54,706 | JSONL |
| Search / 4B | 144,504 | Parquet |
| Search / 8B | 141,365 | Parquet |

来源：[C3 数据说明][C3]。这些是代码文档的发布记录，本次没有下载数据逐行复算、验证模型权重或固定 HF 数据 revision。官方 collection 可访问，个别数据详情页未取回；不能据此声称全部资产都已检查。

<a id="theory"></a>
## 4. 理论：证明了什么，近似了什么

### 4.1 符号与两个误差来源

$t$ 是**环境交互动作的位置**，不是 token 位置。$H_t=(O_1,A_1,\ldots,A_{t-1},O_t)$；当前采样学生为 $\pi_{\theta_{old}}$，更新学生为 $\pi_\theta$，固定教师为 $\pi_T$。由策略和环境共同诱导的历史分布记为 $d_{old}^t$ 或 $d_T^t$；教师池的收集分布为 $P_t$，理想但不可用的改善目标为 $q_t^*$。[P3 §3]

Eq.(1) 在学生会访问的历史上评估相对 $q_t^*$ 的损失。Eqs.(2)–(3) 改为从池 $P_t$ 取历史，以 $w_t$ 加权，并用教师目标替代 $q_t^*$。在理论定义中，$E_{P_t}[w_t]=1$ 对每个 $(x,t)$ 分别成立，因而 $\rho_t=w_tP_t$ 是一个条件概率分布。

定义 $f_t=\ell(\pi_\theta,q_t^*)$，$g_t=\ell(\pi_\theta,\pi_T)$，教师误差 $\epsilon_t=|f_t-g_t|$。假设 $|f_t|\le B$，Eq.(4) 给出：

$$
|R^*-L_\rho|\le E_x\sum_t\alpha_t\left[2B\,TV(d_{old}^t,\rho_t)+E_{\rho_t}\epsilon_t\right].
$$

证明先加减 $E_{\rho_t}f_t$，将两项分别用 total variation 与绝对值期望上界，再求和。学生历史越匹配只压低第一项；教师在该历史上是否给出好的条件目标，由第二项决定。[P3 Proposition 1 及 proof]

**不是以下保证：**它不是任务成功率下界、训练单调改善证明、固定采样复杂度保证，也没有直接测量真实的 $q_t^*$ 或教师误差。用 teacher support 代替可靠性是后续设计假设，不能因为历史来自教师，就断言教师永不犯错。

**假设边界（读者核查）**：KL 并非无条件有界。原文提出目标概率有统一正下界的充分条件；实际还需覆盖学生的概率支持。温度本身不对任意无界 logits 产生统一概率下界，不能把“使用 softmax/temperature”当成已验证此假设。若按整个 action 累加 token KL，上界也要计入最大 token 长度。此处是对假设的解释，不是原文报告的新实验。

### 4.2 几何桥是优化一个代理目标的解

作者将不可直接测量的教师不可靠性换为到教师历史分布的 KL，最小化 Eq.(5)：

$$
\lambda_{stu,t}\,KL(\rho_t\Vert d_{old}^t)+
\lambda_{tea,t}\,KL(\rho_t\Vert d_T^t).
$$

共同支持非空时，Eq.(6) 的解为：

$$
\rho_t^*(h|x)=\frac{d_{old}^t(h|x)^{\gamma_t}d_T^t(h|x)^{1-\gamma_t}}{Z_t(x)},\qquad
\gamma_t=\frac{\lambda_{stu,t}}{\lambda_{stu,t}+\lambda_{tea,t}}.
$$

$\gamma=1$ 退为学生访问分布，$\gamma=0$ 退为教师访问分布。该结果不等于已经找到真实教师误差最小的采样策略，因为 Eq.(5) 本身使用了代理。原文没有在线估计每道题的最优 $\gamma_t$，默认实用方法只调一个 $\kappa$。

### 4.3 历史概率比、位置衰减与两个归一化轴

相同任务和环境转移模型下，比较同一历史的学生／教师访问概率，环境转移因子抵消，得到：

$$
\hat r_t(x,h_t)=\prod_{s<t}\frac{\pi_{\theta_{old}}(a_s|x,h_s)}{\pi_T(a_s|x,h_s)}.
$$

这里每项是完整 action 的条件概率，不能未经转换就用“平均 token logprob”当作其乘积。历史来自最终教师时，Eq.(7) 对每个 $(x,t)$ 归一化 $\hat r_t^{\gamma_t}$，能在**同一位置的不同历史之间**重新分配质量。[P3 §4、Eq.(7)]

作者观察 log ratio 随深度降低，并用平均教师／学生 KL $\bar c$ 推出一阶形状近似 Eq.(8)：

$$
\hat r_t^{\gamma_t}\approx\kappa^t\quad\text{（忽略共同尺度）},\qquad
\kappa=\exp(-\gamma_t\bar c).
$$

实际默认 $\kappa=0.6$，并没有逐轮测量这个公式中的全部量。作者称后期步骤更高偏移；这是经验动机，不是每条轨迹都应更早停止。

**关键区别是原文自己明确说明的**：$\kappa^t$ 在固定 $t$ 内对所有历史相同。若继续做 $E_{P_t}[w_t]=1$ 的归一化，它会变成 1，衰减消失。因此实用方案改在**位置之间**归一化，偏向早期，而非在同一位置内恢复几何桥。

所以，$\kappa^t$ 是降低成本的 surrogate，不是无偏恢复学生 occupancy 的精确 IS，也不能直接把 Proposition 1 对条件历史分布的界当成“实用采样必然改进 return”的证明。$\kappa=1$ 仍然是教师前缀上的均匀训练，不会变回真正在线 OPD。

**读者补充**：教师采到的每个动作，其学生／教师概率比并非必然小于 1；负的平均 log ratio 与 ratio 的算术期望也不同。在完整共同支持上，归一化概率比的教师期望可为 1。Fig.4 的经验下降不能扩展为每条历史的确定性质。

## 5. 训练目标与采样实现必须分层看

### 5.1 论文目标

在教师前缀 $h_t$ 上生成学生 action $A_t=(a_t^1,\ldots,a_t^{n_t})$。原文未编号公式写的是：

$$
\ell_t=\sum_{j=1}^{n_t}KL\left(
\pi_\theta(\cdot|x,h_t,a_t^{<j})\Vert
\pi_T(\cdot|x,h_t,a_t^{<j})\right).
$$

方向为 student‖teacher。动作内上下文来自采样学生，教师固定。原文写的是条件**分布 KL 的 token 求和**，不是单独模仿教师答案、不带模型更新的推理时重试，也不是把工具输出当 action token 学习。[P3 §4、Algorithm 1]

Algorithm 1 按位置概率采样，随后对抽中的 action 使用不再乘 $\kappa^t$ 的损失。若已经按 $\kappa^t$ 抽样，又把 loss 乘一次相同权重，目标将再次偏向早期，不是同一个实验。

### 5.2 采样与加权等价有前提

对固定有限候选池 $i$，固定损失 $L_i$，若 $p_i=w_i/\sum_kw_k$，则 $E_{i\sim p}L_i=\sum_iw_iL_i/\sum_iw_i$。这是原文所说两种估计方式的基础。它需要一致的基准池、归一化、任务／位置边际和损失单位；不能忽略输出 token 数、每条轨迹有多少前缀、数据过滤和小批分母。

公开代码不是每次更新都从完整池按位置重新抽样，而是**预处理时独立 Bernoulli 保留一次，之后在保留池中训练**。这能形成相似的早期偏好，但有限池覆盖与每个任务的实际权重需要另行核查，见 §8.1。

### 5.3 不混淆的三种比值／权重

| 对象 | 比较的东西 | 在本篇的位置 |
| --- | --- | --- |
| 历史比 $\hat r_t$ | 学生和教师沿教师历史的 action 概率 | 解释 occupancy 与理论桥 |
| 位置权 $\kappa^t$ | 不同监督 turn 的采样权 | 默认实用前处理 |
| PPO 的更新比 | 更新学生与采样／参考旧学生在同一 token 上的概率 | 公开训练实现的 surrogate，不是历史桥权 |

它们都可能在代码或论文里叫 ratio，但不能互相替代。ReOPD 本文没有设定 miles 式跨版本 staleness 门槛，也没有为所有异步数据校正提供新定理。

<a id="experiments"></a>
## 6. 实验设置与完整结果口径

### 6.1 P3 的训练与评测参数

| 参数 | Cold Start | SFT 对照 | 教师 GRPO | OPD / ReOPD |
| --- | --- | --- | --- | --- |
| batch | 64 | 64 | Math 32题×8；Search 128题×4 | 256×1 |
| 学习率 | 5e-5 | 5e-5 | 1e-6 | 1e-6 |
| scheduler | cosine | cosine | constant | constant |
| min lr / warmup | 1e-6 / 0.1 | 1e-6 / 0.1 | 未列 | 未列 |
| epochs / updates | **3 epochs** | 5 epochs | 200 steps | 200 steps |
| clip low/high | 未列 | 未列 | 0.2 / 0.28 | 原表为 — |
| temperature | 未列 | 未列 | 1 | 1 |
| max_gen_tokens | 未列 | 未列 | Math 8192；Search **4196** | 同前；双域 8192 |

来源：[P3 Table 1][P3]。**4196 是 v3 原表值，不默改为 4096**。公开脚本另有不同默认值，见 §8.5。表中的 ReOPD 列仍列 Math16／Search4／双域16 的 max tool calls，但方法、并发行和实验解释均称学生 ReOPD 执行 0 次工具调用；这列不能当作 ReOPD 实际执行量，原文没有进一步解释该表述。

Table 2：评测 temperature=1；Math 最多 16,384 generation tokens、16 次调用，AIME24/25/AMC23 用 avg@8，其余数学用 avg@4；Search 最多 8,192 generation tokens、4 次调用，avg@1。avg@n 是生成结果的平均，不是 best-of-n，也不是 n 个训练随机种子。

| 数学评测集 | AIME24 | AIME25 | AMC23 | Minerva | Olympiad | MATH500 | 合计 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 题数 | 30 | 30 | 40 | 272 | 675 | 500 | 1547 |

| 搜索评测集 | NQ | TriviaQA | PopQA | HotpotQA | 2Wiki | MuSiQue | Bamboogle | 合计 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 题数 | 3610 | 11313 | 14267 | 7405 | 12576 | 2417 | 125 | 51713 |

来源：P3 Table 3。Math Avg 是跨 benchmark **macro**；Search Avg 是按题数 **micro**。NQ/HotpotQA 是训练来源域内，另外五个搜索集是数据域外；不等于迁移到不同工具协议或陌生软件仓库。

作者声明 OPD/ReOPD 同教师、batch、update 数等设置，但同一个 batch 元素在 OPD 中可包含完整在线 episode，在 ReOPD 中是单个抽中位置的新 action。**同 batch、同更新数不是同生成 token、同动作数或同独立问题覆盖**。本篇没有给出充分的等总 token、等全流程成本曲线。

### 6.2 数学：P3 Table 4

所有数值为准确率百分比；teacher GRPO 是参考模型，不是同初始化的学生对照，也不是数学上的性能上界。

| 教师→学生 / 方法 | AIME24 | AIME25 | AMC23 | Minerva | Olympiad | MATH500 | Avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4B 教师 GRPO | 42.1 | 32.1 | 79.7 | 37.9 | 56.1 | 85.1 | 55.5 |
| 4B 学生 Base | 6.3 | 6.7 | 36.6 | 31.0 | 29.5 | 58.2 | 28.0 |
| 4B Cold Start | 22.1 | 20.8 | 66.6 | 32.4 | 49.0 | 79.1 | 45.0 |
| 4B→4B SFT | 21.7 | 21.3 | 63.1 | 39.8 | 49.9 | 80.9 | 46.1 |
| 4B→4B OPD | 35.4 | 29.2 | 77.8 | 43.3 | 58.2 | 86.9 | 55.1 |
| 4B→4B ReOPD | 40.8 | 31.3 | 80.0 | 42.9 | 59.4 | 88.9 | 57.2 |
| 8B 教师 GRPO | 28.3 | 23.3 | 73.1 | 38.5 | 52.0 | 84.3 | 49.9 |
| 8B→4B SFT | 22.1 | 22.9 | 63.8 | 36.0 | 44.7 | 80.8 | 45.0 |
| 8B→4B OPD | 28.3 | 26.3 | 70.3 | 39.8 | 55.3 | 85.8 | 51.0 |
| 8B→4B ReOPD | 36.7 | 29.2 | 74.4 | 41.1 | 56.4 | 84.7 | 53.7 |
| 30B-A3B 教师 GRPO | 47.9 | 35.0 | 91.3 | 46.4 | 63.7 | 92.1 | 62.7 |
| 30B→4B OPD | 28.3 | 25.8 | 75.3 | 39.6 | 53.6 | 83.8 | 51.1 |
| 30B→4B ReOPD | 32.5 | 26.7 | 74.4 | 39.4 | 55.8 | 86.5 | 52.5 |
| 8B 学生 Base | 21.3 | 11.3 | 43.1 | 37.2 | 34.4 | 64.8 | 35.3 |
| 8B Cold Start | 23.9 | 19.6 | 67.8 | 38.6 | 49.0 | 82.0 | 46.8 |
| 30B→8B OPD | 40.8 | 29.2 | 77.8 | 45.1 | 56.9 | 89.0 | 56.5 |
| 30B→8B ReOPD | 41.7 | 30.4 | 80.6 | 44.1 | 55.7 | 88.4 | 56.8 |

四组平均改善分别 **+2.1、+2.7、+1.4、+0.3 pp**。存在 Minerva、MATH500 等单项回退。8B 教师本身平均 49.9，低于 4B 教师的 55.5；“更大模型”与“当前任务更强教师”并非同义。作者以教师可靠性解释差异，但没有直接测得理论中的理想教师误差，不能从最终分数倒推该机制已被唯一识别。

### 6.3 搜索：P3 Table 5

| 教师→学生 / 方法 | NQ | TriviaQA | PopQA | HotpotQA | 2Wiki | MuSiQue | Bamboogle | Avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4B 教师 GRPO | 36.1 | 59.2 | 40.2 | 37.2 | 31.8 | 13.8 | 39.2 | 40.4 |
| 4B 学生 Base | 28.4 | 55.5 | 30.6 | 30.8 | 33.6 | 8.4 | 35.8 | 35.6 |
| 4B Cold Start | 26.2 | 48.6 | 33.6 | 24.7 | 26.6 | 5.8 | 24.8 | 32.1 |
| 4B→4B OPD | 36.3 | 59.7 | 40.3 | 37.3 | 31.7 | 14.5 | 44.0 | 40.6 |
| 4B→4B ReOPD | 36.4 | 59.6 | 40.5 | 37.3 | 31.5 | 14.0 | 37.6 | 40.5 |
| 8B 教师 GRPO | 36.6 | 59.3 | 40.2 | 36.7 | 34.7 | 13.8 | 39.2 | 41.0 |
| 8B→4B OPD | 35.5 | 57.3 | 39.0 | 35.0 | 31.2 | 12.8 | 37.6 | 39.1 |
| 8B→4B ReOPD | 34.9 | 57.5 | 39.1 | 34.6 | 31.0 | 11.9 | 37.6 | 39.0 |

两组 micro 平均均比 OPD 低 **0.1 pp**，因此准确表述是接近，而非所有条件下无下降。4B 配对的 Bamboogle 从 44.0 到 37.6，为 **−6.4 pp**；125 题中的约 8 题变化，对 51,713 题 micro 平均只贡献约 −0.0155 pp。不能只凭整体近似持平忽略小测试集变化，也不能用一次变化直接断言显著退化。

搜索 Cold Start 比 Base 低 3.5 pp。论文没有单独报告与 Table 4 同型的 Search SFT 行；辅助 Fig.1 中标作 SFT 的 32.1 对应这里的 Cold Start 值，不能擅自补出另一组搜索 SFT 对照。Table 5 图注仍写教师在 4B family，但表中实际列出 8B 教师，本文以表内模型身份为准，并保留文案不一致。

### 6.4 双域：P3 Table 6（不要沿用 V2）

| 评测 | 单域教师 GRPO | 双域 Cold Start | 双域 OPD | 双域 ReOPD |
| --- | ---: | ---: | ---: | ---: |
| AIME24 | 42.1 | 18.8 | 34.2 | 36.3 |
| AIME25 | 32.1 | 23.8 | 29.6 | 30.8 |
| AMC23 | 79.7 | 67.8 | 79.7 | 75.5 |
| Minerva | 37.9 | 40.5 | 44.5 | 44.5 |
| Olympiad | 56.1 | 48.9 | 57.1 | 57.4 |
| MATH500 | 85.1 | 82.4 | 87.3 | 87.3 |
| Math Avg | 55.5 | 47.0 | **55.4** | **55.3** |
| NQ | 36.1 | 25.7 | 37.3 | 37.7 |
| TriviaQA | 59.2 | 51.3 | 61.0 | 60.7 |
| PopQA | 40.2 | 33.2 | 40.5 | 40.6 |
| HotpotQA | 37.2 | 25.1 | 38.0 | 37.6 |
| 2Wiki | 31.8 | 27.1 | 31.6 | 32.1 |
| MuSiQue | 13.8 | 6.3 | 14.5 | 13.8 |
| Bamboogle | 39.2 | 29.6 | 44.0 | 37.6 |
| Search Avg | 40.4 | 32.7 | **41.0** | **41.0** |

双域整合成立的直接证据是这些独立评测结果与训练运行方式，不是跨任意工具、任务或企业工作流的普遍保证。论文没有给多个训练 seed／置信区间；avg@8 等采样数不弥补这一缺口。

### 6.5 成本需要按阶段记账

作者报告所有实验使用 **8×H100 与 slime**，ReOPD 可在 3 小时内训练完成；未为每个师生配对分列完整墙钟、失败作业及资源账单。[P3 §5 Implementation details]

| 成本对象 | 论文／官方页面支持什么 | 不能直接推出什么 |
| --- | --- | --- |
| 学生 rollout | 官方页称 Math约4.2×、Search约9.1×；P3称至少4× | 完整训练／达到同质量总成本同比例改善 |
| Python 环境 | OPD 用32并发进程；ReOPD学生训练不用执行 | tokenizer、教师推理、CPU数据处理也免费 |
| 搜索环境 | OPD部署检索器和Wikipedia embeddings，报告80GB GPU内存 | 这是全部模型显存，或独立额外80GB GPU的固定硬件方案 |
| 已有教师RL轨迹 | 可免再次执行环境来收集相同用途池 | 教师训练、日志记录、清洗、存储的总成本为0 |
| 专门重新采集池 | P3称计入后仍有>2× rollout效率 | 该结论已包含所有教师训练、评测和集群闲置费用 |

V2 Fig.1 显示 Math `169→40`、Search `64→7` 秒；V2 Fig.8 加入教师重采后为 `79/14` 秒，对应约 `2.1×/4.6×`。这些**图中精确值目前只有旧版目视证据**，不作为 P3 的新增精确测量。官方网页支持4.2×/9.1× headline，但不能证明所有v3图表未改。

公开入口默认教师4卡、学生训练／推理共置4卡。3小时即使换算GPU-hour，也只可能说明特定阶段的算术，不提供单节点RTX PRO 6000预算。teacher forward 要处理长前缀，环境省下的等待可能转移到教师prefill、KV或数据处理，需实际测量。

## 7. 消融、机制证据与负结果

### 7.1 位置衰减

P3 Fig.4 以 normalized step index 展示 log历史概率比随深度下降；未给精确拟合指标、完整按任务分层或所有师生设置。图中趋势支持便宜的位置代理，不证明它逐条准确估计教师误差。

Fig.5(a) 比较抽取不同 chunk，(b) 比较衰减 $\kappa$；v3正文／图注支持早期偏好优于统一抽样。原文没有充分交代 chunk 如何由变长轨迹划分、所有保留样本数和多次重复结果。V2 图中 $\kappa=0.2$ 与 $0.6$ 同为约53.4，$1.0$约50.9；**不据此声称0.6唯一最优**，也不将旧图读数写成v3 sweep结果。v3主表8B→4B的53.7与辅助图0.6的53.4不同，缺少运行对应关系，保留差异。

按位置改变采样，也会改变上下文长度、动作类型与问题权重。作者将改善归因于可靠性；本篇未充分排除这些共同变化，所以应将“机制解释”与“直接受控变量”分开。

### 7.2 前缀生成器与评分教师不是同一个角色

P3 Fig.7 固定评分教师Qwen3-8B、学生Qwen3-4B，只改变前缀生成来源。教师自己的前缀最好，换更强／更大生成器反而可能变差。这支持“评分教师能否理解给定历史”重要，而不是教师API越强、混合轨迹越多越好。

V2 图例具体写4B、8B、**32B** prefix，均值约52.9、53.7、49.3；当前v3图像未取回，不能把32B擅自等同于主实验30B-A3B，也不能补出未披露的准确checkpoint。结果不是“教师只在自身support上才可能正确”的逻辑证明，后者是过强概括。

### 7.3 教师训练过程池与最终教师重采池

P3 Table 7，评分教师8B、学生4B：

| 池来源 | AIME24 | AIME25 | AMC23 | Minerva | Olympiad | MATH500 | Avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 最终教师重新采集 | 37.9 | 30.0 | 72.2 | 39.2 | 56.2 | 85.0 | 53.4 |
| 教师RL期间混合checkpoint | 36.7 | 29.2 | 74.4 | 41.1 | 56.4 | 84.7 | 53.7 |

这一组结果支持复用作者这条教师训练过程的记录。它不验证任意旧policy、任意harness或其他模型混合数据的可靠性；理论中 $P_t\approx d_T^t$ 在这种多checkpoint池上仍是近似，不是精确身份。

### 7.4 原文自己保留的限制

§6承认：池的覆盖和质量限制可学习内容；深度只衡量“走到多后面”，不直接衡量具体历史离可靠区域有多远；直接估计教师误差、学习可靠性权重和在线适配schedule仍是未来工作。本文没有因此实现一个在线可靠性模型，也没有证明离线训练能学会此前教师轨迹未覆盖的全部环境状态。

<a id="implementation"></a>
## 8. 官方代码：从原始轨迹到真实 loss

本节是固定 C commit 与其固定 slime submodule 的**静态事实**。没有执行训练，也没有证明这份发布代码的默认配置逐项等于论文每个实验。检查看到的入口为数学单域，搜索生成器与文档用于核对零工具语义，多域数据源用于核路由；不宣称整个仓库所有路径已审计。

### 8.1 Pool builder：只保留前缀，离线按概率丢行

`data/build_prefix_pool_math.py` 的主流程是收集 `rollout_*.pt` 的 messages，检查结构，找到 assistant 位置，将每一处之前的消息变为独立行，再按 $\kappa^{j+offset}$ 做一次独立随机保留。[C4][C4]

关键事实如下。

**验证是结构性的。** 默认 strict 检查 system/user/assistant/tool、工具JSON、非空Python、调用后有工具响应、最后assistant没有未完成调用并含可解析 `\boxed{}`。`collect_trajectories` 和 `fan_out_prefixes` 没有按与参考答案相等或 reward=1 筛选。因而不应把发布池叫作“全部成功教师轨迹”。只有最终答对的样本才能使用，也不是本文理论的必要条件。

**Target 没有被直接复制进 prompt。** 第j个assistant位置使用 `messages[1:j]`，删除原system，不包含该assistant的原动作或未来观察；label另配，metadata含task、turn index和总assistant turns。渲染时再加系统和工具描述，因此这是消息语义上的重放，不是教师原始token ID的无损运输。

**默认与发布复刻选项不同。** 默认 `exponent_offset=0`，第一assistant位置保留概率为1；代码说明 `offset=1` 用来重现发布math pool的额外一倍 $\kappa$ 保留率。统一归一化后 $\kappa^j$ 与 $\kappa^{j+1}$ 的相对形状相同，但一次Bernoulli采样的实际数量／覆盖不同，默认命令不应宣称精确再生所有发布行数。

**不是每次update都重新抽完整池。** builder先随机丢行，训练阶段对留下的数据shuffle。对长度K的轨迹，offset0的预期保留量为 $(1-\kappa^K)/(1-\kappa)$；$\kappa=0.6$时上界为2.5。长轨迹不再线性地产生K倍数据，但各题实际权重仍受轨迹数、过滤、K和随机保留影响。这个算式是对代码的读者推导，不是论文新的实测结果。

搜索builder本轮没有逐行通读；[C3、C11]描述了inline search JSON、去除泄漏终止标记和最终boxed结构检查。它与math的工具格式不同，不能仅靠math validator代证搜索数据质量。

### 8.2 真实单轮生成：确实在执行工具前停止

数学入口 `scripts/train/reopd_math.sh` 设置 `TOOL_SANDBOX_MAX_TURNS=1`、`TOOL_SANDBOX_MAX_TOOL_CALLS=0`。`generate_with_retool.generate` 在收到assistant输出、处理token后，先检查这两项，再决定是否调用 `execute_predictions`，因而所读路径不执行新的Python动作。函数还明确不支持partial rollout。[C5、C7]

搜索的 `generate_with_search.generate` 在预测一个动作后，遇到 `SEARCH_R1_CONFIGS["max_turns"]==1` 直接break，位置在 `await execute_predictions` 之前。因此正确生效的单轮配置也不发起新的search调用。[C8，约L548附近]

但 `docs/search.md` 仍写“单样本最多一次search”和“仍启动retriever”，并要求DATA_DIR；这与上述早停代码不一致。**需要区分无工具请求与环境服务是否还被脚本部署。** 本稿只确定生成路径的分支顺序，没有实跑search脚本证明完全释放检索器资源，更不据文档旧句子否认论文方法的零调用设计。[C11][C11]

### 8.3 重新分词、拼接与概率对齐仍需检查

数学路径以 `input_ids` 调SGLang；搜索路径以 `text` 调SGLang，并从返回的token/logprob构建训练数据。两者都会清理超出第一完整动作的文本。理想路径寻找与清理文本一致的原token前缀；在无法匹配时，搜索 `_trim_response_token_prefix` 会重新tokenize并截取／补零原logprob。[C7、C8]

这是一条条件性对齐风险：长度相等不证明新token和旧概率逐项对应。当前单轮路径使状态组织更简单，却不自动带来TITO或训推完全一致。本次没有执行token对拍，不报告实际漂移率。

在线基线会在response中拼入新工具观察，观察mask为0；ReOPD的历史观察已在prompt中，当前新assistant token才是训练位置。不是将历史tool response作为新action监督，也不是ECHO式observation CE。

### 8.4 教师接口不是保存的完整 vocabulary logits

`generate_with_multiteacher_opd._teacher_logprob` 向冻结SGLang教师发送**学生的 `sample.tokens`**，设置 `max_new_tokens=0`、`return_logprob=True`、`logprob_start_len=0`，读取 `input_token_logprobs`。[C9][C9]

这是对学生已采样token的概率打分，不是生成教师答案，也不是取得全词表分布。token ID直接交给教师，代码未实现通用跨词表映射。相同Qwen模型族、复制chat template均不自动证明全部特殊token、词表与输入意义相同。教师请求里temperature=0用于无新生成的打分请求，不能解释成教师目标必然是一个argmax点质量。

多教师通过metadata.task选择retool或search-r1 endpoint；分别限制in-flight请求，避免不同容量教师共享一个拥塞队列。教师prefill处理长输入仍有成本，不能只按新生成action长度估计教师GPU负载。

### 8.5 实际优化：采样token的logprob差，进入policy surrogate

发布math脚本名称中虽有 `GRPO_ARGS`，但纯蒸馏默认 `MULTITEACHER_OPD_USE_TASK_REWARD=0`。task scorer仍计算日志，`_normalize_rewards` 返回训练reward全0；它不是用这组标量奖励为学生做outcome-GRPO。[C5、C9]

固定slime的 `apply_opd_kl_to_advantages` 计算：

$$
A_j \leftarrow A_j^{base}-\beta(\log p_{student,j}-\log p_{teacher,j}).
$$

在该纯OPD路径，base项来自零task reward；随后 `policy_loss_function` 使用更新学生／旧学生的概率比及clip进行策略损失，而不是在两端收集全vocabulary张量直接计算式中的KL。[C12][C12]

这可以是reverse-KL的采样实现思路，但不能将“论文分布KL”“采样token概率差”“PPO clipping后的有限步surrogate”当成字面相同的计算。对固定上下文、$p_{old}=p_\theta$、未裁剪的一步局部梯度，$E_{a\sim p}[\log(p/q)\nabla\log p]$与 $\nabla KL(p\Vert q)$一致，常数项因score期望为0而消失。**这是读者的一步条件化推导**，不证明多步更新、变长分母、训练／推理概率不一致时完全等价。

脚本实际设 `eps_clip=0.2`、`eps_clip_high=0.28`，而P3 Table1对OPD/ReOPD列为“—”；差异应记录，不能倒填历史表格。独立KL正则系数默认0，也不等于OPD系数0：`opd_kl_coef`默认1。

**归一化也不是小细节。** `cp_utils.get_sum_of_sample_mean` 在非per-token路径按每行有效token数求均值，再求样本和；`loss_function`进一步按global batch、microbatch和DP缩放。per-token分支不同，且其token normalizer会对空mask使用clamp。论文未给出与这些工程分母逐项对应的完整公式。本轮未验证实际运行解析后的所有默认项及Megatron跨rank归约，因此不宣布“最终全局目标与论文sum完全等价”。[C12、C13]

### 8.6 教师失败不是没有信号

教师请求失败时，helper返回None；`_extract_teacher_log_probs` 随后生成response_length长的**零向量**。教师返回短序列时也会左侧补零；当前后处理记录warning，但未在这里把相应学生action mask清零。[C9][C9]

与C12相接，若这条样本继续被消费，纯OPD信号会变成 $A_j=-\beta\log p_{student,j}$，一般并非0。这既不是正确教师概率，也不是“缺失信息自然被忽略”。需要沿实际生产路径验证或改成明确处置，不能把异常运输的数据当作可信蒸馏目标。

这是固定提交上的**条件性静态发现**：本轮没有触发网络错误、没有复现训练污染，也没有证明它影响了论文结果。避免将这一发现写成上游通用故障；同时，不能因为task reward为0，就认为该样本对训练无影响。

### 8.7 配方、混合与调度的实际边界

| 项目 | 发布路径所见 | 与论文／复用的关系 |
| --- | --- | --- |
| 数学ReOPD生成长度 | max response默认4096、context8192，生成器再留16token余量 | P3 Table1数学8192，不能说默认配方只有prefix不同 |
| 数学OPD长度 | response默认8192；未显式给相同context上限 | 其他上限由配置推导；必须统一实验条件后比较 |
| student分配 |4GPU，train/rollout共置；4B/8B预设，8B启CPU optimizer offload | 不能说8张都用于student训练 |
| teacher分配 |另4GPU；4B/8B TP1×DP4，30B TP2×DP2 |教师与学生各需资源；Qwen30B这里主要作teacher |
| runtime |调用slime `train.py`，generate完成后训练，再publish |是batch屏障路径，不是miles fully-async teacher更新 |
| 混合数据 |`MixedTaskDataSource`按task_order轮流取各池，支持重复task改变比例 |与先concat后shuffle的边际可能不同；需记录实际配置 |
| 任务身份 |每行复制为n个Sample并绑定task/group/index |n=1不需要组内奖励方差，仍不能丢失来源身份 |
| kappa位置权 |已在池构建发生；generator元数据的OPD权重为1 |不是每次loss再乘一次0.6^t |
| 依赖 |slime submodule固定；PyTorch/CUDA/SGLang等安装并非完全锁定 |开放代码不等于完整容器可复现 |

来源：[C5、C6、C10、C14]。`MixedTaskDataSource`保存数据偏移、epoch、task cursor和sample identity；本轮不据此宣称所有在途buffer及故障恢复都实现exact replay。项目若复用，仍需按自己异步消费合同验证。

### 8.8 本轮代码阅读范围清单

| C编号 | 文件／实际读到的范围 | 目的 |
| --- | --- | --- |
| C1 | root README，主要安装、数据与训练段 |模型、资产、实际入口，不声称所有权重验证 |
| C2 | train/README.md 全文 |封装和env配置边界 |
| C3 | data/README.md 全文 |发布行数与前处理说明 |
| C4 | build_prefix_pool_math.py 全文 |结构过滤、fan-out、kappa、offset |
| C5 | reopd_math.sh 全文 |teacher启动、学生训练配置、纯OPD和单轮 |
| C6 | opd_math.sh L245–340 |具体基线参数差异 |
| C7 | generate_with_retool.py L430–690 |动作截取、prompt生成、零工具分支；未读完整sandbox实现 |
| C8 | generate_with_search.py 开头至约430、L450至文件末尾 |渲染、裁剪、单轮执行边界、mask与指标；不称全文无缺行审计 |
| C9 | generate_with_multiteacher_opd.py 全文 |teacher路由与打分、失败填充、训练reward |
| C10 | mixed_data_source.py 全文 |实际混合比例、row/group身份与偏移 |
| C11 | docs/search.md 全文 |环境部署、资产、文档与代码差异 |
| C12 | slime loss.py L1–240、480–750、805–1020、1090–末尾 |目标消费、OPD penalty、policy loss及归约包装 |
| C13 | slime cp_utils.py L1–200 |sample/token reducer与mask边界 |
| C14 | slime train.py 全文 |屏障、训练及权重更新时序 |

没有检查全部search builder、完整eval实现、所有数据集revision、训练动态默认参数及失败注入。以此范围解释静态发现，不将缺失项写成作者没有实现。

<a id="unknowns"></a>
## 9. 差异、未披露与待补证据集中表

| 项目 | 状态 | 怎样处理 |
| --- | --- | --- |
| 精确v3 PDF／图中数值 |本轮获取失败，非作者未公开 |v3 HTML为主；V2图值单列；以后定点补图，不重做整篇 |
| 冷启动与双域成绩 |v2/v3明确不同 |使用v3，保留差异表 |
| 4196、ReOPD工具上限列、Table5图注 |v3正文／表内表述疑点 |逐字保留关键值，明确不确定，不自改配方 |
| §5.2“Table8” |链接与后文实际是Figure8 |按Figure8定位，不虚构第八张表 |
| 历史相关权重与位置代理 |理论与实用设计不同，源文承认 |不称kappa精确IS或理论最优策略 |
| 可靠性 |q*不可用，teacher support为代理 |性能趋势不等于直接测得教师错误 |
| 分布KL与公开训练目标 |公开代码走token logprob差＋policy surrogate |分别记录；等价需要条件与数值验证 |
| 默认配置vs论文 |长度、clip、pool offset等不同 |复现时固定实际配置，不能把差异归零 |
| 搜索环境部署 |文档与零调用代码描述不一致 |区分服务是否启动与请求是否发送，需实跑 |
| 原始教师池 |混合checkpoint，结构过滤不等于全答对 |不要当作冻结最终teacher的精确occupancy |
| 教师失败logprob |当前helper零填充，可能仍产生梯度 |静态风险，待最小复现；不冒称论文受影响 |
| 完整样本与成本 |缺一份覆盖题数、token、动作、教师、环境、失败作业的总账 |4×/9×限定到报告的rollout比较 |
| 评测置信区间 |未给训练多seed/统计检验 |保留微小均值变化和单项回退，不宣称显著 |
| SWE/harness泛化 |无对应实验 |Python数学不等于软件仓库后训练 |
| 公开权重与数据 |collection可访问，未实际下载核验 |不宣称模型/数据已经可直接在本项目训练 |

## 10. 本稿独立核算：只验证解释，不伪装成论文复现

作者自查使用标准库完成以下计算，结果见检查记录。它们不运行论文代码、GPU或环境：

**条件历史归一化**：固定t时两个历史都乘相同kappa^t，再按条件期望归一化，两者权重都为1；说明位置衰减必须改变跨位置分布。

**抽样与双重加权**：比较按kappa^t抽样的无权loss，与固定池的正规化权重平均；相等。若再乘同样权重则改变目标。这个检查不证明静态Bernoulli有限池与每轮动态采样逐次相同。

**局部reverse-KL梯度**：在二分类softmax、冻结q、旧学生等于当前学生的例子中，用有限差分检查KL梯度与log-ratio score-function期望一致；不外推到clipping激活、历史分布梯度或变长全局分母。

**表格算术**：复算数学macro、搜索micro、双域v3数学平均、成本比与Bamboogle影响。表中一位小数可能造成平均末位差异；不据此断言原实验算错。

<a id="project"></a>
## 11. 对RepoHarness的条件化意义

项目映射日期：2026-09-24。只使用9月23日同步基线；已有环境修订、独立求解与67次探针不等于正式八卡学习链验收。本稿不选新基座，不变更GRPO／DIS，不批准新任务或教师API。

### 11.1 它提供的竞争方案

对已有高成本教师交互，ReOPD提出“保存可复用历史、离线训练当前动作、独立在线测效果”的方案。它可能降低学生训练中的sandbox／检索负担，而不是通过提高worker并发继续支付同样交互成本。这与miles负责的调度和捕获是不同层次，可以讨论但无需替换整套infra。

**首先要纠正一个容易产生的担心**：ReOPD本身没有在学生修改代码后，接上教师旧的测试结果并假装是新代码结果；当前动作后不执行、也不继续这条学生世界线。对SWE的真实限制是：历史文本是否足够表达待决状态、教师能否评价该动作、以及离线动作学习是否迁移到活的仓库执行。需要现场评价，而不是修一个论文并没有做的“伪造转移”。

### 11.2 本项目现有轨迹并不是免费且天然兼容的池

当前池包含不同solver、版本、预算和harness条件，评分还有范围争议。它们不自动满足“目标教师自己的交互支持”。原文Fig.7恰好提示前缀生成者与评分教师不匹配可能恶化结果。不能把更强闭源solver轨迹随意交给一个较弱本地teacher评分，就沿用作者的结论。

还需要确认：teacher可对学生token提供什么概率接口；词表／模板是否一致；prompt是否夹带private grader、harness日志或后来新增信息；保存的是模型真实可见历史还是事后汇总。这些是实际表示与可见性问题，不应靠重命名字段解决。

### 11.3 对“全零组”的帮助有限定

本方法可以在没有环境终局reward差异时提供token级蒸馏信号；它不修复错误评分，不证明teacher正确，也不会让不可见的仓库事实凭空可知。纯GRPO的零方差过滤如果无条件放在所有训练目标之前，会丢掉这种潜在信号；但是否增加另一条目标消费路径，要在teacher数据和收益确实成立后决定，而不是先重写rh2。

Conan那类部分修复未被区分，需要先澄清合法任务语义；不能让teacher偏好代替应有的可执行验证。对于真正不会修复的全失败任务，ReOPD也不替代基本技能学习或可达到的训练任务选择。

### 11.4 一个最小辨识方案，而不是直接全面接入

先选择一小批**已经裁定题义、环境与评分稳定**的任务，固定harness与预算，取得一个可提供合法token概率的教师。在部分教师历史上让学生只生成当前动作，不执行；比较教师自身前缀、学生可见错误前缀、不同深度下的概率和动作可用性，并核对实际token。

只有这一步确有可用监督，再比较同初始化的原模型、完整轨迹SFT、简单uniform prefix distillation与step-decay；保留小规模在线OPD作为条件对照。最终效果必须在隔离且真实执行的任务上测量，报告前缀生产、teacher scoring、训练和评测的全部成本。没有预算时，不能以离线loss下降代替SWE能力提升。

这里的实验建议是读者推论，不是已批准任务，也不是论文在SWE上已经验证的流程。对当前优先级，ReOPD是有价值的备选训练路径，不应阻塞正式链、预算和评分语义的先行对齐。

### 11.5 这篇新增和削弱了哪些判断

**新增**：完全学生roll-in不是唯一合理的OPD训练分布；教师在学生历史上的监督质量本身值得检查。环境数据可以保存为前缀资源，但仍要在线获取当前学生动作的teacher概率。

**削弱**：“更强前缀生成器一定更好”“有更多on-policy历史必定更有效”“零工具成本等于总训练免费”“离线复用可直接证明SWE收益”等推论。

**没有改变**：正式评分有效性、实际输入token与概率对齐、策略／教师版本身份和独立held-out评测仍是必要条件。论文阅读不替代这些资格验证。

<a id="review"></a>
## 12. 交付状态与维护

**v3 HTML全文、全部公式／表格／图注、主要官方执行路径及作者自查完成；v3 PDF图页独立核验待补，独立审查与GPU／环境复现均未完成。** 旧版PDF检查只用于发现和标明差异，不计成v3全图完成。

本任务只维护本篇及 [作者自查记录](reviews/reopd_v3_self_check_20260924.md)。不修改共享阅读计数、不合并其他Pro分支、不修改训练配置或实现。后续拿到确切v3 PDF，应优先核Fig.1/4/5/7/8、Table1/6版本变化及所有图中独有数值，而非再从摘要开始重读。

## 来源与可复核入口

[P3]: https://arxiv.org/html/2607.04763v3
[ABS]: https://arxiv.org/abs/2607.04763
[V3PDF]: https://arxiv.org/pdf/2607.04763v3
[V2PDF]: https://arxiv.org/pdf/2607.04763v2
[WEB]: https://baohaoliao.github.io/ReOPD/
[REPO]: https://github.com/BaohaoLiao/ReOPD/tree/7a499d29ab07ff50dfde039f9d7a44dfe313b95e
[HF]: https://huggingface.co/collections/baohao/reopd
[C1]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/README.md
[C2]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/train/README.md
[C3]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/data/README.md
[C4]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/data/build_prefix_pool_math.py
[C5]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/scripts/train/reopd_math.sh
[C6]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/scripts/train/opd_math.sh
[C7]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/train/src/generate_with_retool.py
[C8]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/train/src/generate_with_search.py
[C9]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/train/src/generate_with_multiteacher_opd.py
[C10]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/train/src/mixed_data_source.py
[C11]: https://github.com/BaohaoLiao/ReOPD/blob/7a499d29ab07ff50dfde039f9d7a44dfe313b95e/docs/search.md
[C12]: https://github.com/BaohaoLiao/slime/blob/26525f97179afc47c9ef6fff045dbc28d79f1875/slime/backends/megatron_utils/loss.py
[C13]: https://github.com/BaohaoLiao/slime/blob/26525f97179afc47c9ef6fff045dbc28d79f1875/slime/backends/megatron_utils/cp_utils.py
[C14]: https://github.com/BaohaoLiao/slime/blob/26525f97179afc47c9ef6fff045dbc28d79f1875/train.py

主来源定位使用本稿各节标出的P3章节／表图／式号；C编号为上述固定commit路径，并非聊天工具临时引用。参考来源中的代码许可与论文、模型、数据许可分别判断；本稿没有上传原PDF、权重或第三方代码副本。
