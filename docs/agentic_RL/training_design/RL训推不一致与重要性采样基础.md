# RL 训推不一致与重要性采样基础

本文用于回顾三个容易混在一起的问题：

1. 离散动作不可微，为什么仍然可以训练策略？
2. `score-function`、Monte Carlo 和 `reparameterization` 分别解决什么问题？
3. rollout 策略和当前训练策略不一致时，重要性采样如何校正分布？

本文只讲通用数学和直觉，不讨论具体训练框架、项目代码或工程闸门。

---

## 1. 先区分三个不同层次的问题

下面三件事经常同时出现，但它们不是同一个问题。

| 问题 | 典型方法 | 它解决什么 |
|---|---|---|
| 如何对含随机采样的期望求梯度 | score-function 或 pathwise derivative | 构造可计算的梯度公式 |
| 如何计算公式中的巨大期望 | Monte Carlo | 用有限样本近似期望 |
| 样本来自旧策略，目标却是当前策略 | importance sampling | 把一个分布下的期望改写到另一个分布下 |

最重要的结论是：

> 策略梯度从一开始就不需要对离散动作本身求导。它对“策略为各个动作或轨迹分配的概率”求导。score-function 恒等式把这个梯度写成可采样估计的形式，Monte Carlo 再负责避免枚举所有动作和轨迹。

---

## 2. 离散动作本身不需要参与求导

先考虑只有一个状态、两个离散动作 `A` 和 `B` 的问题。策略的目标是最大化期望奖励：

\[
J(\theta)
=
\mathbb E_{a\sim\pi_\theta}[R(a)]
=
\pi_\theta(A)R(A)
+
\pi_\theta(B)R(B)
\]

这里：

- `A` 和 `B` 是固定的离散标签；
- \(R(A)\) 和 \(R(B)\) 是选择对应动作后得到的奖励；
- \(\pi_\theta(A)\) 和 \(\pi_\theta(B)\) 是策略分配给两个动作的概率；
- 模型参数 \(\theta\) 变化时，动作标签不会变化，变化的是动作概率。

因此直接对参数求导：

\[
\nabla_\theta J
=
R(A)\nabla_\theta\pi_\theta(A)
+
R(B)\nabla_\theta\pi_\theta(B)
\]

整个推导都没有出现：

\[
\frac{\partial A}{\partial\theta}
\quad\text{或}\quad
\frac{\partial B}{\partial\theta}
\]

这些导数既没有意义，也不需要存在。我们真正关心的是：

> 参数稍微变化后，高奖励动作被选中的概率是否上升，低奖励动作被选中的概率是否下降？

所以“离散采样不可微”不代表“离散策略无法训练”。它只意味着我们不能把离散动作当作普通连续中间变量，直接沿动作值反向传播。

---

## 3. Score function 与 log-derivative trick

### 3.1 Score function 的定义

对于参数化分布 \(p_\theta(x)\)，统计学中的 score function 定义为：

\[
\boxed{
s_\theta(x)
=
\nabla_\theta\log p_\theta(x)
}
\]

这里的 `score` 不是奖励，也不是 reward model 给出的分数。它表示：

> 已观察到的样本 \(x\) 的对数概率，对分布参数 \(\theta\) 有多敏感。

需要区分两个词：

- **score function**：\(\nabla_\theta\log p_\theta(x)\) 这个数学量；
- **score-function estimator**：使用这个量构造随机梯度估计的方法。

在这类问题中，下面几个名称通常指向同一条基本方法线：

- score-function estimator；
- likelihood-ratio estimator；
- log-derivative trick；
- 强化学习中的 REINFORCE estimator。

### 3.2 从期望奖励得到 score-function 形式

考虑有限动作空间：

\[
J(\theta)
=
\sum_a\pi_\theta(a)R(a)
\]

直接求导：

\[
\nabla_\theta J
=
\sum_aR(a)\nabla_\theta\pi_\theta(a)
\]

利用恒等式：

\[
\nabla_\theta\log\pi_\theta(a)
=
\frac{\nabla_\theta\pi_\theta(a)}{\pi_\theta(a)}
\]

得到：

\[
\nabla_\theta\pi_\theta(a)
=
\pi_\theta(a)
\nabla_\theta\log\pi_\theta(a)
\]

代回原式：

