# E8 ECHO：终端观测预测辅助目标、训练收益与复现边界

ECHO（Environment Cross-entropy Hybrid Objective）在终端 Agent 的 GRPO 动作损失旁，增加预测环境返回文本的交叉熵；两者更新同一策略模型，但使用不同 token mask 与归一化。论文在 Qwen3-8B、14B 及一个专家 SFT 起点上进行训练：TB2 pass@1 的主要改善为 2.70→5.17、5.17→10.79，但 SFT 起点的增益很小，且并非所有 pass@k、执行效率和迁移指标都改善。“Free”指复用既有 rollout 和 actor forward，不代表全流程零成本；“world model”的直接证据是异策略轨迹上的观测预测改善，而非显式模拟规划。本文完整覆盖四个附录，并保留配置、归一化、曲线及效率口径冲突；微软公开实现单列为固定版本代码事实。[P, §1–5, Table 1–3][P]

导航：[来源与覆盖](#source) · [目标与 mask](#objective) · [数据与配方](#recipe) · [评测与迁移](#results) · [代码与复现](#code) · [项目判断](#project)

<a id="source"></a>
## 1. 来源、版本与阅读范围

**主来源 P。** Vaishnavi Shrivastava、Piero Kauffmann、Ahmed Awadallah、Dimitris Papailiopoulos，Microsoft Research，*ECHO: Terminal Agents Learn World Models for Free*。arXiv **2605.24517v1，2026-05-23**；2026-09-07 检查版本历史只列 v1。[官方摘要与版本页][P-abs]、[固定 v1 PDF][P]、[v1 HTML][P-html]。

PDF 共 **14 个物理页**，包含正文 §1–7、致谢、参考文献、附录 A–D；已通读所有正文与附录，核对 **Eq.(1)–(3)、Algorithm 1、Table 1–4、Figure 1–7**。没有因任务主要是 coding 而省略 verifier-free adaptation、相关工作和负结果。参考文献用于恢复依赖身份，没有宣称将每篇引用来源重新全文精读。

PDF 文本与关键图页通过网页读取。固定 v1 的截图请求失败后，用当时仍为同一 v1 的无版本 PDF 入口补读：作者、水印、14 页及正文一致。容器联网下载 PDF/TeX 失败，未取得本机原始文件；不将这个工具限制写成“作者未公开”。仓库索引记录的 `../pdfs/E8_echo_terminal_synthesis_2605.24517.pdf` 是既有来源线索，本轮没有取得其字节并验证与远端相同，因此不依赖该本地链接作为阅读证据。

**实现来源 C。** [microsoft/echo-rl][C0]，固定 **`f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c`**，提交日期 2026-05-26。README 要求 SkyRL pin **`43aab09782953cc7cfc93bda52b1635d717ce446`**。本轮追查实际配置、generator 的观测构造、trainer 的张量运输和 FSDP loss hook，范围见 §8；没有执行安装、训练或完整后端审计。代码与论文相近发布，不表示所有公开配置就是历史结果的精确配置。

**旧材料。** [SOURCE_CATALOG 的 E8 行](SOURCE_CATALOG.md)及原资料索引主要将它登记为“改进 Endless Terminals，新增 6,170 题”。本稿以原文为准恢复正式标题与主要算法贡献；没有把索引中的解释性名称当作论文名，也没有把已有 6,170 题的出处勘误当作完整精读。

**并行任务边界。** 项目读取基线：`Rogerffff/RepoHarness@miles-migration` 的 **`f5d373b566244ddc02b53b881e773257511820fd`**。遵循 [Codex 对 O01 的复核建议](reviews/15_O01_codex_quality_review_20260907.md)：本线程仅维护 E8 正文与 [E8 作者自查](reviews/E8_echo_self_check_20260907.md)，不修改共享 README、来源目录、批次状态或其他线程文档。

### 1.1 原文覆盖与定位

| 原文位置（PDF 物理页） | 主题 | 阅读与对应笔记 |
| --- | --- | --- |
| p.1 摘要、Fig.1 | 双损失概念图、改善与学习速度概览 | 全读、目视；§2、§5、§7，图中简化式不替代正式 loss |
| pp.2–3 §1 | 稀疏回报、观测作为监督、主要贡献 | 全读；§2–3，区分作者解释与直接证据 |
| p.3 §2、Eq.(2) | 多轮序列与 GRPO 动作损失 | 全读、核公式；§2.2 |
| pp.3–4 §3、Eq.(3)、Algorithm 1 | 辅助 CE、目标子集、系数扫描 | 全读、核图页；§2.3–2.5 |
| pp.4–5 §4 | 数据、模型、训练与测试条件 | 全读；§3–4 |
| pp.5–6 §5.1、Table 1、Fig.2 | 三类起点的任务成功与曲线 | 全读、核原表与坐标；§5 |
| pp.6–7 §5.2、Fig.3 | Qwen3-32B 异策略轨迹的 CE 测量 | 全读、核柱值；§6.1 |
| p.7 §5.3、Fig.4 | 专家 SFT 差距定义与恢复比例 | 全读、核图；§6.2，并与 App.C 交叉核对 |
| p.8 §5.4、Table 2–3 | 学习步数、timeout、turns、completion tokens | 全读、核表；§7.1–7.2 |
| pp.8–9 §5.5、Fig.5 | env-only 继续训练、过滤、PyTerm 和 TBLite 负结果 | 全读、核图表；§7.3 |
| pp.9–10 §6–7、致谢 | 方法谱系、结论、内部训练栈 | 全读；§2.6、§8.5 |
| pp.10–13 References | 环境、模型、harness、相关方法的来源身份 | 检查完整尾部；不逐篇扩读 |
| p.13 App.A、Fig.6 | warning/env CE 曲线 | 全读、目视；§2.5、§9，保留正文与图的差异 |
| pp.13–14 App.B | AdamW、clip、系数、运行资源和统计说明 | 全读；§4、§5.3、§9 |
| p.14 App.C、Table 4 | SFT gap 精确数值与比例 | 全读、核表并复算；§6.2 |
| p.14 App.D、Fig.7 | OT-SFT 完整学习曲线 | 全读、目视；§5.2、§9 |

<a id="objective"></a>
## 2. 方法：同一策略上的两类监督，不是把工具文本当作动作

### 2.1 核心问题与“world model”的含义

一次终端交互得到 stdout、stderr、文件内容、日志或测试错误。传统的本篇 GRPO 基线把这些信息留在上下文里，供后续动作使用，却不给观测 token 直接的预测损失。全零回报组没有组内对比；混合组的失败轨迹仍有负优势，因此**“失败轨迹没有任何学习信号”不是正确概括**。[P, §1–2, pp.2–3][P3]

ECHO 让同一策略同时学习“接下来怎么做”和“做了以后终端会返回什么”。动作仍由模型采样，观测仍由真实环境提供；作者称这种预测训练能改善内部表征和操作先验。它**不增加独立 dynamics 模型，不在推理时做想象 rollout、树搜索或显式环境模拟**。完整状态不可见，终端文本只是容器状态的有损投影。[P, §1、§3.1、§6, pp.2–3、9–10][P10]

“学到世界模型”在论文中的操作性验证是：在其他模型产生的真实轨迹上，预测观测文本的 CE 更低。它支持预测能力改善，但未直接测量长期反事实模拟、规划因果中介或完整隐藏状态恢复。后文将这些未测试的能力与作者的术语分开。

### 2.2 GRPO：动作位置、组级优势与论文自己的分母

序列结构为 prompt 后交替的 `action_1, obs_1, …, action_K, obs_K`。$\mathcal A$ 是 assistant-action token 位置；$\mathcal O$ 是观测位置；$\mathcal O'\subseteq\mathcal O$ 是最终选入辅助监督的观测子集。动作不只包含 bash 内容，也包括模型实际生成的 reasoning 和完成信号；prompt 与环境文本不是策略采样动作。[P, §2、§4][P3]

原文 Eq.(2)：

$$
\mathcal L_{\mathrm{GRPO}}(\theta;\mathcal A)
=-\frac{1}{\sum_i|\mathcal A^{(i)}|}
\sum_i\sum_{t\in\mathcal A^{(i)}}
\min\left(\rho_t^{(i)}\hat A^{(i)},
\operatorname{clip}(\rho_t^{(i)},1-\epsilon,1+\epsilon)\hat A^{(i)}\right).
$$

每题采样一组轨迹，以终局二元 reward 形成 prompt-level group-normalized advantage；同一轨迹的标量优势用于全部动作位置。没有 learned critic。原文称 $\rho$ 为 importance ratio，但没有在此展开全部概率实现、reference/behavior 版本或 std 的数值稳定项，不能从后端默认值补出历史细节。[P, §2, Eq.(2), p.3][P3]

**需要保留的原文差异：Eq.(2) 是跨轨迹动作 token 总数归一化，而 §4 又写 sequence-level loss aggregation。** 二者不是天然等价。App.B 给出了非对称 clip $\epsilon_{lo}=0.2,\epsilon_{hi}=0.28$，Eq.(2) 则是对称示意式。本文记录公式、配方文字与公开实现三层，不把其中某层默认为全部实验的真实计算定义。

### 2.3 辅助 CE：分子选 env，分母仍数完整 observation

原文 Eq.(1)、Eq.(3)：

$$
\mathcal L_{\mathrm{ECHO}}=\mathcal L_{\mathrm{GRPO}}+\lambda\mathcal L_{\mathrm{Env}},\qquad
\mathcal L_{\mathrm{Env}}(\theta;\mathcal O')
=-\frac{1}{|\mathcal O|}\sum_{t\in\mathcal O'}\log p_\theta(x_t\mid x_{<t}).
$$

$|\mathcal O|$ 是**每条序列的总观测长度，不是选中子集的长度 $|\mathcal O'|$**。作者希望不同目标子集在同一 per-observation 尺度比较。最终模型仍预测真实 token $x_t$；没有 teacher logits、reverse-KL、reward-weighted observation CE 或对环境文本的策略采样比率。[P, §3.1, Eq.(1)(3)、Algorithm 1, pp.2–4][P4]

一个**读者算术示例**：一条序列有 4 个 warning token 和 6 个 env token，选中的 6 个 token 各有 2 nats NLL。辅助项是 $12/10=1.2$，不是 $12/6=2$；$\lambda=0.05$ 时贡献 0.06。即使 warning 不进分子，它仍可通过总观测长度影响尺度。示例只解释 Eq.(3)，不冒充论文实验。

Algorithm 1 只需一次 actor forward：在动作位置计算 GRPO，在选定观测位置 gather 同一批预测并计算 CE，最后联合 backward。式中的条件 $x_{<t}$ 是自回归预测语义；实现必须使用与目标 token 对齐的 causal-shift logprob，不能把伪代码里的位置简写误读成让 token 看见自己再预测自己。[P, Algorithm 1, p.4][P4]

原文明确逐序列归一化，但没有在 Eq.(3) 展开整个 batch／分片的外层 reduction。公开代码在 `sequence_mean` 路径补出了局部求和与 worker 权重，见 §8.2；这不消除 §2.2 中原文的聚合差异。

### 2.4 三套位置与目标不能合成一个“训练 mask”

| 位置 | 作为下一动作的上下文 | GRPO 策略梯度 | ECHO 主要辅助项 |
| --- | --- | --- | --- |
| system/user prompt | 是 | 否 | 否 |
| 模型生成的思考、命令、完成信号 | 是 | 是，使用轨迹优势 | 否 |
| harness 的低熵格式 warning | 是 | 否 | 主设置排除，但计入完整观测归一化 |
| 终端返回的选定 env 文本 | 是 | 否 | 是，普通 next-token CE |

这是一张从 §2–3 恢复的方法语义表，不是对所有公开代码边缘路径的保证；代码中实际名为 `env_only` 的区域还可能包含 harness 生成的错误说明，见 §8.3。

“on-policy”指监督来自当前策略自己访问的交互，而不是固定离线专家轨迹；它不意味着对离散环境或采样分布反向传播，也没有自动解决异步陈旧轨迹问题。§5.2 使用其他模型产生的轨迹**做评测**，不能因此说主要训练采用 off-policy replay。

### 2.5 目标选择和系数：有失效区间，不是任意加 CE 都会好

主要设置排除规则生成的 warning，保留命令输出。作者扫描 $\lambda\in\{0.001,0.005,0.01,0.02,0.05,0.1,0.2\}$，描述 0.01–0.05 为有效区间；较小权重作用弱，0.1 会平台化或变差，0.2 可出现输出易预测但没有任务进展的退化轨迹。原文没有提供完整的“每个系数 × 模型 × 最终成绩 × 多 seed”数表。[P, §3.2–3.3, p.4][P4]

正文写所有报告实验固定 0.05；App.B 却写 `{0.02, 0.05} (SFT vs. base)`。不能无解释地将两者合并成统一 recipe。作者提出常数权重会随 CE 下降而“自然退火”；这是对辅助贡献的解释，不是提供了梯度范数或优化影响严格衰减的证明。

**App.A / Fig.6 必须保留图文差异。** 文字说 warning CE 约从 5.6 nats 降至 step 60 时小于 0.05；原图左侧是对数坐标，目测 step 60 附近仍在约 1 nat 量级，接近 0.05 出现在明显更晚的训练区间。不要把“60 步已小于 0.05”当作无冲突精确事实。右图 env-only/full-obs 在前约 100 步由约 0.5–0.7 降到 0.05–0.10，随后大致维持这一量级并有尖峰；正文称其为不可约熵，但没有理论下界或额外实验识别不可约部分。[P, App.A, Fig.6, p.13][P13]

图6没有给 warn-only/full-obs/env-only 的最终任务成功率完整对照。因此，它主要支持目标学习动态的观察，而不是足以独立证明所有性能差来自排除 warning。

### 2.6 与相关方法的关系（保留作者的组织）

§6 先联系经典世界模型和辅助预测 RL：前者可服务规划或想象，后者用预测任务塑造表征。随后比较语言 Agent：CWM 在 Python/Docker 轨迹上训练；RLTF 使用 judge 生成的 critique；OpenClaw-RL 通过 judge 将 next-state 转成分数或提示；SDPO 等利用丰富反馈。作者强调 ECHO 直接预测返回文本，不需另建反馈生成器、独立世界模型阶段或推理时模拟。最后将它与 SkyRL、SimpleTIR、DAPO、ArCHer 的训练系统／策略优化工作区分。[P, §6, pp.9–10][P10]

这些是本篇的关系阐释，不表示本轮全文读了上述所有工作，也不能由“正交可组合”的讨论推出 ECHO 与每种过滤、KL、异步算法都已联合消融。

<a id="recipe"></a>
## 3. 模型、任务供给与训练分支

### 3.1 三个起点、两种继续训练方式

| 分支 | 起点与依赖 | 本篇的更新 | 角色边界 |
| --- | --- | --- | --- |
| 基础 8B | Qwen3-8B | GRPO 或 GRPO+Env CE | “base”相对本文专项 terminal SFT 而言，不等同于特定 `Qwen3-8B-Base` 预训练权重 |
| 专家 SFT 8B | OpenThinker-Agent-v1-SFT（OT-SFT）；Qwen3-8B 经约 15K 条 GLM-4.6 专家终端示范 SFT | GRPO 或 ECHO | 本篇使用现有 SFT 模型；没有报告重新制作这批示范的完整成本 |
| 基础 14B | Qwen3-14B | GRPO 或 ECHO | 与 8B 是分开的模型训练，不是混合专家 |
| 无 verifier reward 的继续适应 | 主要训练之后最强的 8B ECHO checkpoint；Fig.5 标为 step 500 | 关闭动作损失，仅 Env CE，追加至多 100 步 | 不是从零开始不依赖 reward 的完整训练链 |

[P, §4、§5.3、§5.5, pp.5、7–9][P5]

GPT-5 在任务可解性筛选中是 solver；Qwen3-32B 生成的是预测能力**评测轨迹**；GLM-4.6 是 OT-SFT 的示范来源。它们都不能被写成 ECHO auxiliary loss 的逐 token teacher。“ECHO 不需要专家示范”适用于方法与非 OT 分支，不等于全流程没有外部强模型、没有任务筛选成本。

### 3.2 数据漏斗：已知数量与缺失的候选分母

| 阶段 | 数量与处理 | 本篇能说明／不能说明的范围 |
| --- | --- | --- |
| 现有来源筛选后 | 1,977 Endless Terminals + 723 OpenThoughts-Agent-v1-RL = **2,700 题** | 排除 analysis/computation、specialized-application、infrastructure/networking、complex-bash；原始候选数未给 |
| 新合成部分 | 修改 Endless Terminals 管线，得到 **6,170 题** | 说明任务 specification、Dockerfile 生成／验证与 Harbor 导出；没有逐阶段候选数、模型分工、重试和人工成本表 |
| 可解性筛选 | GPT-5 在至多 16 次尝试中至少成功一次的任务保留 | 不是目标 8B/14B 的 pass@16，也不是全部合法替代解审计；筛前分母未给 |
| 最终任务池 | **8,870 题**，覆盖数据处理、系统操作、开发／工具 | 2,700+6,170=8,870 是算术一致性，不能推出筛选零淘汰或 100% 构建率 |
| 主要训练／同分布验证 | **8,770 train + 100 val100** | 没有逐任务 manifest、生成家族隔离、时间切分、去重／污染审计细节 |
| 后续 PyTerm 适应 | **928 题 = 828 adaptation + 100 eval** | synthetic Python script generation；不是主要 8,870 任务池的另一种计数 |

[P, §4, p.4；§5.5, p.9][P4]

本篇不是环境生产论文。它足以说明训练使用了可执行容器和单元测试，不足以恢复完整的任务生成 prompt、empty/golden 检查、flakiness 阈值、hidden grader 隔离与反作弊协议。代码库公开训练集成也不能自动补足这些数据资格事实。

### 3.3 交互与评分

主要 harness 每轮读完整历史，生成 thinking block 后接 Qwen XML bash 命令或 task-done；解析首条命令或完成信号，执行后返回可选格式 warning、stdout/stderr 与 exit code。Docker 承载任务，Harbor 编排环境。终局单元测试通过记 1，否则 0；它不是基于语言 judge 的主 reward，也没有论文披露的逐步过程奖励。[P, §4, pp.4–5][P5]

代码公开时明确将生成控制留在 SkyRL/vLLM，而不让 Harbor 接管整个 agent loop。这使 token IDs、logprob 和辅助 mask 能进入 trainer；Harbor 负责容器、命令和 verifier。由此可以学习层间职责，但不能把这一选择写成“ECHO 在原生 Terminus-2 里训练”：Terminus-2 是 TB2 的评测 harness。[C0][C0]

## 4. 训练与评测预算：论文、附录、代码分别记录

### 4.1 主要训练配方

| 字段 | 正文／附录披露 | 未披露或冲突 |
| --- | --- | --- |
| 组采样 | 每题 n=16；batch size=16 | 原文没有展开 DP、microbatch 与每步实际保留量；按公开配置是 16 prompts、名义 256 rollouts |
| 优势 | prompt-level normalization，无 learned value function | std 实现、零方差丢弃与重采细节未给 |
| policy loss | Eq.(2) clipped GRPO | token-global 式与 §4 sequence-level 描述不同，见 §2.2 |
| 优化器 | App.B：AdamW，β=(0.9,0.95)，weight decay=0.01 | 当前公开 YAML β2=0.999，不倒填正文 |
| 学习率／梯度裁剪 | 1e-6；gradient norm clip=0.2；App.B 无 warmup/decay | gradient clip 不等于 policy ratio clip；公开 YAML 有 20-step warmup |
| policy ratio clip | App.B：low=0.2/high=0.28 | 公开两份 YAML high=0.2；Eq.(2) 仅给对称示意 |
| KL | §4 除特别说明外不加；App.B 不加 | 没有足够披露支持添加其他 entropy 或 staleness 配方 |
| Env CE | 正文 λ=0.05，env-only，总观测长度归一化 | App.B SFT/base 对应 {0.02,0.05}；外层 reduction 需另查 |
| 采样 | train temperature=0.8 | top-p/top-k 等正文未给 |
| 轮数／长度 | 16 turns、16K context、每 turn 至多 2,048 generated tokens | 总生成量、单轮上限与 context window 不能互换；未披露 learned compaction |
| 超时 | 每任务 agent 600s、verifier 120s | 不能替代工具命令自己的 timeout 或 TB2 评测预算 |
| 步数／硬件 | §4：每模型 500 GRPO steps、8 B200 | App.B：500–1,000 steps、8 GPUs（A100/B200 mix）、24–48h/run；逐实验对应关系未给 |

[P, §4, pp.4–5；App.B, pp.13–14][P13]

### 4.2 不应继承的系统结论

“on-policy observation target”和代码 `async_engine=true` 都不能直接证明 fully-async learner。论文没有 stale-policy 年龄、权重发布协议、partial rollout resume、重启恢复或跨版本校正实验。当前 generator 会等待整批任务结束后交付，底层训练内核来自 SkyRL；本轮没有将其全部版本生命周期重新审计。[C1、C2][C1]

训练使用整段 history 的描述，也不构成任意多 harness、subagent、context compaction 下 loss 保真的证据。对本项目最相关的 token 边界问题，限于 §8 实际检查的单序列路径。

<a id="results"></a>
## 5. 任务评测：保留完整结果，特别是小增益与反向指标

### 5.1 评测对象与协议

| 集合 | 任务来源／数量 | harness、采样和限制 | 报告指标与角色 |
| --- | --- | --- | --- |
| val100 | 从本篇任务池留出的 100 题 | minimal harness；每题8次；T=0.6；16 turns | pass@1/平均成功率；同分布验证 |
| ITD（internal-dev） | 71 题，TB1.0 core/non-core 与 OpenThoughts-TB-dev 中选择上述领域 | 同上 | 域外开发切片，不是新造的私有真实工程集 |
| TBLite | OpenThoughts-TBLite，100 题，为小模型校准的 terminal-style 集合 | 同上 | 域外评测切片；参与论文学习曲线与模型比较 |
| TB2 | TerminalBench-2.0，89 题 | Terminus-2；每题5次；T=0.6；32K context；App.B seed42、agent/verifier 各1200s | pass@1、3、5；不同 harness 的外部结果 |

[P, §4、Table 1, p.5；App.B, p.14][P14]

内部8次不是 pass@8：论文报告单次成功概率的平均估计。TB2 的 pass@k 是 k 次中至少一次成功，不是连续 k 次全部成功。原文没有给精确 estimator 代码、任务相关性处理或各列最终 checkpoint 选择协议；不能擅自套用某一种 pass@k 公式并称作者已使用。

### 5.2 Table 1：原始表值（%）

| 起点 | 训练 | val100 | ITD | TBLite | TB2 p@1 | TB2 p@3 | TB2 p@5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3-8B | 起点 | 34.2 | 7.0 | 4.9 | 1.57 | 3.71 | 4.49 |
| Qwen3-8B | GRPO | 54.9 | 16.2 | 9.5 | 2.70 | 6.74 | 8.99 |
| Qwen3-8B | ECHO | 63.7 | 18.9 | 11.4 | 5.17 | 10.45 | 13.48 |
| OT-SFT 8B | 起点 | 38.5 | 10.7 | 6.0 | 5.62 | 10.45 | 12.36 |
| OT-SFT 8B | GRPO | 63.5 | 18.8 | 11.6 | 7.64 | 14.38 | 17.98 |
| OT-SFT 8B | ECHO | 73.1 | 22.7 | 12.9 | 7.87 | 13.82 | 17.98 |
| Qwen3-14B | 起点 | 35.3 | 12.1 | 5.7 | 4.27 | 8.99 | 12.36 |
| Qwen3-14B | GRPO | 60.3 | 17.9 | 9.8 | 5.17 | 10.67 | 13.48 |
| Qwen3-14B | ECHO | 65.0 | 19.8 | 15.1 | 10.79 | 16.52 | 19.10 |

[P, Table 1, p.5][P5]

8B 与 14B 的 TB2 p@1 相对 GRPO 分别增加 **2.47 pp、5.62 pp**，约为 1.91×、2.09×；原始绝对成功率仍只有 5.17%、10.79%。**OT-SFT 的 p@1 只增加 0.23 pp，p@3 下降 0.56 pp，p@5 持平。** 所以“每项指标全面提升”和“强 SFT 起点仍翻倍”均不受此表支持。比较单位是百分点与倍率两套量，不混写。

**曲线保留量级，但不替代表值。** Fig.2 纵轴为各集合 pass-rate，横轴0–500 steps，粉色与青色分别是 ECHO/GRPO，填色表示两曲线差而非置信区间。目测14B TBLite 在后期 ECHO 约17%–18%，GRPO 回落到约9%–10%；ITD 则存在交叉，最末端 GRPO 略高。因此“ECHO 从始至终更高”不应无条件转述。[P, Fig.2, p.6][P6]

App.D Fig.7 的 OT-SFT val100 末端约73%/66%，ITD 约23%/21%，TBLite 约17%–18%/16%（均为原图目测）。TBLite 的量级与 Table1 的12.9/11.6不同；作者没有说明图表逐 run/checkpoint 对应关系。记录差异而不自行认定哪个才是最终正确值。[P, Fig.7, p.14][P14]

### 5.3 比较条件与统计边界

作者声明匹配主要 recipe、数据与起点，只增加 auxiliary objective；这比跨论文排行榜更接近受控对照。公开8B两份 YAML 的行为字段也只改变 `world_model_coeff: 0.0→0.05`，支持存在可比较的示例入口。但论文、图表、附录和 YAML 仍有 §9 所列差异，缺原始 run 清单、eval 日志和训练 seed 重复，不能确认每张图表都是同一对作业。

App.B 给出内部评测所谓 per-task “variance ±0.05”、100任务均值约“±0.025（Wilson interval）”，TB2 standard error约1.5 pp。这些为**作者报告值**：variance 与区间半宽并非同一统计量；没有置信水平、计算过程和逐任务数据，本文不据此重算显著性。OT-SFT 的0.23 pp尤不应被包装成已证明的可靠增益。[P, App.B][P13]

## 6. 机制证据与专家 SFT 对照

### 6.1 Fig.3：真正测到的是外部策略轨迹的观测 CE

作者用 **Qwen3-32B** 在 val100、ITD、TBLite 每题产生8条轨迹，共 $(100+71+100)\times8=2,168$ 条；被评模型未生成这些轨迹。固定真实历史后，测量实际终端输出的 next-token CE，降低“只拟合自己 rollout 风格”的解释空间。[P, §5.2, pp.6–7][P7]

下表来自 **Fig.3 柱上标注**，不是目测插值；单位为 nats/env-token：

| 起点 | val100：起点 / GRPO / ECHO | ITD：起点 / GRPO / ECHO | TBLite：起点 / GRPO / ECHO |
| --- | --- | --- | --- |
| Qwen3-8B | 0.29 / 0.27 / 0.07 | 0.46 / 0.44 / 0.32 | 0.35 / 0.34 / 0.25 |
| OT-SFT 8B | 0.26 / 0.27 / 0.09 | 0.44 / 0.45 / 0.34 | 0.35 / 0.35 / 0.26 |
| Qwen3-14B | 0.24 / 0.22 / 0.07 | 0.39 / 0.39 / 0.31 | 0.30 / 0.30 / 0.23 |

[P, Fig.3, p.7][P7]

这支持未见任务和其他策略动作上的预测改善，但**不是自由生成完整终端响应的准确率，也不是从文本预测正确状态后再进行规划的成功率**。交叉熵使用 teacher-forcing 历史，真实输出内部的前缀也作为条件；复制规律、格式和重复文本的贡献没有被单独消融。作者对表征改善的解释合理，但未隔离“CE改善是任务成功改善的因果中介”。这是证据范围分析，不是否认其 world-model 命名。

训练 Eq.(3) 的分母是完整观测长度；Fig.3 标注 per env-token，公开代码另有 selected-token CE 指标。不能把两种数值无条件当成同一个 loss 曲线。

### 6.2 专家差距：比较的是三个已训练系统，不是 SFT 没有价值

作者定义 SFT gap 为 `OT-SFT+GRPO − Qwen3-8B+GRPO`，ECHO lift 为 `Qwen3-8B+ECHO − Qwen3-8B+GRPO`，恢复比例为 lift/gap。App.C Table4 给出高于主表精度的结果：[P, §5.3、App.C][P14]

| 指标 | 8B GRPO | 8B ECHO | OT-SFT+GRPO | SFT gap (pp) | ECHO lift (pp) | 原表恢复比例 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| val100 | 54.94 | 63.66 | 63.52 | 8.58 | 8.72 | 101.6% |
| ITD | 16.22 | 18.89 | 18.79 | 2.57 | 2.67 | 103.9% |
| TBLite | 9.47 | 11.39 | 11.63 | 2.16 | 1.92 | 88.9% |
| TB2 p@1 | 2.70 | 5.17 | 7.64 | 4.94 | 2.47 | 50.0% |
| TB2 p@3 | 6.74 | 10.45 | 14.38 | 7.64 | 3.71 | 48.6% |
| TB2 p@5 | 8.99 | 13.48 | 17.98 | 8.99 | 4.49 | 50.0% |

Fig.4 用 ITD/TBLite/TB2 p@1 三组条形图展示上述比例，是同一结论的可视化，不是另一个独立实验。0.14 pp／0.10 pp 的内部差距不能证明 ECHO 显著超过专家 SFT。TB2 仍只恢复约一半，而且 OT-SFT+ECHO 在内部集合还可继续改善，故不能说专家示范已经可删除。[P, Fig.4, p.7][P7]

作者将可替代部分解释为 interaction prior，未替代部分解释为更高层 strategy prior。这是机制解释；本篇没有将专家知识按这两类标注并独立干预，也没有等“示范生成+SFT+RL”全流程成本对照。

## 7. 效率与 verifier-free adaptation：正负结果一起解释

### 7.1 Table2 的学习效率存在定义差异

§5.4 正文说测 ECHO 首次超过匹配 GRPO 在500步内的最佳分数；Table2 标题却说每个 run 首次到达**各自**的最佳分数。这两者分别是共同阈值 time-to-quality 与不同峰值时刻，不能默认为同一指标。[P, §5.4、Table2, p.8][P8]

| 起点 | Total：GRPO / ECHO step | 作者 speedup | TBLite：GRPO / ECHO step | 作者 speedup |
| --- | --- | ---: | --- | ---: |
| Qwen3-8B | 460 / 240 | 1.92× | 500 / 220 | 2.27× |
| OT-SFT | 400 / 260 | 1.54× | 220 / 300 | 0.73× |
| Qwen3-14B | 380 / 380 | 1.00× | 380 / 380 | 1.00× |

Total 聚合 val100+ITD+TBLite，具体权重未给。保留作者的比值，但在没有日志消除定义差异前，不写成严格重现的同质量时间节省。**OT-SFT/TBLite 更晚，14B 两列无步数优势**；不能把1.5–2.3×推广到全部起点。

Fig.1 与 Fig.2 都有到达某水平的步数箭头，但 ITD 标注分别为−140/−80、TBLite为−260/−280；图注未说明它们的 run 或选点差异。只把它们作为示意／曲线观察，不混合成新的精确实验。

即使共同阈值定义得到核实，steps 仍不是墙钟、token 或 GPU-hours。策略改变会改变轨迹长度和环境成本；本篇没有匹配的 per-step 性能 profiler 或显存／吞吐测量来证明 auxiliary loss 的全部实现开销为零。

### 7.2 Table3：更少 completion tokens，不等于每项执行指标都改善

表值为 TB2 每 trial 的统计；timeout是撞到1200s限制的比例，turns与tokens分别是平均交互轮数与**completion** token，不含所有累计输入/prefill成本。[P, Table3, p.8][P8]

| 起点 | Timeout：GRPO→ECHO | Turns：GRPO→ECHO | Completion tokens：GRPO→ECHO |
| --- | --- | --- | --- |
| Qwen3-8B | 19.8%→9.0% | 24.3→19.8 | 43.2K→30.3K |
| OT-SFT | 45.2%→24.7% | 66.3→37.7 | 35.4K→34.8K |
| Qwen3-14B | 40.7%→43.1% | 22.0→23.5 | 49.8K→43.1K |

作者分别给8B/OT的timeout约−55%/−45%，14B反而约+6%；14B turns约+7%，但completion tokens约−13%。OT tokens只减少约2%，不能与43%的turn减少混写。

这组统计覆盖全部trial，不是每个成功任务的成本；更早结束也可能是更早失败。结合Table1可以看到收益和代价，但不能由更少tokens单独推出同质量经济效率。TB2的32K context是当前上下文限制，43K以上是跨turn累计completion；与训练16-turn限制不同，不构成算术矛盾。

### 7.3 只训练环境预测的适应实验

从最强8B ECHO模型开始，Fig.5在step500关闭GRPO／verifier reward，继续用自身交互产生的观测训练至多100步。没有action-token loss，没有任务正确性标签参与该适应目标。**此前模型已经接受reward训练，终局效果仍由verifier评估**，所以“verifier-free”不能扩成全生命周期没有verifier。[P, §5.5、Fig.5, pp.8–9][P9]

| 适应目标分布 | Rollout筛选 | 报告的追加step | 目标变化 | val100变化 |
| --- | --- | ---: | ---: | ---: |
| val100 | 不筛选 | 70 | +3.8 pp | +3.8 pp |
| PyTerm | 全部tool calls可解析且有效 | 100 | +10.0 pp | −0.9 pp |
| ITD | 同上 | 100 | +5.2 pp | +0.4 pp |
| TBLite | 同上 | 100 | **−3.9 pp** | −0.4 pp |

这是Fig.5内嵌表，**不是Table5**。图注说报告best post-adaptation变化，不可一律改称最终固定checkpoint增益。val100曲线在约570步达到峰值，之后回落；PyTerm原图从适应前约11%到末端约21%–22%，但这些量级只是图示，精确增量以嵌表为准。

PyTerm明确划分828 adaptation/100 evaluation。val100、ITD、TBLite的适应任务与评估实例是否相互隔离，本篇没有给同样清楚的manifest与拆分；不能默认所有“unseen/OOD”都意味着适应过程中从未接触被评任务。停止checkpoint的选择也使用结果观察，因此“更新不使用reward”与“研究者不再使用评测反馈选择结果”不同。

“clean tool calls”是格式／解析资格，不是任务成功过滤。作者观察到OOD轨迹中的坏格式、parse error和无效循环会让CE学到错误交互模式；过滤后ITD/PyTerm改善，TBLite仍退化。PyTerm与TBLite起始通过率近似，并未因此产生相同收益：作者推测Python traceback、打印值和文件内容对具体动作的关联更直接，而TBLite依赖更多未显露的系统状态。这是合理解释，不是已受控隔离的领域因果机制。[P, §5.5, p.9][P9]

该实验没有提供完整的“所有目标分布 × 过滤/不滤 × env-only/继续GRPO”对照。它足以显示一些条件下能继续适应，不能得出不需要终局reward、所有失败轨迹都应训练或CE更低必然使策略更好。

<a id="code"></a>
## 8. 固定官方实现：从实际入口追到辅助目标消费

范围限于解释论文实现主张所需的文件，不展开整个SkyRL审计。全部C链接固定到`f4c3c7ec…`。README给出两个示例，分别`world_model_coeff=0/0.05`；代码MIT许可，模型、第三方数据和论文许可不据此一并推定。[C0][C0]

### 8.1 开放资产与真实入口

`echo_rl/terminal_agent/entrypoint.py`选择`TerminalAgentGenerator`、`EchoPPOTrainer`，并明确限制fsdp/fsdp2和non-step-wise轨迹；README要求对固定SkyRL提交应用`patches/skyrl_minimal_hooks.patch`。不能只因类存在，就声称任意trainer已消费了这些mask。[C7][C7]

公开树中有terminal-agent代码、world-model loss、两个8B配置、hook patch及运行脚本。配置中的train8770/val100 parquet仍是作者PVC本地路径。**本轮检查的README、文件树和配置没有给出本篇完整8,870题、PyTerm、全部ECHO checkpoint、评测原始日志或任务合成管线的可下载入口**；这是核查范围内未定位，不是断言作者任何地方都没有发布。没有把上游Endless、OT数据存在写成精确本篇taskset已公开。

本轮未读取repo中的`echo.pdf`镜像，也未将它和arXiv视为逐字节一致。正文以四作者的arXiv v1为主，镜像差异若影响后续复现需另核。

### 8.2 两个loss如何共用一次forward

| 位置 | 读到的实际行为 | 语义意义 |
| --- | --- | --- |
| `terminal_agent_generator.py::_run_one/_add_observation` | 输出动作mask、world/warning/env mask及整序列`world_full_observation_count` | 一条逻辑轨迹附多种目标字段，而非重生成一条教师轨迹 |
| `world_modeling/trainer.py::convert_to_training_input` | 按response长度右对齐mask；assert行数/长度；对padding行置零；传入generic extras | token位置与样本padding必须一起运输 |
| `world_modeling/loss.py::compute_world_model_loss` | 使用`-action_log_probs`，在world mask上求和；`sequence_mean`时按每序列full-observation count除，另加1e-3 | 变量名`action_log_probs`不意味着tensor里只能包含动作位置 |
| `world_modeling/fsdp_worker.py::compute_aux_policy_loss` | 将上述loss乘λ与本地batch权重；记录selected/warning/env CE | 辅助项与policy loss独立聚合；诊断per-token CE与训练loss不是同一分母 |
| hook patch的policy worker部分 | 接收同一forward产出的logprob，在原总loss上加入auxiliary loss，再执行一次backward | 源码支持单actor forward与联合反向的设计，不等于已测完整零开销 |

[C2–C6][C4]

`sequence_mean`函数内部是逐序列除后求和，外层worker使用`1/max(len(data),1)`权重；另外还实现fixed max-seq denominator和token denominator路径。示例只选sequence_mean。本轮没有验证DP/序列并行下全局等价，不能仅凭这些局部函数断言任意packing都保留原目标。

### 8.3 `env_only`不天然等于纯stdout/stderr

`_get_observation_content_spans`比较空内容、warning内容和完整消息的template token差分，用共同前后缀确定warning/env范围。`full_observation_body_count`累计消息正文长度，含warning+env，不含共同role包装；所选mask排除warning，但仍保留env区的实际序列化文本。默认`keep_all`保留生成thinking；推理使用token IDs，模型输出保留原token，新增环境消息仍经过模板编码。[C2, generator lines459–648][C2]

这里有一项值得记录的**实际路径限定**：

`_agent_loop`遇到解析错误时调用`_add_observation(interaction, "", parse_result.error, …)`；无命令时也把“没有命令”等提示放入env参数。`_execute_commands`会加入命令回显、执行状态、exit code以及异常说明。因此，公开实现的env区域除真实输出外，还可能包含harness构造文本。它通过参数位置区分目标，不是独立证明内容都来自容器。

这并不推翻排除warning prefix的方法，而是说明“把warning排掉后，剩余目标一定是纯物理反馈”超出了实现。原文示意的`<command_output>`与公开代码的具体包装也不完全相同。若要检验CE学到了什么，应记录实际被选文本；不必因此把整篇阅读扩大成通用harness安全审计。

### 8.4 过滤和verifier-free的当前实现范围

`EchoPPOTrainer._apply_world_model_filter`在quality不合格时清零world/warning/env辅助mask，而不是直接删除原轨迹的policy mask或改reward；可配置parse-clean、valid-tool-call和correctness比例三类筛选。**correctness比例筛选会依赖终局正确性，不应在声称无需verifier信息的设置里默默开启。** 两份公开主配置未启用这些特殊过滤，不能从支持字段推出Fig.5的精确运行设置。[C3][C3]

`world_model_only`先将动作loss mask置零。可是所查`_agent_loop`在多数正常终止路径仍调用`environment.run_verifier()`，该开关没有在这里绕开调用；`max_total_tokens`是已见到的另一条不评分分支。因此，公开路径能表达“无动作目标”，但**尚不能由它证明实际关闭了verifier执行及其成本**。这与论文说适应更新不使用verifier reward不是同一断言；本轮不据此反推历史实验违规。[C2 lines350–390；C3][C2]

普通解析错误会返回观察并继续；max-turn/context终止通常仍评分；总token耗尽可直接给0；外层timeout/error可产生单EOS、全零mask占位。内部`_mark_failure`保留已有轨迹内容的情况又不同。原论文未给完整终止消费合同，本稿不把某一类错误处置概括成所有失败都会清零，也不将占位观测强行训练。

### 8.5 示例与附录的配方差异、资源与复现

| 字段 | arXiv v1 / App.B | 公开8B主配置 |
| --- | --- | --- |
| Adam β2 | 0.95 | 0.999 |
| 学习率调度 | constant，无warmup | constant_with_warmup，20步 |
| policy clip upper | 0.28 | 0.2 |
| Env λ | 正文统一0.05；App.B SFT/base {0.02,0.05} | 两份8B示例分别0 / 0.05，没有对应OT配置 |
| 训练长度 | 正文500步；App.B500–1000步 | epochs=2；每batch update epoch=1，非直接固定500步 |
| model/样本 | 三种起点与多评测面 | 公开recipe只有Qwen3-8B及val100数据路径 |

[C1、C8；P, App.B][C8]

示例另设置8个TP1 vLLM engine、单节点8GPU共置、NCCL权重同步、prefix cache与chunked prefill、1CPU/1GB容器、agent并发512、build并发32、最多3次构建重试、输出截断50,000字符。这些是公开配置事实，不是论文按任务验证了如此资源均充足。`agent_max_concurrency=512`也不是每批实际拥有512条；batch16×n16的名义量为256。

论文声明8GPU、24–48h/run的范围，但没拆开任务生成／GPT-5 pass@16筛选、OT专家示范、训练、评测和失败作业的总费用，也没有精确型号到每run的映射。本文不把它换算成H100-hours或本项目8×RTX PRO 6000的预算保证。

**可复用程度：有正式开源训练集成与loss实现，不只是营销说明；但缺少精确数据、全部模型/日志、各实验配置一致性和本轮运行验证，不能标为一键复现或独立复现。**

## 9. 最影响引用与复用的未解问题

| 项目 | 状态与对应位置 | 后续正确处理 |
| --- | --- | --- |
| Eq.(2) token聚合 vs §4 sequence聚合 | 原文内部表述不同；§2.2、§4 | 公式与recipe分列，不擅自修正原文 |
| λ、optimizer、warmup、clip、steps、GPU | 原文/附录/代码不一致；§4、§8.5 | 要重跑时先选择并公开一个确定配置，而不是称完全复刻 |
| Table2效率定义 | 正文共同阈值 vs 表注各自峰值；§7.1 | 取得日志或作者说明前不作严格time-to-quality结论 |
| Fig1/2箭头、Fig7与Table1终值 | 图表标注/量级不同，run对应关系缺失 | 保留原值、目测精度和出处，不互相替换 |
| warning step60与Fig6 | 正文阈值与图形量级不符；§2.5 | 不引用为精确收敛阈值；原图趋势仍有价值 |
| zero-variance/overlong/infra failure怎样影响PG与Env消费 | 论文未完整披露；代码有多个独立路径 | 不把“可组合”写成已经验证；本轮未审计全部SkyRL父类过滤 |
| 全套task manifest、PyTerm外的适应/测试分离 | 本篇未给；§3、§7.3 | OOD是任务分布标签，不自动证明测试实例从未进入适应 |
| 统计重复和区间定义 | 作者给近似值，缺原始计算与seed分布 | 不为单点小差距添加显著性；阴影不是CI |
| world model的因果解释 | 有固定异策略CE与任务表现，没有独立规划/因果中介实验 | 保留预测能力结论，不扩成完整模拟能力 |
| 目标区域是否纯环境观测 | 当前代码env参数含部分规则文本；§8.3 | 检查实际token内容，不只查字段名 |
| verifier-free是否不调用评分器 | 论文目标不使用reward；公开入口多数路径仍评分；§8.4 | 学习信息、筛选信息、执行成本分别核 |
| 一手资源未取得 vs 未公开 | 本机PDF/TeX未取得；网上PDF/HTML已读；release资产本轮未定位 | 不以抓取失败或索引缺项证明作者没有发布 |

这些事项限制精确复现和结论强度，不等于论文所有正结果失效。可以确认的是：作者进行了三类起点的训练，对比了有无辅助项，提供了跨评测面的结果、观测预测测量和部分适应负结果；独立团队复现与完整运行记录不在本轮证据内。

<a id="project"></a>
## 10. 对 RepoHarness 项目一的有限、条件化判断

映射日期2026-09-07，依据当前分支简报：miles/SGLang负责训练推理运行时，真实coding harness经adapter接入，rh2负责环境、评分和训练消费；目标约30B-A3B、8×96GB。当前首训taskset、loss及harness工具面还有未定项。本节**仅设计层映射**，不声称已审计本地辅助目标实现，也不把阅读变成采用ECHO的批准。

ECHO对项目一最有用的启发，不是再把项目命名成“世界模型”，而是问：**昂贵rollout已经产生的哪些反馈，除终局reward以外仍能形成有效监督？** 它给出一个可复用的具体算法和公开hook，说明增量可能很窄；但也表明mask、目标分母、反馈来源和样本过滤必须一起定义。

| 候选 | 适用条件／不适用边界 | 最小辨识实验 |
| --- | --- | --- |
| 在可信真实工具输出上测试单一Env CE辅助项 | 环境输出与动作后果有足够关联；不默认适用于大量规则提示、随机日志或压缩摘要 | 固定基线与任务，比较GRPO和GRPO+Env；同时看独立成功率、未见轨迹CE与实际训练/推理成本 |
| 将PG资格与auxiliary资格分开表达 | 零reward方差不等于无CE；但数据错误/身份不明也不能因“有文本”就训练 | 用已有确定轨迹检查两个mask、原轨迹计数和分母；再决定是否需要窄adapter扩展，不重建通用准入平台 |
| 保留原始反馈来源的最小标记 | stdout、harness error、judge解释和hidden grader资产不是一类内容 | 抽查实际选中token；同预算对比env-only与一种明确替代目标，检查是否仅记住模板 |

对本项目，最大的实现外推是：当前训练已有既定policy loss、MoE和异步消费，而ECHO公开hook针对SkyRL FSDP单序列路径。**不能将工具token直接加入现有policy mask；也不能把所有辅助样本沿用同一staleness／过滤规则后就声称正确。** 是否需要改动以及成本，应由小规模固定样本和短训练验证决定。

项目判断：**值得保留为有公开实现、具备训练证据的算法候选；不应成为首条SWE闭环必须完成的前置条件，也不足以单独证明任务供给或verifier可以取消。** 简历能承重的是我方真实的目标消费适配、受控效率与held-out结果，不是“接上ECHO”或借用论文的翻倍数字。

## 11. 快速查阅与交付状态

| 要回答的问题 | 先查哪里 |
| --- | --- |
| 为什么不是把所有token一起做GRPO？ | §2.2–2.4；P Eq.(1)–(3)、Algorithm1 |
| O与O'的分母有什么区别？ | §2.3；C4 loss与C5 worker |
| 6,170题来自哪里，是否已有完整生产管线？ | §3.2、§8.1；P §4 |
| “翻倍”“无teacher”“无verifier”分别限定什么？ | §3.1、§5.2、§7.3 |
| 哪些模型／指标没有改善？ | §5.2、§7.1–7.3 |
| 实际开销是不是零？ | §7.1、§8.2、§8.5 |
| 原文与代码有哪些不能合并的值？ | §4、§8.5、§9 |

关联笔记：[O01 SkyRL-Agent](O01_skyrl_agent_sa_swe.md)、[E2 CalibForge](E2_calibforge.md)、[N11 miles接入](N11_miles_agentic_rollout.md)。Endless Terminals（E4）、SDPO（N07）是关联来源；本稿不假设并行线程的成品已经发布，不提前建立未知文件链接。

**完成状态：全文与附录精读、关键图表核对、代码定点附查、作者自查完成；没有独立reviewer，没有训练复现。** 详细过程与建议抽查位置见 [E8作者自查](reviews/E8_echo_self_check_20260907.md)。本线程仅提交这两份E8专属文件，共享索引留给汇总线程。

## 一手来源链接

[P-abs]: https://arxiv.org/abs/2605.24517
[P]: https://arxiv.org/pdf/2605.24517v1
[P-html]: https://arxiv.org/html/2605.24517v1
[P3]: https://arxiv.org/pdf/2605.24517v1#page=3
[P4]: https://arxiv.org/pdf/2605.24517v1#page=4
[P5]: https://arxiv.org/pdf/2605.24517v1#page=5
[P6]: https://arxiv.org/pdf/2605.24517v1#page=6
[P7]: https://arxiv.org/pdf/2605.24517v1#page=7
[P8]: https://arxiv.org/pdf/2605.24517v1#page=8
[P9]: https://arxiv.org/pdf/2605.24517v1#page=9
[P10]: https://arxiv.org/pdf/2605.24517v1#page=10
[P13]: https://arxiv.org/pdf/2605.24517v1#page=13
[P14]: https://arxiv.org/pdf/2605.24517v1#page=14
[C0]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/README.md
[C1]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/configs/qwen3_8b_rl_wm05.yaml
[C2]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/echo_rl/terminal_agent/terminal_agent_generator.py
[C3]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/echo_rl/world_modeling/trainer.py
[C4]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/echo_rl/world_modeling/loss.py
[C5]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/echo_rl/world_modeling/fsdp_worker.py
[C6]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/patches/skyrl_minimal_hooks.patch
[C7]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/echo_rl/terminal_agent/entrypoint.py
[C8]: https://github.com/microsoft/echo-rl/blob/f4c3c7ecf78412a507d3c7b0dc0079cdae45d10c/configs/qwen3_8b_rl.yaml
