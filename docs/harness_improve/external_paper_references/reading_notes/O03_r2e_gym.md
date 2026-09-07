# O03 R2E-Gym: Procedural Environments and Hybrid Verifiers for Scaling Open-Weights SWE Agents：环境与训练精读

R2E-Gym 的核心成果是从真实 commit 构建可执行 SWE 任务，再用离线轨迹训练编辑 agent、测试 agent 和轨迹判别 verifier。三者均采用 SFT；论文没有在线 RL 实验。论文报告完整集 8,135 题，去除与 SWE-Bench 测试仓库重叠后为 4,578 题；编辑模型用 3,321 条成功轨迹、覆盖 2,048 题，32B 的 SWE-Bench Verified Pass@1 为 34.4%。混合 verifier 将多候选选择提高到 Best@26 51%，不能把这部分归为权重训练收益。最有价值的限制是：历史依赖恢复仍需半人工；生成测试会无区分或偏爱错误补丁；无执行 verifier 会依赖轨迹话术。当前公开数据、配置与论文若干数字不同，下文逐项区分。

导航：[来源与覆盖](#来源与覆盖) · [环境生产](#环境生产) · [三条训练路径](#三条训练路径) · [推理扩展与证据](#推理扩展与证据) · [资产与复现](#资产与复现) · [项目映射与审查](#项目映射与审查)

<a id="来源与覆盖"></a>
## 1. 来源、版本与完整覆盖

- **论文**：Naman Jain、Jaskirat Singh（共同一作）、Manish Shetty、Liang Zheng、Koushik Sen、Ion Stoica；UC Berkeley / Australian National University。正式标题见本文标题。[arXiv v1](https://arxiv.org/abs/2504.07164v1)，提交 2025-04-09；截至本次读取仅列 v1；PDF 标注 Preprint / Under review。阅读和修订日期：2026-09-07。
- **原文附件**：[arXiv PDF](sources/O03/2504.07164v1.pdf)、[官方 TeX 包](sources/O03/2504.07164v1.tar.gz)、[提取全文](sources/O03/paper.txt)。全文共 27 页；本文 p.N 同时指 PDF 第 N 物理页与印刷页，两者一致。
- **官网版本**：[项目页](https://r2e-gym.github.io/)及其 [PDF 附件](sources/O03/project-paper.pdf)。官网标题多出 “Environment Generation”；PDF 正式标题与 arXiv 相同。两份 PDF 全 27 页提取文本在去掉 arXiv 水印、归一空白后完全相同，覆盖正文后训练、数据、infra、评测和 A–E 附录，未发现实质文本增删；另将 p.2–27 以 Poppler 60 DPI 渲染，对应 PNG 字节全部相同；p.1 仍有水印/版面差异。图表另回 arXiv 原页检查。不能把官网视为新增训练版本。
- **官方代码**：[R2E-Gym/R2E-Gym](https://github.com/R2E-Gym/R2E-Gym)，实际读取 commit `0d94c4eb9431cd195c55a7ea3abd54006c9a1735`（下文简称 C）；[本地只读摘录](sources/O03/official_repo/README.md)。它已加入 DeepSWE/rLLM 指引和更多 runtime 支持，故不是论文实验代码的时间锁定版本。本文单列能影响复现的当前增量，不把 DeepSWE 当作本论文新增 RL 阶段。
- **网页/资产快照**：[arXiv 摘要 HTML](sources/O03/arxiv_abs.html)、[官网 HTML](sources/O03/project_page.html)、[资产读取记录](sources/O03/SOURCE_RECORD.md)。官网检查了全部正文、图注和 HTML；未见包含额外技术案例的 tab/select，展示图对应论文图。论文图像中的数字和轨迹不只依赖文本提取。
- **版本冲突**：arXiv 摘要网页写 `AgentGym`、`SYNGEN`、`>8.7K`，PDF p.1/§2 写 R2E-Gym、SWEGEN、`>8.1K`，Table 1 为 8,135。这里用完整 PDF 作为论文实验事实，保留网页矛盾，不据摘要另造一版 8.7K 实验。官网及 C 的 README 把 51% 写成 pass@1；本文严格采用 PDF Table 4 的 Best@26。
- **旧稿**：[knowledge/summary_r2e_gym.md](../../../../knowledge/summary_r2e_gym.md)，在全文/附录覆盖建立并阅读后才对照。旧稿的 SFT 定位、主要数值基本正确，主要缺失是测试 agent/EF verifier 训练细节、公式、预算、负案例和资产差异，详见 §9。

按原文结构建立的覆盖表如下；“精读”包括相关图表、公式与图像案例，不以派工问题作范围上限。

| 原文章节与页码 | 深度与覆盖内容 | 本文位置 |
| --- | --- | --- |
| Abstract、§1 Introduction，p.1–2，Fig.1 | 精读：两项贡献、训练与 test-time scaling 分界、历史对比 | §1、§3、§6 |
| §2 Procedural Synthetic Data Generation，p.3–4，Tables 1–2 | 精读：commit、build、F2P、backtranslation、repo 去重 | §2 |
| §3 / §3.1 Training SWE-Agents / Results and Analysis，p.4–5，Table 3、Figs.2–3 | 精读：SFT 样本、规模曲线、thought、真实/合成对照 | §3、§6 |
| §4.1 Exploring Different Axes for Training Verifiers，p.5–6，Eq.1 | 精读：EB/EF 两种模型与打分 | §3–4 |
| §4.2 Comparative Analysis，p.6–8，Figs.4–7 | 精读：采样、区分率、毒性、注意力分析 | §4–6 |
| §4.3 Hybrid Inference Time Scaling，p.8–9，Eq.2、Table 4 | 精读：Top-n、回归过滤顺序、Best@K | §4、§6 |
| §4.4 Ablation Studies，p.9–10，Fig.8 | 精读：测试/编辑采样预算、去组件对照 | §6 |
| §5 Related Work、§6 Conclusion，p.10；致谢/参考文献 p.11–14 | 阅读：环境、SFT、SWE-RL、通用 coding verifier 的关系；无新增自身后训练实验 | §3、§6；参考文献仅作线索 |
| Appendix A Dataset Details，p.15–18，Fig.9、Listings 1–5 | 精读：全部阈值、半人工安装、gold-conditioned testgen、issue 模板、两个合成问题、patch minimization | §2、§5 |
| Appendix B SFT Training，p.18–19，Fig.10 | 精读：四工具、无网络、成功拒绝采样、全部已给训练/采集预算 | §3、§5 |
| Appendix C.1 EB Testing Agents，p.19–21，Fig.11、Listing 6 | 精读：正负测试轨迹、full SFT、Django starter 示例 | §3、§5 |
| Appendix C.2 EF Verifiers，p.21，Fig.12 | 精读：Sonnet/本模型轨迹、平衡标签、LoRA | §3–4 |
| Appendix C.3 / C.4，p.22–23，Eqs.3–6、Figs.13–14 | 精读：max 定义、毒性分母、四注意力窗口、oracle Pass@K | §4–6 |
| Appendix D.1 / D.2，p.23–25，Listings 7–8 | 精读：SymPy 成功区分、Django 异常反例；原文删节处明确保留 | §5 |
| Appendix E Agent Trajectory Example，p.25–27，Figs.15–16 | 精读原图：问题及六个 thought/action/observation 阶段 | §5 |

<a id="环境生产"></a>
## 2. SWE-GEN：可执行任务怎样产生

### 2.1 数据来源、漏斗与单位

SWE-GEN 从真实 GitHub 历史修复 commit 出发；“synthetic”主要指生成问题描述、补充测试，并不表示全部 bug 都是模型注入。通过 SEART GitHub search 寻找 commit 较多的 Python 仓库，收集历史 diff，再筛选适合修复学习的小改动。环境安装、测试与问题生成是不同工序（§2 p.3、Appendix A p.15–18）。

| 阶段 | 论文数量/单位 | 处理与限制 | 原文定位 |
| --- | --- | --- | --- |
| 搜索仓库、原始 commit、规则/LLM 过滤后 commit | 未给逐层数量 | Python、较多历史 commit；行级和 AST 级筛选 | §2、A |
| 成功构建环境、原有/补生成 F2P 测试 | 未给分层数量和存活率 | Docker 历史依赖搜索；原有测试优先，缺测试时补生成 | §2、A |
| 完整任务集 R2E-Gym | **8,135 任务，13 仓库** | 每题有环境、测试、自然语言描述；不是最终 SFT 消费量 | Table 1 p.3、Fig.9 p.15 |
| 无 SWE-Bench 测试仓库重叠的 Subset | **4,578 任务，10 仓库** | 通常用于全部实验，除非另有说明；不是完整集都用于训练 | §2–3、Table 2 p.3 |
| 编辑成功轨迹池 | **3,321 条，2,048 个独立环境** | Sonnet-3.5-v2，环境测试拒绝采样 | §3 p.4、B p.19 |
| 测试 agent 轨迹池 | **2,203 条** | 含正、负轨迹，minimal rejection sampling | C.1 p.20 |
| EF verifier 轨迹池 | **5,700 条** | Sonnet 采集池加已训 32B 的采样，正负平衡 | C.2 p.21 |

**不能倒推采集成功率**：3,321 是保留下来的成功轨迹，不知总尝试数、逐题重采次数、提前终止或过滤数；2,048/4,578 也不是完整测量协议下的 solver pass rate。两个 epoch 不自动意味着实际消费恰好 6,642 个完整长轨迹，因 32K 采集与 20K 训练窗口之间的处理未写清。

Table 2 实为环图：Subset 中 pandas 31.5%、numpy 17.1%、pillow 13.5%、orange3 10.5%、aiohttp 6.5%、tornado 5.7%、scrapy 4.7%、pyramid 4.1%、datalad 3.9%、coveragepy 2.4%（四舍五入）。Fig.9 完整集另外出现 sympy、matplotlib、moto；完整集最大的是 sympy 28.7%，其次 pandas 17.8%。**repo 去重与问题/commit 去重不是同一声明**；文中未给跨 fork/派生 bug/近重复文本的全面去重方法，也未披露基座预训练污染审计。该分布还说明“题数多”不等于仓库均匀或 bug 机制独立。

### 2.2 筛选和安装的实际工作量

Appendix A p.15 给定的 commit 阈值是：最多 **5 个非测试文件**、非测试文件合计 **100 编辑行**、patch 最长 **2,000 字符**；非测试 AST entity 最多删 **1** 个、加 **3** 个、改 **3** 个；最多 **10 个 statement 级变化**。偏好非文档改动、代码与测试相匹配，另用 LLM judge；judge 型号、提示词和校准统计未给。这里是任务生产偏好，不是证明这些任务更适合 GRPO 的难度定律。

依赖恢复步骤是读取 `requirements.txt/setup.py` 等信息 → 识别版本冲突 → 生成多组 pin → 逐一试装直到成功。作者明确承认 **semi-manual、难扩展**；未来更多使用 LLM 是展望。Listing 1 用 pandas 的 Python/numpy/setuptools 等组合展示尝试过程，属于示意代码（还有参数/排版笔误），不能当可直接运行的完整构建器。论文没有给镜像层复用率、每题构建耗时/磁盘、失败重试成本或总人工时。

当前代码 C 的 [docs/ENV_GENERATION.md](sources/O03/official_repo/docs/ENV_GENERATION.md)要求给新仓库添加配置、枚举、测试命令，再跑历史采集、可测试 commit 分析及环境验证。对应完整路径为 `src/r2egym/repo_analysis/constants.py`、`src/r2egym/repo_analysis/repo_analysis_args.py`、`src/r2egym/repo_analysis/store_repo_commits.py`、`src/r2egym/repo_analysis/analyze_testable_commits.py`、`src/r2egym/repo_analysis/repo_testextract.py`。文档示例用 `o1-mini`、12,000 max tokens，但不能回填为论文所有生产阶段的模型/预算。`src/r2egym/repo_analysis/repo_testheuristics.py::repo_heuristics` 还有 pyramid fixture/import、aiohttp Makefile 等仓库特例，说明跨仓库迁移仍有工程维护成本。

### 2.3 验证测试、反译问题和最小补丁

1. **F2P 验证**：F2P 指测试在原 buggy commit 失败、fixed commit 成功。先利用历史关联测试，缺失时用类似 Agentless 的 reproduction test generation 补齐。Appendix A p.16 特别说明：**环境生产的测试生成可见 ground-truth patch**。这与推理时测试 agent 只由问题/代码起步的场景不同，不能把后者说成拥有金标修复。
2. **Backtranslation**：给问题生成模型 commit hash/message、非测试 diff、测试 diff、旧/新执行结果、相关失败函数及 assertions。仅看 diff 的朴素反译容易生成空泛描述；加入执行信息是作者的质量理由（§2 p.3、A p.16–17）。
3. **输出约束**：Listing 3 要求简洁标题、错误示例、expected/actual behavior；不直接提测试函数/文件，不泄露 solution；允许短的复现代码，超过约 5–6 行应简化。**这是 prompt 要求，不是泄漏率为零的实测**。题面带 bug 输入和期望属于作者设计，不等于完全无 hints。
4. **Patch minimization**：迭代删除改动、重新跑测试，只保留仍能修复的更小集合，为 localization 评价提供更细信号（A p.18）。没有给该流程的保留数量、预算或对训练/评测的独立收益；“通过有限测试仍成功”也不证明语义上的唯一最小修复。

论文验证的是 F2P、成功修复及测试筛选；没有报告 fresh reset 的重复稳定性、合法替代解接受率、金标/隐藏测试防读、评分控制文件保护、抗输出伪造或全库 flakiness 统计。不能用“可执行 Gym”推出已满足在线 RL 的评分隔离。

<a id="三条训练路径"></a>
## 3. 后训练全流程：三个 SFT 模型，不是三阶段 RL

```text
GitHub commit → SWE-GEN 环境/问题/测试 → 去测试仓库重叠的任务池
                                       ├─ Sonnet 编辑尝试 → 测试通过轨迹 → 编辑 agent full SFT
                                       ├─ Sonnet 测试生成轨迹（含正负） → 测试 agent full SFT
Sonnet 编辑采集池 + 已训编辑 32B 再采样 ──┴─ 正负平衡标签 → EF verifier LoRA SFT
推理时：编辑 agent 多候选 + 测试 agent 产物 + EF 分数 → hybrid 排序 → 选一个补丁
```

三个模型分别训练，最后按工具流程组合；不是参数合并、专家蒸馏或在线共同优化。C.2 的 **on-policy trajectories** 指已训 32B 对任务采样形成 verifier 的监督数据，不能由此推导 PPO/GRPO 更新。论文 §5 提及 SWE-RL 是相关工作；全文和附录没有给本方法的 RL reward/advantage/策略梯度实验，也没有数学、多模态、安全偏好等其他独立后训练阶段。

| 模型角色 | 初始化与训练输入 | 监督/参数更新 | 已披露训练配置 | 采集配置 |
| --- | --- | --- | --- | --- |
| 编辑 agent | Qwen2.5-Coder 7B/14B/32B；Sonnet-3.5-v2 成功 thought/action 轨迹 3,321 条 | **full SFT**；学习端到端探索、复现、修复、测试 | LLaMA-Factory；2 epochs；batch 8；LR 1e-5；warmup ratio 0.1；context 20K | Sonnet，T=0.2；≤40 steps；≤32K tokens/轨迹；≤10 min/轨迹；≤90 s/action |
| EB 测试 agent | Qwen-Coder-32B；Sonnet 测试生成轨迹 2,203 条，正负均有 | **full SFT**；目标为含约 M=10 多样测试的脚本 | 同框架；2 epochs；batch 8；LR 1e-5；warmup 0.1；context 20K | ≤40 steps；≤20K tokens；≤5 min/轨迹；≤60 s/action；本小节未单列采集温度 |
| EF 判别 verifier | Qwen2.5-Coder-14B；Sonnet 采集来源 + 已训 32B 采样；总计 5,700 条，正负平衡 | **LoRA rank 64**；由 issue、thought/action/observation、patch 预测 YES/NO | 同框架；2 epochs；batch 8；LR 1e-5；warmup 0.1；context 32K | 逐来源配比、采样温度/次数、独立环境数未给 |

来源：§3 p.4、B p.19、C.1 p.20、C.2 p.21。若正负完全平衡，5,700/2=2,850/类是算术推得，不是另列的原始采样数。论文称 Qwen-Coder base model 是“初始化模型”的用法；当前配置明确写 `Qwen/Qwen2.5-Coder-{14,32}B-instruct`，不要凭 base 一词改成 pretrained base checkpoint。

**保留与丢弃的不同用途**：编辑 agent 只学测试通过轨迹；失败编辑轨迹可以进入 EF 的 NO 类。测试 agent 使用包含失败的轨迹，原文只说 minimal rejection sampling，未定义失败类别、保留阈值或质量评分。不能统一总结为“三者都只学成功样本”，也不能说失败轨迹受到负梯度惩罚。

**训练 loss 的证据边界**：编辑模型训练目标明确包括 thoughts 和 actions，EF 的预测目标是 YES/NO；论文未列逐 token loss 公式、工具 observation 的实际 mask、assistant 序列边界、长轨迹截断/拆段策略或 token/trajectory/batch 归一分母。此处不从 LLaMA-Factory 默认值补写。没有本论文的 advantage、critic、KL、IS/clipping、动态 group、策略版本/staleness 配方；这些并非已披露 RL 的缺字段，而是本论文没有做这种训练。

## 4. 推理打分机制与诊断公式

### 4.1 EB、EF 和 hybrid 的严格含义

对同一问题 D 的 K 条轨迹 T_k 及补丁 P_k，执行验证 EB 包含两部分：生成复现测试计数，及已有回归测试过滤。论文 Eq.(1)（p.5）为：

\[
\mathrm{TestScore}_k=\sum_i\mathrm{Pass}(P_k,\mathrm{Test}_i),\qquad
s_k^{EB}=\begin{cases}
\mathrm{TestScore}_k,& RS_k=\max_{j\in[1,K]}RS_j,\\
0,&\text{otherwise.}
\end{cases}
\]

`Pass` 是单测试通过指示；`RS` 为 regression test score。**这是候选中相对最高回归分，不是全部回归测试绝对全过**；TestScore 是通过数，不是平均通过率。文字把非最高者叫“过滤”，公式却置 0；全零/并列时公式不独自规定如何选，当前代码用实际列表过滤，见 §7。M=10 是每份生成脚本的目标规模，不保证每条产物都生成十个有效且独立测试。

EF 不执行代码，输入完整轨迹和最终补丁，输出 YES/NO token 的相对概率（§4.1 p.6、C.2 p.21）：

\[
s^{EF}=\frac{P(\mathrm{YES})}{P(\mathrm{YES})+P(\mathrm{NO})}.
\]

概率来自对应 token 的 log-prob；这不是整条轨迹概率，也未证明概率经过校准。这里的 “reward model” 是 outcome-supervised 判别器用于推理排序，不是给编辑 policy 做 RL 的在线奖励。

混合 Eq.(2)（p.8–9）：

\[
s_k^H=\mathrm{Top}_n(s_k^{EF})+s_k^{EB},\quad
\mathrm{Top}_n(s_k^{EF})=\begin{cases}s_k^{EF},&k\text{ 属于 EF 前 }n,\\-\infty,&\text{否则。}\end{cases}
\]

先按 EF 取前 n，再做 regression filtering，然后按生成测试通过数、EF 连续分决定优先级。整数测试分使 EF 通常用于打破同分；论文未给 n 的具体值。官网将流程简写成“先执行过滤、再 EF 排序”，会漏掉前置 Top-n，不能替代 Eq.(2)。当前 C 的实现用 `n=len(candidates)//2`，是代码补充，不能写成 v1 已明示的超参数。

### 4.2 区分率和 toxic test：分母与方向

Appendix C.3 p.22 Eqs.(3)–(6) 定义：将候选补丁划为正确集合 P_c、错误集合 P_i，令 `Pass(p,t)`∈{0,1}：

\[
\mathrm{Distinguish}(t)=\mathbf1[\max_{p\in P_i}\mathrm{Pass}(p,t)\ne\max_{p\in P_c}\mathrm{Pass}(p,t)],
\]
\[
\mathrm{Toxic}(t)=\mathbf1[\max_{p\in P_i}\mathrm{Pass}(p,t)>\max_{p\in P_c}\mathrm{Pass}(p,t)].
\]

两种 rate 都是在同一问题的生成测试集合 T 上求和除以 |T|。注意它比较的是两类中的 **max**，不是任意正确/错误成对样本平均，也不是要求“所有正确通过、所有错误失败”。读者推论：若两类 max 都为 1，则此指标为 0，即使测试能区分部分个体；若错误类 max=1、正确类 max=0，则既 Distinguish=1 又 Toxic=1，所以**高区分率不自动是好信号**。P_c/P_i 为空如何处理、分析子集准确题量没有在该节给出。

§4.2 p.7、Fig.5–6：多数分析问题少于 20% 测试提供上述区分；少部分问题 toxic rate 可达约 10%，不是说“10% 的整个库有毒”或“总体错误奖励率 10%”。大量生成测试属于 Pass→Pass（原 bug 未被复现）或 Fail→Fail（连正确修复也不能通过，常因生成测试异常）；用于展示不同 test generator 的问题级分布，不是原始训练环境 F2P 接受率。

<a id="推理扩展与证据"></a>
## 5. Harness、运行时与全部附录案例

### 5.1 论文 rollout 时序和预算

论文在 OpenHands 之上设计轻量 ReAct scaffold（§3 p.4）；Appendix B 将实现称为 AgentHub。四个工具为 file editor、search、non-interactive bash、submit/finish。给环境和问题后，自主搜索、写复现脚本、编辑、测试、结束，无固定定位/修复流水线；**训练过程不提供互联网或浏览器**。这项声明不是对容器所有 egress/权限隔离的安全审计。

离线采集后测试保留成功轨迹，再交给 LLaMA-Factory；推理时编辑候选和测试脚本生成可分别运行，随后 EB 执行和 EF 排分、聚合并输出一个 patch。B/C 的 10 min、5 min 等是采集预算；论文没有完整逐项重列最终 benchmark 的全部 timeout/context/token 参数，不能无条件宣布评测完全同预算。

论文未给训练 GPU 型号/数量、GPU-hours、推理服务版本、训推 token 捕获、batch 并行布局、权重发布、异步队列、partial rollout/resume、KV/prefix reuse 或端到端吞吐。不能用当前 runtime 的 Kubernetes、vLLM 示例替它补上历史 fully-async RL 设计。

### 5.2 附录中不能省掉的具体案例

| 原文案例 | 内容与要点 | 证据边界 |
| --- | --- | --- |
| A，Listings 4–5，p.17–18 | PIL 的 thumbnail 在 draft 前 load 导致优化失效；aiohttp 同时含点和冒号的 route name 被拒。都含复现代码、expected/actual | 是生成 issue 示例，未给人工双盲准确率；PIL 描述直接提调用顺序，说明“不暴露解”的 prompt 仍需实际审计 |
| C.1，Listing 6，p.20–21 | 固定 Django starter：配置 SQLite/settings、`django.setup`、模型 app_label、建表/迁移和样本记录 | §4.2 称帮助约 2% 问题的 testgen 格式/领域知识；不是 SWE resolve rate 绝对 +2pp 的完整对照。Django 属测试域；这是公开通用 setup 示例，并非 repo-disjoint SFT 轨迹 |
| D.1，Listing 7，p.23–24 | SymPy PR #24661，`parse_expr(..., evaluate=False)` 与关系运算符、链式比较；打印 resolved/reproduced/other issues | 作者展示成功区分正确/错误补丁；中间六个测试被原文省略，不能凭示例恢复完整脚本 |
| D.2，Listing 8，p.24–25 | Django PR #13933，ModelChoiceField 错误信息是否含非法值，含临时模型、schema 建/删表和合法选择 | **作者明确写多数测试因未处理异常而失败，无区分力**。示例在非法值未抛异常的分支也打印 resolved：读者据代码指出其判据本身值得审计；这不是全库误奖测量 |
| C.4 Fig.13，p.23；§4.2 Fig.7，p.8 | 错误的 `sympy__sympy-24443` 轨迹，最高注意力的 2/4 个滑窗包含“已修复/成功”等 thought、工具动作及自建测试成功输出 | 可见判别器受轨迹线索影响；注意力图是关联性诊断，不是对话术因果影响的严格干预实验 |
| E，Figs.15–16，p.26–27 | `PolyElement.as_expr()` 忽略传入 symbols。搜索类→查看 `sympy/polys/rings.py`→写 reproduction→执行观察→修正无条件覆盖 symbols 的逻辑→再跑脚本 | 图中六阶段展示完整 thought/action/observation 结构；作者称成功例，但图未展示官方 grader 全套输出，不由自报成功推出普遍可靠性 |

## 6. 评测结果、负结果与因果边界

### 6.1 训练收益：单候选 Pass@1

Table 3 p.4 的 resolve rate（%）如下，原样保留误差值；论文未说明 ± 是标准差、标准误还是置信区间，也未清楚报告重复训练数。

| 规模 | Lite 初始化 | Lite SWE-Gym | Lite 本文 | Verified 初始化 | Verified SWE-Gym | Verified 本文 |
| --- | --- | --- | --- | --- | --- | --- |
| 7B | 1.0±1.0 | 10.0±2.4 | 11.0±0.8 | 1.8±1.3 | 10.6±2.1 | 19.0±1.0 |
| 14B | 2.7±1.9 | 12.7±2.3 | 20.67±0.7 | 4.0±1.6 | 16.4±2.0 | 26.8±1.4 |
| 32B | 3.0±1.4 | 15.3±2.5 | 23.77±0.8 | 7.0±1.3 | 20.6±2.1 | 34.4±1.2 |

SWE-Bench Verified 和 Lite 是最终外部评测，本文环境 Subset 按仓库避开 SWE-Bench test；无明确单独训练内 validation/checkpoint selection 方案。当前 C 的 Verified 示例用 test split 前 500 题并要求 official SWE-Bench harness 最终评分；论文表本身未给评测 revision、过滤清单或统一可复刻的评测命令，因此本文不从当前示例追认历史准确任务清单。Lite 的具体消费题量同样应由历史评测记录核实。

在同系列、同参数规模下，32B 相对 SWE-Gym 为 +13.8 **百分点**，相对初始化 +27.4pp；它们是系统配置下报告的成绩差。没有同时固定 SFT 数据量、教师成本、训练 token 和所有 harness 条件，不能将 +13.8pp 单独归因为“合成描述优于真实描述”。

更接近受控的两项消融（§3.1 p.4–5、Figs.2–3）：

- **数据量**：100、200、400、800、1,600、3,200 条轨迹；14B 到约 800 后趋于平台且非严格单调，32B 仍有边际收益，作者解释为更大容量。没有误差/算力匹配信息足以建立普适 scaling law。
- **真实 vs 合成问题**：各 400 条轨迹，28.0% vs 27.8%；支持该设置下相近，不是合成总体严格等效或优越的统计证明，也不能由此推出无需真实测试。
- **Thought 监督**：Fig.3 给 34.4% vs 去 thought 30.4%；相邻正文误写 34.2、并误引 Table 3。本文保留图/正文差异。该对照说明完整 thought/action SFT 有帮助，不证明显式 thought 对所有模型都是必要条件。

### 6.2 推理收益：候选覆盖率与选择能力必须分开

§4.2 p.6–7：编辑 32B 每题采 **26** 条候选，其中 1 条 T=0，余 25 条来自 T=0.8/0.9；两种非零温度各占几条未给。测试 agent T=0.8，采 **7 次测试生成**；结合 C.1 理解为测试 agent rollout/脚本，不是总共七个 unit tests。Fig.4 右图进一步变化测试 agent 0–7 次与编辑 11/16/21/26 次。

- **Pass@26=64.4%**：候选集合至少有一个正确解的 oracle 覆盖（§4.2、Fig.14 p.23）。它需要真实正确性标签识别，不能作为部署时选中率。
- **Best@K**：verifier 从 K 个候选中选出的那一个补丁正确的问题比例。Table 4 的 hybrid Best@16=49.4%、Best@26=51.0%；51.0% 与 64.4% 之间仍有选择损失。
- **单独 EB/EF**：§4.2、Fig.4 约 43.7%/42.8%，继续增加编辑候选的收益趋于平台。Fig.8 柱图写 43.8%/42.7%，§4.4 还出现 42.9%；小幅差异没有被文中解释，不能擅自统一。
- **K=1 图值**：Fig.4/14 曲线从约 32.0（Agentless 图 31.9）起，而 Table 3/4 Pass@1 为 34.4。混合温度采样池/聚合统计与单次评测的关系未完全交代，不能把曲线端点直接替代 Table 3。

评测是 SWE-Bench Verified，训练环境集不是该 benchmark 的随机训练 split；论文也未说明 verifier 分析使用的 Verified 子集准确大小。公开生成测试资产的当前 200 行（§7）不能反推整篇当年只评了 200 题。

### 6.3 Hybrid 消融、成本解释和历史榜单

| 比较 | 成绩/指标 | 可支持的结论与限制 | 原文 |
| --- | --- | --- | --- |
| 只用 regression 的 hybrid vs 加生成测试 | 47.4 → 51.0 Best@26 | 已有回归测试不能替代针对 bug 的测试 | §4.4 / Fig.8 p.9 |
| 官方 Agentless 测试 vs 专门测试 agent | 48.8 → 51.0 | 在该 hybrid 框架/产物下 agentic testgen 更强；不是等教师/训练总成本证明 | §4.4 / Fig.8 |
| 去 Top-n vs 有 Top-n | 49.8 → 51.0 | 预筛候选有益；“减弱毒性影响”是作者解释，未单独测介导因果 | §4.4 p.10 |
| 16→21 编辑 rollouts vs 加 5 测试 rollouts | 共同起点为 1 次测试；编辑方向 47.6→48.4；固定 16 编辑、测试从 1→6 次，正文称 49.3，图中对应点为 49.4（5 次为 49.1） | 保留图文差异；采样预算可分给测试 agent，横轴是 rollout 数，非等 token/GPU-hour | §4.4 p.9 / Fig.4 右 |
| EF 全输入 vs patch-only vs 去 thoughts | accuracy 71.82 / 68.01 / 68.77；Best@26 42.8 / 37.6 / 41.4 | 分别训练对应输入版本的 verifier，并非同一冻结模型推理时删输入；分类准确率与最终选中率不同，去 thought 也不等于删去全部轨迹 | §4.2 p.7 / Fig.7 p.8 |

作者说测试 rollout 通常比编辑便宜（p.9 脚注），但未给逐项 token/时长/美元成本，不能量化节省几倍。26 编辑 + 7 测试还须计算补丁×测试的执行、回归和 14B verifier forward，绝非“26 次总调用”；ReAct 的一次 rollout 本身就包含多轮 LLM/工具交互。

Table 4 是 2025 年不同系统的历史坐标：SWE-Gym-32B Best@16 32.0、SWE-RL-70B Best@500 41.0、DeepSeek-R1/Agentless 49.2、本文 51.0。不同模型、工具、搜索预算和训练方法不相同；“SOTA/与商业模型竞争”仅是作者当时的声明。表中 `Claude-3.6-Sonnet` 的名称与正文 Sonnet-3.5-v2 不一致，不能自行修成另一型号再比较；该论文不建立今天的榜单结论。

<a id="资产与复现"></a>
## 7. 当前开放资产与论文之外的实现信息

### 7.1 已核可访问资产，不下载权重或整套数据

2026-09-07 通过 HF 官方 API 读取元数据/文件列表，数字是 **当前卡片记录的 train 行数**，没有下载 parquet 逐行核验。完整 revision 与响应保存在 `sources/O03/hf_*.json`，由 [SOURCE_RECORD](sources/O03/SOURCE_RECORD.md)索引。

| 官方资产 | 本次元数据结果 | 与论文的关系 |
| --- | --- | --- |
| [R2E-Gym-Subset](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset) | train 4,578；rev `2e8108ff942f24fcb5686badfaf7f9a8808566d5`；Apache-2.0 | 对应论文主体 Subset 数量；仍未逐行证明内容是原实验集 |
| [R2E-Gym-V1](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-V1) | train **8,101**；rev `903d405799ac435061c41e72260c81ca5100f964`；Apache-2.0 | 与论文 8,135 不同；C README 提到的 `R2E-Gym-Full` API 返回 401，实际组织列表有 V1，未证明二者完全同一集 |
| [R2E-Gym-Lite](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Lite) | train 4,578；另有 9 个 dev split；rev `8d3163011f01f9393bb3dc7700497a79a8686ae5` | 这些 dev split 没有在 v1 论文训练协议中说明，不能倒填；Appendix B 还写 Lite 4,538，见 §8 |
| [编辑 SFT 轨迹](https://huggingface.co/datasets/R2E-Gym/R2EGym-SFT-Trajectories) | **3,231** 行；rev `63ab4eb37668f8be0104133c21d896bedbcf8404` | 论文 3,321；差异原因未知 |
| [测试 agent SFT 轨迹](https://huggingface.co/datasets/R2E-Gym/R2EGym-TestingAgent-SFT-Trajectories) | **2,281** 行；rev `0cfc507e195ff875fa622ab5cd4403d4a7409c46` | 论文 2,203；差异原因未知 |
| [EF verifier 轨迹](https://huggingface.co/datasets/R2E-Gym/R2EGym-Verifier-Trajectories) | **5,750** 行；rev `d8340c4605bb1a00a206a1978813cee35daeff8c` | 论文 5,700；差异原因未知 |
| [生成测试 patches](https://huggingface.co/datasets/R2E-Gym/R2E-TestgenAgent-Patches) | 200 行；rev `005f0eb8c80cb93f3cbfe8699590f752a1c514c3` | 当前执行脚本引用的测试产物；无法据此认定 500 题复现覆盖完整 |
| [32B Agent](https://huggingface.co/R2E-Gym/R2EGym-32B-Agent) | rev `b7b39e295ca764d57ae05b72122da9659e1731b3`；有模型分片、配置和 tokenizer 文件 | 可见权重文件，不等于已运行验证；组织还列出 7B/14B Agent |
| [R2E-TestgenAgent](https://huggingface.co/R2E-Gym/R2E-TestgenAgent) | rev `e91db21ab3069ac8f3fdcdc98c13046c5527be84`；有完整权重分片 | 正确资产名不同于 YAML 本地 output_dir |
| [R2EGym-Verifier](https://huggingface.co/R2E-Gym/R2EGym-Verifier) | rev `623145b2adfdfa3ed59063899480a568811bf5e3`；有 adapter 配置/权重 | 对应 LoRA 形态；并不是名为 `R2EGym-14B-Verifier` 的独立完整模型仓库 |

C 的代码许可证是 Apache-2.0；上述多数轨迹/模型 cardData 没有填写 license，不能把代码许可自动移植给所有资产和原始仓库。论文未逐项交代原始代码/测试授权处理；需要使用时按具体上游许可核对。

### 7.2 当前训练配置与复现入口的增量

以下只陈述 C 的静态文件，不宣称重跑过：

- `train/train_r2egym_32B_agent.yaml`、`train/train_r2egym_32B_testing_agent.yaml`、`train/train_r2egym_14B_verifier.yaml`（[目录摘录](sources/O03/official_repo/train/)）提供 SFT 入口；对应 `llamafactory-cli train <yaml>`。初始化明确为 Qwen2.5-Coder Instruct；编辑/测试 full，verifier LoRA rank 64、target all。
- 三者均 LR 1e-5、2 epochs、**warmup 0.05**（论文为 0.1）、cosine、BF16、FlashAttention2、Liger、Unsloth gradient checkpointing 开关；编辑/测试 cutoff 20,480，verifier 32,768；每设备 batch 1、accumulation 1。编辑/测试选择 ZeRO-3 offload，verifier ZeRO-3。未给启动 GPU 数/DP 布局，不能凭 batch 8 宣称用了八卡，也不能据开关算实测吞吐。
- `train/dataset_info.json` 是 ShareGPT messages 的 role/content 映射。没有固定 LLaMA-Factory commit，也没有显式 token loss denominator、`train_on_prompt`、packing/长轨迹策略等完整历史证据。
- `src/r2egym/agenthub/run/edit.py` 提供并行采集/评测入口；README 示例 54 workers、编辑采集 T=0.2、40 steps，评测 T=0、40 steps，输出轨迹/patch 后再用官方 SWE-Bench harness 评分。样例 worker 数不等于论文训练资源。
- C README 的 quickstart config 路径仍写缺少 scaffold 子目录的 `src/r2egym/agenthub/config/edit_fn_calling.yaml`；实际相应配置在 `src/r2egym/agenthub/config/r2egym/edit_fn_calling.yaml`。此外文档提到的 `src/r2egym/agenthub/runtime/runtime.py` 已对应到 `src/r2egym/agenthub/runtime/docker.py` 等。复现需按实际文件，不能只复制 README。

### 7.3 环境 reward、推理聚合和静态复现风险

C 的 `src/r2egym/agenthub/environment/env.py::RepoEnv.calculate_reward` 每步返回 0；最终用 `RepoEnv.compute_reward` 调 runtime。`src/r2egym/agenthub/runtime/docker.py::_calculate_reward_r2e` 执行测试、解析并规范化 test-name，再与 `expected_output_json` 比较：长度一致且所有非空解析键的预期状态相符即给 1，否则给 0；缺数据字段时会读容器内 `expected_test_output.json`。函数跳过空字符串键，本身未拒绝双空映射（双空会给 1），也不把返回的 `error_code` 作为独立拒绝条件。这些是静态边界，不表示当前数据实际包含双空记录或论文已发生误奖。该逻辑不等于“所有测试必须 PASSED”，而是匹配期望状态映射；与 SWE-Bench 专门评分分支要区分。这只是当前代码提供的可计算 reward，并非本论文用它完成了 RL。

`src/r2egym/agenthub/verifiers/create_bestofn_aggregate.py::run_hybrid_verifier` 当前确实按 **EF 前 floor(K/2) → 最高 regression → 最高 reproduction → 最高 EF** 过滤；`run_eb_verifier` 则直接从回归分最高候选中最大化 reproduction score。`K=1` 会令 hybrid 的列表为空，因此它不是开箱即用的任意 K 实现；论文 Eq.(2) 本身也没规定单候选特例。

`src/r2egym/agenthub/verifiers/run_reproduction_tests.py::run_test_patch` 先施加测试 patch 和候选 patch，运行 `python3 test_issue.py -v`，以输出中 `resolved` 的出现次数计分；内部异常可返回 0，外层 `process_single_task` 默认最多 3 次总尝试（首次加最多 2 次重试），每次 `join` 超时为 600 s；终止清理与退避另有开销，最终仍可记 0。这种当前脚本行为不能当作论文完整失败过滤协议，也不能直接当在线 RL 的模型失败/infra 失败分类。

同一文件的 `add_reproduction_tests` 把结果按 `(docker_image, test_index)` 存储，未包含候选 patch 身份；**若一次输入含同一环境的多个候选**，后来的候选结果会覆盖前者，然后给该环境轨迹回填同一组分数。这是静态可见的条件性复现风险，本次未运行复现，不声称论文当年数据遭此错误。

`src/r2egym/agenthub/verifiers/run_ef_verifier.py::process_trajectories_to_verifier_format` 两次按 `as_completed` 追加数据/概率，最后与原轨迹 `zip`，没有保留原索引；**并行完成顺序不同**时存在标签错配路径。其 `run_model` 还固定取第 5 个生成 token 的 top-20 logprobs，YES/NO 缺失回填 -10000。若两者都缺失，直接指数运算会下溢并形成 0/0 非有限分数路径，不是稳定的默认概率；这是静态风险，未实测触发。`src/r2egym/agenthub/verifiers/prepare_ef_verifier_input.py::traj2verifier_data` 则使用 `<judgement>` 格式并调用 `deepswe_condense_thoughts`。这些是当前版本的概率位置、输出格式、长上下文与候选身份检查点，不应省略成“公开脚本保证复现”。无需据此扩展为完整源码审计或修改外部实现。

### 7.4 成本口径

| 成本项 | 已有证据 | 尚不能得出的结论 |
| --- | --- | --- |
| 环境生产 | 半人工历史依赖搜索；当前 README 称单镜像约 300–500 MB | 没有全流程 CPU/人工/API/存储账，也未实测镜像大小/层共享 |
| 教师轨迹 | 上述三类保留样本数和部分采集上限 | 无失败尝试分母/总 token/美元成本，不能由成功条数算总预算 |
| SFT | epochs、batch、LR、context；当前优化配置 | 无 GPU 型号、数量、时长、训练 token；不构成八卡低成本复现证明 |
| 推理扩展 | 26 编辑/7 测试和 EF 排序机制，部分减少 rollout 的对照 | 没有等 token/等 GPU-hour 的端到端成本曲线，不能将 Best@26 当 Pass@1 成本 |

## 8. 未披露项与文本矛盾汇总

| 关键问题 | 查阅范围与结论 |
| --- | --- |
| 4,578 vs 4,538 | §2–3、Table 1/2 是 Subset 4,578；B p.19 称 Lite 4,538。TeX `appendix/training.tex` 也写 4,538，非 PDF 解析错误；当前 Subset/Lite train 元数据都是 4,578，仍不擅改历史正文 |
| 3,321/2,203/5,700 vs 3,231/2,281/5,750 | 原文 B/C 与当前三个 HF 卡片不一致。已分别记录，未有逐行差异或发布说明可解释变化 |
| 8,135 vs 8,101 vs >8.7K | 分别是 PDF 完整集、当前 V1 card、arXiv 摘要网页。没有证据把它们视为相同口径 |
| warmup 与 thought/EF/EB 数字 | PDF 0.1 vs 当前 YAML 0.05；thought 34.2 vs 图 34.4；EF/EB 的 42.7/42.8/42.9 和 43.7/43.8；追加测试采样正文 49.3 vs Fig.4 对应点 49.4；均保留各自位置 |
| 生成/验证漏斗 | §2、A、当前生成指南：未给原始 commit 总数、各过滤损耗、生成测试比例、judge 准确率、每任务重采次数、失败成本；Appendix A 的 issue backtranslation 和 gold-conditioned reproduction testgen 也未披露实际模型/每 commit 采样预算，不能把 Sonnet 轨迹教师或当前指南 o1-mini 移植过去 |
| 长轨迹与 SFT 实际消费 | B/C 与三个 YAML：32K 采集到 20K 编辑训练怎样截断/拆分、mask、loss 分母、实际消费 token/轨迹缺失；不能由当前框架默认推回 |
| Benchmark 选择与误差 | §3.1/§4/图表、B/C：未完整说明 checkpoint selection、±/阴影定义、seed/重复、子集名单、混合温度分配、Top-n 历史实参 |
| 评分可信与失败类别 | §2、A–D；静态 runtime/verifier 路径：缺全库替代解、重复稳定性、隐藏材料/测试控制面审计；当前脚本会混合部分错误与零分，但非论文明确 RL 处置 |
| 通用 RL/OPD infra | 全文与全部附录没有自身在线 RL、OPD、异步训推、版本/staleness 实验；README 的 DeepSWE 指引属于后来的独立工作，不回填 |
| 资源与可复现性 | 全文、附录、当前配置/资产：缺论文训练硬件、总时长、API 总成本、原训练框架 pin；本次没下载镜像/权重、没运行训练/benchmark |

原文有数处交叉引用笔误：Subset 分布写 Fig.2，实在 Table 2；§4.4 多处写 Fig.5(right)，实际消融位于 Fig.8；Fig.7 总图注误写 execution-based，分析对象是 execution-free。本文按真实图内容定位，不沿用错号。TeX 包含已注释的旧配置/标题，不把这些当额外正式结果。

## 9. 旧稿更正与证据界限

旧稿的环境链、SFT 与 51% 区分可以保留；此次不是把旧稿推翻，而是补足可查证的训练与评测细节：

1. 补充 **测试 agent 2,203 条正负轨迹的 full SFT** 与 **EF 5,700 条平衡数据、LoRA rank 64**，以及各自不同的 context/timeout。旧稿只写编辑 SFT 容易让人忽略两个训练产物。
2. “多数测试无区分、个别 toxic 约 10%”必须带 Appendix C.3 的 max 公式和每问题测试分母，不能当全库审计率；也不能据此直接推断某题对 GRPO 有学习收益。
3. 旧稿“Prime 重新验证只保留 4,522/4,578、镜像测试可读”属于**后续外部审计**，不是 R2E-Gym 论文事实。本次没有独立复核该 Prime 来源，不在本文把这个数升级为已核结论；可保留为另查线索。
4. 当前公开资产的行数、路径与训练配置差异已实查；旧稿没有这些复现限制，不能凭原论文数字假定下载所得就是原训练数据。

<a id="项目映射与审查"></a>
## 10. 对 RepoHarness 项目一的有限映射

映射日期 2026-09-07；读取主资料目录实际 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`，miles 集成目录实际 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`。参考 [CURRENT-STATE-BRIEF](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)（2026-09-05）和 [项目一建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)（建议而非批准）；后者补充 09-06 审查所指出的 token 覆盖、失败归因和当前消费正确性缺口，不能只依据旧简报说链路已经全闭合。没有以本 worktree 默认分支替代 miles 当前状态。

只核对相关实际文件：`rh2/src/repoharness2/envpack/training_view.py` 的 `TrustedTaskController/RolloutTaskView`，`rh2/src/repoharness2/grading/trusted_projection.py` 的评分控制面说明，`rh2/src/repoharness2/adapters/miles/group_admission.py` 的组准入职责；没有做全仓审计。

| 候选借鉴 | 来源依据 | 上游已有/我方增量/暂不适用 | 最小验证与成本 |
| --- | --- | --- | --- |
| 优先复用现成环境，再做小规模 commit→F2P→反译补充 | §2/A 的生产链及半人工限制 | 任务来源/开源环境是外部资产；rh2 增量是目标执行环境与评分边界适配，不先重建 SWE-GEN 平台 | 少量跨仓库任务跑真实 no-op/gold/重复测试，记录可构建、可评分和失败成本；无效环境不能按模型失败记账 |
| 把完整数据记录拆成公开问题、私有评分与金标材料 | 生产阶段可见 gold，HF 含 `parsed_commit_content/prompt/expected_output_json` | rh2 已有 `training_view.py` 的公开/host 视图理念；当前 source 类型仍是 `swe_gym_lite`，**不是已支持 R2E ingestion** | 若采用 R2E，明确字段语义和测试控制文件，真实检查 solver 可见面；沿用现有控制器，不另建资格证书系统 |
| 评分检查关注错误补丁与合法替代解，而非只看 gold | Eq.3–6、D.2 的异常反例 | 属 rh2 应用层质量验证；fresh grader 已有，但 `trusted_projection.py` 明示通用 pytest/plugin 控制面尚有边界 | 小批 no-op/gold/alternate/不完整修复，在固定测试集分别报 survival、区分与毒性，勿将测试通过冒充需求完整 |
| 完整轨迹 SFT 可作有竞争力初始化/对照 | §3/B 的单候选改进 | 训练内核归上游；是否需要 SFT 取决于目标模型工具能力与失败诊断 | 固定 checkpoint/harness/预算比较初始化与 SFT；若后续 RL，增量从直接 SFT 初始化计，不能把 SFT+搜索收益全归 RL |
| 测试 agent/EF 只作条件性的评测候选 | §4 的混合排序提升与局限 | 暂不应替代首训终局可执行 reward，更不直接把 EF 分数塞入 GRPO | 若确需提高推理选择质量，在 dev 比较等预算编辑重采与测试重采；新增 32B/14B 服务和执行交叉成本要入账 |
| 不从“有正负”推出必须保留所有失败进任何目标 | 编辑成功 SFT、测试含负 SFT、EF 平衡数据的差异 | rh2 `group_admission.py` 的 GRPO 组准入不是 SFT 标签过滤；staleness 仍由 miles consume-time 承担 | 按目标分别统计环境/系统失败、模型失败、实际消费；论文不支持新增 RL group filtering 或 staleness 定案 |

[本项目历史 prefix 检查](../../../agentic_RL/repo_harness_rh2_workstreams/data_freeze/r2e_prefix_check.md)只在 2026-07-07 核了 orange3、coveragepy、numpy 三个镜像的 Git/文件状态：数据 commit 指修复提交，镜像工作区是父提交；没有运行项目测试，且记录修复提交在 Git 历史中存在。它支持“字段语义需查实”，**不证明全库 F2P、隐藏答案不可读或当前 target Linux 可评分**；本次没有重跑该检查。

简历可借该论文解释环境生产与评分质量为何重要，以及为何要区分 SFT、RL 和推理预算。RepoHarness 自身贡献必须由自己的真实评分、训练消费、成本和 held-out 实测支撑；不能把 34.4%/51% 或论文 8,135 题写成本项目成果。

## 11. 快速定位与关联阅读

- 环境和漏斗 → §2；原文 §2、A p.15–18。
- 三个训练模型/失败保留 → §3；原文 B、C.1–C.2 p.19–21。
- reward/reranking 公式 → §4；原文 Eqs.1–6 p.5、8、22。
- rollout、所有案例 → §5；原文 B、C.1、D、E，尤其 p.26–27 图像。
- 训练与搜索增益 → §6；原文 Tables 3–4、Figs.2–8/14。
- 资产/配置差异 → §7–8、[来源记录](sources/O03/SOURCE_RECORD.md)。
- 关联：O02（SWE-smith，任务 11，尚不链接未交付稿）；已完成的 [CalibForge](E2_calibforge.md)可比较离线 SFT 和任务校准，[miles](N11_miles_agentic_rollout.md)可区分上游 rollout/消费能力；本篇不替代它们。

## 12. 独立检查与修订记录

本任务主线程 `01a07827-1e42-70f2-ac37-48ca0e1af7a7`，实际 GPT-6 Astra / high（主线程已核验配置）。唯一审查子 agent `01a0782e-169c-7b10-939b-bff6f99d0f9a`，canonical `/root/review_o03`，调用参数 GPT-6 Astra / high / `fork_turns="none"`。原文为 arXiv v1（2025-04-09）；被审固定副本 [O03_r2e_gym.draft_20260907.txt](sources/O03/O03_r2e_gym.draft_20260907.txt) 在审查期间未改动。

2026-09-07 已收到完整独立审查：[12_O03_review.md](reviews/12_O03_review.md)。审查者先读原文全部正文/A–E 附录，再对照初稿、关键原图和当前代码/HF 元数据；确认覆盖充分，提出四项必改、两项建议，均已处理：

- **R1**：§6.3 明确 EF 输入消融分别重训模型，而非同一冻结 verifier 的输入删除干预。
- **R2**：§6.3/§8 补 Fig.4 与正文差异：测试从 1→6 次，正文 49.3、对应图点 49.4。
- **R3**：§7.3 修正为最多三次总尝试，每次 join 600 s；清理/退避开销另计。
- **R4**：§7.3 精确描述 reward 非空键匹配、双空映射和未独立使用 error_code 的静态边界。
- **S1/S2**：补 EF YES/NO 同时缺失的非有限概率风险；集中补生成模型和每 commit 预算未知。

同日由同一审查者完成六项定点复核，确认均准确落地且未发现新问题；这不是第二次全文审查。

这些修订没有改变三种 SFT/推理扩展的核心结论。残余未披露项见 §8；对当前代码的条件性路径没有冒称运行复现或论文历史错误。附件比对、相对链接和发布一致性另作交付检查，不替代技术审查。