\[
\nabla_\theta J
=
\sum_a
\pi_\theta(a)R(a)
\nabla_\theta\log\pi_\theta(a)
\]

按照 \(\pi_\theta\) 加权求和就是期望，因此：

\[
\boxed{
\nabla_\theta J
=
\mathbb E_{a\sim\pi_\theta}
\left[
R(a)\nabla_\theta\log\pi_\theta(a)
\right]
}
\]

这个公式不需要对离散动作 \(a\) 求导。采样完成后，\(a\) 被当作固定的已观察样本；反向传播只计算该动作的 `logprob` 对模型参数的导数。

如果被积函数本身还显式依赖参数，即 \(f_\theta(x)\)，更一般的公式还会多出：

\[
\mathbb E_{x\sim p_\theta}
[\nabla_\theta f_\theta(x)]
\]

经典策略梯度推导通常假设环境奖励没有对策略参数的这种显式依赖。

---

## 4. Monte Carlo 只负责近似期望

上面的 score-function 公式仍然要求计算所有动作或所有轨迹上的期望。真实语言模型的轨迹空间极大，不可能完整枚举，因此使用采样近似：

\[
\nabla_\theta J
\approx
\frac{1}{N}
\sum_{i=1}^{N}
R(a_i)
\nabla_\theta\log\pi_\theta(a_i),
\qquad
a_i\sim\pi_\theta
\]

正确的逻辑顺序是：

```text
先写出期望目标
→ 对期望求导
→ 使用 log-derivative 恒等式
→ 得到 score-function 形式
→ 最后用 Monte Carlo 样本均值近似期望
```

因此不能说“Monte Carlo 让离散采样变得可微”。

更准确的说法是：

> Score-function 恒等式使我们不必对离散动作求导；Monte Carlo 使我们不必枚举所有可能的动作和轨迹。

下面这种做法并不能得到策略梯度：

```python
actions = categorical_sample(probs)
mean_reward = reward(actions).mean()
mean_reward.backward()
```

因为离散采样切断了这条直接反向传播路径。必须使用类似下面的 score-function surrogate loss：

```python
actions = categorical_sample(probs)      # 动作本身不求导
logp = distribution.log_prob(actions)    # 对策略参数可微
loss = -(reward.detach() * logp).mean()
loss.backward()
```

这里这个标量 `loss` 的主要用途，是让自动微分产生所需的策略梯度；它的数值本身不必等于负的期望奖励。

---

## 5. 另一条方法：Pathwise derivative / Reparameterization

Score-function 和 pathwise derivative 是随机梯度估计中的标准分类，不是强化学习项目中特有的术语。

### 5.1 连续随机变量的重参数化

假设：

\[
x\sim\mathcal N(\mu_\theta,\sigma_\theta^2)
\]

可以等价写成：

\[
\epsilon\sim\mathcal N(0,1)
\]

\[
x
=
\mu_\theta+\sigma_\theta\epsilon
\]

随机性现在来自与 \(\theta\) 无关的基础噪声 \(\epsilon\)，而 \(x\) 是 \(\theta\) 和 \(\epsilon\) 的可微函数。梯度可以沿着下面的路径传播：

```text
θ → μ, σ → x = μ + σε → f(x)
```

因此：

\[
\nabla_\theta f(x)
=
\frac{\partial f}{\partial x}
\frac{\partial x}{\partial\theta}
\]

这就是 pathwise derivative。把随机变量写成确定性可微函数与基础噪声的组合，就是 reparameterization trick。

### 5.2 为什么普通 categorical token 不适合这条路径

离散 token 采样类似：

```text
θ → token probabilities → categorical sample → token ID
```

概率稍微变化时，token ID 不会连续地从 `42` 变成 `42.1`；它可能保持 `42`，也可能突然跳到另一个整数。因此普通 categorical sample 没有可供反向传播使用的连续路径导数。

这时 score-function 方法很合适，因为它根本不需要：

\[
\frac{\partial a}{\partial\theta}
\]

两类方法可以这样区分：

| 方法 | 是否需要穿过采样结果反传 | 典型应用 |
|---|---:|---|
| Score-function / likelihood-ratio | 否 | REINFORCE、离散 token 策略梯度 |
| Pathwise / reparameterization | 是 | 正态随机变量、VAE、部分连续动作算法 |
| Monte Carlo | 不决定求导路径 | 用样本近似上述两类公式中的期望 |

