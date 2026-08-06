# SA-SWE（SkyRL-Agent）horizon masking 精读与 FA-4 交互分析

```text
status: draft
scope: FA-2A 决策包 v3.2 引用的 "SA-SWE 保组统计屏蔽梯度" 外部依据核实，
       以及 D1a 第 10 条五个 FA-4 延后项的证据映射
sources:
  paper (E0): arXiv 2511.16108v1（HTML 全文，2026-08-04 取回）
  code  (E1): github.com/NovaSky-AI/SkyRL，main @ 6ae5d677d8f0（2026-08-03）
  ours:  rh2/src/repoharness2/training/faithful_dis.py
         rh2/src/repoharness2/adapters/slime/batch_admission.py
         docs/agentic_RL/repo_harness_rh2_workstreams/fa/fa2a_decision_package.md
relation: 本文是 agentic_rl_training_recipe_evidence_matrix.md §6.2.1/§8.7 的
          深化（逐字引文 + 机制级交互分析），不替代该矩阵的索引职责
maintenance: 本任务只允许产出本文档；manifest.json / README.md 的登记
             （矩阵 §12 规定的新来源流程）留待下一次仓库维护补做
```

---


> **措辞修正（codex 五审 2.6，2026-08-07）**：本文所有 "mean 与 LOO 只差
> 常数因子 (n−1)/n" 的表述均为**理想代数等价**——在 Adam 的逐参数归一、
> gradient clipping、动态 batch 与有限精度下，常数尺度差**不保证训练
> 完全等价**，预注册选择时按"近似尺度关系"引用。另：`faithful_dis.py`
> 是数值参考/对拍实现，尚不是已验证的生产 reducer——本文对它的引用是
> 设计意图层面，不是生产行为证据。
## 0. 论文 ID 勘误与命名澄清

**ID 无需勘误，但引用名需要澄清**：arXiv 2511.16108 的论文标题是
**"SkyRL-Agent: Efficient RL Training for Multi-turn LLM Agent"**（Cao,
Li, Zhao 等，UC Berkeley Sky Computing Lab 系，v1 生成于 2025-11-20）。
**SA-SWE-32B 是该论文训练出的模型名**，不是论文名。codex 引用中说的
"SA-SWE 论文"是非正式简称，指向正确，但检索与引用时应写
"SkyRL-Agent 论文（其 SWE 模型为 SA-SWE-32B）"。

另一个必须知道的事实：**这是一篇系统框架论文**。horizon masking 的全部
论文级描述只有 §4.2 的一个散文段落，**全文没有任何一个编号公式描述
masking、advantage 或 loss 归一化**——HTML 全文（LaTeXML 转换）中唯一的
展示公式是 §2 Background 里的通用 POMDP 目标：

> $J(\theta)=\mathbb{E}_{\pi_{\theta}}\Big[\sum_{t=1}^{T}r_{t}\Big]$
> （§2 Background，无编号；"where $T$ is the number of agent turns per task"）

因此"引用必须可回溯"的回溯终点是**一段散文 + 官方仓库代码**，不是公式。
这本身是对 FA-4 决策的重要输入：外部依据的分辨率不足以直接决定
loss 分母与 batch 计数语义，那两层必须由我们自己预注册（见第 4、7 节）。

---

## 1. 论文事实（E0，逐条带章节出处）

### 1.1 核心段落逐字引文

以下引文均来自 §4.2 "Training Recipe" 的 "RL algorithms and
hyper-parameters." 小节（arXiv 2511.16108v1 HTML），原文照录，不做转写：

> "For stable training, we adopt a fully on-policy setup where the
> training batch size equals the mini-batch size (both set to 64), and
> the number of rollouts per task is 8."

> "Trajectories that terminate due to external constraints, such as the
> maximum context length (32K tokens), step limit (50 turns), are masked
> out during gradient updates to prevent the model from being biased
> against trajectories with more actions or reasoning steps."

> "Importantly, this masking does not modify the reward or advantage
> estimation; it only excludes those samples from the gradient
> computation."

> "Following prior works (Luo et al., 2025a; Liu et al., 2025b), we
> apply leave-one-out advantage estimation and remove both standard
> deviation and length normalization in advantage computation."

