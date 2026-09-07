# E11 Nemotron-Cascade 2：分阶段 RL、同源教师恢复与 SWE 训练证据

Nemotron-Cascade 2 从 Nemotron-3-Nano-30B-A3B-Base 出发，先进行覆盖十类能力的大规模 SFT，再依次训练指令遵循、多域、MOPD、偏好、长上下文、竞赛代码和 SWE。MOPD 的主要角色是**利用同源历史 checkpoint 恢复能力回退**，而不是在最终阶段汇入一组外部巨型教师。报告明确给出 sampled-token 蒸馏目标、严格 on-policy 更新及两类 SWE 训练；OpenHands 上的最终成绩为 50.2，Terminal-Bench 2.0 为 21.1，不能由竞赛推理的强结果推出通用 agent 领先。最值得借鉴的是分阶段观察干扰、区分廉价修复训练与真实执行、保留评测协议；最重要的限制是缺少完整成本、若干正文／附录配置冲突，以及开放数据与论文配方并非逐项相等。

导航：[来源与覆盖](#source) · [阶段与 SFT](#pipeline) · [目标与 MOPD](#objectives) · [SWE 与环境](#swe) · [结果与评测](#evaluation) · [资产与项目判断](#assets)

<a id="source"></a>
## 1. 来源、版本与本次覆盖

**主来源 P**：Zhuolin Yang 等，NVIDIA，*Nemotron-Cascade 2: Post-Training LLMs with Cascade RL and Multi-Domain On-Policy Distillation*。[arXiv 版本页][ABS]列 v1 为 **2026-03-19**，v2 为 **2026-03-22**；本次主读 [v2 PDF][P] 与 [v2 HTML][H]，检查日期 **2026-09-07**。封面另印 **March 16, 2026**，这是文内日期，不替代 arXiv 提交日期。v2 共 **63 个物理页**，arXiv 标注 CC BY 4.0；模型和数据的许可另列于 §11。

**阅读范围**：通读摘要、§1–6、附录 A–D；附录 E 的五份 IMO 解答、P2 的 LLM 审查和其他题的专家评论均阅读，按“输出工件、审查方式与局限”归纳，**不宣称独立验证了全部数学推导**。检查致谢与参考文献以确认文档结束及引用身份，不逐篇扩读全部参考文献。

已核正文全部四个编号图及未编号封面图、Table 1–10、Appendix C 的两个提示框。Table 11–12 的 PDF 截图多次失败，其正文、表头、数字与 caption 通过 HTML 和 PDF 文本交叉读取；附录 E 主要依赖 HTML／PDF 文本，不能称逐页视觉审查完成。**原始 TeX 和本机 PDF 下载未成功**，不是“作者未公开”。文中页码均指官方 v2 PDF 物理页，避免 HTML 锚点和图像抽取造成偏移。

**配套资料**：查阅官方 Hugging Face 模型卡、SFT/RL 数据卡、目录与可取得的 commit 页面，版本见 §11；未下载权重或全部 JSONL，未运行训练、沙箱、评分或性能复现。本轮不开展 NeMo RL 整库代码审计：它在论文中的职责明确，但作者没有钉死完整历史训练 commit。

**项目读取基线**：`Rogerffff/RepoHarness@miles-migration`，`09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6`。读取当前简报、笔记模板及 [Codex 对 O01 的质量反馈](reviews/15_O01_codex_quality_review_20260907.md)。旧稿 [knowledge/summary_nemotron_cascade2.md](../../../../knowledge/summary_nemotron_cascade2.md) 作为提纲和待核线索，保留不改；本文为 E11 后续维护入口。

### 1.1 原文章节覆盖与检索位置

| 原文位置 | 原文内容／阅读方式 | 本笔记对应 |
| --- | --- | --- |
| p.1、p.2–4 | 摘要、目录、§1；核封面图，完整阅读 | §2、§8 |
| p.5–6，§2、Table 1–2 | 全域最终结果、竞赛汇总与脚注，核原表 | §8–9 |
| p.6–9，§3.1–3.2.10、Fig.1 | SFT、模板、十类数据生产与筛选，全读 | §3 |
| p.9–11，§4.1、Fig.2、Eq.(1) | 阶段顺序、GRPO 与严格 on-policy，全读并核图／公式 | §2、§4 |
| p.11–12，§4.2–4.3 | IF、混合域，动态过滤与奖励，全读 | §5.1–5.2 |
| p.12–14，§4.4、Eq.(2–4)、Fig.3、Table 3 | 教师身份、蒸馏、训推修正、配置与对照，全读并核图 | §6 |
| p.14–16，§4.5–4.8、Table 4 | RLHF、长上下文、竞赛代码、两类 SWE，全读 | §5.3–5.5、§7 |
| p.17–19，§5–6、Fig.4、Table 5–6 | 证明与竞赛测试时扩展、代码细分、失败与限制，全读 | §8.2、§9 |
| p.20–24，Appendix A.1–A.7 | 数学、代码、知识、对齐、长上下文、agent、多语言全部评测协议 | §9–10 |
| p.24–26，Appendix B、Table 7–10 | 全部公开训练超参数，正文交叉核对 | §3.1、§4.3、§6、§7.2 |
| p.26–27，Appendix C.1–C.2 | IOI 迭代输入及 HLE judge，HTML 缺框体，回 PDF 核 | §9.3、§10.2 |
| p.27–29，Appendix D、Table 11–12 | 40 场模拟 Codeforces、惩罚／排名、Python 对照；读表文，图页获取失败 | §8.2 |
| p.30–56，Appendix E | P1–P5 解答、人工批注及 P2 LLM judge；全文文本阅读，不重证全部数学 | §9.4 |
| p.19、p.57–63 | 致谢、参考文献，检查尾部范围与重要依赖 | §1、§11 |

本篇按来源组织，不把暂不采用的数学、偏好、多语言或证明实验删去；不过数学证明工件不会原样复制成二十多页的 RL 笔记。

<a id="pipeline"></a>
## 2. 真实训练流程：顺序优化、兼容域混合和中途恢复

### 2.1 主线与教师支线不能画成同一条直线

根据 Fig.2 和 §4.1，主训练顺序为：

```text
Nemotron-3-Nano-30B-A3B-Base
  → 单阶段多域 SFT
  → IF-RL
  → Multi-domain RL
  → Multi-domain On-Policy Distillation
  → RLHF
  → Long-context RL
  → Code RL
  → SWE RL（正文分 agentless 与 execution-based 两部分）
  → Nemotron-Cascade-2-30B-A3B
```

该图没有另外的 Terminal RL 阶段，也没有把 MOPD 放在最终发布前。模型是 **30B 总参数、3B 激活的 MoE**，但底座不是 Qwen；同量级不等于相同预训练、算子、内存或训练预算。[P, Fig.2、§4.1, p.10][P10]

MOPD 使用的教师来自如下分支，不能把“后面的 RLHF”当作已经存在的教师：

| 教师领域 | 论文明确的来源 | 与主线的关系 |
| --- | --- | --- |
| Math | 初始 SFT checkpoint | 用早期已具备的数学能力修复后续漂移；不是先额外训练一个数学 RL 专家 |
| RLHF | 从初始 SFT 单独进行 RLHF 得到的 checkpoint | 必须先建立的教师支线，不是主线 MOPD 之后才产生的最终 RLHF 模型 |
| Multi-domain | IF-RL + Multi-domain RL 之后选出的 checkpoint | 在先前阶段中选择相应验证表现较强的版本 |

教师共享 SFT 初始化、tokenizer 和词表；每个样本按领域选择教师。论文未给教师的公开 checkpoint ID、完整选择日志、各域最终配比或在线更新规则。这里的“无需引入外部模型家族”只指 **MOPD 教师池**；SFT 生成与 GenRM 实际使用很多外部强模型。[P, §4.4, pp.12–13][P13]

### 2.2 Cascade 不是证明某个固定顺序永远最优

作者的目标是减少域间干扰，同时优先优化最重视的能力。更好的 SFT 和更多样的 RL 环境改变了模型行为，所以第二代顺序与第一代不同。IF 可能伤害 ArenaHard 偏好表现；某些 RLVR 阶段会降低熵、缩短推理并伤害数学；同时训练兼容、生成与验证时长相近的域又可能更有效率。[P, §4.1.1、§4.4, pp.10–12][P10]

因此它不是“所有领域永不混训”：Multi-domain RL 就包含三个领域。它也不是“顺序 RL 不遗忘”：MOPD 正是为仍然存在的回退服务。论文没有给所有顺序排列、相同总计算预算的完整消融，阶段安排首先是作者基于训练观察形成的工程方法，不能写成已证明的普适最优顺序。

## 3. SFT：不是工具语法预热，而是主能力来源之一

### 3.1 一阶段大规模训练与模板

所有域混合、packing 到 **最多 256K tokens**，作者观察约 **1.5 epochs** 最优。Table 7 给出 global batch 64、实际 **33,000 steps**，cosine scheduler 的 Max Steps 为 **40,000**；两者不是矛盾的实际步数。最大学习率 `5e-5`、最小 `5e-6`、warmup 200 steps，AdamW，`β1=0.9, β2=0.98`，weight decay 0.1。[P, §3.1 p.6；Table 7 p.24][P24]

256K 是 packed sequence 上限，不表示每条任务都含 256K 输入或是一个长程 agent episode。数据中的 sample、conversation、trajectory、独立 prompt 与 packing 后训练序列必须分开计数。

Fig.1 展示 thinking／non-thinking 和工具调用模板：移除显式 `/think`、`/no_think` 指示，利用 thinking 边界和空 thinking 块区分模式；工具定义置于 system 的 `<tools>`，工具调用使用 `<tool_call>` 及 XML 风格函数／参数结构。这个模板会影响历史 reasoning 保留与 agent 接入，不应假定任意普通 tool role 都等价。**当前发布卡的具体序列化与 parser 建议另列 §11，不反填三月的实现。** [P, §3.1.2、Fig.1, pp.6–7][P7]

### 3.2 数学、竞赛代码、科学与长上下文

| 原文领域 | 数据来源、数量与生成过程 | 学习与证据边界 |
| --- | --- | --- |
| 数学计算／解答 | 1.8M Python tool-calling，DeepSeek-V3.2 生成；约 1.9M 非工具 Speciale 数据，另有 676K Nano generation-selection、GPT-OSS-120B 生成，合称 2.6M 非工具样本 | 工具数据与非工具数据不是同一预算；模型生成不自动等于全量可验证 |
| 自然语言证明 | 98K AOPS proof problems；DeepSeek-V3.2-Speciale 生成 410K proof generation 与 400K proof verification，正文称总计 816K | 分项算术为 810K，与总称不完全一致；不擅自补出 6K 类型 |
| 竞赛代码 | 约 165K unique coding prompts；OpenCode-Stage2、OpenCodeReasoning、HardTests，来自 Codeforces、AtCoder、AIZU、CodeChef；I/O fingerprint 与 n-gram 去重去掉约 24.2% 自重复 | 165K 与去重前后的精确关系未展开；这不是跨 benchmark 全面污染审计 |
| 竞赛代码轨迹 | GPT-OSS-120B 生成；有测试的保留正确程序，无可验证测试的倾向选更长 reasoning；产出 1.9M Python、1.0M C++14、1.3M Python tool-calling traces | “更长推理可能分析更充分”是作者启发式，不是 verifier 通过 |
| 科学代码 | 生物、材料、物理、化学、数学研究型 coding prompts；GPT-OSS-120B，1.1M 样本 | 与 science 问答和真实仓库修复分开 |
| Science | Cascade 1 的 1.4M + Nano 的 1.3M，物理／化学／生物；GPT-OSS-120B 生成 | 公开说明生成来源，没有每一步有效率／生成成本 |
| Long context | Nano 的 160K，平均序列 128K tokens；ChatQA-2 的 74K，平均 29K | 这里是 SFT 数据长度，不是后面 long-context RL 的 32K 输入限制 |

以上来自 [P, §3.2.1–3.2.4, pp.7–8][P8]。本篇不将原始问题数与多次采样后的轨迹数相加，构造一个没有依据的“总独立任务量”。

### 3.3 一般对话、指令、安全与工具对话

**General chat**：Cascade 1 来源构造 4.9M reasoning-on、372K reasoning-off；前者由 GPT-OSS-120B 生成。off 的解释却列 300K 数据内高质量短答和另 330K DeepSeek-V3-0324 生成，合计 630K，不能与 372K 强行对齐。另用两个 GPT-OSS-120B 分别扮用户／助手，合成约 **700K 多轮 conversation samples**，用户模型可提前结束以抑制重复；再加入 Nano 的 4.6M reasoning-on chat，prompts 来自 LMSYS/WildChat，响应由 GPT-OSS-120B、Qwen3-235B 的 Thinking/Instruct 版本产生。[P, §3.2.5, p.8][P8]

**Instruction following**：Cascade 1 的 230K on、64K off，再加 Nano 的 497K（457K on、40K off）；生成教师包括 GPT-OSS-120B、DeepSeek-V3-0324 与 Qwen3-235B 两个模式。不能把这一 SFT 配方的样本数当作后续 IF-RL 独立题数。[P, §3.2.6, pp.8–9][P9]

**Safety**：约 4K Nano 样本，源于 Content Safety v2、Gretel Safety Alignment v1、Harmful Tasks、Red-Team-2K，目标是对不安全输入适当拒绝。**Conversational agent**：822K 多轮多工具样本，要求选择并使用工具，生成教师包括 GPT-OSS-120B、Qwen3-32B 与 Qwen3-235B 的 Thinking/Instruct。工具对话不只包含前述数学 Python；安全 SFT 也不等于已经单独验证了 coding agent 的权限与反作弊行为。[P, §3.2.7–3.2.8, p.9][P9]

### 3.4 SWE 与 terminal SFT 的可复用部分

**SWE** 同时采用 OpenHands、SWE-Agent、Mini-SWE-Agent 和 agentless scaffold。125K agentic samples 来自 Nano/Super 的数据，Qwen3-Coder-480B-A35B-Instruct 生成，问题源为 SWE-Gym、SWE-rebench 和 R2E-Subset。这里引用的是当时的 SWE-rebench，不能自动换成后来精读的 V2 资产。另有 389K agentless samples，包含错误位置定位、修复、测试生成；修复数据用 DeepSeek-V3.2 重建。agentic 数据以 **non-thinking** 训练，agentless 数据以 **thinking** 训练。[P, §3.2.9, p.9][P9]

初步对照中，只有 agentic SFT 时，OpenHands/SWE-bench Verified 的 Pass@1/Pass@4 是 **48.9/62.8**；加入 agentless 后 **49.9/65.2**。这是增加一类 SFT 数据后的观察，**未给等总 token／等数据量／等训练算力对照**，不能隔离为“agentless 表示本身”带来的因果提升。也不能与 §7 的 agentless RL 表混成一次实验。

**Terminal** 采用 Terminal-Task-Gen：适配静态任务、从种子和技能分类生成任务，再以 DeepSeek-V3.2 在隔离 Docker 内进行执行反馈循环，由 Terminus 2 组织工具交互。正文总称 490K samples，分项为数学162K、代码32K、SWE32K、seed-based120K、skill-based140K，合计486K。保留这两个口径，不假设差额来自隐藏数据。这里说的是任务／轨迹生产及 SFT；Fig.2 没有独立 terminal RL 阶段。[P, §3.2.10, p.9][P9]

**数据生产披露的边界**：论文给出丰富来源和产出数，但未恢复“所有候选仓库／PR → 成功镜像 → gold/no-op 验证 → 稳定可解任务 → 保留轨迹”的完整漏斗，也未给每个数据源的 grader 隔离、合法替代解、flakiness、未来 git 内容及全流程费用。因此这份报告不能单独用作所有环境已经可信的证明。公开卡与实际实验数量的差异另见 §11。

<a id="objectives"></a>
## 4. GRPO、on-policy 与训练配置：必须保留阶段例外

### 4.1 原文 Eq.(1) 与作者的操作性定义

§4.1.2 称整个 Cascade RL 使用 NeMo RL 中的 GRPO：每次由当前策略采样一组 $G$ 个回答，然后只做一次梯度更新，使数据采集与被更新策略相同，作者据此称 importance ratio 为 1。它是“按当前权重采样后更新”的说明，**不是 fully-async learner，也不是所有训练／推理数值已完全一致的证明**。[P, §4.1.2, p.11][P11]

Eq.(1) 原样写成：

$$
\mathcal J_{\mathrm{GRPO}}(\theta)=
\mathbb E_{(q,a)\sim\mathcal D,\,\{o_i\}_{i=1}^G\sim\pi_\theta(\cdot\mid q)}
\left[\frac{1}{\sum_i |o_i|}\sum_{i=1}^G\sum_{t=1}^{|o_i|}\hat A_{i,t}\right],
\qquad
\hat A_{i,t}=\frac{r_i-\operatorname{mean}(r_1,\ldots,r_G)}{\operatorname{std}(r_1,\ldots,r_G)}.
$$

同一回答各 token 共用其组归一化优势，分母按组内响应 token 总量写出；reward 在 RLVR 来自答案／执行验证，在 RLHF 来自 GenRM 聚合。**该打印公式没有显式写 log-policy 或比率项**。它描述一个依赖策略采样的期望，但不是可将 detached advantage 直接送进 autodiff 的完整实现公式。本笔记不偷偷补上一个 PPO loss 再称为原文，也不由简写推出作者实际训练没有梯度。

std 的 epsilon、工具 observation／模板 token 的精确 mask、跨 DP/CP reduction 和失败组补采顺序，在本篇没有完整展开。后面的 MOPD 是单独的 Eq.(2–4)，不能因总述“全程 GRPO”就对其额外施加 group normalization。

### 4.2 “全程去掉 KL”与 RLHF 的例外

§4.1.2 写完全移除 KL；然而 §4.5.3 明确将 **RLHF KL coefficient 设为 0.03**，用于保护其他能力。IF、多域和 long-context 小节则明确 KL/entropy 为零。正文还为 MOPD 引入了训练引擎与推理引擎间的重要性权重。因此正确概括应是：

> 作者总体采用严格 on-policy 的 RL 更新安排，但各阶段训练目标不同；RLHF 有显式 KL 例外，MOPD 另有训推修正。

不能写成“全部阶段都无 KL、无任何比率修正”。这个冲突是来源内部差异，不用框架默认值消解。[P, pp.11、13、15][P15]

### 4.3 公开配置总表：正文／附录分别保留

以下主要抄录 **Appendix B, Table 8–9**；与正文冲突之处就在表后说明。batch 表示 prompts，rollout size 表示每题生成数，而不是 minibatch 或单次 tool call。

| 阶段 | prompts × rollout | 最大 response | lr | steps | 表中 optimizer | T / top-p | 表中 overlong filtering |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IF-RL | 128×16 | 49K | 3e-6 | 180 | AdamW | 1 / 1 | False |
| Multi-domain RL | 128×16 | 49K | 3e-6 | 70 | Adam | 1 / 1 | True |
| MOPD | 128×4 | 98K | 3e-6 | 52 | AdamW | 1 / 1 | False |
| RLHF | 128×16 | 16K | 3e-6 | 25 | AdamW | 1 / 1 | True |
| Long-context RL | 128×16 | 49K | 3e-6 | 30 | Adam | 1 / 1 | True |
| Code RL | 128×16 | 118K | 3e-6 | 22 | AdamW | 1 / 0.95 | True |

六列 optimizer 均列 `β1=0.9, β2=0.95`。Table 8–9 **没有给这些阶段统一的 warmup、min-lr 或完整 scheduler**，不能从 SFT 或 Table 10 自动继承。[P, Table 8–9, p.25][P25]

需要保留的差异：MOPD 正文 lr=2e-6，并给30步warmup，附录是3e-6；RLHF 正文约30步、无overlong filtering，附录25步、True；long-context 正文无overlength filtering，附录True；多域与long-context正文说AdamW，附录说Adam。long-context正文的49K是 **最大 sequence**，表中字段是 **最大 response**。这些不是已经确认的“错字”，目前无法恢复唯一运行配置。

## 5. 各领域 RL 的数据、反馈与负结果

### 5.1 IF-RL：验证约束、组过滤与零奖励超长惩罚

IF 复用 Nano-v3 可客观验证的指令数据，例如少于200词；主要修正某些约束的 kwargs 格式，如 `count_increment_word`。动态过滤移除一组全正确或全错误的题，目的是让每个训练 prompt 有组内对比信号。超出最大生成长度尚未结束的回答获得 **零 reward**，以抑制不必要的长输出；这不是把自己梯度置零且保留原reward的 horizon masking。[P, §4.2, pp.11–12][P12]

本代只训 thinking mode，不再加辅助 reward model。先训 IF 是因为它可能压低 human-alignment，后续再恢复；早期高 IF checkpoint 又可作为 MOPD 教师。小节报告 IFBench **83.13%** 是阶段结果，最终 Table1 是82.9，二者不替换。动态过滤的补采开销、保留组数和淘汰比例未量化，不能只以180个optimizer steps估计全部生成量。

### 5.2 Multi-domain RL：选择相容且成本相近的域

混合比例约 **55% STEM MCQA、30% Workplace Assistant 工具调用、15% structured output**，数据来自 Nano-v3。作者观察这些域共训不会造成其所看 benchmark 的退化，并改善 MMLU-Pro、τ²、IFBench；响应长度和验证时长接近，减少对长输出和慢验证的等待。[P, §4.3, p.12][P12]

这是根据工作负载组织训练的实例，不是一个“所有域均衡采样”的通用公式。本文没有给此混合与按域分开、随机混合或负载无感混合的等算力性能消融；也没有完整列各子域 reward 实现与环境动作协议。

### 5.3 RLHF：外部 GenRM、成对比较与 thinking-only 的代价权衡

数据为 HelpSteer3、arena-human-preference-140k 的 commercially-friendly subset 及合成 safety blend。`140k` 是源数据集名称的一部分，不代表本阶段实际用了140K题。GenRM 为经 HelpSteer3 框架训练的 **Qwen3-235B-A22B-Thinking-2507**：对同题两个候选先分析优缺点，再给 helpfulness 分数和相对排名。[P, §4.5.1, p.14][P14]

作者对每题 rollout 做 all-pairs 比较，沿用 Nano-v3 的聚合、长度归一化奖励调整和 quality-gated conciseness bonus，以减少无收益的冗长回答。本报告没有完整写出这些继承机制的公式，不以普通胜率或长度惩罚自行替代。在16条rollout下，无序组合为120对，这是算术推导；是否两个顺序都评、如何batch/cache以及实际API调用数未披露，不能据此给出实际费用。

将 thinking 与 non-thinking 混训能略改善收敛和部分成绩，却严重伤害 IF，且先前 IF 增益不能完全恢复。因此选 thinking-only。这个负结果比“RLHF全面无回退”的笼统描述更重要。正文配置为128×16、T/top-p=1、response16K、lr3e-6 AdamW、entropy0、KL0.03、约30步；附录差异见§4.3。[P, §4.5.2–4.5.3, pp.14–15][P15]

### 5.4 Long-context RL：刻意不混其他领域

只用 Nano-v3 long-context blend，作者说混入其他域反而伤害无关 benchmark。执行环境为 **NeMo Gym**，问答 judge 为 **Qwen3-235B-A22B-Instruct-2507**，不是上一节 Thinking GenRM。输入最多32K，正文最大sequence49K；128×16，T/top-p1，lr3e-6，KL/entropy0，约30步，再延长训练会快速增加生成token。[P, §4.6, p.15][P15]

这不证明“一般混训都会遗忘”，也不证明该阶段把模型窗口训练到了1M。1M检索评测与发布模型容量是另外的事实。正文／附录的长度定义、optimizer和overlong冲突保留，不选择一个版本拼成完整配方。

### 5.5 Code RL：小而难的竞赛题，不是交互式仓库 RL

从 Cascade coding corpus 的 AtCoder、Codeforces、AIZU 等题取数据，剔除 **GPT-OSS-120B 8/8都通过**的题，最终3.5K个hard prompts。它是外部模型校准的难题集，不是已经证明随当前student能力持续刷新的在线curriculum。[P, §4.7.1, p.15][P15]

训练128×16、response118K、lr3e-6 AdamW，使用严格二元正确性reward，以降低partial-test shortcut风险；“采用二元分”是防hacking设计动机，不是完整免疫证明。Table9给22步、T1/top-p0.95和overlong filtering True。[P, §4.7.2；Table9][P25]

**系统数字的准确归属**：每个RL step的 **2,048份程序验证**，异步reward server在 **384 CPU cores 上427.2秒**完成一批。这里不是2,048个SWE容器任务，不是整个训练step，也不是GPU预算。验证并发与严格on-policy参数更新可以同时存在，不能据此把训练叫fully asynchronous RL。[P, §4.7.2, p.15][P15]

## 6. MOPD：利用同源 checkpoint 修复能力漂移

### 6.1 教学信息来自哪里

本篇的 MOPD 是 **Multi-domain On-Policy Distillation**。同题输入$x$，student推理引擎产生$y$，选定领域teacher在student实际访问的前缀上评分，不生成一条外部teacher完整轨迹来取代student。teacher身份见§2.1。当前样本只选择对应领域teacher，不是把三个teacher的全词表概率逐token平均。[P, §4.4, pp.12–13][P13]

数学teacher本身是初始SFT，说明这一实验的重要场景是**恢复已经获得但被后续阶段削弱的能力**。它不能单凭teacher/学生同源，就保证student访问的所有长程状态上teacher都可靠；本篇也没有详细的跨tokenizer或异源teacher对照。

### 6.2 Eq.(2–4)：三种概率、两个 stop-gradient 与带外归零

记$s_t=(x,y_{<t})$，$\pi^{inf}$为生成引擎的student分布，$\pi^{train}$为训练引擎当前student，$\pi^{domain_i}$为本例领域teacher。仅在student采样的token上定义：

$$
a_t^{MOPD}=\log\pi^{domain_i}(y_t\mid s_t)-\log\pi^{train}(y_t\mid s_t).\tag{2}
$$

teacher认为该token比当前student更可能时，advantage为正。不是GRPO按同题reward减均值除标准差；也不是观察未来执行反馈后构造的SDPO特权上下文教师。

训推修正为：

$$
r_t=\frac{\pi^{train}(y_t\mid s_t)}{\pi^{inf}(y_t\mid s_t)},\qquad
w_t=\operatorname{sg}[r_t]\,\mathbf1[\epsilon_{low}\leq r_t\leq\epsilon_{high}].\tag{3}
$$

$\epsilon_{low}=0.5,\epsilon_{high}=2.0$。**带外权重为零，不是将比率夹到0.5或2**；带内保留真实比率，但不对它反向传播。例如$r=0.4,0.75,2.5$分别得到$w=0,0.75,0$。这只是公式示例，不是本轮训练实验。

最终surrogate为：

$$
\mathcal L_{MOPD}=-\mathbb E_{x\sim\mathcal D,\,y\sim\pi^{inf}}
\left[\frac{1}{|\mathcal V(y)|}
\sum_{t\in\mathcal V(y)}w_t\,\operatorname{sg}[a_t^{MOPD}]
\log\pi^{train}(y_t\mid s_t)\right].\tag{4}
$$

$\mathcal V(y)$是token mask保留的有效response tokens；advantage也stop-gradient，显式梯度作用于最后的student logprob。**分母按$|\mathcal V(y)|$写，不是按importance band内token数重归一化**。是否另有模板、工具观测、padding、坏样本的具体mask，以及$\mathcal V$为空时怎样处理，本篇没有完整实现说明。sampled-token reverse-KL视角也不等于实际传输了full-vocabulary logits或top-k分布。[P, Eq.(2–4), p.13][P13]

这里的$\pi^{inf}$／$\pi^{train}$区分首先处理生成和训练引擎不一致；论文未给跨多次权重更新陈旧轨迹的版本上限。因此它不能直接证明本项目fully-async + faithful DIS在相同区间下正确或最优。

### 6.3 训练配置、曲线与结果

默认 **128 prompts×4=512 responses/update**。后续实验改为512prompts×1，作者称更稳定且最终相近；没有给对应完整数表。正文lr2e-6，从2e-7开始用30步线性warmup，通常40–50步收敛；附录Table8记3e-6、52步、response98K。warmup观察有Fig.3支持，但没有完整的“有/无warmup”定量消融。[P, §4.4 p.13；Table8 p.25][P13]

Fig.3(a) reverse-KL从约0.02–0.03降至第60步附近约0.007–0.008；(b)grad-norm从约0.8–0.9下降到后期约0.1–0.2。**这是原图目测量级，非精确日志，无误差条。** 图3(c)数学专域实验中，MOPD更快接近teacher虚线，存在波动，不是单调提升；正文称GRPO由89.9到25步后的91.0，MOPD在30步内达到92.0。图轴是AIME25 avg@64与optimization steps，不是总GPU-hour。[P, Fig.3, p.13][P13]

Table3的ArenaHard v2结果如下，列出两类指标以保留小回退：

| 方法 | steps | Hard Prompt | Creative Writing |
| --- | ---: | ---: | ---: |
| Initial | 0 | 71.5 | 40.6 |
| RLHF | 100 | 81.7 | 68.6 |
| RLHF | 160 | 80.7 | 71.2 |
| MOPD | 52 | 85.5 | 71.0 |

MOPD在较少更新步获得更好的Hard Prompt，但Creative比160步RLHF低0.2；不能写成所有指标均更高。Table3所比较的长RLHF实验也不是主线Table9的25步阶段。[P, Table3, p.14][P14]

**效率证据界限**：作者从相同初始checkpoint比较，支持该设置下更少步获得相近或更高分。每步生成量、response长度、teacher前向、GenRM成对评分、teacher支线训练的成本不同，不能把160/52约3.08写成GPU吞吐或总费用改善3倍。MOPD提示池正文为RLHF、IF、多域和AceReason-Math；完整比例未给，公开数据卡的区别见§11.2。

<a id="swe"></a>
## 7. SWE 两条训练路线：廉价修复监督与真实执行互补，但证据不能合并

### 7.1 Agentless RL：没有 Docker 时用模型评分

多数实例没有可执行Docker环境，因此采用 **GPT-OSS-120B作为修复reward model**；正文将名字误排为`GPTOOS-120B`，本文按同文模型身份记录。prompts混用golden localization和top-5 retrieved localization，再过滤相对简单的题。**这是训练期带gold定位信息的样本构造，不是测试时也获得gold定位。** [P, §4.8.1, pp.15–16][P16]

配置为128×16=2048 responses、最大sequence98,304、T/top-p1、lr3e-6 AdamW，约40–50步。若一题所有rollout的reward都不大于0.5，则将**该题loss屏蔽**。这是对低质量信号的prompt级处理，不等于逐个reward≤0.5的回答都归零，也不同于先前IF的零方差过滤。reward打分提示、校准误差、group统计与mask的实现先后、masked组是否补采没有完整给出。

Agentless Mini评测用NV-Embed-Code检索5个候选文件并提供代码上下文，模型输出修复；OpenHands允许工具交互。Table4给出同次agentless训练前后两种scaffold：

| 状态 | Agentless Mini avg@4 | Agentless Mini pass@4 | OpenHands avg@4 | OpenHands pass@4 |
| --- | ---: | ---: | ---: | ---: |
| Init. | 41.9% | 55.2% | 49.8% | 64.2% |
| after Agentless RL | 44.3% | 57.4% | 50.8% | 65.0% |
| 本文算术差 | +2.4pp | +2.2pp | +1.0pp | +0.8pp |

`avg@4`是四次采样的平均成功率，`pass@4`是四次中至少成功一次，不能互换。结果支持修复能力在这一跨scaffold评测中有增益；没有证明任意未见harness、仓库或真实软件任务上都迁移。没有重复训练种子或差值置信区间。[P, Table4, p.16][P16]

### 7.2 Execution-based RL：真实 OpenHands 仓库交互

每个episode解决一个软件issue，OpenHands提供文件检查、搜索、编辑和测试；通过编译／单元测试评价候选patch。原文称反馈提供反映functional correctness的确定性reward，但没有明确将各测试结果组合成哪一个标量、F2P/P2P的全部条件、评分资产可见性、权限边界或环境异常处理。**不能用“deterministic”替代对grader实现的审计。** [P, §4.8.2, p.16][P16]

| 项目 | 本篇明确值／条件 |
| --- | --- |
| 实际训练每步 | **16 prompts×64 rollouts=1024 responses** |
| context / turns | 256K / 最多200交互轮 |
| 采样temperature | 0.8；top-p未在Table10给出 |
| 学习率 | max3e-6、min0、warmup10steps |
| 数据源 | SWE-Gym + R2E-Subset |
| 离线难度预筛 | 中间模型每实例生成**16条**；全通过题删除；全失败题随机丢弃90%，仍保留10% |
| 未披露 | 这一阶段总训练步数、精确最终题单、训练硬件／时长、完整optimizer、超时／重试／mask及版本运输细节 |

配置来自 [P, §4.8.2 p.16；Table10 p.26][P26]。预筛的16条与正式每题64条不是冲突；预筛使用中间模型，不是论文已经给出了持续随student更新的课程。全失败也没有全部删除，因此不能将其总结为“0%任务一律不能训练”。公开发布的3612条SWE记录见§11，不能直接推成所有阶段实际消费题数。

### 7.3 不能从现有表倒推出执行 RL 的独立增益

Table4给出agentless后OpenHands avg@4=50.8，最终Table1是50.2。**不能据最终50.2声称execution-based RL单独提高了某个确定幅度，也不能直接认定它导致了0.6pp的真实退化。** 两表没有完整对齐最终checkpoint选择、所有评测条件和随机误差的逐阶段实验。作者报告执行RL确实进行过，与“它的独立增益被隔离证明”是两个证据层次。[P, Table1 p.5；Table4 p.16][P5]

同理，多harness生成SFT数据、有一项跨scaffold迁移结果、使用OpenHands执行RL，并不是固定算力的harness-diversity训练消融。对项目有用的是两类信号和真实执行的可组合路线，不是未经分解的“多harness必然更好”。

<a id="evaluation"></a>
## 8. 全域最终结果：保留强项、弱项与相同底座比较的限制

### 8.1 Table1 的完整能力面

下表按原表领域重排数值。`—`表示未报告；括号为作者TIR结果（允许Python），不是误差条。竞赛三项是测试时扩展结果，预算见§9。Nano与Cascade2共享预训练base，但SFT和整条后训练不同，**不是只开关Cascade/MOPD的因果消融**。其余基线混合官方报告值与按推荐配置重跑，不能视为全量同预算复现。[P, §2、Table1, pp.5–6][P5]

| Benchmark | Nano 30B-A3B | Super 120B-A12B | Qwen3.5 35B-A3B | Cascade2 30B-A3B |
| --- | ---: | ---: | ---: | ---: |
| IMO2025 | — | — | — | 35/42 |
| IMO-AnswerBench | 70.4 | 77.2 | 74.8 | 79.3 |
| IMO-ProofBench | — | — | — | 72.9 |
| AIME2025 | 89.1 | 90.2 | 91.9 | 92.4 (98.6) |
| AIME2026 | 89.9 | 89.8 | 91.1 | 90.9 (95.0) |
| HMMT Feb25 | 84.6 | 93.7 | 89.0 | 94.6 |
| IOI2025 | — | — | 348.6 | 439.28/600 |
| ICPCWF2025 | — | — | — | 10/12 |
| LiveCodeBench v6 (2408–2505) | 68.3 | 78.7 | 74.6 | 87.2 (88.4) |
| LCBPro25Q2 Easy | 54.5 | 81.7 | 81.1 | 87.0 (89.3) |
| LCBPro25Q2 Med | 3.50 | 23.2 | 17.8 | 27.6 (36.8) |
| SciCode | 33.3 | 42.1 | 38.0 | 36.4 |
| MMLU-Redux | — | — | 93.3 | 86.3 |
| MMLU-Pro | 78.3 | 83.7 | 85.3 | 79.8 |
| GPQA-Diamond | 73.0 | 79.2 | 84.2 | 76.1 |
| HLE no tool | 10.6 | 18.3 | 22.4 | 17.7 |
| ArenaHard v2 Avg. | 67.7 | — | 65.4 | 83.5 |
| ArenaHard Hard Prompt | 72.1 | 73.9 | 64.5 | 88.2 |
| ArenaHard Creative Writing | 63.2 | — | 66.3 | 78.7 |
| IFBench prompt | 71.5 | 72.6 | 70.2 | 82.9 |
| Scale AI Multi-Challenge | 38.5 | 55.2 | 60.0 | 45.3 |
| AA-LCR | 35.9 | 58.3 | 58.5 | 39.1 |
| LongBench v2 | 39.6 | — | 59.0 | 40.3 |
| NIAH@1M (RULER subset) | 94.8 | 98.3 | 94.3 | 99.0 |
| CL-Bench | 12.0 | — | 15.5 | 12.2 |
| BFCL v4 | 53.8 | — | 67.3 | 52.9 |
| τ²-Bench | 49.0 | 61.2 | 81.2 | 58.9 |
| Terminal-Bench2.0 | 8.5 | 31.0 | 40.5 | 21.1 |
| SWE Verified / OpenHands | 38.8 | 60.5 | 69.2 | 50.2 |
| MMLU-ProX | 59.5 | 79.4 | 81.0 | 72.5 |
| WMT24++ en→xx | 86.2 | 86.7 | 87.6 | 84.1 |

结论不是全域占优：作者自己指出knowledge与agentic仍弱于Qwen3.5，并将更强预训练和agentic RL投入列为未来方向。相对Nano，BFCL **53.8→52.9**、WMT **86.2→84.1**也有回退；不能说“全部基座能力保持”。NIAH99与AA-LCR39.1、CL12.2分别测不同能力，不能用检索高分替代长期执行与上下文学习。[P, §2, p.6][P6]

### 8.2 竞争性编程、TIR 与 Codeforces 附录

Table6扩展到GPT-OSS、Qwen不同规模、Kimi等模型；比较配置跟随各模型推荐、至少128K至最多256K思考预算，不是严格同资源。以下保留本模型的完整Q1/Q2难度形状，避免只看headline87.2。[P, §6、Table6, pp.18–19][P18]

| 指标 | 无Python工具 | TIR |
| --- | ---: | ---: |
| LCB v6 | 87.2 | 88.4 |
| LCBPro25Q1 Easy | 88.1 | 91.0 |
| LCBPro25Q1 Med | 39.2 | 45.2 |
| LCBPro25Q1 Hard | 0.7 | 2.2 |
| LCBPro25Q2 Easy | 87.0 | 89.3 |
| LCBPro25Q2 Med | 27.6 | 36.8 |
| LCBPro25Q2 Hard | 0.0 | 0.0 |
| 估计Codeforces Elo | 2320 | 2345 |
| 估计percentile | 99.6 | 99.7 |

“hard split非零”只在Q1成立，Q2仍为0。§6所说within8attempts与主实验avg@8／pass@1口径要区分，不能把这张表都改成pass@8。

Appendix D按2025/01–07的 **40场Div.1/2比赛**模拟参赛，每题最多8次尝试，普通轮次用期望penalty调整分数，ICPC风格以通过题和罚时计，估计相对人类rank/Elo。它不是在线Codeforces账号真实rating。Table11 caption是 **without Python**，Table12是 **with Python**；正文“with and without … respectively”的顺序反了，本文按明确caption读取，不隐去冲突。[P, Appendix D、Table11–12, pp.27–29][P28]

两张明细表有逐场改善也有退步：例如Teza Round1总分由无工具3830到有工具9723.21，改善很大；Round996则5793.75到5025.00，并非每场都受益。这些是原表分数，不是百分比。作者仍指出constructive、interactive和hypothesis-driven题的弱点。Table11–12本轮图页未取得，以上数值经HTML／PDF文本交叉核对，不称目视验证完成。

## 9. IMO／IOI／ICPC：权重能力与大量测试时计算共同构成结果

### 9.1 Generate–verify–refine 的真实预算

通过NeMo-Skills实现DeepSeek-Math-V2式自改进推理：生成候选证明，模型验证，选择更好证明，依据低分反馈再修订；不是在测试题上更新权重。[P, Appendix A.1.2, pp.20–21][P20]

| 配置 | 默认 IMO／证明 TTS | 为节省计算的 ProofBench 子集 |
| --- | --- | --- |
| 初始proof generations | 128 | 32 |
| 每proof verifications | 64 | 16 |
| 选择refinement的proofs | top32 | top8 |
| 反馈与新proof | 每proof配8份优先低分的验证分析，生成4份refinement | 其余沿用所述流程，未逐字段另列 |
| 最大轮数 | 8，或平均proof score达到0.99999停止 | 2 |
| 单次最大生成／采样 | 256K，T1，top-p0.95 | 同段未给另一套token配置 |

减配用于 **全部30个Basic问题**及Advanced中11题：1、4、7、13、14、17、19、22、25、26、28。因此60题成绩并非完全一致的每题TTS预算；不能简单用64次最终judge乘一次响应量估计整个推理成本。

### 9.2 ProofBench 的评分者与复评分区别

最终ProofBench评分由 **DeepSeek-V3.2-Speciale + ProofAutoGrader**执行，每题64次grading。作者发现对公开DeepSeek-Math-V2解答直接取mean，在Advanced得73.8，明显高于人工61.9，于是采用：**任一次judge给0，最终就0；否则取均值**。重新评分得57.7。61.9−57.7=4.2，正文概称“within4”不应替代精确差值。[P, §5.2；Appendix A.1.2][P21]

Table5如下；“our reproduced score”指对已有解答重新评分，不是重新生成并复现DeepSeek-Math-V2训练或完整推理系统。

| 模型／结果来源 | Basic30 | Advanced30 | Overall60 |
| --- | ---: | ---: | ---: |
| Aletheia（引用expert结果） | — | 91.9 | — |
| Gemini3 Deep Think（引用） | — | 76.7 | — |
| Gemini Deep Think / IMO Gold（引用） | 89.0 | 65.7 | 76.7 |
| DeepSeek-Math-V2（引用人工分） | 99.0 | 61.9 | 80.2 |
| DeepSeek-Math-V2公开proofs，本文LLM复评 | 99.5 | 57.7 | 78.6 |
| Cascade2，本文LLM评分 | 92.5 | 53.4 | 72.9 |
| GPT-5.2-Thinking high（引用） | — | 35.7 | — |
| Gemini3 Pro（引用） | — | 30.0 | — |
| GPT-5 Pro（引用） | — | 28.6 | — |

引用expert榜单的访问日为2026/03/09。不同judge、TTS和模型来源不能当作统一盲评。重新评分接近一套human结果，可以校准其宽松程度，但不是对所有模型证明LLM judge无偏。[P, Table5, p.17][P17]

Fig.4的Advanced分数在round1–5标为 **40.7、45.0、50.5、50.1、53.4**。显示更多推理计算总体有益，但第4轮比第3轮低，不能称单调或保证性scaling law；没有误差条。图中基准横线使用同grader的DeepSeek结果，不等于对齐两者全部推理预算。[P, Fig.4, p.18][P18]

### 9.3 竞赛三金的条件

Table2：IMO P1–P5各7、P6=0，**35/42**；IOI六题分别39、88.53、100、100、28.75、83，合计**439.28/600**；ICPC A–L除B、G外均过，**10/12**。这些是作者在问题集上得到的金牌水准结果，不是参加现场竞赛或单次pass@1。[P, Table2, p.6][P6]

**IOI** 对subtask进行多轮候选生成，每轮40个、最多50轮，结合官方judge反馈与已通过其他subtask的代码继续改进。正文称439.28对应2000 generations，增至5000可得507.66；但这两个总数与逐subtask预算的汇总范围没有完全解释，不擅自给出全竞赛精确生成总量。P2还报告200次以内超过86分。**ICPC** 每题生成1000解，经初筛再由官方测试judge，解10题；除A/I外的八个成功题在100次submissions内解决。[P, §6续文及 Appendix A.2, pp.19–22][P22]

Appendix C.1的IOI提示框包括题目、历史失败代码及judge结果、其他subtask已接受方案等。反馈是该评测协议明确提供的搜索信息，不应称为无需反馈的裸模型解题，也不把它等同于越权读取隐藏测试。没有人类同墙钟、同提交次数、同总计算的公平性实验。[P, Appendix C.1, p.26][P26]

### 9.4 附录 E：完整解答、审查归属与保留的问题

本文阅读五份proof以恢复工件和评分证据，但不重证所有代数推演；没有P6解答附录，Table2给P6零分。人工评审Jiafan He为IMO2015金牌得主，同时也是本报告作者，不能称独立第三方复现。[P, §5.1；Appendix E, pp.30–56][P30]

| 工件与位置 | 模型解法主线 | 报告的审查与限制 |
| --- | --- | --- |
| P1，pp.30–33 | 晴朗直线覆盖格点，构造k=0/1/3，再以边界计数和归纳排除其他值 | 人工7分；批注要求解释边界集合／计数等，不只展示最终答案 |
| P2，pp.34–42 | 解析几何坐标化，通过长度、圆和切线等关系组织长代数推导 | **不是人工完整验证例外**：使用带参考解与marking scheme的LLM judge；p.39明确标GPT-5.4-Thinking (Extensive)，给7/7 |
| P3，pp.43–46 | bonza函数的最优常数4，素数／赋值分析与达到界的构造 | 人工7分；若干记号、依赖说明有批注 |
| P4，pp.47–51 | 因子递推、整除结构与下降，刻画能达到终态的初值族 | 人工7分；解答保留较多中间引理与符号负担 |
| P5，pp.52–56 | 双人游戏阈值√2/2，分方向策略及不等式／余量估计 | 人工7分；存在不必要中间步骤、推理痕迹和结尾后的重新表述 |

P2 judge输入包括原题、参考证明、评分规则和候选proof，明确要求不要修补候选中的缺口，但允许合法替代解；其输出逐项检查依赖后给分。**这不同于ProofBench最终统一的DeepSeek-V3.2-Speciale judge**，也不应因Table2总caption写human expert，就删掉P2脚注例外。[P, Table2脚注 p.6；Appendix E p.38–42][P39]

§5.1对工件质量的总结是：证明可能过长、定义和步骤冗余、泄露中间推理、偶有排字问题。保留这些意见不是否认其数学成绩，而是避免“金牌分数”等于所有专业工件质量都已成熟的外推。

## 10. Appendix A/C 的评测协议：分数离不开模式、预算与评分器

### 10.1 数学、代码、知识、对齐、长上下文与多语言

| 评测面 | 样本／重复和模式 | 预算、grader或特殊条件 |
| --- | --- | --- |
| AIME25/26、HMMT Feb25 | 每集30题；thinking，avg@64 | response131K、T1/top-p1；TIR允许stateful Python最多100次 |
| IMO-AnswerBench | 400题；avg@16 | response256K；GPT-OSS-120B + AnswerAutoGrader；非ProofBench证明评价 |
| LCB v6 | 454题；thinking，pass@1 averaged8 | 无工具128K、T1/top-p0.95；TIR response131K，Python≤100calls |
| LCBPro25Q1/Q2 | 分别166/167题；主要报告Easy/Med的avg@8，Table6另列Hard | 原文时间范围Q1写2025/01–04，Q2写04–07；按作者定义，不自行改为日历季度 |
| SciCode | 80main tasks、338subproblems | 数量披露；没有为本篇恢复完整任务级运行协议 |
| MMLU-Redux / MMLU-Pro | 3000题/30subjects；12K+题；thinking单次EM | response128K、T1/top-p0.95 |
| GPQA-Diamond | 198题，thinking avg@8 | 同知识评测采样设置 |
| HLE | text-only2158题，thinking | response128K、T1/top-p0.95；GPT-OSS-120B judge；boxed回答改写见§10.2 |
| ArenaHard2.0 | 750prompt=500hard+250creative；thinking | GPT-4.1 judge，**无style control**；T0.6/top-p0.95，response32K |
| IFBench | 294prompt、58种新约束；thinking avg@8 | 与Arena同段的32K设置；约束不重叠是作者／benchmark设计主张，本轮未审训练题单 |
| Scale AI Multi-Challenge | 273conversations，四类保持／记忆／编辑／自洽；thinking avg@10 | 不把Arena/IF的decode设置自动套到此项 |
| AA-LCR | 100题，平均输入约100K tokens，thinking avg@16 | 多文档推理，不是needle检索 |
| LongBench v2 | 503题，thinking avg@4；原数据8K–2M **words** | 数据范围不等于模型实际无损接收全部最大上下文；未完整列截断处理 |
| NIAH@1M | RULER四类×100=400；non-thinking avg@1 | 1M检索结果，不等于1M长程执行能力 |
| CL-Bench | 1899tasks、500contexts、31,607rubrics；thinking avg@1 | 上下文学习与规则运用 |
| MMLU-ProX | 原集29语言，本篇6种：en/de/es/fr/it/ja；thinking avg@1 | 不能称已验证29语言 |
| WMT24++ | 原集55语言，本篇en→de/es/fr/it/ja；thinking单次 | **XCOMET-XXL**质量分；原文沿用pass@1一词，但不应解释为二元翻译正确率 |

来源为 [P, Appendix A.1–A.7, pp.20–24][P20]。各处avg@k表示多次生成平均，不是“至少一次成功”的pass@k。基线通常优先引用原报告，否则按推荐设置重跑；没有统一总计算或所有模型相同context的保证。

### 10.2 HLE 的回答格式本身改变成绩

作者保留HLE默认system prompt，并在每题后附“最终答案放入`\boxed{}`”要求，替代官方要求explanation、answer、confidence的输出形式。作者称这一改动带来约 **6–7个百分点**，主要在数学，因为更贴合SFT答案格式。[P, Appendix A.3, p.22][P22]

Appendix C.2的GPT-OSS-120B judge提取最终答案、对照reference，处理数值容差和不可提取的`None`等情形；若缺少confidence则填100。**这个默认值不是模型校准能力的证据**。因此Table1的HLE17.7应保留协议，不把所有差异都归于参数更新。[P, Appendix C.2, p.27][P27]

### 10.3 Agent 评测：训练和部署序列化条件相互影响

| Benchmark | 论文的具体运行条件 |
| --- | --- |
| BFCL v4 | 官方配置，thinking，avg@1 |
| SWE-bench Verified | 500题，OpenHands，**non-thinking，avg@4**；256Kcontext、最多200turn，保留完整交互历史 |
| Terminal-Bench2.0 | 89题，Terminus2默认scaffold，avg@5；不替换成后来的版本 |
| τ²-Bench | airline50、retail114、telecom114；airline avg@16，后两者avg@8，目标降低standard error至≤1.5pp；这不是给出了所有实测置信区间 |

τ²工具调用保留**最近一轮用户消息之后的历史reasoning**，包括交错tool响应之间的reasoning，而非仅最后一条assistant的思考。作者称不保留会降 **3–5个百分点**；保留全部更早history会增加token，但结果相近。telecom还将用户指导重复三次。这些是58.9分的协议组成，不是无条件的模型能力常数。[P, Appendix A.6, pp.23–24][P23]

SWE评测的non-thinking与agentic SFT一致；agentless训练则thinking。不能把这篇概括成“所有agent都用thinking最大预算”。另一方面，报告没有系统的独立安全／权限执行结果表；SFT与RLHF有safety数据，不足以证明真实coding代理已通过所有行为安全检查。

<a id="assets"></a>
## 11. Infra、费用与开放资产：论文配方不等于发布目录

### 11.1 已披露的系统事实及尚缺的成本

训练后端为 **NeMo RL**；long-context使用 **NeMo Gym**；证明TTS使用 **NeMo-Skills**；agentic SWE使用 **OpenHands**；terminal SFT为 **Terminus2 + Docker**。这些分别承担训练、环境、推理搜索和agent流程，不应因为同属NVIDIA生态就认为它们提供了全部相同的接口。[P, §4、Appendix A及参考文献][H]

本篇最明确的吞吐数字是§5.5的384CPU程序验证服务器；MOPD主要是step-to-quality。没有披露完整GPU型号／数量、总GPU-hour、总墙钟、SFT生成费用、teacher支线成本、长证明TTS token数，或SWE镜像生产总CPU成本。并行布局、训推dtype、MoE routing replay、weight publication、恢复与staleness均未充分展开。**33K SFT steps、22 Code-RL steps和3B激活参数都不能替代实际成本。**

以下资产附查截至2026-09-07，主页面可取得，不等于已下载并运行。可见HEAD用于记录这次访问的版本线索；读取部分是`main`网页，未声称所有文件都按该SHA下载验字节。

### 11.2 官方模型与数据发布状态

| 资产 | 官方入口／观察到的revision | 实际核查与范围 |
| --- | --- | --- |
| 模型 | [Nemotron-Cascade-2-30B-A3B][MODEL]；HEAD `6327cdbcf907e1c7cec9cb29fb6e6cebdf8feaf7` | 模型README、tree及commit页；13个safetensors分片和config/template/tokenizer等，目录合计约63.2GB；**未下载或验证权重** |
| RL数据 | [Nemotron-Cascade-2-RL-data][RLD]；HEAD `05bbaf03bac608e804efc86c5f8bf99844f2d197` | 卡、目录及SWE添加commit；只作为访问记录，不补齐所有训练阶段 |
| SFT数据 | [Nemotron-Cascade-2-SFT-Data][SFTD]；HEAD `9f36020daf067f1a8b39336bf619fe30af30bb02` | 卡和八个域目录；未下载全量JSONL、重算总数或核对训练manifest |

RL版本同时核对了[添加SWE数据的commit页面][RLC]；未下载LFS数据文件。

RL数据卡列 **IF45,879、Multi-domain18,147、MOPD6,171、SWE3,612**，合计73,809条。SWE卡称约20%SWE-Gym、80%R2E-Subset，这是**发布数据混合**，不自动证明完整历史训练消费比例。MOPD列1853 AceReason-Math、1854 IF、610 Workplace、927 STEM、927 Structured，合计6171；其中没有单列正文提到的RLHF prompts。不能据公开子集反推论文并未使用RLHF，也不能假装配比已经完全恢复。[官方RL数据卡][RLD]

RL schema含`responses_create_params`、`agent_ref`、`dataset`、prompt/约束/ground_truth、`environment_name`及部分`pass_rate_*`。这些是任务与元数据，不是全部实际rollout、行为logprob、teacher logits或sample consumption ledger。Hugging Face viewer出现转换／Arrow错误只说明本轮预览失败，**不是本轮已经证明原始JSONL损坏**。

SFT tree有chat、conversational-agent、IF、math、safety、science、SWE、terminal八类目录；没有独立code／long-context目录，不能据此断言相关数据一定不存在于其他混合内。卡中SWE为 **439,610**，与论文125K+389K=514K不同；terminal为 **822,213**，与正文490K不同，且卡中的conversational-agent同样822,213。本文保留来源差异，不猜测是去重、后来扩容还是复制错误。部分行的`generator`为`-`，不能宣称每条数据教师来源都可完整追踪。[官方SFT数据卡][SFTD]

许可标注：模型与SFT为 **NVIDIA Open Model License**，RL数据为 **ODC-By-1.0**。不是整套Apache-2.0；这里只记录发布标签，不作数据再分发或使用许可的完整法律判断。**官方有模型、数据和训练框架，不等于全部历史阶段、教师checkpoint和过滤后manifest均已公开且可一键复现。**

### 11.3 当前模型卡的接口事实，不能混成三月论文训练配置

[模型作者README][MC]声明当前主要面向OpenHands，**尚不支持OpenCode**；tool responses使用user role包裹`<tool_response>`，而不是独立tool role。推荐部署T1/top-p0.95；它不能替代论文各阶段采样配置。

README记录2026-07-09的reasoning parser更新：`nano_v3`只用`</think>`分割，无该token时整段作为reasoning；旧`nemotron_v3`会把thinking中的tool call当成隐式结束。这会影响工具调用，但本轮只读卡中的说明，未追parser代码或运行对拍，不把它认定为原论文发生过的错误。[模型作者README][MC]

卡声明模型支持1M上下文，示例vLLM≥0.17.1却使用`--max-model-len 262144`。前者是声明容量，后者是示例服务限制；二者不应合并成“运行示例就开启1M”。也不能把当前serving版本当作论文的历史软件revision。

### 11.4 为什么本轮没有继续审计整套 NeMo 代码

论文没有给一个绑定各阶段的完整训练脚本与commit，公共框架存在并不能恢复全部实验。故本轮以公式、配置、数据卡和模型运行边界为主，记录[NeMo RL][RL]、[NeMo Gym][GYM]、[NeMo-Skills][SKILLS]作为依赖入口，**未检查这些仓库的所有loss／mask消费者，也未把其最新默认值写进论文配方**。这与O01需要追实际token捕获主张的代码范围不同。

## 12. 证据冲突、缺口与旧稿修正

### 12.1 来源内部及论文—发布之间的差异

| 问题 | 位置与实际差异 | 本稿处理 |
| --- | --- | --- |
| 全程无KL | §4.1.2无KL；§4.5.3 RLHF=0.03 | 保留阶段例外，不统一化 |
| GRPO实现公式 | Eq.(1)未显式写policy梯度因子 | 作为原式与文字理解，不伪造完整可运行loss |
| MOPD lr | 正文2e-6，Table8 3e-6 | 分别记录，warmup不由表推断 |
| RLHF步数／过滤 | 正文约30且无overlong，Table9 25且True | 不能静默任选 |
| Long-context字段 | 正文max-sequence49K、无过滤、AdamW；表max-response49K、True、Adam | 长度语义和参数差异逐项标明 |
| Multi-domain optimizer | 正文AdamW，Table8 Adam | 历史recipe仍有缺口 |
| SFT数量 | proof816K vs分项810K；chat-off372K vs分项630K；terminal490K vs分项486K | 不虚构遗漏类别或原因 |
| MOPD prompt池 | 正文含RLHF；发布卡未单列 | 发布范围与实际训练不能互相替代 |
| SFT发布量 | SWE439610 vs论文514K；terminal822213 vs490K | 不称全数据逐项一致 |
| IMO人工评审 | Table2总caption简写human，P2脚注明确LLM；附录注明GPT-5.4-Thinking | 记录逐题审查归属 |
| Codeforces with/without | Appendix D引文顺序与Table11/12caption相反 | 按caption定位，保留冲突 |
| SWE阶段效果 | intermediate OpenHands50.8 vs最终50.2 | 不算execution-RL独立增益或确定退化 |

这张表是复用前必须知道的边界，不意味着十二项都是已确认论文错误；四舍五入、版本变化、简写与真实运行差异的原因仍需作者或历史工件确认。

### 12.2 哪些是未披露、未取得、未检查

**原文未充分披露**：完整GPU/API/环境成本；所有教师与训练revision；逐阶段最终题单与精确消费量；各类超时、异常、truncation的组统计与梯度合同；SWE评分隔离和精确reward；固定总计算的阶段顺序／多harness／执行RL消融。检查范围包括所有相关正文与Appendix B，不把没有找到附录当成理由。

**本轮未取得**：TeX和可用于本地渲染的PDF；Table11/12图页；部分HF固定revision原始文件入口。替代取得HTML、PDF文本和主要图表，但没有宣称这些替代具有完整视觉校验能力。

**本轮未检查**：完整模型文件、全量数据有效性、NeMo分布式实现、真实训练／sandbox／推理性能、全部数学证明的独立正确性。未运行不等于不能运行，也不等于论文未公开。

旧稿对阶段、教师、agentless/agentic区分有用，本文主要收紧三类概括：**“全部数据／配方公开”改为按资产核查；“全程无KL／top-p1”改为逐阶段；“步效率提高”和“模型同量级”不再直接换成总成本或八卡适用性。** 原文已给出的细节保留，不因配置冲突就降成整篇没有可用证据。

## 13. 对 RepoHarness 项目一的条件化判断

映射基线为2026-09-07读取的[当前状态简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)：miles + SGLang +外部coding harness，目标8×96GB、约30B-A3B，rh2负责环境、reward与训练消费可信性。这里只做设计层候选，不声称本轮审计了RepoHarness实现，也不改变其未定taskset、loss或harness范围。

**本篇相对既有阅读的新增证据**是：一个相近参数规模模型的完整SFT→分域RL→同源teacher恢复流程；agentless修复训练向OpenHands迁移的有限对照；以及强数学／代码推理与较弱真实agent结果并存。它不是一个fully-async系统加速论文。

| 可借鉴判断 | 原文依据 | 适用条件与最小对照 |
| --- | --- | --- |
| 先观察能力干扰，再决定是否分域或蒸馏恢复 | §4.1、§4.4、Table3及RLHF负结果 | 先用固定retention集观察真实回退；在相同初始化和总成本口径下比较简单混合／顺序训练，再决定是否需要历史teacher。无回退就不必强加MOPD |
| agentless修复可作为较便宜的训练来源，但不能替代真实执行验证 | §3.2.9、Table4、§4.8.2 | 比较原模型、强SFT／agentless增量与执行训练，在同一冻结OpenHands或当前harness上测试；同时核RM评分与真实测试的一致性 |
| reward筛选、样本mask与优化目标必须按阶段区分 | IF零奖励、agentless整prompt屏蔽、MOPD带外token归零 | 复用上游训练后端；针对选定目标建立小型同样本参考计算，明确何时改变组成员、梯度和分母。不因本篇用了[0.5,2]就更改faithful DIS |

SFT里的多scaffold数据和Table4跨scaffold结果值得作为迁移动机，但还不支持“多harness随机训练已经因果证明有效”。同样，“3.5K难题”或“执行SWE每步16prompts”也不能证明整个流程成本低：生成长、每题采样多、强教师和SFT很重，且缺GPU预算。

**本篇对项目选择的直接约束**：不要以另加MOPD或更多训练阶段作为进阶的形式标准。更有价值的是拿出一个可解释的学习闭环：明确训练信号来自哪里，监测它增强和损害什么，在真实harness上独立验证。该报告支持阶段管理与反馈利用是严肃工程问题，但项目一仍需要自己的等条件结果，不应把作者的35分IMO或50.2 SWE当成项目收益。

## 14. 快速定位与交付状态

| 常见问题 | 本文位置 | 原文最短入口 |
| --- | --- | --- |
| SFT是否只是预热？各教师与数据量？ | §3 | §3.2、pp.7–9；Table7 p.24 |
| MOPD位于哪里、教师从哪来？ | §2、§6 | Fig.2 p.10；§4.4 p.13 |
| strict on-policy是否没有任何修正？ | §4、§6 | Eq.(1) p.11；Eq.(2–4) p.13；RLHF p.15 |
| 零reward、整题mask、token带外归零有何区别？ | §5.1、§6.2、§7.1 | §4.2、§4.4、§4.8.1 |
| agentless到真实SWE的证据？ | §7 | Table4 p.16；Table10 p.26 |
| 竞赛成绩用了多少推理计算？ | §9 | Appendix A.1–A.2、C.1及Table2 |
| HLE／τ²为何高度依赖协议？ | §10 | Appendix A.3、A.6、C.2 |
| 哪些真实资源和资产可复用？ | §11–12 | 数据卡／模型卡；Appendix B不等于成本表 |

关联来源：E11旧摘要保留历史；R2 Nemotron 3 Ultra、N07 SDPO、Nemotron-Terminal数据工程可以用于进一步比较，但这里不替它们重写总结。后续讨论优先查本篇对应节，不需要再次从63页第一页起读。

**状态：全部后训练正文、相关附录与证明工件文本阅读完成，主要图表已核，作者自查完成；Table11/12原图仍未取得，待独立复查，无实验复现。** 详细核验、算术检查和未完成事项见 [E11作者自查记录](reviews/E11_nemotron_cascade2_self_check_20260907.md)。本轮仅维护本文与自查，不更新共享索引、不改其他线程成果。

## 官方来源

[ABS]: https://arxiv.org/abs/2603.19220
[P]: https://arxiv.org/pdf/2603.19220v2
[H]: https://arxiv.org/html/2603.19220v2
[P5]: https://arxiv.org/pdf/2603.19220v2#page=5
[P6]: https://arxiv.org/pdf/2603.19220v2#page=6
[P7]: https://arxiv.org/pdf/2603.19220v2#page=7
[P8]: https://arxiv.org/pdf/2603.19220v2#page=8
[P9]: https://arxiv.org/pdf/2603.19220v2#page=9
[P10]: https://arxiv.org/pdf/2603.19220v2#page=10
[P11]: https://arxiv.org/pdf/2603.19220v2#page=11
[P12]: https://arxiv.org/pdf/2603.19220v2#page=12
[P13]: https://arxiv.org/pdf/2603.19220v2#page=13
[P14]: https://arxiv.org/pdf/2603.19220v2#page=14
[P15]: https://arxiv.org/pdf/2603.19220v2#page=15
[P16]: https://arxiv.org/pdf/2603.19220v2#page=16
[P17]: https://arxiv.org/pdf/2603.19220v2#page=17
[P18]: https://arxiv.org/pdf/2603.19220v2#page=18
[P20]: https://arxiv.org/pdf/2603.19220v2#page=20
[P21]: https://arxiv.org/pdf/2603.19220v2#page=21
[P22]: https://arxiv.org/pdf/2603.19220v2#page=22
[P23]: https://arxiv.org/pdf/2603.19220v2#page=23
[P24]: https://arxiv.org/pdf/2603.19220v2#page=24
[P25]: https://arxiv.org/pdf/2603.19220v2#page=25
[P26]: https://arxiv.org/pdf/2603.19220v2#page=26
[P27]: https://arxiv.org/pdf/2603.19220v2#page=27
[P28]: https://arxiv.org/pdf/2603.19220v2#page=28
[P30]: https://arxiv.org/pdf/2603.19220v2#page=30
[P39]: https://arxiv.org/pdf/2603.19220v2#page=39
[MODEL]: https://huggingface.co/nvidia/Nemotron-Cascade-2-30B-A3B
[MC]: https://huggingface.co/nvidia/Nemotron-Cascade-2-30B-A3B/raw/main/README.md
[RLD]: https://huggingface.co/datasets/nvidia/Nemotron-Cascade-2-RL-data
[RLC]: https://huggingface.co/datasets/nvidia/Nemotron-Cascade-2-RL-data/commit/05bbaf03bac608e804efc86c5f8bf99844f2d197
[SFTD]: https://huggingface.co/datasets/nvidia/Nemotron-Cascade-2-SFT-Data
[RL]: https://github.com/NVIDIA-NeMo/RL
[GYM]: https://github.com/NVIDIA-NeMo/Gym
[SKILLS]: https://github.com/NVIDIA-NeMo/Skills