Gumbel-Softmax、straight-through estimator 等方法会为离散变量构造连续近似或替代梯度，但它们属于额外近似，不是经典离散策略梯度的基本前提。

---

## 6. 扩展到语言模型的完整轨迹

一条强化学习轨迹可以写成：

\[
\tau
=
(s_0,a_0,s_1,a_1,\ldots,s_T)
\]

它的概率通常分解为：

\[
P_\theta(\tau)
=
\rho(s_0)
\prod_t
\pi_\theta(a_t\mid s_t)
P_{\mathrm{env}}(s_{t+1}\mid s_t,a_t)
\]

其中：

- \(\rho(s_0)\) 是初始状态分布；
- \(\pi_\theta(a_t\mid s_t)\) 是模型在当前上下文中生成 token 或动作的概率；
- \(P_{\mathrm{env}}\) 是环境状态转移概率。

如果环境转移本身不显式依赖模型参数 \(\theta\)，那么：

\[
\nabla_\theta\log P_\theta(\tau)
=
\sum_t
\nabla_\theta
\log\pi_\theta(a_t\mid s_t)
\]

所以轨迹级策略梯度为：

\[
\nabla_\theta J
=
\mathbb E_{\tau\sim P_\theta}
\left[
R(\tau)
\sum_t
\nabla_\theta
\log\pi_\theta(a_t\mid s_t)
\right]
\]

这并不是忽略了状态分布随策略变化的问题。状态访问分布的变化已经包含在整条轨迹概率 \(P_\theta(\tau)\) 中；我们不需要对环境执行过程本身做反向传播。

在语言模型实现中，可以把一次 token 训练直观地理解为：

```python
token_id = 42                         # 已采样的固定离散索引
logp = log_softmax(logits)[token_id]  # 对 logits 和模型参数可微
loss = -advantage.detach() * logp
```

反向传播时：

- 不对整数 `token_id` 求导；
- 不对工具返回文本和环境执行过程求导；
- 通常也不对已经计算好的 reward 或 advantage 求导；
- 梯度通过所选 token 的 `logprob` 流入 logits，再流入模型参数。

使用 advantage 代替原始 reward，主要用于降低方差并表达“这个动作相对基线好多少”。它不改变 score-function 的基本结构。

---

## 7. Logit、softmax、logprob 与梯度方向

### 7.1 Logit 是什么

模型在一个 token 位置先输出每个候选 token 的未归一化分数：

\[
z_A,z_B,\ldots
\]

这些分数叫 logits。softmax 把它们转换成概率：

\[
p_A
=
\frac{e^{z_A}}
{\sum_j e^{z_j}}
\]

对应的 logprob 为：

\[
\log p_A
=
z_A-log\sum_j e^{z_j}
\]

### 7.2 所选 token 的 logprob 对各 logits 的梯度

一般公式为：

\[
\frac{\partial\log p_A}{\partial z_j}
=
\mathbf 1[j=A]-p_j
\]

假设只有 `A` 和 `B`，并且：

\[
p_A=0.731,
\qquad
p_B=0.269
\]

那么：

\[
\frac{\partial\log p_A}{\partial z_A}
=
1-p_A
=
0.269
\]

\[
\frac{\partial\log p_A}{\partial z_B}
=
-p_B
=
-0.269
\]

正负号表示局部变化方向：

- 增大 \(z_A\)，会提高 `A` 的 logprob；
- 增大竞争 token 的 \(z_B\)，会降低 `A` 的 logprob。

对于常见的策略损失：

\[
L
=
-A\log p_A
\]

- advantage \(A>0\) 时，梯度下降倾向于提高已采样动作的概率；
- advantage \(A<0\) 时，方向反转，倾向于降低已采样动作的概率；
- advantage \(A=0\) 时，这个样本对策略梯度没有贡献。

### 7.3 函数值为零不等于梯度为零

例如：

\[
f(x)=x
\]

在 \(x=0\) 时：

\[
f(0)=0
\]

但：

\[
f'(0)=1
\]

因此，看到 `loss == 0`、`logprob == 0` 或 importance ratio 等于 1，不能仅凭数值判断梯度是否为零。必须看这个量在当前点附近是否会随模型参数变化。

---

## 8. 单例采样支持集为什么可能产生零梯度

### 8.1 什么是采样支持集