> "We disable KL and entropy loss and train with a learning rate of
> $1e{-}6$."

其中 Luo et al., 2025a = DeepSWE（Notion 技术博客），Liu et al., 2025b =
"Understanding R1-Zero-Like Training: A Critical Perspective"（Dr. GRPO）
——两条出处均在论文参考文献区核对过。

### 1.2 论文明确回答了什么（我方转述，逐条挂回 1.1 的原文）

以下是**我方转述与解读**，与上面的原文严格分开：

1. **组统计包含 horizon 轨迹**：到达 32K context 或 50 turns 的轨迹，
   reward 照常评、照常进 advantage 估计（"does not modify the reward or
   advantage estimation"）。这正是 FA-2A v3.2 三正交处置里
   `group_membership=included + reward_disposition=included_in_advantage
   + gradient_disposition=masked` 的形态。**codex 的引用方向正确。**
2. **baseline 用 leave-one-out，不是 group mean**：论文自己的配方是
   LOO（"leave-one-out advantage estimation"）。注意 FA-2A D1a 第 10 条
   把 "GRPO mean 还是 leave-one-out" 列为延后项——论文对它自己的设置
   给出了答案（LOO），但见第 5.1 节：在 std 关闭且成员集固定时，两者
   只差一个常数因子，真正改变数值的是"成员计入还是剔除"。
3. **不做 std 归一化，也不做长度归一化**："remove both standard
   deviation and length normalization in advantage computation"。
4. **屏蔽的粒度是"样本"（整条轨迹）**："excludes those samples from
   the gradient computation"——是轨迹级排除，不是 token 级或 turn 级
   部分屏蔽。屏蔽动机是**防长度偏置**（"prevent the model from being
   biased against trajectories with more actions or reasoning steps"），
   不是训练稳定性。
5. **完全 on-policy**：train batch = mini-batch = 64（按任务计），每任务
   8 条 rollout（每步 512 条轨迹）。没有 importance sampling 修正，
   自然也没有任何与 DIS 的组合证据。

### 1.3 论文没有回答什么（对 FA-4 最要紧的空白）

1. **loss 分母**：被屏蔽样本是否留在 loss 归一化分母里（token 总数、
   序列数、常数分母），论文只字未提——没有 loss 公式。
2. **batch 计数**：被屏蔽样本是否计入 optimizer 的有效 batch、是否补充
   新的带梯度样本——未提。on-policy 固定 64 任务的设置下样本天然占着
   批次位置，但"占位"与"占分母"是两回事，论文没区分。
3. **horizon 命中率**：训练中多大比例轨迹到达 32K/50 turns 被屏蔽——
   **全文没有这个数字**。这意味着连"该机制在多大剔除面上生效"都无法
   从论文外推。
4. **mask 的实现层**（token loss mask 置零 vs 从 batch 剔除样本）——
   散文无法区分，需查代码（见第 2 节）。
5. **turn 上限与 context 上限是否同一处置**：段落把两者并列举例
   （"such as"），未说明是否有差别处理，也未提 wall-clock 超时。

### 1.4 论文其他相关事实

- **§4.2 "Hints for agent to recover and proceed."**：训练时给 agent
  注入结构化提示，其中包括——原文：
  > "notifications that the remaining step budget or context window is
  > about to be exceeded"
  即 agent 在接近 horizon 时**会被告警**。这改变 horizon 轨迹的构成
  （很多本会撞限的轨迹提前收敛或提前提交），论文还说 agent 常
  "stop solving the problem prematurely without reaching the maximum
  turn or context limit"。外推我方 Claude Code 黑盒 harness（默认无此
  告警）时，horizon 命中率与命中人群不可比（见第 6 节）。
- **§5.1 Deep Research 的 "masking abnormal trajectories"**：推理服务
  供给不足导致 timeout 污染 rollout 时用屏蔽保护 reward 信号——这是
  **基建故障屏蔽**，与 §4.2 的策略 horizon 屏蔽是两码事，对应我方的
  `missing`/fault-domain 处置，不是 scored_horizon_masked 的依据。
