# FlashREINFORCE：无 critic 单轨迹异步 RL，以及与 SAO 的区别

阅读日期：2026-09-17。本文为论文精读与算法讨论记录，不是项目算法变更决定。

## 1. 来源、版本与覆盖

- [作者发布页](https://www.researchgate.net/publication/414274571_FLASHREINFORCE_CRITIC-FREE_SINGLE-ROLLOUT_ASYNCHRONOUS_RL_FOR_AGENTIC_LANGUAGE_MODELS)：NVIDIA 的 Jian Hu、Yifan Zhang 等，2026 年 9 月。
- [本次实际读取的固定版本 PDF](https://github.com/yifanzhang-pro/FlashREINFORCE/blob/a1ebe22c6951e40b7be83395f9f15e9b41ab36dc/FlashREINFORCE.pdf)：30 页；SHA256 为 `b82abfa7e6fff9e7812ebbdbde72a25c1805000b1da744bcc2b62483ca233800`。
- [作者项目页](https://yifanzhang-pro.github.io/FlashREINFORCE/)。算法参考库固定在 `yifanzhang-pro/FlashREINFORCE@a1ebe22c6951e40b7be83395f9f15e9b41ab36dc`；训练框架固定在 `NVIDIA-NeMo/labs-molt@7a114d6076a8f3ad7493a43b2518bb8f5dcf1697`。
- SAO 对照：[原文 v1](https://arxiv.org/html/2607.07508v1) 与[已有精读](R15_single_rollout_asynchronous_optimization.md)。本次重新核对原文方法、训练配置和主要消融。

阅读覆盖：FlashREINFORCE 全部正文、附录 A/B/C 与参考文献，19 张表的文本；目视检查全部 4 幅编号图，以及 p.7/8/11/17 上的关键结果与配置表。公式主要通过 PDF 文本和公开 loss 交叉核对，未逐页目视全部公式。附录 B.1/B.3 提出的额外算法没有实验，不能记成已验证组件。

代码覆盖：独立参考 loss、配套实验配置和说明；Molt 的 advantage、policy loss 与 R1D quick-start 脚本。没有做完整训练入口审计、独立 reviewer 审查或 GPU 复现。ResearchGate 直接下载受限，取得的是作者 GitHub 发布的 PDF；网页关键公式和表值与之相符，没有证明两个入口逐字节相同。

## 2. 核心判断

该方法以批次奖励均值替代学习型 critic，以每题单轨迹替代同题多轨迹组，并将一次性更新、token 重要性采样、序列级漂移筛选、按轨迹平均 loss 组合起来。贡献是这组选择在异步训练中的经验效果，不是第一次发现无 critic 或单轨迹策略梯度。

SAO 确实使用 critic 和 GAE。称它为 PPO/actor–critic 家族的异步变体基本合理，但其实际 policy objective 改为 DIS 双侧硬屏蔽，不能等同于标准 PPO clipped surrogate。

FlashREINFORCE 没有同条件 SAO 对照，也没有 SWE-Bench 修复训练结果，因此不能据此认定它胜过 SAO 或可以直接替换本项目主线。

## 3. One-Batch REINFORCE：单轨迹不等于单样本更新

设一个 learner batch 包含 B 道题各自的一条轨迹，最终奖励为 R_i。论文 Eq.5 使用：

$$
\bar R=\frac1B\sum_jR_j,\qquad A_i=R_i-\bar R.
$$

这是不同 prompt 之间的批次基线，不是同题 group baseline，也不是每题维护历史滑动均值；没有除以奖励标准差。轨迹中所有策略生成 token 共用 A_i。

例如 4 道题奖励为 `[1,0,1,0]`，优势为 `[0.5,-0.5,0.5,-0.5]`。失败轨迹获得负反馈；直接以原始 0/1 reward 作权重时，失败轨迹的 policy gradient 为零。环境或评分器仍负责提供 reward；critic-free 不等于不需要评分器。

每个 batch 只执行一次 optimizer update，随后不再使用这些轨迹。可以用 microbatch 累积实现这一次更新，但不能将同一批拆成几个依次更新参数的 minibatch 后称其等价。这里 fresh 指尚未被训练消费，不表示一定来自最新权重。训练期间同一道题仍可以再次被抽到。

### 为什么没有 critic 仍然成立

REINFORCE 可以直接用实际回报构造策略梯度，critic 是学习状态价值、降低估计方差的办法，并非策略梯度存在的必要条件。本方法选择更粗的非参数基线，省去价值模型前向、反向和优化器状态，同时接受较弱的状态相关信用分配。

以下为读者解释，而非本文新的实验结论：

- 跨题平均不能像好的 V(h) 那样识别题目难度或轨迹中间状态。
- 这不意味着跨题均值的梯度方差必然更大，同题 reward mean 也不一定是方差最优基线。2026-09-17 补读的[固定预算下 Group/Batch 比较](group_vs_batch_baselines_20260917.md)进一步区分了基线目标、估计噪声与题目覆盖；其结论限定于文中 on-policy 等假设，不能直接证明完整异步算法的排名。
- B=1 时 A 恒为零；整个 batch reward 完全相同时也没有任务 policy-gradient 信号。AdamW 的动量或权重衰减仍可能改变参数，不能把零优势直接等同于参数绝对不动。
- 在独立轨迹、未加筛选和长度归一化的标准推导中，含自身的 batch mean 相对 leave-one-out 只引入 `(B-1)/B` 缩放；不能将这个简单结论直接扩展到完整实际 loss。

## 4. Sequence Trust Region：校正动作概率，再筛选整条轨迹

### 4.1 实际行为概率

对轨迹 i 的策略 token t，保存真正采样它时的行为概率 mu，并在训练时计算当前概率 pi：

$$
\rho_{i,t}=\frac{\pi_\theta(a_{i,t}\mid h_{i,t})}{\mu_i(a_{i,t}\mid h_{i,t})}.
$$

不能用事后重算的 old-policy logprob 自动替代生成时概率：模型版本、训推 kernel、MoE routing 等都可能不同。

token IS 在共同支持集假设下校正给定旧历史 h 上的动作分布，但不能把旧策略生成的历史变成新策略本来会访问的历史。完整轨迹或 prefix IS 能处理更多分布差异，但连乘长序列 ratio 会增加方差。本文保留 token IS，并用漂移筛选控制实践风险。[原文 §2、附录 B]

### 4.2 Bernoulli KL 代理量

只看已采样 token 的概率 p=mu(a|h)、q=pi(a|h)，把整个词表压成“这个 token / 其他所有 token”两类：

$$
d_{i,t}=p\log\frac pq+(1-p)\log\frac{1-p}{1-q},
\qquad
\bar D_i=\frac1{T_i}\sum_td_{i,t},
\qquad
m_i=\mathbf1[\bar D_i\le\delta].
$$

超出阈值时，该轨迹全部策略 token 不贡献 policy loss；其余轨迹保留各 token 的 IS 权重。这既不是将 ratio clamp 到 PPO 区间，也不是把 token ratios 相乘作为整条轨迹权重。

与 SAO 的区别是两个维度：SAO 按 token 的 ratio 是否越界进行筛选；本方法按全轨迹平均的概率散度代理量进行筛选。因而不能把本文 token-local KL 消融直接当成 SAO/DIS 的失败证据。

### 4.3 理论边界

原文给出的局部 surrogate 误差界涉及全分布、最坏历史下的累计策略漂移。实际 Bernoulli KL 是完整 categorical KL 的下界：代理量大可识别一些高漂移样本，代理量小却不能证明完整分布接近。例如已采样 token 的概率保持不变，其他 token 之间仍可以发生很大的概率转移。

平均值也可能稀释个别位置的大漂移。本筛选判断当前 learner 与 behavior 的差异，不是更新后对所有状态强制满足 TRPO 约束。附录 B 明确没有为实际“筛选 + 长度归一化”的更新证明无偏或单调改进。

## 5. Sample-Mean Optimization：限制长度带来的额外权重

论文 Eq.11 的最小化形式为：

$$
L=-\frac1B\sum_i\frac{m_iA_i}{T_i}
\sum_t\operatorname{stopgrad}(\rho_{i,t})
\log\pi_\theta(a_{i,t}\mid h_{i,t}).
$$

T_i 是该完整轨迹中策略生成 token 的数量，不含 prompt、工具 observation 或 padding。先在每条轨迹内平均，再按轨迹平均；筛选后仍使用原始 B、T_i，不按保留数量重新归一化，reward mean 也在筛选前计算。

读者数值例子：两条轨迹分别包含 1,000 和 10,000 个策略 token。若每条的平均 token loss 相同，token-mean 赋予后者 10 倍权重；sample-mean 的外层权重都是 1/2。实际梯度大小仍取决于 advantage、IS 和各 token 梯度方向，不能说每条轨迹最终梯度范数相等。

这对“失败后不断尝试直到撞到长度上限”的 agent 有意义：长失败轨迹不再仅因长度而支配 batch。但它没有判断哪一步导致失败，正确的早期探索仍可能一起受罚。长度归一化是有意改变贡献权重的实用近似，不是原始期望终局回报梯度的无偏恒等变形。[原文 §3.3、附录 B p.23]

## 6. 主实验与证据范围

原文 avg@k 是对每题 k 次采样的正确率取平均，不是“k 次中任一次成功即成功”的 pass@k。

| 实验 | 论文报告 | 需要保留的条件 |
| --- | --- | --- |
| R1-Distill-Qwen-1.5B 长推理 | AIME24/25 mean 21.7→33.7；累计 6,000 更新，lag≈4 | 1,460 道筛过难度的 MATH 题；128 轨迹/更新；第 5,000 步后从权重续训，重建 AdamW 状态并再次 warmup；33.7 对应最后评测约第 5,896 步 |
| Qwen2.5-Math-1.5B | 五任务均值 38.0，GRPO 36.3；256k vs 512k 轨迹 | GRPO/C-RF 来自其他论文报告、同步 veRL；Flash 使用异步框架且更新数不同。MATH-500 和 AMC23 低于 GRPO，不是逐项全面领先；38.0 是所报告峰值 checkpoint |
| Qwen2.5-7B + Python | 第 600 步三任务 37.0 vs GRPO 30.3；调用数 3.25 vs 0 | 同更新数、同总轨迹数；Flash 为 128×1，GRPO 为 32×4；不能推出 GRPO 普遍无法学工具 |
| Qwen3-30B-A3B + Python | 第 800 步 67.1 vs 60.3；各 102.4k 轨迹 | Flash lag≈8、GRPO≈1；主比较不启用 R3、delta=1e-2；1,450 步的较长稳定性展示使用 R3、delta=1e-3，不能混为同一运行 |
| Qwen2.5-7B ALFWorld | 第 200 步 seen/unseen 98.3/96.5；C-RF 90.5/86.3，GRPO 78.6/76.8 | Flash 用 12.8k 训练轨迹；对照来自其他论文；当前公开配置还含 q=0.9 的失败 token 熵筛选，见 §8 |

没有完整的端到端 GPU-hour、wall-clock 吞吐对照或统一多训练 seed 的置信区间证据，不能把“rollout 减半”写成“算力/费用减半”。Qwen3 未开 thinking，而 SAO 数学分支使用 Thinking 模型并先做 TIR SFT，二者分数不构成直接算法比较。

“首个开源、无 critic、单轨迹、异步、6,000+ 稳定更新”是限定组合的作者优先权主张，本次没有做穷尽历史检索。本文可核查的主曲线展示至累计 6,000 步，不是任意模型/环境上稳定性的保证。

## 7. 消融、负结果与没有验证的方案

- **更新新鲜度（Table 5）**：同为 102.4k 轨迹、800 optimizer steps，每步新收 128 条为 28.45；一次收 512 条后依次更新 4 个 128 minibatch 为 26.80。两者都不重复使用某条轨迹，差异是后续 minibatch 面对更晚 learner。
- **保留失败负反馈（Table 6a）**：批次中心化为 36.2、3.30 工具调用；仅正反馈为 9.8、0 次调用。这是该配方内消融，不能证明任何正反馈训练都会失败。
- **长度权重（Table 6b）**：从第 900 步 checkpoint 续训约 150 步，sample-mean reward 0.477、截断 17.2%；token-mean reward 0.403、截断 45.3%，响应更长、工具更少。支持检查归一化，但不等于所有任务都应采用 sample-mean。
- **筛选粒度（Table 7）**：相同 KL 代理与 delta=1e-3，序列筛选运行至 2,160 步；token-local 在 1,237 步崩溃。没有匹配拒绝率，也不是与 SAO 的直接对比。
- **筛选并非所有稳定性的唯一来源（Tables 3/8）**：R1 无筛选分支也没有被报告为全面崩溃，约 5,888 步得 30.6，带筛选约 5,896 步得 33.7；30B 的无 gate 分支也能学习。不能概括成“一去 gate 必崩”。
- **阈值（Table 15）**：1e-3、3e-3 都稳定至 4,000 步；后者第 2,000 步峰值约 37.97，此后不是单调上涨。3e-3 比较运行只拒绝 0.13% 轨迹，说明至少该场景中不是靠大量丢样本维持稳定。
- **几何平均代理（Table 16）**：算术平均和几何平均分别在一个 benchmark 更好，未见一致优势，默认仍为算术平均。
- **联合去掉 IS 与 gate**：ALFWorld 第 40 步从 81.0/77.6 降为 35.0/27.6。因为同时移除了两个组件，不能单独归因于其中之一。
- **附录 B.1–B.3**：最大代理、完整 KL、top-k TV 上界、独立验证预算下的 candidate update 检查均为提议或推导，没有运行结果。后者约束的还是原始局部 surrogate，不自动证明实际 masked/sample-mean 更新改进回报。

## 8. 附录的失败 token 熵筛选，以及代码交叉核对

### 8.1 可选熵筛选

成功轨迹保留所有策略 token；失败轨迹只保留熵最高的 ceil(q*T_i) 个位置。mask 固定，分母仍为原 T_i。它按明确失败标签工作，不等同于所有 A<0 的样本都一定是失败，尤其 reward 不是二元值时。

Table 19 的 7B 工具实验：q=1 的峰值 37.0；q=0.9 为 39.4；q=0.2 为 32.2 且后期工具调用接近零；q=0 为 13.1 且工具调用为零。最佳 checkpoint 不同。Table 18 数学 q=0.9 的部分 checkpoint 改善，但到第 4,000 步不再领先。

Figure 4 包含 Qwen3.5-4B terminal-task 的失败位置熵诊断：72% 标注位置高于轨迹内 80th percentile，46% 高于 90th。未披露足够标注规模与完整 terminal 基准协议，不能把这张诊断图当作 SWE/terminal RL 能力提升实验。熵是选择启发式，不是错误位置的可靠标签。

### 8.2 三类公开材料不能混用

1. [算法参考 loss](https://github.com/yifanzhang-pro/FlashREINFORCE/blob/a1ebe22c6951e40b7be83395f9f15e9b41ab36dc/flashreinforce/loss.py)：明确每行覆盖完整多轮轨迹，排除 observation；整批中心化先于 DP/microbatch 分割；detach 的 ratio、序列 mask 和原始分母与本文 Eq.11 对应。函数自身没有分布式归约。
2. [Molt advantage](https://github.com/NVIDIA-NeMo/labs-molt/blob/7a114d6076a8f3ad7493a43b2518bb8f5dcf1697/molt/trainer/algorithm/advantage.py) 和 [Molt loss](https://github.com/NVIDIA-NeMo/labs-molt/blob/7a114d6076a8f3ad7493a43b2518bb8f5dcf1697/molt/models/loss.py)：公开 `flash_reinforce` 批均值 estimator、binary-KL 序列筛选和 `seq-mean-token-mean`。quick-start 用 `force_on_policy` 加行为概率 IS 组合出该方向；参数名不表示实际生成已经同步 on-policy。没有沿整个 trainer 运行链证明所有边界都与论文实验完全相同。
3. [项目配套配置说明](https://github.com/yifanzhang-pro/FlashREINFORCE/blob/a1ebe22c6951e40b7be83395f9f15e9b41ab36dc/examples/README.md)：明确一部分实验 JSON 要求另一个提供 native loss flags 的 trainer，公开 Molt pin 不提供这些 flags；agent、数据和 checkpoints 未完整打包。这些配置不是所有结果的一键复现包。

论文附录 A 记述的训练实现对 log-ratio 作 [-30,30] 数值截断，并直接对截断后 ratio 求导；独立参考函数使用未截断的 detach ratio，并在 overflow 时报错。两种表达只在相应范围内有梯度等价关系，不能称所有边界逐位一致。

当前 ALFWorld 配置含 q=0.9，论文 Table 17 没列这个参数，因此把 98.3/96.5 全部归结为不含额外选择器的“三组件基础配方”证据不充分。当前 Qwen3 JSON 是 20-turn 的另一项 trust ablation，不能代替 Table 12 的 10-turn 主比较配置。

## 9. 与 SAO、GRPO 的比较

| 维度 | GRPO 常见设置 | SAO | FlashREINFORCE |
| --- | --- | --- | --- |
| 同题 rollout | 多条 | 一条 | 一条 |
| 基线 | 同题组 reward 统计 | 学习的 V(h) | 不同题组成的当前 batch reward 均值 |
| 优势粒度 | 终局 reward 时通常整轨迹同优势 | Skip-Observation token-level GAE | 整轨迹同优势；可选失败 token 熵筛选 |
| critic | 不需要 | 需要；每 policy update 配 K=2 value updates，critic attention 冻结 | 不需要 |
| 异步保护 | 依具体变体 | 真实 rollout logprob + DIS token ratio 双侧硬屏蔽 | 真实 rollout logprob + token IS + 全轨迹平均 Bernoulli KL gate |
| 数据消费 | 依具体实现 | 不能由 single-rollout 名称推出 one-pass | 明确一个 batch 一次 optimizer update |
| 额外成本 | 同题重复生成与等组 | 价值模型训练 | 不训练价值模型，但仍要当前 actor 前向/反向及行为概率 |

SAO 针对 value model 的工程不是额外可忽略项：每 policy step 两次 value 更新、冻结 critic attention、skip-observation GAE 都属于其稳定配方。DIS 与 critic 并不绑定，SAO 原文自己也评测了 GRPO+DIS。

比较“6,000 vs 1,000 steps”不能得出 Flash 稳定性提高六倍：模型、训练题、horizon、lag、batch、评测都不同。SAO 的 per-prompt running-mean 失败对照也不是 Flash 的跨题当前 batch mean，不能互相替代。

## 10. 对项目一的条件化建议

本节是读者建议，未修改项目定案、loss 或采样器，也未审计当前主线实现。

FlashREINFORCE 值得作为无 critic 的单轨迹实验候选：如果 SWE 生成与环境执行昂贵、组等待严重，而价值模型资源又受限，它提供了一条实现较轻的路线。不过对我们的真实仓库长轨迹，现有论文证据还缺关键外推环节。

建议在已有可靠闭环上逐项验证：

1. 先明确当前同题组基线和分母；只把 group size 改为 1 可能得到恒零优势，不能称作本算法。
2. 固定模型、harness、reward、题集与预算，对比组采样和跨题 batch mean；同时报告生成轨迹、生成 token、GPU-hour 与真实时间，区分覆盖收益和系统收益。
3. 检查基座成功率及全同 reward batch 比例；报告有效非零优势、完整策略 token 捕获率、行为/current logprob 对齐。稀疏 reward 下不应只看提交给 optimizer 的 batch 数。
4. 独立比较 loss 归一化与筛选粒度，避免同时换基线、gate、reduction 后把所有收益归给一个开关。筛选率按题型、长度、成败和 policy lag 分层，检查训练分布是否被改变。
5. 评测修复成功率、工具行为、长度/截断、entropy、proxy-KL、IS 尾部；对丢弃与零信号作可见记录。SWE 的有效探索步骤被终局失败统一惩罚这一问题，仍需实验观察。

如果组等待并非主要瓶颈，或者跨题基线在异质 SWE 数据上信号明显变差，引入这一方法未必改善整体效率。当前证据支持“小规模、可归因的比较”，不支持先重构主线或移除已有可信基线。