在一个 token 位置，采样器可能先通过 top-k、top-p 或其他规则排除部分 token，再在剩余候选中重新归一化并采样。

剩下仍有非零采样概率的 token 集合称为 sampling support，记作 \(S\)。例如：

\[
S=\{A,B\}
\]

在这个固定支持集内重新归一化后：

\[
P(A\mid S)
=
\frac{e^{z_A}}
{e^{z_A}+e^{z_B}}
\]

提高 \(z_A\) 或提高 \(z_B\) 会改变二者的相对概率，因此存在非零梯度。

### 8.2 支持集只有一个 token

如果经过采样过滤后：

\[
S=\{A\}
\]

那么支持集内重新归一化的概率必然是：

\[
P(A\mid\{A\})=1
\]

所以：

\[
\log P(A\mid\{A\})
=
z_A-log e^{z_A}
=
0
\]

它对 \(z_A\) 恒为零：

\[
\frac{\partial}{\partial z_A}
\log P(A\mid\{A\})
=
1-1
=
0
\]

其他 token 已被固定 mask 在支持集之外，也没有来自这个条件分布的梯度。直觉上，采样规则已经禁止所有其他选择；`A` 在这个条件分布中的概率已经是 100%，无法通过调整相对 logits 继续超过 100%。

### 8.3 这个结论有一个重要限定

“单例 support 导致梯度为零”只适用于下面这种定义：

> 训练使用固定支持集内重新归一化后的 logprob，并把支持集 mask 当作固定条件。

如果 rollout 虽然使用 greedy、top-k 或 top-p 选出了唯一 token，但训练时仍然计算完整词表上的原始 softmax：

\[
p_A
=
\frac{e^{z_A}}
{\sum_{j\in V}e^{z_j}}
\]

那么只要完整词表中仍有其他有限 logit，通常就有：

\[
p_A<1
\]

此时：

\[
\frac{\partial\log p_A}{\partial z_A}
=
1-p_A
\neq 0
\]

所以不能只看到“采样时只有一个可选 token”，就断言训练梯度必为零。必须先确认训练使用的是：

- 完整模型分布的 logprob；还是
- 按采样支持集 mask 后重新归一化的条件 logprob。

此外，top-p 等支持集本身会随 logits 离散变化。常见训练计算会把已经记录或重放的支持集 mask 视作固定条件，而不会尝试对 support membership 这个离散决策求导。

---

## 9. 从 on-policy 过渡到训推不一致

### 9.1 Behavior policy 与 target policy

如果生成轨迹时使用的策略与训练时的当前策略相同，就是最直接的 on-policy 情况。

异步训练中常见的是：

- rollout 由较旧的策略 \(\mu\) 生成；
- trainer 更新后，当前目标策略已经变成 \(\pi_\theta\)；
- 手中的轨迹服从 \(P_\mu(\tau)\)，但目标函数关心的是 \(P_\theta(\tau)\)。

这里：

- \(\mu\) 通常称为 behavior policy；
- \(\pi_\theta\) 通常称为 current policy 或 target policy。

这是一种分布不一致：数据来自一个分布，目标却定义在另一个分布上。

### 9.2 重要性采样的基本恒等式

对于目标分布 \(p(x)\) 下的期望：

\[
\mathbb E_{x\sim p}[f(x)]
=
\sum_x p(x)f(x)
\]

乘除一个 behavior 分布 \(q(x)\)：

\[
\mathbb E_{x\sim p}[f(x)]
=
\sum_x
q(x)
\frac{p(x)}{q(x)}
f(x)
\]

于是：

\[
\boxed{
\mathbb E_{x\sim p}[f(x)]
=
\mathbb E_{x\sim q}
\left[
\frac{p(x)}{q(x)}f(x)
\right]
}
\]

比值：

\[
w(x)=\frac{p(x)}{q(x)}
\]

就是 importance weight。

### 9.3 用 behavior 轨迹估计当前策略梯度

当前策略下的轨迹梯度是：

\[
\nabla_\theta J
=
\mathbb E_{\tau\sim P_\theta}
\left[
R(\tau)
\nabla_\theta\log P_\theta(\tau)
\right]
\]

如果轨迹来自 behavior policy \(P_\mu\)，则可改写为：

\[
\nabla_\theta J
=
\mathbb E_{\tau\sim P_\mu}
\left[
\frac{P_\theta(\tau)}{P_\mu(\tau)}
R(\tau)
\nabla_\theta\log P_\theta(\tau)
\right]
\]