- **实验规模（§1、§4.2、§4.3、Fig.1(b)、Table 2）**：dense Qwen3-32B
  （24.4% → 39.4% Pass@1 SWE-Bench Verified）；4.5K R2E-Gym 任务；
  125 个 RL steps；2×8 H100；总成本 4601 H100-hours（DeepSWE 为 9180）；
  训练预算 32K context / 50 turns，评测 40K / 100 steps；scaffold 是
  自建 tool-guided ReAct（bash + file editor + AST 搜索工具 + hints）。

---

## 2. 官方仓库代码事实（E1——与论文分开，注意版本漂移）

以下取自 `github.com/NovaSky-AI/SkyRL` main 分支
（commit `6ae5d677d8f0`，2026-08-03），**晚于论文 (2025-11) 约 9 个月**。
不能断言 SA-SWE-32B 当时跑的就是这些代码路径（论文支持 SkyRL-train /
VeRL / Tinker 三种 backend，正文未点名 SWE 训练用哪个），只能作为
"该团队生态里 masking 机制长什么样"的 E1 证据。

1. **屏蔽实现 = 整条轨迹 loss mask 置零，样本留在 batch 里**。
   `skyrl/train/generators/utils.py::apply_overlong_filtering`：

   ```python
   # docstring: "Implements DAPO Overlong Filtering: zero-out every
   # token's mask whenever the response was truncated (i.e. did not
   # end with a stop token)."
   return [
       [0] * len(mask) if stop_reason != "stop" else mask[:]
       for mask, stop_reason in zip(loss_masks, stop_reasons)
   ]
   ```

   即：generator 把非正常终止映射为 `stop_reason != "stop"`（例：
   `examples/train/mini_swe_agent/mini_swe_generator.py` 在超限路径上
   写 `stop_reason = "length"`），随后整条轨迹的 token loss mask 全部
   置零。**样本不被从 batch 删除**——这与我方 D1a 第 6 条的立场有一个
   关键差异：他们直接改写了 loss mask（provenance 语义与算法语义合并在
   同一个 mask 里），我方要求 `provenance_loss_mask` 不可变、
   `horizon_gradient_mask` 独立（fa2a_decision_package.md D1a 第 6 条）。
   机制上等价（都是该轨迹梯度为零），但账目上他们的做法丢失了
   "该 token 本来可归因"的事实，我方契约不允许。

2. **被屏蔽样本占不占 loss 分母，取决于 `loss_reduction` 配置**。
   `skyrl/backends/skyrl_train/utils/ppo_utils.py::
   apply_loss_reduction_to_advantages_minibatch`（`reduce_loss` 恒为
   `(loss * loss_mask).sum()`，归一化预先折进 advantage）：

   | `loss_reduction` | 分母 | 全零 mask 样本占不占分母 |
   | --- | --- | --- |
   | `token_mean` | `loss_mask.sum()`（batch 内有效 token 总数） | **不占**（贡献 0 个 token） |
   | `sequence_mean` | `batch_size × 每序列 mask sum` | **占**（`batch_size` 数全部序列） |
   | `seq_mean_token_sum_norm`（代码注释自称 "Dr. GRPO style"） | `batch_size × max_seq_len`（常数） | **占** |
   | `prompt_mean` | `num_prompts × 每 prompt token 数` | prompt 内不占 token 数；全屏蔽 prompt 仍占 `num_prompts` |

   也就是说：**同一份官方代码库里，"masked 样本是否稀释别人的梯度"
   随配置翻转**。论文说去掉了长度归一化，若按代码注释对应到
   `seq_mean_token_sum_norm`，则 masked 样本**占常数分母**（等比稀释
   当步全部梯度）——但"论文跑的就是这一档"是 E3 推断，未被任何公开
   材料钉死，登记为 `U`。

