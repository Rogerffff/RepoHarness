# SWE-2 基线理论核查：Greensmith、Kool 海报、OPO 与有限样本语义

本文是 SWE-2 的配套定点核查，不是一篇声称“重新完整读完全部 baseline 文献”的综述。核心结论是：总体最优标量 baseline、同组经验估计、LOO、长度代理，以及 clipped/off-policy/归一化后的实际梯度，是不同对象。它们之间有明确联系，但不能因最后都出现一个组均值就混为同一算法。

导航：[范围](#scope) · [总体最优](#population) · [有限样本](#finite) · [原始来源边界](#references) · [可运行检查](#code)

<a id="scope"></a>
## 1. 来源与实际覆盖

阅读日期 2026-09-12；源包与项目基线同 [SWE-2 主笔记](cognition_swe2.md)，即 `d8bdc510c2da950fe51987f614f68b7969061153` 的 Cognition 2026-09-11 来源补充。

| 来源 | 实际覆盖 | 不应误标的状态 |
| --- | --- | --- |
| SWE-2 正文、Appendix B/C | 全读，公式／视觉与原文块核对 | 发布报告没有完整 trainer 实现 |
| OPO `2505.23585v2` | 13 页全文、附录和全部图表；[单独笔记](opo_2505.23585v2.md) | 不是实际 off-policy SWE 算法的证明 |
| Greensmith / Bartlett / Baxter 2004 | 60 页 PDF 可读；重点读引言、问题设定、§5 baseline 定理、§7 估计讨论，核 PDF pp.9–10、16–20、26、29–30 | **只完成本专题相关部分，不是 60 页全文精读** |
| Kool / van Hoof / Welling 2019 | 作者一页海报完整查看，包括有放回／无放回公式和 TSP 图 | **全文未取得，海报不能代替论文** |

后文“读者推导／算术检查”均明确标识，不将其写成任何作者已经做过的实验。

<a id="population"></a>
## 2. 总体最优 baseline 的准确对象

### 2.1 为什么基线不改变期望梯度

固定 prompt $x$、normalized policy $p_\theta(y\mid x)$，令 $z=\nabla_\theta\log p_\theta(y\mid x)$。在允许交换微分和积分、支持集相容等条件下：

$$
\mathbb E[z]=\sum_y p_\theta(y\mid x)\nabla_\theta\log p_\theta(y\mid x)
=\nabla_\theta\sum_y p_\theta(y\mid x)=0.
$$

若 $b=b(x)$ 不依赖本条采样动作，$\mathbb E[(R-b)z]=\mathbb E[Rz]$。固定条件下，向量估计器的协方差迹为二阶范数期望减均值范数平方；均值与 $b$ 无关，故优化

$$
Q(b)=\mathbb E[(R-b)^2\|z\|^2]
$$

即可。其导数零点是

$$
b^*=\frac{\mathbb E[R\|z\|^2]}{\mathbb E[\|z\|^2]}.
$$

并有恒等式

$$
Q(b)-Q(b^*)=\mathbb E[\|z\|^2](b-b^*)^2.
$$

前面形式来自 SWE-2 Appendix C/OPO Appendix A；最后恒等式是直接展开所得，也与 Greensmith 的加权平方误差观点对应。这里未把 Markov 长程估计器的全部混合时间界移植到 LLM 场景。[SWE-2][S2] [OPO][OPO] [Greensmith][G]

### 2.2 三种“最优”不能互换

最小化 $\mathbb E[(R-b)^2]$ 得 reward 均值；最小化完整 Euclidean gradient 方差得上述 score-norm 权重；若关心经过某个固定线性预条件器 $M$ 的梯度，则权重变成 $\|Mz\|^2$。实际 Adam 状态、clipping、跨 rank reduction 和变化的 mask 比固定 $M$ 更复杂。**一个 baseline 对某个估计器最优，不等于对所有参数更新规则最优。**[后半为读者数学解释]

### 2.3 token 长度为何只是代理

令 $z=\sum_t z_t$，则

$$
\|z\|^2=\sum_t\|z_t\|^2+2\sum_{s<t}z_s^\top z_t.
$$

要由长度近似它，需要控制交叉项及各 token 范数差异。OPO 明确提出近似正交与相近范数分布的假设；SWE-2 提供 K3 经验散点。两者都不构成任意长轨迹、工具控制 token、截断和压缩条件下的逐条等式。

本次还发现 SWE-2 的绘图脚本从 983 点中滤去 39 个高于 yMax 的点；全部显示数据 Pearson 约 0.268，而过滤后约 0.691，详情见主笔记 §5.3。它限制“只凭图证明全部轨迹均高度线性”的说法，但不能替代用真实训练梯度比较 baseline 的效果。

<a id="finite"></a>
## 3. 同组估计、LOO 与 finite-sample bias

### 3.1 普通组均值的偏差可直接算出

若 $(R_i,z_i)$ 同策略独立同分布，$\bar R=\frac1n\sum_jR_j$，则

$$
\mathbb E\left[\frac1n\sum_i(R_i-\bar R)z_i\right]
=\frac{n-1}{n}\,\mathbb E[Rz].
$$

其中 own-sample 项贡献 $\frac1n\mathbb E[Rz]$，其他样本因独立及 $\mathbb E[z_i]=0$ 消失。LOO

$$
b_{-i}=\frac1{n-1}\sum_{j\ne i}R_j
$$

给出无偏估计，并与 $\frac1{n-1}\sum_i(R_i-\bar R)z_i$ 等价。这就是 Kool 海报中 **with replacement** 部分的关键关系；没有乘 $n/(n-1)$ 的普通 mean-baseline 估计器不等于海报的无偏式。[Kool 海报][K]

这里只讨论估计器期望。一个常数缩放在带 Adam、梯度裁剪、有限精度和动态 batch 的完整训练中是否无关，还需要单独判断。

### 3.2 长度加权同组基线一般不只造成一个常数缩放

$$
\widehat b_L=\frac{\sum_jL_jR_j}{\sum_jL_j}.
$$

其分母和分子共同依赖本条样本，普通组均值的 $(n-1)/n$ 推导不能原样套用。只要 $L$ 与采样动作有关，就可能改变期望梯度方向，而不只是整体幅度。

**本轮独立有限枚举，非作者实验。** 四动作 softmax 模型，$p=(1/4,1/4,1/4,1/4)$，score 为 $z_j=e_j-p$，reward 为 $(1,0,2,-1)$，人为指定长度 $(1,3,2,6)$。这个玩具例不声称模拟真实自回归 token 或真实梯度范数，只用于区分 baseline 的样本依赖。

真实梯度为 $(0.125,-0.125,0.375,-0.375)$。穷举所有 $4^n$ 组得到：

| n | baseline | 期望梯度四个分量 |
| --- | --- | --- |
| 2 | 同组普通均值 | (0.062500, −0.062500, 0.187500, −0.187500) |
| 2 | 同组长度加权 | (0.052530, −0.083780, 0.176637, −0.145387) |
| 2 | 排除自身的长度加权 | (0.125000, −0.125000, 0.375000, −0.375000) |
| 4 | 同组普通均值 | (0.093750, −0.093750, 0.281250, −0.281250) |
| 4 | 同组长度加权 | (0.092846, −0.117132, 0.278322, −0.254036) |
| 4 | 排除自身的长度加权 | (0.125000, −0.125000, 0.375000, −0.375000) |

由于其他样本独立于第 i 条，任何仅由其他样本计算且有适当矩的 $b_{-i}$ 都满足 $\mathbb E[b_{-i}z_i]=0$；不要求它恰好等于总体最优值。但这只恢复该理想估计器的期望，**不保证方差更小，更不保证模型学习更好**。本稿没有建议把 SWE-2 改成 LOO，也没有证明它的原配方失效。

### 3.3 与真正训练消费有关的四个边界

**组与过滤。** 同 prompt 的样本若经过成功筛选、不同终止规则、policy-version 混合或非独立的分支复制，以上 iid 推导需要重新检查。删除某成员、屏蔽其梯度、仍保留其 reward 到别人的 baseline，是不同操作。

**长度与 segment。** 若逻辑 rollout i 被切成多个训练 row，$L_i$ 应由声明的目标决定；对每个 row 重新加权不是自动等价的实现。若 mask 改变了 token，不能把输出长度直接当 trainable length。

**loss 分母。** 将 $z$ 替换成 $z/L(y)$ 后一般没有 $\mathbb E[z/L]=0$；因此 action-dependent 的每序列归一化会影响“任意常数 baseline 无偏”的简单论证。需要从实际目标导出，而不是只替换 reward mean。

**off-policy/clipping。** 对行为分布 $q$ 采样，需要完整相容的重要性校正等条件才能恢复目标 score 身份；逐 token ratio、截断、clipping 和 policy 漂移不自动满足它。SWE-2 本文已经承认其实际 baseline 不再严格最优，不能用 OPO on-policy 证明取消这项限制。

<a id="references"></a>
## 4. Greensmith 2004：真正支持什么

完整标题 *Variance Reduction Techniques for Gradient Estimates in Reinforcement Learning*，JMLR 5（2004）1471–1530。本文提供的是 average-reward GPOMDP/POMDP 梯度估计、控制变量、baseline 与 actor-critic 的理论，而非 LLM specific recipe。[原始 PDF][G]

本轮对应位置：

| PDF 物理页／印刷页 | 核查对象 | 在本专题中的用途 |
| --- | --- | --- |
| 9–10 / 1479–1480 | 方差、向量方差定义与相关性 | 总方差采用 covariance trace；有限 Markov 估计不等于 iid rollout |
| 16–17 / 1486–1487 | §5.2，Theorem 8、Lemma 9、Theorem 10 | 最优基线及与次优基线之差的加权平方形式 |
| 18 / 1488 | Theorem 11、Corollary 12 | constant baseline 的 score² 加权式；平均 reward 不一般最优 |
| 19–20 / 1489–1490 | §5.3，observation-conditioned baseline、Theorem 13 | 不同可观测条件对应不同条件期望，不能只写同一个无条件均值 |
| 26 / 1496 | §7.1、Theorem 20 | 估计 baseline 时的加权平方拟合观点 |
| 29–30 / 1499–1500 | 算法与学习 baseline 的讨论 | 在线更新 baseline 会改变收敛分析；文中没有据此给所有联合训练的保证 |

特别注意，Theorem 11 的符号涉及 state/action transition score 与折扣回报对象 $J_\beta$；不能将它逐字替换成任何现代 clipped PPO 目标。现代独立 rollout 的简洁证明可直接从 §2 导出，但那应标作相应设定下的推导，而不是声称老论文覆盖了全部条件。

本文没有全面精查 §6 actor-critic、所有 Markov mixing 界和全套模拟实验；不据此宣布 critic 不必要或 value function 无用。精确“最优 baseline”和正确价值估计是不同目标，这篇论文讨论了其区别。

## 5. Kool 2019：海报的内容与缺口

海报标题 *Buy 4 REINFORCE Samples, Get a Baseline for Free!*，Wouter Kool、Herke van Hoof、Max Welling，ICLR 2019 相关 workshop。已完整查看一页海报。[本地原始海报][K]

**有放回采样**给出独立样本的 LOO 公式与组均值等价重写。**无放回采样**依赖 stochastic beam search、阈值／重要性权重等不同机制，不能因为同样有 K 个样本就继续套独立有放回结论。海报还讨论 self-normalization 的偏差与方差取舍。

图例为 TSP20、K=4/8 等小实验，显示两种随机种子曲线。没有取得全文，不补写完整训练预算、全部证明、所有任务或原作者未显示的方差结果。原 OpenReview 入口受验证限制，作者 Drive 链接在采集时失效；上传包已明确标 `POSTER_ONLY`。当前没有解决全文缺口。

<a id="code"></a>
## 6. 可复核的有限枚举

下列代码仅验证 §3 的数学例子，不导入任何模型，不执行官方网页脚本，也不读测试集。运行得到表中结果；无需 GPU。它不是新算法实现或训练复现。

```python
from itertools import product
import numpy as np

p = np.full(4, 0.25)
z = np.eye(4) - p
reward = np.array([1.0, 0.0, 2.0, -1.0])
length = np.array([1.0, 3.0, 2.0, 6.0])
truth = np.einsum("i,i,ij->j", p, reward, z)
for n in (2, 4):
    result = {key: np.zeros(4) for key in ("mean", "weighted", "weighted_loo")}
    for choices in product(range(4), repeat=n):
        idx = np.array(choices)
        r, l, score = reward[idx], length[idx], z[idx]
        probability = np.prod(p[idx])
        baselines = {
            "mean": r.mean(),
            "weighted": np.sum(r*l)/np.sum(l),
            "weighted_loo": (np.sum(r*l)-r*l)/(np.sum(l)-l),
        }
        for key, baseline in baselines.items():
            result[key] += probability * np.mean((r-baseline)[:, None]*score, axis=0)
    assert np.allclose(result["mean"], (n-1)/n*truth)
    assert np.allclose(result["weighted_loo"], truth)
    print(n, result)
```

同样的源包检查还完成：983 散点与过滤后 944 点计数、12 条展示的长度／token 求和、48 个安全区间端点核对，以及主文引用的百分比算术。它们都是对公开显示数据或人为数学模型的检查，没有证明真实训练样本完全如此。

## 7. 对 A 线最实用的结论

需要先固定“我们实际在估计哪个梯度”，再决定 baseline。最少应明确逻辑 rollout、组成员、sampled action token、行为／目标策略、截断与过滤、reward 处理、最终分母。之后再对真实有限组比较 bias/variance 与短训练结果。

**不建议以“理论最优”四字替代这些事实，也不建议因为有限样本存在偏差就自动否定实践方法。** 本稿提供检查问题与可运行例子；采用什么配方仍需本项目实验。

状态：定点理论核查与作者自查完成；无独立 reviewer、无训练复现。详细质量记录见 [本轮自查](reviews/cognition_swe2_self_check_20260912.md)。

[S2]: source_supplements/cognition_20260911/swe-2/reading_text.md
[OPO]: source_supplements/cognition_20260911/papers/opo_2505.23585v2.pdf
[G]: https://jmlr.org/papers/volume5/greensmith04a/greensmith04a.pdf
[K]: source_supplements/cognition_20260911/papers/kool_2019_POSTER_ONLY.pdf