这时两个机制同时出现，但职责不同：

- score-function 提供 \(R(\tau)\nabla_\theta\log P_\theta(\tau)\) 这一梯度形式；
- importance sampling 使用 \(P_\theta(\tau)/P_\mu(\tau)\) 校正采样分布；
- Monte Carlo 使用有限条 behavior 轨迹估计这个期望。

### 9.4 Token 级 log-ratio

在一个 token 位置，记：

\[
\log p_{\mathrm{current},t}
=
\log\pi_\theta(a_t\mid s_t)
\]

\[
\log p_{\mathrm{behavior},t}
=
\log\mu(a_t\mid s_t)
\]

则：

\[
\log r_t
=
\log p_{\mathrm{current},t}
-
\log p_{\mathrm{behavior},t}
\]

\[
r_t
=
\exp(\log r_t)
=
\frac{\pi_\theta(a_t\mid s_t)}
{\mu(a_t\mid s_t)}
\]

整条轨迹的朴素 importance ratio 是各步比值的乘积：

\[
\frac{P_\theta(\tau)}{P_\mu(\tau)}
=
\prod_t r_t
\]

等价地：

\[
\log
\frac{P_\theta(\tau)}{P_\mu(\tau)}
=
\sum_t\log r_t
\]

长轨迹上的乘积很容易变得极大或极小，导致估计方差很高。因此实践中经常使用 token 级校正、截断、裁剪、mask 或其他偏差—方差折中。采用这些操作后，必须根据具体算法分析它估计的目标，不应把所有变体都简单称为“无偏的完整轨迹重要性采样”。

### 9.5 为什么 current logprob 需要重新计算

`behavior_logp` 描述的是生成该 token 时，behavior policy 实际赋予它的概率。它可以随 rollout 轨迹一起保存。

`current_logp` 描述的是当前训练模型对同一个已采样 token 的概率。模型权重已经可能发生变化，所以通常必须使用当前训练权重重新前向：

```python
current_logits = current_model(recorded_context)
current_logp = log_softmax(current_logits)[recorded_token_id]
log_ratio = current_logp - behavior_logp
```

这里仍然没有重新采样 token，也没有对 token ID 求导。训练器只是在当前策略下重新评价同一个固定动作。

---

## 10. 重要性采样成立所需的条件

### 10.1 支持集覆盖

重要性采样要求：只要目标分布可能产生某个事件，behavior 分布就不能把它完全排除。离散情形可写成：

\[
p(x)>0
\quad\Longrightarrow\quad
q(x)>0
\]

否则会出现：

\[
\frac{p(x)}{q(x)}
\]

分母为零，而且 behavior policy 永远无法采到这部分目标分布的事件。已有样本无法恢复从未被采样分布覆盖的概率质量。

### 10.2 分子和分母必须描述同一种事件分布

如果 rollout 实际执行了 temperature、top-k、top-p、min-p 或其他采样变换，那么 behavior probability 应当与真正执行采样的分布一致。

不能在没有明确转换关系的情况下，把下面两种量直接相除：

- 分子：完整词表上的原始模型概率；
- 分母：经过截断并重新归一化后的采样概率。

二者可能定义在不同支持集、不同条件分布上。可靠的重要性比值要求：

- token 与上下文对应一致；
- 概率所针对的事件一致；
- support/mask 语义一致或有明确的数学校正；
- behavior logprob 确实来自生成该动作的行为分布。

### 10.3 大 importance weight 会导致高方差

若 behavior policy 认为某动作很罕见，但当前策略认为它很常见：

\[
\mu(a\mid s)\ll\pi_\theta(a\mid s)
\]

则 importance ratio 很大。少数样本可能主导整个梯度估计，训练会变得不稳定。

裁剪或丢弃极端 ratio 可以降低方差，但通常也会引入偏差。因此它们不是免费的数值技巧，而是对估计目标和稳定性的明确折中。

---

## 11. “训推不一致”不只表示策略版本陈旧

重要性采样可以处理的是：

> 已知 behavior 分布和 target 分布，并且满足支持集条件时，数据分布与目标分布不一致的问题。

但“训推不一致”还可能包括：

