# O02 Agentica DeepSWE：直接 RL 配方、失败尝试与可消费资产

**DeepSWE-Preview 是从已有 Qwen3-32B thinking 模型出发的专项 RL，不是随机初始化训练，也不是先做本项目 SWE-SFT 再 RL。** 公开 release 将 R2E-Gym 的可执行任务、LOO 风格优势、固定长度归一化和 Compact Filtering 组合起来；actor 的 SWE-bench Verified 单次结果为 42.2%，59.0% 则来自多候选加 verifier 的推理系统。最值得 B 线保留的反向证据，是作者在另一些数据和 SFT 起点上未得到相同改善，而不是据此淘汰所有 SWE-Gym 或 SFT 路线。本次追到发布当日的 rLLM／verl 与 R2E-Gym 文件，发现公开示例和报告配置并不完全一致，且选优实现仍需核验。**正文、模型卡与关键代码已精读；原图、原 Notion 附录案例和原始运行日志未完整取得，不能标为全部图表与实验复现完成。**

导航：[来源与覆盖](#sources) · [数据和模型关系](#data) · [算法与终止语义](#training) · [评测与负结果](#evaluation) · [代码与复现缺口](#code) · [B 线应用](#project)

<a id="sources"></a>
## 1. 来源、版本和实际阅读范围

阅读日期：**2026-09-08**。这是一个同次发布的官方技术文、模型卡、配套代码和复现说明的**分层配方专题**，不是一篇有 arXiv 正文／附录的论文，也不是 Datacurve 的同名 DeepSWE benchmark。

主文正式标题为 *DeepSWE: Training a Fully Open-sourced, State-of-the-Art Coding Agent by Scaling RL*，Together 发布时间 **2025-07-02**，Agentica 与 Together AI 合作。作者为 Michael Luo、Naman Jain、Jaskirat Singh、Sijun Tan、Ameen Patel、Qingyang Wu、Alpay Ariyak、Colin Cai、Tarun Venkat、Shang Zhu、Ben Athiwaratkun、Manan Roongta、Ce Zhang、Li Erran Li、Raluca Ada Popa、Koushik Sen、Ion Stoica。[B，页首与贡献说明][B]

### 1.1 来源分层

| 标识 | 来源与固定身份 | 本次实际取得及用途 |
| --- | --- | --- |
| B | [Together 官方技术文][B]，2025-07-02；网页没有独立修订号 | 全部可读正文至 §8、贡献说明及 Citation 标题；图注全部可读，图像加载失败 |
| N | [作者原始 Notion][N]，页面 ID `22281902c1468193aabbe9a8c59bbe33` | 只取得 TLDR／开头和背景片段；不能以它补齐 B 所说的 Appendix |
| M | [DeepSWE-Preview 模型卡][M]；文件历史最近 README 标识 `4887205c533cd162baac7ba758159cfc3304cf94`（2025-07-03） | 模型卡正文完整读取；commit 用于资产定位，没有下载权重或逐字校验固定 revision 的 raw README |
| V | [DeepSWE-Verifier 模型卡][V]，历史标识 `16722b828afa4c31ed150c435eff2ca4b29365e6`（2025-07-02） | 完整模型卡、[adapter_config.json][V-config]；区分推理选择器和 actor 训练 |
| C | `agentica-project/rllm@c4d1cfc1c9320d0f298524b309bdcae3c33bfabe`，2025-07-02 | 从发布日 `examples/swe` 历史定位；不是已证明与最终训练完全相同的 run commit |
| L | `agentica-project/verl@777704aa64c5745c4ccb250ae8977469579ebfc0` | C 的实际 submodule pin；读 LOO、policy loss、reduction 和 actor 消费，不拿现代 verl 默认补历史 |
| R | `R2E-Gym/R2E-Gym@8fb8f05a3b367126f70c54b21907a195521bcebc`，2025-07-02 | 同期复现指南及 verifier 数据流；rLLM 安装指令并未固定该版本，因此它是阅读快照，不是最终训练依赖证明 |
| D | [R2E-Gym-Subset 当前数据页][D] | 可见 train 约 4.58K 行及字段样例；未下载全量并恢复 2025 最终消费 manifest |
| I17 | [R2E-Gym issue #17][I17] 及回复 | 第三方复现困难报告与一个文档错误确认；不是成功独立复现，也不是其他疑问已获确认 |

项目读取基线：`Rogerffff/RepoHarness@miles-migration`，commit **`d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`**。任务范围依据 [B 外部补读请求](../../../agentic_RL/repo_harness_rh2_workstreams/project1_execution/b_external_reading_requests_20260908.md)。只维护本篇和自查，不修改项目实现或共享索引。

官方 rLLM 旧仓库当前 main 为 `7b47687f6a9ef1bf5cbd56dd1af61fff08c4b0e4`（2025-09-17），README 指向后来迁移的仓库。本篇主动回到上述发布日 C 快照；**后来框架更强或不同，不应倒填成 DeepSWE 最终运行的配置。**

### 1.2 原文章节覆盖

以下位置按 B 的标题与图号，不为网页编造 PDF 页码。没有把不能取得的图像标成已目视核验。

| 原文部分 | 本轮覆盖 | 本笔记位置 |
| --- | --- | --- |
| 发布导语、DeepSWE-Preview、Fig.1–2 | 全部文字、图注；模型关系、训练结果与验证集名称差异 | §2、§7 |
| §1 Background，Fig.3–4 | 全部文字／图注；agent 与 SWE 交互结构 | §2–3 |
| §2.1 数据 | 全文；实际来源与去污染主张 | §3 |
| §2.2 环境、工具、reward、Kubernetes | 全文；配套 SWEEnv 入口附查 | §3、§6 |
| §2.3 GRPO++、Compact Filtering，Fig.5–7 | 全文／图注；固定代码逐项对照 | §4–5 |
| §3 Test-Time Scaling，Fig.8–10 | 全文／图注；EF／EB／hybrid 实现与使用指南 | §7–8 |
| §4 Evaluation，Fig.11 和 HTML 表格 | 全文及可读数表；未从图中估读额外数值 | §7 |
| §5 Emergent Behaviors，Fig.12–13 | 全文／图注；只记录作者轶事，不当作统计消融 | §9 |
| §6 Other Attempted Experiments | 全部三个负结果分支及作者限制 | §9 |
| §7 Future Work | 全文；未发生的阶段仍列计划 | §2、§9 |
| §8 Conclusion、Major Individual Contributions | 全文；59.0／59.2 冲突、actor 与 verifier 工作分工 | §2、§7、§11 |
| 原 Notion 的附录／额外案例 | **未取得**；B 明确提及 Appendix，但其页面未含对应正文 | §11、作者自查 |
| W&B 与 Google Drive 原始日志 | 入口存在，W&B 无可读导出、Drive 显示登录；**未检查原始记录** | §10–11 |

图5的任务是 FrozenLake，图6的模型是 Qwen3-14B；两者不能被写成 Qwen3-32B SWE 主训练的同条件逐项消融。图2图注称 SWE-Bench-Hard，邻近文字谈 SWE-bench Verified；没有原始 run config／task manifest 时，不能将二者静默合并。[B，Fig.2、5、6][B]

没有复制第三方全文、图像或完整代码进仓库。下文以自写分析为主，网页原文按节／图定位，代码按固定 commit、完整路径和符号定位。

## 2. 真实训练链：actor 的 pure RL，不等于整个发布没有 SFT

本次发布包含三条应分开的链：

```text
已有 Qwen3-32B（thinking）
  └─ R2E-Gym 任务上的 outcome RL → DeepSWE-Preview actor

已有 Qwen3-14B
  └─ 正误轨迹/补丁的 SFT（LoRA）→ DeepSWE-Verifier，供推理时选优

候选 actor 轨迹 + 回归测试 + 模型生成的复现测试
  └─ EF / EB / hybrid 选择 → 一份提交补丁 → 官方 SWE-bench 最终评分
```

第一条没有额外教师轨迹 warm-start；第二条明确是监督微调；第三条增加推理预算，不更新 actor。模型卡把 verifier 称作 critic，但它**不是主 RL 中参与 GAE 的 value critic**。公开 LOO 主路径不需要该 verifier 提供 reward，也没有披露 actor OPD 阶段。[M，Overview、Training Recipe；V，Overview；C1、C4；L1][M]

“from scratch”是从现成 Qwen3-32B 开始本次专项后训练，不是重新预训练；也不是证明 Qwen3 自身从未做过 SFT／RL。它是 dense 32B 配方，不能因参数数字接近，就按本项目 30B-A3B MoE 的激活量、显存或吞吐直接换算。

作者另尝试了四个 Claude 轨迹 SFT 起点，但没有把它们作为最终 actor 的前置阶段。类似 DeepSeek-R1 的后续整理训练、更大模型、更长上下文及 web agents 属于未来计划，不是本次 release 已做完的后续阶段。[B，§6–7][B]

<a id="data"></a>
## 3. 数据、环境和评分：实际拿到了什么

### 3.1 来源与消费量不是同一个数

[M，Data][M] 声明使用约 4.5K R2E-Gym 问题，并去除与 SWE-bench Verified 相同仓库衍生的问题，例如 sympy。其每题对应 Docker image。当前 [D][D] 的页面约 4.58K 行，不能因此改写发布时精确训练数，也不能证明当前 revision 仍等于最终训练 manifest。

| 阶段 | 已知事实 | 本次未恢复的部分 |
| --- | --- | --- |
| 原始候选 | 复用 R2E-Gym，不是本文新建的 PR 采集器 | 全部原始 PR／仓库候选数、DeepSWE 专属筛选每一步的存活率 |
| 训练候选 | Release 约 4.5K、声明仓库级去重；当前 HF Subset 可读 | 实际 run 的 dataset revision、精确题目列表及去重脚本输出 |
| 环境 | `docker_image`、`commit_hash`、题面、测试预期等字段 | 镜像 digest、当前 pull 成功率、历史环境与当前镜像的等价性 |
| 正常发布 batch | B 报告 64 题×每题 8 次=512 条 rollout | 最终各步有效 loss 轨迹、mask 数、失败重试与丢弃数量 |
| 训练进度 | 模型卡指向约 200 RL steps 的成果 | 原始每步日志、更多尝试总量和 checkpoint 选择协议 |
| 最终评测 | 复现指南按 500 个 Verified 实例处理 | 全部原始预测／运行记录本次未取得 |

[C2：`examples/swe/prepare_swe_data.py`][C2] 不只登记 Subset，还登记 R2E-Gym Lite/V1、SWE-bench Lite/Verified 和 `r2e-edits/SweSmith-RL-Dataset`。它复制整行并注册可用 split，没有在此执行仓库排除、题意审计或镜像验证，`load_dataset` 也未固定 revision。**能加载多个数据源，不等于报告中的每条失败实验都公开了完整配方。**

该脚本对无 train/test 名称的数据使用第一个可用 split 作为 train，是通用 helper 行为；它不是正式数据划分依据。对 B 线，实际使用时应自行明确 split 和 revision，而不是继承 fallback 语义。

### 3.2 数据行不应直接全部暴露给模型

当前 Subset 可见 `repo_name`、`docker_image`、`commit_hash`、`parsed_commit_content`、`execution_result_content`、`modified_files`、`relevant_files`、`prompt`、`problem_statement`、`expected_output_json` 等字段。其中部分显然属于生产／评分侧材料；`prompt` 还可能是生成题面时的模板，不能仅凭字段名当成求解提示。[D，Dataset Viewer][D]

[C3：`rllm/environments/swe/swe.py::SWEEnv.reset`][C3] 实际通过 `RepoEnv.get_task_instruction()` 取得任务，源码中的 `gt_patch` 返回项已注释。它说明有一层选择，不证明 runtime 内不存在其他泄漏。数据行可包含参考信息，与 agent 真正看到了什么是两个问题；判断后者需要检查具体模板、文件和网络可见性。

此类字段也不应在日志或 learner/debug 工具中意外成为模型上下文。这个提醒是对数据消费的工程推论，不是已经发现 DeepSWE 将整行答案喂给模型。

### 3.3 工具、反馈与评分层

[C3][C3] 的 r2egym scaffold 安装 file editor、search、execute_bash、finish 四组工具；另有 sweagent 的编辑／shell／submit 工具集合。默认环境后端为 Kubernetes。`reset` 创建／重置 RepoEnv，`step` 传递工具观察，`compute_final_reward` 才调用环境最终评分。per-step reward 在这一封装下通常为零，不能称为有逐步 correctness reward。

[M，Environment][M] 所说的 sparse ORM 是测试执行产生的二元 outcome，不是另训练一个 reward model。成功要求选定的 P2P/F2P 测试通过；测试失败／评分超时为零。**这并未描述 setup 损坏、parser 空输出、远程服务故障等所有情况的可信评分合同。** 不应将“超时记零”的简短配方扩张成所有基础设施异常一律可训练失败。

本文没有恢复 DeepSWE 专属的 gold/no-op/合法替代解测试报告，也没有验证所有镜像的 flakiness、评分隔离、未来 git history 或网络访问规则。引用 R2E-Gym 并不能替代这些实际资格验证。已有 [O03 R2E-Gym](O03_r2e_gym.md) 可说明原始环境研究，但不能替本次运行补出未知的版本和操作。

### 3.4 四种时间限制必须分列

| 限制 | 报告／实际源码 | 不能混淆的对象 |
| --- | --- | --- |
| 训练测试评分 | M：300 秒；C3 默认 `reward_timeout=300` | 不是整条 agent 生成时限 |
| Release Compact Filtering 时限 | M：generation timeout 20 分钟 | 不能当作公开 shell 实际值 |
| 发布日训练脚本 | C1：`agent.trajectory_timeout=5400`；engine 还有每次 retry 7200 秒外层 wait | 名义 90 分钟配置及外层保护，不等于论文20分钟 |
| 评测轨迹内评分 | R1/R2：`max_reward_calc_time=1200` | 不是官方最终 SWE-bench scorer 的30分钟口径 |
| 官方最终评分 | M 描述30分钟；R1另导出补丁调用官方 scorer | 未固定最终 scorer 版本，本轮未重跑 |
| 单次工具执行 | C3 默认 `step_timeout=90` | 不覆盖初始化、生成、整个评分生命周期 |

对于环境敏感任务，短评分 timeout 可以改变 reward 的含义。因此 B 应先用 gold 和已知合法解测真实运行分布，再决定训练评分预算；这里没有批准任何统一阈值。

<a id="training"></a>
## 4. GRPO++：文字配方与可执行语义分开

### 4.1 发布描述中的七项并不是七个独立验证的收益

模型卡将 clip-high、关闭 reference-KL loss、移除 reward 标准差归一化、固定最大长度归一化、LOO baseline、Compact Filtering、关闭 entropy loss 组合为 GRPO++。[M，RL Algorithm][M]

其中，去掉 KL 不等于去掉 PPO likelihood-ratio clipping；关闭 entropy 正则也不意味着不计算 entropy 诊断。原文关于 entropy 0.3–1 的经验范围不能当成所有 tokenizer、底座和任务的通用稳定条件。

B 的整套 GRPO++ 对照图5来自 FrozenLake；图6的 Compact Filtering 对照模型为 Qwen3-14B。本轮仅取得图注和解释，未取得曲线原图。因此不提供任何额外的峰值、收敛步、置信区间或逐组件贡献数字。[B，§2.3，Fig.5–7][B]

### 4.2 从发布日代码恢复 LOO 和固定分母

[C1][C1] 选择 `algorithm.adv_estimator=loop`；[L1：`compute_loop_outcome_advantage`][L1] 以 UID 分组，先汇总每条完整 trajectory 的终局 reward，再在 `no_grad` 内计算 leave-one-out baseline。用 $G$ 表示组内实际成员数，等价的自写表达为：

$$
A_i=r_i-\frac{\sum_{j\ne i}r_j}{G-1},\qquad G>1.
$$

单成员组在此实现回退为零 baseline，而不是自动再采到指定组大小。原文没有把这一分支作为已验证配方。`loop` 也不是开启了一个 GAE critic；API 出现 critic 配置、gamma 或 lam，不能据此认为它们在该分支参与了更新。

[L2：`compute_advantage`][L2] 将上述优势广播到 response 的 attention 范围；[L3：`DataParallelPPOActor.update_policy`][L3] 真正优化时优先读取 `traj_mask`。因此工具观察可以存在于上下文和 attention 中，却不应成为 actor policy loss 的目标 token。不能把 attention mask、优势广播 mask 与最终 loss mask 看成一个对象。

同一发布日的 [L1：`compute_policy_loss`、`agg_loss`][L1] 实际采用 token ratio，低端 clip 0.2、高端由 C1 设0.28。`dual-clip` 的辅助值虽被计算，其最终启用分支在源码中注释掉了。对一个 microbatch，可用下式概括选中分支，**这是源码代数重述，不是文章原有公式，更不是未经核验的全分布式梯度定理**：

$$
\ell_{it}=\max\{-A_i\rho_{it},\;-A_i\operatorname{clip}(\rho_{it},0.8,1.28)\},
\quad
\rho_{it}=\exp(\log p_\theta-\log p_{old}),
$$
$$
L_{micro}=\frac{1}{B_{micro}L_{pad}}\sum_i\sum_t m_{it}\ell_{it}.
$$

`seq-mean-token-sum` 在**这个固定 fork**里先将每行 masked token loss 求和，除以矩阵宽度 `L_pad`，再对行求平均。它不是按每条有效 response 长度取均值，也不是简单的全批有效 token mean。C 的 transform 把 response pad 到32768；actor 再处理 gradient accumulation。不同框架同名 reduction 未必相同，完整 DP/SP 缩放没有在本轮做 GPU 数值对拍。

`old_log_probs` 在 [C4：`AgentPPOTrainer.fit_agent`][C4] 里是在生成后、更新前由训练后端重算的。这个快照没有把推理端逐 token 概率原样交给此字段，所以不能宣称已经验证 trained-policy、behavior-policy、重分词和数值执行全部一致。

### 4.3 成员、reward 和 loss：Compact Filtering 不是整组删除

文章／模型卡明确说将达到长度、步数或生成时限的轨迹 loss 屏蔽，但没有给出完整成员消费与分母合同。[M，RL Algorithm][M] 发布日 [C5：`run_agent_trajectory_async`][C5] 则提供了更具体的实现：

1. `overlong_filter=True` 且结束原因是 `TRUNCATION`、`MAX_STEPS` 或 `TIMEOUT` 时，将整个 `response_masks` 置零；条件没有检查 reward 是否为零，尽管注释写了类似限定。
2. `masked_out=True` 时跳过 `compute_final_reward`；在该 SWE 封装的零中间 reward 路径下，通常留下零 outcome。
3. trajectory 仍返回，transform 仍保留其 reward 和行；默认不做整组 rejection。
4. 组优势使用原返回成员，actor 的 `traj_mask` 才屏蔽该行自身梯度；全零行仍可能影响 LOO baseline 和行均值分母。

因此它不是“已经运行最终测试并保留真实 outcome，然后仅取消自身梯度”的同一语义，也不能直接与 SA-SWE 的文字描述合并。

一个纯算术示例：reward 为 $(1,0,0,0)$，第四条置零 mask但仍留组，则另外两条失败轨迹的 LOO 优势为 $-1/3$；若先删除第四条再计算，则变成 $-1/2$。本地只验证了这个代数区别，没有复现原训练。固定分母下的梯度总尺度还会变化。

### 4.4 超时并非全部走同一个分支

C5 的 `env.step` 外层 `wait_for` 捕获超时后标为 **`ENV_TIMEOUT`**，而它不在上面的三个过滤原因中；之后仍可能调用最终评分。普通计时达到阈值则标为 `TIMEOUT`，会被过滤。retry 外层另有7200秒保护，最多使用默认三次重试；这不是保存并恢复旧 prefix 的 partial rollout。

这是可定位的**发布期静态实现差异**，不是证明最终64卡实验出现了错误奖励，也不能据此断言目前上游仍然如此。对迁移者，至少应该明确区分工具超时、轨迹预算耗尽、评分超时和基础设施故障。

### 4.5 “有课程效果”不等于代码配置了动态课程

[C4][C4] 总是计算按 UID 的 `solve_none`、`solve_all`、`solve_partial` 指标；真正删除全错／全对组由 `trainer.rejection_sample` 控制。[C6：配置][C6] 默认该项为 **False**，C1 没有开启。脚本存在其他数据源、可选过滤或 stepwise 模式，并不证明最终运行使用它们。

这个快照的数据入口没有披露根据策略能力在线合成新任务或调整难度的 controller。B 对 R2E-Gym 的 curriculum 解释，宜记录为作者对既有任务分布的经验描述，而不是一个可直接移植的已验证课程算法。

<a id="code"></a>
## 5. 报告、脚本、训练后端：不能拼成一张虚构的最终配置

| 项目 | Release 文字／模型卡 | 发布日公开 C／L 路径 | 如何使用这项证据 |
| --- | --- | --- | --- |
| 模型 | Qwen3-32B thinking，专项 pure RL | `Qwen/Qwen3-32B`，LoRA 默认0 | 支持已有模型全参数RL路线，不支持本项目MoE预算直接照搬 |
| GPU | B 报告64 H100、约6天 | `nnodes=2` ×8=16GPU | 两者不能称为完全一致的最终脚本 |
| prompt batch | B 报告64题×8条 | `train_batch_size=8`、`n=8` | 8题与64题的组数不同，不能拿512条填补脚本 |
| prompt／response | 文章未给完整分层长度 | prompt4096；response32768；初始之后计数含观察 | 32768不是纯assistant输出总量的同义词 |
| steps | 主文没有完整配置表 | `agent.max_steps=50` | 来源是代码，不冒称正文明确50 |
| generation时间 |20分钟 | trajectory5400秒，retry外层7200秒 | 保留冲突，等待原W&B resolved config |
| 学习率 |主文未逐项写 |1e-6 | 可复用的公开示例值，不保证等于每次训练尝试 |
| 更新 |组合GRPO++描述 |LOO；PPO epoch默认1；mini-batch8；无KL/entropy项 | 不由算法名反推未读取的run状态 |
| 训练精度／布局 |未完整分项 |vLLM bf16默认；TP8、Ulysses SP8、FSDP offload、checkpointing | 这是示例配置；未做GPU配置验证 |
| 零方差组 |文字未完整披露 |rejection默认关闭，照常有诊断指标 | 不将“统计到了”当“过滤了” |
| 验证 |图注Hard、主结果Verified |val文件Verified，单次贪心默认 | 不等于最终temp1、16-run评测 |
| 训练停止 |约200步模型结果 |`total_epochs=1000`；每10步save/test | 示例上限不是最终训练步数 |

文件来源：[C1][C1]、[C6][C6]、[C4][C4]、[L1][L1]。这个表的目的不是否认发布结果，而是防止“公开 recipe”被误读成所有运行细节已经冻结、相互一致。

## 6. Infra 和 rollout：并发 agent，不是已经证明的 fully-async learner

### 6.1 真实主路径

C1 → `rllm.trainer.verl.train_agent_ppo` → `AgentPPOTrainer.fit_agent` → `AsyncAgentExecutionEngine` 是本次附查的入口。[C0][C0][C4][C5]

在 trajectory-level 默认设置下，UID 在重复采样前产生；每题重复8次，环境按索引建立。所有 trajectory 可异步交互，但 trainer 收齐本批结果并按 `idx` 排序后，才转换张量、重算概率、计算优势并更新。生成引擎在 batch 生成时唤醒、完成后休眠，使用 hybrid 资源。

所以 `rollout.mode=async`、`agent.async_engine=True` 首先说明模型请求／agent 执行可以并发，不证明 learner 持续消费跨策略陈旧轨迹。本轮未见这个 SWE 入口的 bounded-staleness、在途跨版本恢复或持续新旧权重并存的合同。

### 6.2 模型调用与训练 token 的边界

C5 的 verl响应路径先取生成token再decode，移除pad/eos字符串并返回文本；随后按assistant与environment消息重新编码、拼接token和mask。模型对话模板、special token 和跨轮前缀的等价性需要另外验证，不能从“返回了Token模式”推成原始token端到端保真。

其 response 长度计数包含 assistant 加 environment 消息；工具输出既消耗上下文，又通过 mask 不参与 policy loss。这解释了为什么只比较模型输出 token 或只提高 max response，可能不能解决真实 agent 的长度瓶颈。上述是实现语义，不是本轮测得的性能瓶颈。

### 6.3 环境扩展不是额外GPU的一句脚注

发布文将容器数量、dockerd过载、Kubernetes迁移和镜像预热列为实际运行经历；配套 [C7：SWE README][C7] 也要求大型CPU/磁盘资源，并明确本地 kind 不足以代表完整训练集群。作者的环境服务池与64H100不是同一个资源分母。

对 RepoHarness，重点不是复制Kubernetes。需要先测当前并发下的启动、工具执行和评分成本，再判断单机容器、远端环境池或缓存是否必要。CPU和镜像供给跟不上时，增加推理并发可能只是增加等待与失败。

<a id="evaluation"></a>
## 7. 评测：42.2、59.0 和71.0分别测什么

### 7.1 Actor 与选择器的结果分列

[M，Evaluation][M] 报告使用R2E-Gym scaffold，64K上下文、100最大环境步，生成patch后交官方SWE-bench最终评分。Pass@1为16次运行的平均。

| 结果 | 单位与含义 | 不应写成什么 |
| --- | --- | --- |
|42.2%|DeepSWE-Preview actor，单份候选的平均成功率|32B模型一次输出就有59%|
|71.0% Pass@16|每题16个候选中至少有一个最终通过的覆盖率|实际选择器能识别全部正确候选|
|59.0% Hybrid Best@16|生成16候选，再用EF＋EB混合选择一份patch的系统成绩|与单次模型推理相同成本|
|57.9% Hybrid Best@8|较少候选下的选优结果|证明所有预算下8次都最优|

单次actor→Hybrid Best@16的差为16.8个百分点；从8到16候选只增加1.1个百分点，是这套选择器的观测结果。它不包含完整推理费用、任务级方差或高预算时的最优性证明。Pass@16与Best@16之间仍有12个百分点选择缺口；并不是“Pass@K=100%”。

官方表中不同模型使用OpenHands、SWE-Agent、R2E-Gym以及不同训练来源；例如Devstral24B单次46.6高于DeepSWE单次42.2，而其headline借助TTS更高。SOTA是2025发布时的分类和预算条件，不能写成当前榜单结论，也不能将所有跨行差归给RL算法。[M，Evaluation表；C7][M]

B §3另外报告扩大单次上下文到128K的收益有限；这一现象和并行采样收益应分开。图9未取得，不能据图注以外推断完整各预算点或成本曲线。较长上下文没有明显提高该测试结果，也不证明所有长程SWE任务都不需要更大上下文。[B，§3，Fig.9][B]

### 7.2 原始复现链比一条模型调用长

[R1：`reproduction/DEEPSWE_REPRODUCTION.MD`][R1] 的步骤是：vLLM服务actor → `edit.py runagent_multiple`运行500题 → 保存轨迹 → `create_swebench_submission.py`导出patch → 另调用官方`swebench.harness.run_evaluation`。

主要参数是r2egym scaffold、**`use_fn_calling=False`**、temp由环境变量指定（说明推荐1）、context65536、绝对步数100、Docker、`condense_history=False`、轨迹内评分1200秒。`--k 500`在此命令表示处理题数，不是Pass@500。它不是Claude Code、不是自动压缩harness，也不是训练时50步／32K的同预算。

同一指南命令的`max_workers`为48，解释文字却为54；训练README还曾写`bash deepswe_32b.sh`，实际文件名是`train_deepswe_32b.sh`。这些可修正的文档问题说明“有复现指南”并不代表原样复制即可复现，不涉及否定模型本身。

最终scorer依赖没有固定commit，本轮未运行所有测试；不能只因`--cache_level none`就推定完全去污染和隔离正确。训练中用Verified文件做periodic validation的示例与最终测试之间，缺少完整checkpoint选择记录；也不能由文件名认定作者故意在测试集上优化。

## 8. Test-Time Scaling：教师、verifier和数据可见性

### 8.1 EF verifier 是独立SFT资产

[V][V]与[V-config][V-config]显示，DeepSWE-Verifier基于Qwen3-14B，LoRA rank64、alpha128、dropout0，覆盖attention和MLP投影；卡片报告2epochs、lr1e-5、8devices、全局train batch8、eval batch64、seed42、AdamW、cosine和5%warmup。它不是actor的冻结reference policy，也不是outcome reward的二元测试器。

卡片元数据关联[`r2e-edits/deepswe-swebv-eval-n16-verifier-v1`][V-data]，HF将其显示为训练数据；adapter初始复制记录同样带`swebv-eval-n16`名称。关联数据viewer显示约8K行，但本轮未取得足够逐题内容、实际训练split、cross-fitting或未见题验证记录。**这是需要澄清的评测独立性缺口，不是仅靠名字就能断定训练泄漏。** 也不能将它扩张成actor RL一定使用了Verified训练题。

模型卡顶部license为`other`，仓库又有MIT LICENSE记录；这里只记录元数据差异。不能从actor的MIT声明自动推出所有轨迹、原始仓库、镜像和依赖都统一获得同一许可。

### 8.2 发布日 hybrid 的确切选择规则

[R3：`create_bestofn_aggregate.py`][R3] 按`docker_image`聚合候选，而不是按文件中自然相邻顺序。EF选择`verifier_prob`最高的候选；EB先最大化`regression_pass_count`，再最大化`reproduction_test_score`。

Hybrid不是把两个分数线性加权：先保留EF分数前`floor(N/2)`，再依次保留回归通过数最高、复现测试分最高的候选，最后用EF打破剩余平局。该公开实现给出比主文更具体的规则，**但本轮没有原始run日志证明最终59%就是这一代码版本的原样产物**。

这个实现也说明：测试覆盖、候选排序、平局、缺失评分和候选数都会影响选优，而不是有一个“verifier accuracy”就决定全部收益。

### 8.3 EB所用测试与最终hidden判定不是一回事

[R2：TTS指南][R2]称EB结合regression tests和R2E-TestgenAgent生成的reproduction tests。[R6：`run_regression_tests.py`][R6]实际读取`r2e-edits/swebench-verified-v2`中的`run_tests_regression`，应用候选补丁后执行。它不证明读到了最终hidden F2P；实际测试内容与来源仍需检查。

同样，EF读取trajectory中的observation并不天然等于作弊：正常agent自己跑的公开测试可以是合法证据，最终评分注入的hidden测试结果则是另一种信息。要判断泄漏，需要知道**该字段何时、由谁、用什么测试填入**，不能仅搜索到`test_output`便下结论。

### 8.4 复现指南的LoRA路径错误已得到回复确认

R2及V示例曾在Qwen3-14B服务器上写`--lora-modules verifier=agentica-org/DeepSWE-Preview`。Preview是actor仓库，Verifier才是上述adapter。I17的回复明确确认应为Verifier。[I17及回复][I17-comments]

指南随后请求的模型名称与LoRA服务别名也应核对。本文不提供一份已经执行成功的“修正版完整脚本”，只记录命名错误和需要检查的调用身份。

I17提问者报告EF结果低于作者值，并询问截断、测试信息和库版本；检索到的一条回复只回答LoRA名称。**未回答的问题仍未回答，issue未解决不构成论文错误的证明，也不构成成功独立复现。**

### 8.5 EF公开实现还有具体的身份与概率读取前提

[R4：`run_ef_verifier.py`][R4]先异步完成trajectory→verifier input，再异步计算分数，两次均通过`as_completed`追加结果；最后将分数列表与原始`trajectories`直接`zip`。代码没有在这两个阶段保留原始index或trajectory ID。因此一旦完成顺序不同，评分可能绑定到另一条patch。

本轮用标准库构造了一个确定性的双任务完成顺序反例，验证“完成顺序分数＋原始顺序zip”会交换归属；**没有加载实际模型、运行原脚本或证明此问题改变了历史59%结果**。它是可复核的发布期静态风险及最小原理测试，不是新上游bug定案。

R4还固定读取生成输出的`logprobs.content[4]`，在top20里寻找YES/NO并归一化。它依赖精确输出格式、tokenizer及top-logprob支持；若两个目标都缺失，默认极小值存在数值失效风险。复现者应核对输出position、概率有效性和candidate ID，而不是只换模型名。

[R5：`prepare_ef_verifier_input.py`][R5]的实际input是题面、trajectory的thought/action/observation和最终patch，训练label单独追加为YES/NO；R4推理时只取system/user两条，未直接使用assistant label。该版本并没有在这个转换函数内另行运行hidden tests。I17关于另一处`create_bestofn.py`的信息泄漏疑问，不能用本次读到的这些函数直接确认或推翻。

R5的超长处理是替换较长thought片段；其docstring称保留第一段、从较旧片段开始，但实现按长度降序选择，并未显式排除第一段。这是**verifier输入压缩**，不是actor训练compaction，也不是已经训练了摘要策略。

## 9. 负结果、轶事与未来计划：先保留原始结论强度

B §6的三个分支可以压缩为：作者在四个Claude轨迹SFT起点上继续100次RL迭代未改善；换SWE-smith/SWE-Gym时改善有限且全失败组较多；Qwen3-32B非思考模式改善也有限。作者没有将这些尝试视为普遍否定结论。[B，§6][B]

| 尝试 | 原始披露缺什么 | 不成立的泛化 | 对B线可提出的辨识问题 |
| --- | --- | --- | --- |
| 教师轨迹SFT后再RL | 精确训练题／token、SFT超参、过滤、工具模板、原始checkpoint和完整学习曲线 | “SFT必然损害RL”“教师示范没用” | 是SFT训练后能力、输出格式、熵，还是RL配置和任务分布发生变化？ |
| 替换数据源 | 具体subset/revision、匹配题数、预算、harness、测试条件、各源有效环境率 | “SWE-Gym不能训”“R2E对任何模型最好” | 失败首先来自环境不可判分，还是合法轨迹里没有成功？ |
| 非思考模式 | 同等token／计算预算、模式模板、初始化控制及重复实验 | “必须显示CoT”“大模型非思考模式也无效” | 同底座切换模式改变了哪些条件？工具行为是否仍可执行？ |

这些问题是读者分析，不是声称作者已做过相应消融。低`solve_partial`值得记录，但不是独立的环境无效证明；0/8也不是数学意义的成功概率为零。应把环境有效性与在当前模型／harness／预算下的可学习性分开。

§5的边界条件检查、回归测试和按步骤复杂度分配思考长度属于作者提供的定性观察。没有配对基座轨迹、出现率或盲审协议时，不能据此证明RL专门学会了可靠验证、校准停止或一般性规划。对应Fig.12–13原图和更多Appendix案例本轮未取得，故不重述具体示例操作。

§7的后续整理训练、增加模型规模／上下文、转向web agents仍是计划。不能因为rLLM有其他环境示例，就把它们计入DeepSWE这次release的训练成绩。

## 10. 成本与B线可消费资产表

### 10.1 资源数字的分母

B称最终训练约64H100×6天；按全天连续使用作**名义算术估算**为9,216 H100-hours。这不是W&B导出的精确总GPU小时，也不含全部失败尝试、教师SFT、verifier、CPU环境、镜像和最终评测成本。不能反算成八卡所需天数或租赁报价。[B，导语；C7训练要求][B]

64题×8候选＝512个正常batch的trajectory；200步乘此数只会得到名义采样尝试量，不能替代去掉初始化失败、重试、mask、rejection和checkpoint选择后的有效消费量。B所说可采集“millions”的基础设施规模，也不是这一个最终运行的有效训练样本数。

R2建议16轮×500题，名义8,000 actor运行，之后仍有EF推理、EB执行和最终官方评分。由42.2升至59.0并非零成本提升，也不能拿仅actorGPU时长代表TTS完整预算。

### 10.2 可消费资产清单

| 资产 | 当前能取得什么 | 本次核查的边界 | B接入前还需什么 |
| --- | --- | --- | --- |
| Actor模型 | `agentica-org/DeepSWE-Preview`，模型卡、文件列表、版本历史 | 未下载权重；存储dtype不证明训练dtype | 固定模型／tokenizer revision，核实际推理协议与资源 |
| RL题源 | `R2E-Gym/R2E-Gym-Subset`，当前约4.58K行和字段样例 | 未恢复2025精确消费manifest | 固定data revision、题单、训练／测试关系 |
| 镜像引用 | 每题`docker_image`，示例指向作者Docker registry | 没有实际pull、digest核对或运行 | 镜像可得性、依赖、CPU/内存/网络、可重放性 |
| 环境封装 | C3的SWEEnv和外部R2E-Gym依赖 | 追到最终reward调用，未全审原始parser与所有repo runtime | 与原作者评分差分、empty/gold、合法替代解、flakiness |
| Actor训练 | C1/C4/C5及L子模块 | 精确公共快照；与64卡报告不一致 | 修正／核对配置并做短验证，不能原样许诺复现 |
| Eval | R1/R2，实际run／导出／官方评分入口 | 文档有参数和名称差异，未运行 | 冻结harness与scorer，明确错误／重试规则 |
| EF verifier | Qwen3-14B LoRA64、模型卡与adapter配置 | 数据划分与candidate身份仍有未闭合问题 | 清楚训练来源／heldout，先修正确映射再评估 |
| EB／Hybrid | R3、R6及关联测试生成说明 | 读了选优与回归路径；没有完整执行测试生成 | 核公开／hidden边界、候选数、平局与缺失评分 |
| 原始日志 | W&B、Google Drive入口 | 本轮没有取得可用run config／完整trajectory包 | 合法访问后定点核报告、脚本和实际结果 |

模型卡MIT、rLLM代码Apache-2.0、Subset数据页Apache-2.0是各自声明，不构成原始仓库内容和所有容器依赖统一许可的法律结论。不要把actor及verifier公开与整个训练集群可复现混为一谈。

## 11. 本篇最影响决策的未知与冲突

| 项目 | 分类 | 当前处理 |
| --- | --- | --- |
| 59.0%与59.2% | 源文内部／来源间数字差异 | 正文表和M用59.0；B结尾、旧README出现59.2，分别保留，不平均 |
|64卡/batch64/20分钟与公开16卡/batch8/5400秒|报告与发布代码差异|不合成单一“精确recipe”；需要原始resolved config|
|Hard验证曲线与Verified结果|命名／划分未解释|不把图注推成独立heldout定义|
|原始各数据源负实验条件|未充分披露|保留局部失败，不做来源普遍排名|
|Compact过滤后reward／成员完整合同|文字未充分披露、代码可部分恢复|以C/L限定实际行为，不代证最终run|
|EF数据训练／评测划分|元数据存在疑问，本轮未查完整行与配置|不认定泄漏，也不声称已排除；actorRL与TTS结论分开|
|LoRA指向Preview|已由issue回复确认文档错误|应为Verifier；完整服务别名仍需核对|
|EF异步分数对应|发布代码静态风险，完成顺序原理测试通过|不当作历史成绩已被推翻或当前上游未修|
|图5–7、9–13原图、原Notion附录|本轮未取得|只引用正文／图注，不估读曲线或宣称全文附录核验|
|原W&B／Drive日志|未取得／未检查|不声明成本、checkpoint和评测已独立重算|
|完整环境评分与GPU行为|未复现|代码路径阅读不能替代真实环境和训练测试|

“没有取得”不是作者没有公开；“这里没描述”也不等于另一篇上游论文没讲。Open-source标签本身不能消除这些具体缺口。

<a id="project"></a>
## 12. 对 RepoHarness 项目一／B 线的意义

映射日期2026-09-08，条件为miles＋SGLang＋真实coding harness＋rh2、单节点8×96GB、约30B-A3B目标。下述只依本次任务说明作设计层映射，没有审计当前全部实现，也不批准题单、预算、过滤或新算法。

### 12.1 这篇不能替B直接选出数据集

它使R2E-Gym成为有直接RL使用证据的候选，也使SWE-Gym／SWE-smith上的高全失败组成为必须观察的风险。但不同底座、harness、采样预算和评分版本下，成功分布可能变化。**已有成功配方是候选优先级依据，不是本项目可学习性的测量结果。**

B可以先在相同模型／harness／预算下比较少量已经通过环境验证的候选，分别记录：环境有效、可评分、模型成功、全错组和mask原因。若失败主要是parser或镜像，不进入“数据太难”的结论；若合法轨迹可评分却基本全错，再比较任务、示范或反馈改变。

### 12.2 对A线最直接的三项语义要求

**第一，明确mask在哪一层生效。** horizon成员是否留组、是否已运行最终测试、哪种score参与其他成员的baseline、全零行是否改变loss尺度，必须独立记录。

**第二，异步边界按权重时序命名。** 本文是并发执行加batch更新的公开路径，不能据其成功证明本项目fully async＋stale校正的稳定性。

**第三，数据身份要一直保持到最终消费。** RL的UID/idx排序和EF选优的完成顺序是不同链条，任何一个错配都可能制造貌似合理的结果。外部代码里的具体问题是回归测试灵感，不是扩张一套通用治理平台的理由。

### 12.3 可验证的有限借鉴

| 候选借鉴 | 本篇依据 | 上游／本项目边界 | 最小辨识检查 |
| --- | --- | --- | --- |
| R2E-Gym作为对照题源 | actor direct-RL正例，负结果未普遍化 | 复用原资产；B负责版本和资格，不先造生成器 | 固定条件抽样，环境可评分与模型失败分层 |
| 保留正常开发测试、隔离本题评分信息 | 工具和TTS输入的角色差异 | 不把全部测试一律隐藏；评分输入不能反流 | 逐字段／文件检查训练时与选优时可见性 |
| Compact Filtering作为可比较策略 | 源文描述＋C5分支 | 不直接覆盖rh2错误分类或FA算法合同 | 固定小组的保组mask／删后重算／先评分对照 |
| 环境并发与镜像预热 | C7部署要求、B运行复盘 | 基于实际并发需求，不默认引入K8s | 初始化/工具/评分分阶段计时与错误率 |
| TTS作为单独系统坐标 | actor、EF、EB、hybrid可分开 | 不用TTS分数代替actor学习结果 | 冻结候选、ID和可见测试后比较选择器 |
| 公共代码前置静态验证 | 脚本与报告差异、EF序列错配 | 窄测试优于声称所有开源都可靠／不可靠 | 配置解析、样本重排、概率有效性小测试 |

现阶段**不由本篇推动自动curriculum、全面SFT否定、RL胜过所有SFT、任意超时reward0、或替换miles**。最有价值的结论是：完成一个真实agent训练实验，需要数据、工具、运行预算和消费语义一起成立；某个组合有效，不代表每个组件的效果独立可搬运。

## 13. 快速检索与关联阅读

| 要找什么 | 本篇位置 | 一手定位 |
| --- | --- | --- |
| 有无SFT／critic／OPD | §2、§8.1 | M Overview；V Overview／Training；C1、L1 |
| 数据源和Full/Lite/Subset | §3、§10.2 | M Data；D viewer；C2 |
| reward与各种timeout | §3.3–3.4、§4.3–4.4 | M Environment；C3、C5；R1/R2 |
| LOO、clip和固定分母 | §4–5 | L1 core_algos；L2 ray_trainer；L3 dp_actor |
| 同步／异步真实时序 | §6 | C4 fit_agent；C5 trajectory_generator |
| 42.2／59／71与候选选择 | §7–8 | M Evaluation；R3 hybrid规则 |
| 三个负实验 | §9 | B §6 |
| 复现命名错误及未解答问题 | §8.4–8.5 | I17；R2；R4/R5 |
| 能直接交给B的资产 | §10.2、§12 | C/R固定路径与D |

关联已有入口：[O01 SkyRL-Agent](O01_skyrl_agent_sa_swe.md)、[O03 R2E-Gym](O03_r2e_gym.md)、[E5 SWE-smith](E5_swe_smith.md)、[N11 miles](N11_miles_agentic_rollout.md)。本次仅以既有索引避免重复，不声称重新独立审完这些笔记原文。

对旧资料中“DeepSWE训练代码公开不完整”的收紧：实际可以追到发布当日rLLM、其verl pin与环境封装；更准确的缺口是**最终run配置、原始日志、数据revision以及端到端复现链仍未全部闭合**，不是完全没有训练代码。旧索引也不能把20分钟放到所有时间字段，或将59.2当唯一一致结果。

## 14. 作者自查、当前完成度与后续补核

详见 [O02作者自查](reviews/O02_self_check_20260908.md)。本轮完成可得全文／模型卡、发布期关键代码、复现指南和issue的精读；完成本地LOO、成本与完成顺序反例检查。没有独立reviewer、GPU训练、容器评分或模型复现。

当前状态应写为：**正文与关键代码精读完成，作者自查完成；原图、Notion补充案例和原始日志待补。** 不能复用其他批次的“独立审查通过”标签。以后取得缺失材料时按§1覆盖表定点补核，不必重读所有已确定的源码。

## 官方来源与固定代码入口

[B]: https://www.together.ai/blog/deepswe
[N]: https://pretty-radio-b75.notion.site/DeepSWE-Training-a-Fully-Open-sourced-State-of-the-Art-Coding-Agent-by-Scaling-RL-22281902c1468193aabbe9a8c59bbe33
[M]: https://huggingface.co/agentica-org/DeepSWE-Preview
[V]: https://huggingface.co/agentica-org/DeepSWE-Verifier
[V-config]: https://huggingface.co/agentica-org/DeepSWE-Verifier/blob/ffdc14249d885aea43bbc5d13ea80776e8049ee6/adapter_config.json
[D]: https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset
[V-data]: https://huggingface.co/datasets/r2e-edits/deepswe-swebv-eval-n16-verifier-v1
[I17]: https://github.com/R2E-Gym/R2E-Gym/issues/17
[I17-comments]: https://github.com/R2E-Gym/R2E-Gym/issues/17#issuecomment-3307917384
[C0]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/rllm/trainer/verl/train_agent_ppo.py
[C1]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/examples/swe/train_deepswe_32b.sh
[C2]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/examples/swe/prepare_swe_data.py
[C3]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/rllm/environments/swe/swe.py
[C4]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/rllm/trainer/verl/agent_ppo_trainer.py
[C5]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/rllm/engine/agent_execution_engine.py
[C6]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/rllm/trainer/config/ppo_trainer.yaml
[C7]: https://github.com/agentica-project/rllm/blob/c4d1cfc1c9320d0f298524b309bdcae3c33bfabe/examples/swe/README.md
[L1]: https://github.com/agentica-project/verl/blob/777704aa64c5745c4ccb250ae8977469579ebfc0/verl/trainer/ppo/core_algos.py
[L2]: https://github.com/agentica-project/verl/blob/777704aa64c5745c4ccb250ae8977469579ebfc0/verl/trainer/ppo/ray_trainer.py
[L3]: https://github.com/agentica-project/verl/blob/777704aa64c5745c4ccb250ae8977469579ebfc0/verl/workers/actor/dp_actor.py
[R1]: https://github.com/R2E-Gym/R2E-Gym/blob/8fb8f05a3b367126f70c54b21907a195521bcebc/reproduction/DEEPSWE_REPRODUCTION.MD
[R2]: https://github.com/R2E-Gym/R2E-Gym/blob/8fb8f05a3b367126f70c54b21907a195521bcebc/reproduction/DEEPSWE_TTS_REPRODUCTION.MD
[R3]: https://github.com/R2E-Gym/R2E-Gym/blob/8fb8f05a3b367126f70c54b21907a195521bcebc/src/r2egym/agenthub/verifiers/create_bestofn_aggregate.py
[R4]: https://github.com/R2E-Gym/R2E-Gym/blob/8fb8f05a3b367126f70c54b21907a195521bcebc/src/r2egym/agenthub/verifiers/run_ef_verifier.py
[R5]: https://github.com/R2E-Gym/R2E-Gym/blob/8fb8f05a3b367126f70c54b21907a195521bcebc/src/r2egym/agenthub/verifiers/prepare_ef_verifier_input.py
[R6]: https://github.com/R2E-Gym/R2E-Gym/blob/8fb8f05a3b367126f70c54b21907a195521bcebc/src/r2egym/agenthub/verifiers/run_regression_tests.py