3. **RLOO 实现确认了两件事**。`ppo_utils.py::
   compute_rloo_outcome_advantage`：

   ```python
   factor = response_num / (response_num - 1)
   scores[i] = (scores[i] - id2mean[index[i]]) * factor
   ```

   （a）LOO 是按恒等式 `r_i - mean_others = (r_i - mean_all) × n/(n-1)`
   实现的，分组键是 prompt index，**对该 prompt 在 batch 里的全部
   response 计算**——loss mask 置零发生在别处，不影响这里的 baseline。
   这与论文 "masking does not modify the reward or advantage estimation"
   一致。（b）无 std 除法；单成员组直接 advantage=0 并告警。

---

## 3. 我方实现事实（交互分析的对照基线）

只列与本分析直接相关的语义，出处为当前工作区代码：

1. `rh2/src/repoharness2/training/faithful_dis.py`
   - DIS 目标（SAO 论文式 1~3 的参考实现）：
     `L(θ) = Ê_t[ f(r_t; ε_ℓ, ε_h) · Â_t · log π_θ(a_t|s_t) ]`，
     信任区间 (0.2, 4.0)，f(r) detach。
   - 分母两档预注册：`DENOMINATOR_SEMANTICS_V1 = "provenance_tokens"`
     （被 DIS 拒绝的 token **留在分母**，梯度为零不重归一化），
     `accepted_tokens` 留作消融。
   - `faithful_dis_loss_by_execution` 三层归约：
     `loss_e = -(Σ_{i∈e} f(r_i)·A_i·logp_i) / D_e`（D_e = 该 execution
     的 provenance token 数）→ `loss = (Σ_e loss_e) / N_exec`
     （execution 等权平均）→ `dL/dlogp_i = -(f·A)/(D_e·N_exec)`。
     **分母按 execution 隔离**；execution 的 provenance token 数为 0
     直接抛错（fail-closed）。
   - `DisTokenRecord` 目前只有 `provenance_mask` 一个掩码字段——
     `horizon_gradient_mask` 还没有表达位。
   - `reject_ratio_by_length_bucket`：按轨迹 provenance token 数分桶
     （边界 2048/8192/32768）统计 DIS 拒绝计数。
2. `rh2/src/repoharness2/adapters/slime/batch_admission.py`
   - `normalize_rewards_by_group`：**group mean**（`std_normalization`
     默认 False），按唯一 RolloutExecution 计组统计再广播给 branches；
     E 不变量五条；`zero_trainable_tokens_execution` fail-closed 守卫。
     **没有 LOO 选项，也没有 membership/masking 参数**——横向对比
     SkyRL 的 RLOO 实现，差一个 `n/(n-1)` 因子与分组键下的成员处置。
   - `predict_batch_schedule`：镜像 slime `build_dp_schedule`
     （pin e848052a）——按**唯一 rollout 数**计 `num_steps =
     num_rollouts // global_batch_size`（branch 不增加 rollout 数），
     动态装箱 first-fit 按 token 长度。**装箱只看 token 长度与 rollout
     计数，不知道梯度有无**：一个有 token 无梯度的 masked member 若被
     交付，就占 rollout 名额、占 microbatch token 预算。
3. `docs/agentic_RL/repo_harness_rh2_workstreams/fa/fa2a_decision_package.md`
   - D1a 第 5 条：三 disposition 枚举 + `GroupOutcomeView`（固定 n 个
     成员及 reward → advantage 计算）/ `TrainableBranchView`（只含可构造
     训练张量的 branches → trainer）两个派生视图。
   - D1a 第 6 条：`provenance_loss_mask`（不可变事实）与
     `horizon_gradient_mask`（step-local 算法决定）严格分离。
   - D1a 第 10 条：五个 FA-4 延后项（本文第 4 节逐项映射）。
   - D1a 第 11 条：固定 n、不做静默 n-1。

---

## 4. 五个延后项 + DIS 耦合项的证据映射表

图例：**E0** = 论文明确回答；**E1** = 官方代码回答（带版本漂移风险）；
**E3** = 我方从证据推断；**U** = 无人回答；**exp** = 必须实验/诊断数据
才能定数值。所有"建议"仅是证据映射，不是拍板。