- 推理与训练使用不同精度或数值内核；
- tokenizer、chat template 或上下文拼接不同；
- temperature、top-k、top-p 等采样变换没有一致重放；
- token、mask、位置或截断边界没有对齐；
- behavior logprob 并非实际采样分布的概率；
- 模型结构、路由结果或其他前向语义不一致。

重要性采样不会自动修复这些实现错误。只有当两侧概率确实描述同一事件、轨迹来源可信，并且差异可以表达为合法的概率比值时，importance ratio 才具有预期含义。

因此可以把问题分成两层：

```text
第一层：语义和数据是否对齐？
token、上下文、mask、采样分布和 logprob 是否描述同一件事？

第二层：在已经对齐的前提下，behavior 与 current policy 的概率差异有多大？
是否需要 importance sampling、裁剪或其他 off-policy 校正？
```

不能使用第二层的概率校正，掩盖第一层的语义不一致。

---

## 12. 零数值、零 advantage 与零梯度

以下情况必须区分：

### 12.1 `logprob == 0`

这表示对应概率为 1，但单凭函数值还不能判断梯度。必须确认它是否因固定单例支持集而成为对 logits 恒定的表达式。

### 12.2 `ratio == 1`

这表示当前策略和 behavior 策略在该动作上的数值概率相等。它不自动表示梯度为零，因为 current logprob 仍可能对当前参数敏感。

### 12.3 `advantage == 0`

对于形如：

\[
L=-A\log\pi_\theta(a\mid s)
\]

的策略损失，如果 \(A=0\)，这个样本的策略梯度贡献为零。

组内相对 advantage 算法中，如果一组 reward 完全相同，就可能得到整组零 advantage。此时有真实样本、有 reward、有 logprob，也仍然没有策略更新信号。

### 12.4 有样本不等于有有效梯度

样本数大于零、某个 token 通过过滤或某个比值落在允许范围内，都只说明对应样本满足了特定条件，不能单独证明最终梯度非零。

最终梯度还取决于：

- advantage 是否非零；
- loss mask 是否保留该位置；
- logprob 是否真正依赖当前参数；
- 各样本梯度是否相互抵消；
- 分布式归约后的全局梯度是否仍有有效信号。

---

## 13. 最容易混淆的结论

1. **不是 Monte Carlo 让离散采样可微。** Score-function 让策略梯度不需要对离散动作求导；Monte Carlo 只负责近似期望。
2. **策略梯度不对 token ID、工具返回或 reward 求导。** 它对策略为已采样动作分配的 `logprob` 求导。
3. **Score function 不是奖励分数。** 在这里它是 \(\nabla_\theta\log p_\theta(x)\)。
4. **Score-function 与 reparameterization 是两类正式的随机梯度估计方法。** 前者不穿过离散样本反传；后者通过可微的采样生成路径反传。
5. **重要性采样不负责解决离散动作不可微。** 它负责在 behavior 分布与 target 分布之间变换期望。
6. **`logprob == 0` 不必然表示梯度为零。** 只有当表达式对参数局部恒定时，梯度才为零。
7. **单例 support 的零梯度结论依赖训练概率的定义。** 固定支持集内重归一化与完整词表 softmax 不能混为一谈。
8. **有轨迹或有被接受的 token，不保证有训练信号。** 零 advantage、固定单例支持集、mask 和梯度抵消都可能产生零梯度。
9. **重要性采样有支持集和概率语义前提。** 它不能恢复 behavior 从未覆盖的动作，也不能修复 token、mask 或 logprob 本身不对齐的问题。

---

## 14. 一条完整的思考链

回顾这类问题时，可以按下面顺序判断：

```text
目标：最大化当前策略下的期望奖励
  ↓
离散动作是否需要求导？
不需要；对动作或轨迹的概率求导
  ↓
如何得到可计算的梯度？
使用 score-function / log-derivative trick
  ↓
如何避免枚举全部轨迹？
使用 Monte Carlo 样本近似期望
  ↓
样本是否来自当前策略？
如果来自 behavior policy，需要考虑 importance sampling
  ↓
importance ratio 是否有意义？
检查 token、上下文、support、采样分布与 logprob 语义是否一致
  ↓
有样本是否等于有梯度？
不等于；继续检查 advantage、mask、支持集和最终全局梯度
```

这条链路中，每一步回答的是不同问题。把它们分开，才能避免用 Monte Carlo、importance ratio 或样本准入条件去解释它们本来没有解决的事情。