| # | D1a 第 10 条延后项 | 论文（E0） | SkyRL 代码（E1） | 未回答的部分 | 结论形态 |
| --- | --- | --- | --- | --- | --- |
| 1 | GRPO mean 还是 leave-one-out | **LOO**（§4.2 逐字，沿 DeepSWE + Dr.GRPO） | RLOO 按 `(r−mean_all)·n/(n−1)` 实现，对全组 n 计算，masked 成员照常进 baseline | 无——但注意数学事实：std 关闭且成员集固定时 mean 与 LOO 只差常数因子 (n−1)/n，masked member 在场**不放大**两者差异（第 5.1 节数值验证）；真正改数值的是成员计入/剔除 | 设计可决（T0 预注册）；不需实验区分 mean/LOO 本身 |
| 2 | 是否做 std 归一化 | **不做**（§4.2 逐字，且连长度归一化一起去掉） | RLOO 路径无 std 除法 | std 开启时与 membership 的交互非线性（第 5.1 节场景 B：计入 horizon 成员使 A_fail 从 −0.4082 变 −0.5773）；但论文与 DeepSWE、Composer 2、DeepSeek-V3.2 一致均关 std | 设计可决：关（与我方 `std_normalization=False` 默认一致） |
| 3 | masked member 是否进 loss 的 execution 平均分母（`N_exec`） | **U**（无 loss 公式） | 机制随 `loss_reduction` 翻转：`token_mean` 不稀释、`sequence_mean`/`seq_mean_token_sum_norm` 稀释（第 2 节表）；论文用哪档为 U | 我方 `faithful_dis_loss_by_execution` 的分母按 execution 隔离，masked member 唯一的跨成员耦合就是 `N_exec` 与 DP 按 execution 数加权；两种选择都可实现（第 5.2 节数值） | **T0 预注册 + exp**（小规模消融看梯度尺度方差） |
| 4 | masked member 是否占 optimizer `global_batch_size`（slime `build_dp_schedule` 按 rollout 装箱） | 弱证据：on-policy 固定 64 任务批，样本天然占位、未见补充；但"占位≠占分母"论文未区分 | `apply_overlong_filtering` 置零不删样本 → 样本留在 batch 形状里（占序列位） | 我方特有：交付则占 rollout 名额 + 装箱 token 预算（horizon 成员是最长样本，≈32K token 的零梯度 forward/backward 开销）；不交付则 GBS 只数带梯度 execution、每组交付数变成 8−#masked | **T0 预注册 + exp**（依赖 horizon 命中率实测） |
| 5 | BatchAssembler 是否需补充 gradient-bearing execution | **U**（固定 on-policy 批无补充机制，也未报告 horizon 率——连"要不要补"的输入都没有） | 无补充逻辑 | 若延后项 4 选"不交付"，每步带梯度 execution 数 = 64−#masked 随机波动，是否补齐取决于命中率与波动容忍 | **exp-required**（先由 D1b 诊断测 horizon 率再决定） |
| 6（追加） | 与 DIS 分母档位（`provenance_tokens` vs `accepted_tokens`）的耦合：horizon token 是"被拒 token 留分母"还是另一类 | **零证据**——论文完全 on-policy，无任何 importance sampling | 无 DIS 对应物 | 是**第三类**：DIS 拒绝是 per-token 的 off-policy 信任窗事实，horizon mask 是 member 级 step-local 算法决定，两者应是独立相乘的算法掩码（`provenance_mask × f(r) × horizon_gradient_mask`）。分母语义、指标归属、accepted_tokens 消融下的口径全部要自定义（第 5.2/7 节） | **T0 预注册**；组合效应 exp-required |

映射表外的一条独立发现：**指标污染风险**。horizon 成员按构造是最长
轨迹（context 上限 ≈32K token），若其 token 继续流入
`reject_ratio_by_length_bucket`，会集中落进最高长度桶 `(32768,inf)` 或
`(8192,32768]`，把"DIS 长度相关拒绝偏差"这个监测指标与 horizon 屏蔽
政策搅在一起。建议 FA-4 把 gradient_disposition=masked 成员从 DIS 拒绝
指标聚合中单列（tag 分开，不混桶）。

---

## 5. 数值例子

### 5.1 advantage：n=8、1 个 masked member 的口径对比

设定：一组 n=8 个 execution。场景 A：1 个成功（r=1）、6 个正常失败
（r=0）、1 个 horizon 成员 r=0（到限未解决，gradient masked）。场景 B：
同上但 horizon 成员 r=0 改为 r=1（冻结快照过了测试——scored profile 下
horizon 成员可以有正 reward）。std 用总体方差、`std_epsilon=1e-6`，与
`normalize_rewards_by_group` 同式。

**场景 A（horizon r=0）**：

| 口径 | 成功者 A | 正常失败 A | horizon 成员 A（反正被屏蔽） |
| --- | --- | --- | --- |
| group mean，horizon 计入（n=8） | **0.8750** | −0.1250 | −0.1250 |
| group mean，horizon 剔除（n=7） | 0.8571 | −0.1429 | — |
| LOO，horizon 计入 | **1.0000** | −0.1429 | −0.1429 |
| LOO，horizon 剔除 | 1.0000 | −0.1667 | — |
| mean+std，计入 | 2.6457 | −0.3780 | −0.3780 |
| mean+std，剔除 | 2.4495 | −0.4082 | — |

**场景 B（horizon r=1）**：

| 口径 | 成功者 A | 正常失败 A | horizon 成员 A |
| --- | --- | --- | --- |
| group mean，计入 | 0.7500 | **−0.2500** | 0.7500 |
| group mean，剔除 | 0.8571 | −0.1429 | — |
| LOO，计入 | 0.8571 | **−0.2857** | 0.8571 |
| LOO，剔除 | 1.0000 | −0.1667 | — |
| mean+std，计入 | 1.7320 | −0.5773 | 1.7320 |
| mean+std，剔除 | 2.4495 | −0.4082 | — |

三条可核验的读数：

1. **mean vs LOO 在 masked member 在场时差异不放大**：成员集固定、
   std 关闭时严格满足 `A_mean = (n−1)/n × A_LOO`（场景 A/B 均验证：
   0.8750 = 7/8×1.0000；0.7500 = 7/8×0.8571）。这是一个纯梯度尺度
   因子（7/8），可被学习率吸收，**不改变组内样本的相对权重**。所以
   延后项 1 的实质不是估计器之争，而是尺度约定 + 与外部配方的可比性
   （选 LOO 则与 SA-SWE/DeepSWE 配方逐项同构）。
2. **真正改变数值的是 membership**（计入 vs 剔除），且方向依赖 horizon
   成员的 reward：场景 B 里 LOO 计入使每个正常失败者的负 advantage 从
   −0.1667 加深到 −0.2857（×1.71）——一个"到限但成功"的成员会显著
   加重兄弟失败样本的惩罚。若 horizon 成员系统性偏向某种 reward
   （例如全是 0），计入相当于给全组 baseline 持续下压。这正是
   strict_horizon_excluded_v1 与 scored_horizon_masked_v1 两个 profile
   的分布差异所在，必须靠 D1b 诊断的 horizon 成员 reward 构成来定。
3. **std 放大 membership 敏感度且非线性**（场景 B：−0.4082 → −0.5773），
   关 std（论文配方 + 我方默认）能把 membership 的影响限制在 mean 一层。

顺带一条巧合警示：场景 A 中 "LOO 计入" 的失败者数值（−0.1429）恰好
等于 "mean 剔除"（因为被剔除者 r=0 与失败者同值），不要据此误判两种
口径等价——场景 B 立即分裂（−0.2857 vs −0.1429）。

### 5.2 loss 分母：masked member 占不占分母的具体后果

设一个训练 step 交付 8 个 execution（简化为一组），其中 1 个是 horizon
masked；正常 execution 各有 8K provenance token，horizon 成员有 32K
（到 context 限的轨迹就是最长的）。

**（a）我方 by-execution 归约（`faithful_dis_loss_by_execution`）**：

```text
masked 计入 N_exec（交付 + advantage 置 0 或 horizon_gradient_mask=0）：
  每个带梯度 token 的梯度 ∝ 1/(D_e × 8)
masked 不计入 N_exec（不进 TrainableBranchView）：
  每个带梯度 token 的梯度 ∝ 1/(D_e × 7)
两者相差恒定因子 7/8 ≈ 0.875
```

因为 `D_e` 按 execution 隔离，masked 成员的 32K token **不会**流进
任何别人的分母；唯一的跨成员耦合就是 `N_exec`（以及 DP 分区按
execution 数加权时要不要数它——两边必须选同一口径，否则 partition
invariance 测试会碎）。代价是这个 7/8 因子逐 step 随 #masked 波动：
horizon 率 p 下每步的梯度尺度乘子是 `(8−#masked)/8` 的随机变量。

一个巧合值得记录但不构成设计论据：若同时选 "LOO baseline"（×8/7）与
"masked 计入 N_exec"（×7/8），两个因子在这个配置里恰好抵消。

**（b）平铺全局 token-mean（`faithful_dis_loss` 单分母口径）陷阱**：

```text
分母 = provenance token 总数（v1 = provenance_tokens 档）
  masked 不在 batch：D = 7 × 8K = 56K
  masked 在 batch 且其 token 留分母：D = 56K + 32K = 88K
  → 全部带梯度 token 的梯度一律 × 56/88 ≈ 0.636
```

即：如果 horizon 屏蔽用"advantage 置 0 但 token 留在平铺分母"实现，
`provenance_tokens` 档会让**最长的零梯度轨迹按长度稀释整个 step 的
梯度**——且稀释比例与 horizon 成员长度成正比（这不是 DIS 拒绝 token
留分母的本意：DIS 拒绝是 per-token 零散事件，horizon 是整条 32K 的
块状注入）。SkyRL 的 `token_mean` 之所以没有这个问题，是因为它的分母
是 `loss_mask.sum()`，mask 置零后 token 连分母都不进。**结论：horizon
屏蔽的分母语义不能自动继承 "DIS 被拒 token 留分母" 的 v1 预注册**，
两者必须分开预注册（这就是映射表第 6 项说 horizon token 是"第三类"
的定量理由）。

**（c）GBS/装箱（`predict_batch_schedule` 口径）**：

```text
global_batch_size=64（按唯一 rollout 计）、horizon 率 p=10% 时：
  交付 masked：64 个 rollout 中 ≈6.4 个零梯度，但占满装箱 token 预算
    ——horizon 成员是 32K 级最长样本，first-fit 装箱里单条即占
    大半个 microbatch（max_tokens_per_gpu 量级时），零梯度照付
    forward/backward
  不交付 masked：每组交付 8−#masked 个 rollout，GBS 语义变成
    "64 个带梯度 execution"，需要 assembler 多供组（延后项 5），
    且组的交付原子性（整组同 step 交付的假设）被打破
```

---

## 6. 外推风险声明

把 SkyRL-Agent 的 horizon 语义搬到 RH2 首训前，以下差异必须写进决策
理由，不能默认可迁移：

1. **模型**：dense Qwen3-32B vs 我方 Qwen3-30B-A3B（MoE，激活 3B）。
   轨迹级屏蔽会缩小每步有效梯度 token 量，对 MoE 还叠加 router 负载
   统计的噪声——论文对此零证据。
2. **on-policy vs 我方 version-aware fully async + faithful DIS**：论文
   的屏蔽证据是在**零 off-policyness**下取得的。horizon 成员恰是墙钟
   最长、版本跨度最大的轨迹，在我方异步设置里它们本来就是 DIS 拒绝率
   最高的人群——"屏蔽 horizon"与"DIS 部分拒绝"在我方是叠加生效的
   两层，论文无法为这个组合背书。
3. **scaffold 与 horizon 人群构成**：他们的 agent 在接近 step/context
   预算时**收到显式告警**（§4.2 hints），且论文抱怨 agent 更常"提前
   放弃"而不是撞限；Claude Code 黑盒无此告警（且我方首训关闭
   compaction）。两边"到达 horizon 的轨迹"在能力构成、reward 构成、
   命中率上都不可比——而论文连自己的命中率都没报。
4. **反例存在**：Composer 2 明确报告小规模实验未见 overlong masking
   收益因而不屏蔽；DAPO 最终配方偏向 soft overlong shaping；K3 对相对
   token 预算超限直接 reward=−1。"保组统计 + 屏蔽自身梯度"是证据最强
   的**起点**（与证据矩阵 §8.7 结论一致），不是业界定律，必须保留
   audit_only 双 profile 对照与后续消融。
5. **batch 语义不同构**：论文 batch=64 按任务计；slime GBS 按 rollout
   计且有 microbatch 对齐/装箱约束；fan-out branch 模型（execution 内
   多 branch 共享分母）完全是我方特有——论文与 SkyRL 代码都没有对应物。
6. **E1 证据的版本漂移**：第 2 节代码事实取自 main @ 6ae5d677d8f0
   （2026-08-03），晚于论文九个月；SA-SWE-32B 实跑的 backend 与
   `loss_reduction` 档位公开材料未钉死。引用第 2 节结论时必须带
   commit 与 `U` 标注。

---

## 7. 给 FA-4/D1b 决策包的建议问题清单

按"可由设计直接预注册"与"必须先有实验/诊断数据"分列。均为建议问题，
不预决任何 T0。

**可由设计预注册（决策包给方案即可，不需要新数据）**：

1. baseline 估计器与尺度：选 LOO（与 SA-SWE/DeepSWE 同构，
   `normalize_rewards_by_group` 加 `n/(n−1)` 因子与单成员组守卫）还是
   保持 group mean（当前实现，差常数因子）？std 归一化保持关闭
   （E0 一致证据）。
2. `horizon_gradient_mask` 的表达位：`DisTokenRecord` 增字段、execution
   级 advantage 置零、还是从 `TrainableBranchView` 剔除？三者梯度等价
   但账目、指标、分母后果不同（第 5.2 节），且必须满足 D1a 第 6 条
   "不改写 provenance_loss_mask"（SkyRL 的 `apply_overlong_filtering`
   直接改 loss mask，**不可照抄**）。
3. horizon token 的分母语义单独预注册：明确它不继承 "DIS 被拒 token 留
   分母" 的 v1 条款；平铺 token-mean 口径下禁止"advantage 置零 + token
   留分母"的组合（0.636 倍长度耦合稀释，第 5.2(b) 节）。
4. DIS 指标隔离：gradient_disposition=masked 成员是否从
   `reject_ratio_by_length_bucket` 及 DIS accept/reject 计数中单列？
   （建议单列；否则最高长度桶被 horizon 政策污染。）

**experiment-required（D1b 诊断/小规模消融先行）**：

5. horizon 命中率与构成：50~100 题 × n=8 诊断中实测
   `termination_kind ∈ {context_limit_reached, max_turns_exhausted,
   task_token_budget_exhausted}` 的比例、这些成员的 reward 分布（撞限
   仍 resolve 的比例——场景 B 敏感度的输入）、及其 policy_version_lag。
   论文没报命中率，无锚可抄。
6. `N_exec`/GBS 处置的效应量：masked 计入（步内梯度尺度随 #masked
   波动 + 32K 零梯度样本的装箱成本）vs 不计入（assembler 供组压力 +
   组交付原子性破坏）——建议在 FA-5 校准窗做一次 A/B 小消融再定死。
7. BatchAssembler 是否补充 gradient-bearing execution：仅当第 6 项选
   "不计入"且实测 horizon 率高到让每步带梯度 rollout 数波动超出容忍时
   才需要；低命中率下建议首版不补（少一个新机制面）。
8. 屏蔽 vs 负信号消融（既有矩阵 §8.7 已登记）：scored_horizon_masked
   与"把可归因 horizon 当负向训练信号"（K3/Qwen 路线）的对照实验留
   正式训练后，不进首训。

---

## 8. 结论一行版

codex 引用方向正确、ID 正确（命名应澄清为 SkyRL-Agent 论文的
SA-SWE-32B 模型）；"保组统计 + LOO + 无 std + 轨迹级梯度屏蔽"是 E0
逐字可回溯的；但**分母与 batch 计数两层论文完全沉默、官方代码随配置
翻转**，这两层加上与 DIS/fan-out/异步的全部组合，必须由 FA-4 自行
预注册并经 D1b 诊断校准。
