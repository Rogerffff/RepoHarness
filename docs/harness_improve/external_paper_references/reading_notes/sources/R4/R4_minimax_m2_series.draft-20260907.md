# R4 The MiniMax-M2 Series：后训练与项目一精读

MiniMax-M2 系列以约 10B 激活的 MoE 为底座，经多领域轨迹生产、interleaved-thinking SFT 和分阶段的混合领域 CISPO RL，发展到 M2.7。报告最有用的部分是把真实工作空间、按产物选择 verifier、请求级策略动作及训练系统解耦放在同一流程中；覆盖 SWE、应用开发、terminal、搜索、办公、金融表格、幻灯片、推理、对话和角色扮演。Windowed FIFO 与 prefix tree merging 提供系统设计依据，但最高 40 倍是训练侧局部声明，不能换算成端到端 RL 加速。M2.7 多数评测提高，MMLU-Pro 却低于 M2.5；训练关键配置和若干图文口径仍未闭合。

导航：[来源与覆盖](#source) · [全流程与数据](#data) · [CISPO 与奖励](#algorithm) · [Forge 与 token 边界](#infra) · [评测与负结果](#evaluation) · [项目映射和审查](#project)

<a id="source"></a>
## 1. 来源、版本和完整覆盖

正式标题为 **The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence**，机构/团体作者 MiniMax；个人贡献者见附录 A。阅读日期 2026-09-07。

- 本地主资料指定 PDF 是 **arXiv:2605.26494v1，2026-05-26，35 页**，见[固定 PDF](sources/R4/source.pdf)及[官方 v1](https://arxiv.org/abs/2605.26494v1)。本文 p.n 使用 PDF 物理页，p.2 起与印刷页码相同；首页按 p.1 计。
- 当前官方版本是 **v2，2026-07-30，35 页**：[官方 v2](https://arxiv.org/abs/2605.26494v2)、[固定 PDF](sources/R4/source-v2.pdf)。已下载两版官方 TeX，并逐文件比较；仅 `app.tex` 改变，新增贡献者并将 Lunbin/Qunhong 的 Ceng 改为 Zeng。`main.tex`、`intro.tex`、全部 `section/*.tex`、`eval.tex`、`conclusion.tex`、图表资产和文献文件相同。PDF 提取文本差异仅首页版本水印和附录名单排版，见[版本差异](sources/R4/version-diff.txt)。因此后训练、环境、infra、评测和全部附录均已覆盖当前版本；没有新增技术内容要另补。
- [v1 TeX 入口](sources/R4/tex/main.tex)递归包含架构、预训练数据、后训练数据、SFT、RL、agent mechanism、评测、结论和 `app.tex`。源码用于核对公式及目录，**不是训练实现代码**。本次未查 Forge 内部源码；不借 M1 或配套博客补齐实现。
- N10 是 2026-02-13 独立官方文章，针对 M2.5；其 200k、样本吞吐、黑盒 reward 曲线等见[N10 笔记](N10_minimax_forge.md)，不合并为本报告实测结果。

先按原文结构阅读，再对照旧稿。覆盖表的页码也适用于 v2。

| 原文目录/图表 | 深度与主要内容 | 本文位置 |
|---|---|---|
| 摘要、§1，p.1–3；Fig.1 | 全读；系列定位、三项贡献、headline 结果，回看首页图 | §2、§7 |
| §2.1–2.2.1，p.3–4；Table 1 | 架构概要；细粒度专家与 MTP 小规模消融 | §2、§7.3 |
| §2.2.2，p.4–6；Tables 2–3 | 全读注意力选择及 SFT 后长上下文负结果 | §2、§7.3 |
| §2.3，p.5–7；Fig.2 | 全读 MTP 复制初始化、冻结/联合训练与推测解码 | §2、§6.4 |
| §3，p.6–7 | 概要；数据组成与 8K→32K→192K 延展 | §2 |
| §4.1.1 SWE，p.7–9；Fig.3 上半 | 全读六阶段与任务类型对应验证器 | §3.1 |
| §4.1.2 AppDev，p.9–11；Fig.3 下半 | 全读专家 query、prompt distillation、三层 AaaV | §3.2 |
| §4.1.3 Terminal-Gym，p.11–12 | 全读来源过滤、环境修复、hint 演化与难度校准 | §3.3 |
| §4.2.1–4.2.4，p.12–14 | 全读搜索、办公、金融/表格、幻灯片四条管线 | §4.1 |
| §4.3–4.5，p.14–16 | 全读推理、多轮对话写作、role-play/RLHF | §4.2–4.4 |
| §5，p.16 | 全读 SFT 与 interleaved-thinking 冷启动 | §2、§5.4 |
| §6.1.1–6.1.6，p.16–19；Eq.1–7 | 全读生成接口 MDP、CISPO、奖励、混合领域课程 | §5 |
| §6.2.1–6.2.6，p.19–23；Eq.8，Fig.4–6 | 全读 Forge 三层、黑白盒、Windowed FIFO、训练前缀合并、三项推理优化 | §6 |
| §7.1–7.2，p.23–26；Eq.9–10，Fig.7–8 | 全读思考状态保留、自演化系统及人机决策边界 | §5.4、§7.4 |
| §8.1–8.3，p.25–30；Table 4，Fig.9–10 | 全读全部评测、预算、系列演进、MLE 案例；原页核表与图 | §7 |
| §9，p.30–31；References p.31–34 | 结论全读；文献用于识别来源，不将引用论文视作已精读 | §8 |
| Appendix A Contributors，p.35 | 查全；只有名单，没有隐藏技术附录 | 本节 |

所有十幅图和四张表均已检查；Fig.1/9/10 的结果口径差别见 §7。未把排版残留或 TeX 注释当实验事实。

## 2. 底座、阶段链与模型关系

**原文事实。** M2 是 62 层 decoder-only Transformer，总参数 229.9B、每 token 激活 9.8B；hidden size 3,072，词表 200,064。每层完整注意力，48 query heads / 8 KV heads 的 GQA；256 个专家、每 token 选 8 个，sigmoid gating 与可学习专家 bias。它不是 MiniMax-Text-01/M1 的混合 Lightning Attention 架构，不能继承旧模型的配方。预训练总 29.2T tokens，包括 constant phase 19.9T 和 decay phase 9.3T；上下文从 8K 经 32K 扩展到 192K。语料涵盖 web、书籍、学术、代码与 QA，提升代码/数学/STEM 权重，长上下文用代码拼接、长 PDF 和主题相关 packing。（§2–3，p.3–7）

已知依赖关系为：

1. 预训练/continued pretraining 建立底座；MTP 初始一个模块，loss 权重 0.3 衰减到 0.1。continued pretraining 的 decay 阶段复制主模型权重扩成三个模块，先短暂冻结主模型、只训 MTP，稳定后联合训练。持续只训 MTP 的最终质量较差，随机初始化也比复制初始化收敛慢并暂时损害主模型。（§2.3，p.5–7，Fig.2）
2. 领域数据经 rejection sampling 与多阶段清理，构成 chat/reasoning/code/cowork 四类 SFT 语料；SFT 学习思考、动作、观察交替的轨迹，为 RL 冷启动。（§5，p.16）
3. RL 使用 CISPO，在**多个训练阶段中的每个阶段同时混合** reasoning/coding/agent/general，跨阶段调整领域比例、各领域 context 和难度。（§6.1.6，p.18–19）
4. M2→M2.5→M2.7 是公开 checkpoint 的系列演进。报告没有给每个版本逐阶段的 checkpoint 血缘、SFT/RL token 预算，也没有披露先训多个 policy experts 再融合的方案。轨迹由轮换的强 teacher 产生，不等于 token 级 OPD；MTP 的 top-K KL 是另一条辅助训练机制。（§4.2、§6.2.6、§8.2）

**作者解释。** 以高可信 reward 和数据覆盖提升真实任务能力，比仅扩大激活参数更重要。**阅读者判断。** Table 4 是最终系统的横向/纵向表现，未隔离 SFT、RL、数据、harness 或自演化各自贡献；不能把所有 M2.5→M2.7 提升归给 CISPO。

<a id="data"></a>
## 3. Coding / SWE / terminal 任务生产

### 3.1 SWE：真实 PR 到按任务类型验证

来源是采用宽松许可的公开 GitHub 仓库，采集 PR、关联 issue、diff 和测试；规则筛选已合并 PR 及相关测试。六阶段为采集过滤→逐 PR Docker 环境构建→任务类型 tagging/routing→测试 reward→模型检查题意与测试一致性→任务转换扩增。Fig.3 把最终数据集画为第七个节点，它不是额外的第七道过滤。（§4.1.1，p.7–9；Fig.3）

环境 agent 用专家知识和执行反馈迭代修复构建脚本。非 Python 环境较不可靠，难点包括 Java/Go/Rust/C++ 工具链版本、异构测试接口、仓库结构和依赖定位。报告称覆盖 **十余种语言**，但没有逐语言构建成功率。（p.8–9）

| 任务类型 | 构造/接受信号 | 必须保留的边界 |
|---|---|---|
| Bug fix | 提取 F2P/P2P；golden patch 通过后认定任务有效；solver sandbox 同时验修复与回归 | 没有完整 no-op/替代合法解/评分隔离协议 |
| Feature addition | 抽新功能测试点，要求 golden patch 通过 | 新测试可依赖新代码，不能机械套 F2P/P2P |
| Performance optimization | 用 P2P 测试确认行为稳定且性能差异稳定、显著 | 未给性能重复数、显著性阈值或资源控制 |
| Bug injection / commit merging | 注入额外 bug；合并相邻 commit/PR 增加多步复杂度 | 每次转换后重新验证的完整门槛未列 |
| SWE-Test | 让 agent 写在 pre-patch 失败、post-patch 通过的测试 | 训练动作是写测试，不能当修复轨迹统计 |
| Code review | 静态看改动、找潜在缺陷；第二个 LLM 检查一致性 | 原文明确不需要 runnable environment，只有近似可验证性 |

模型还检查描述与测试一致性，补足信息，使题目自洽可执行。这是质量改写，不是已证明不会泄漏参考解。报告末称每个 SWE instance 含题意、测试 reward 与 Docker，需与 code review 的无运行环境例外并读，不把概括推广到所有变体。（p.9）

### 3.2 AppDev：专家先验与可交互 verifier

AppDev 从零搭建完整应用，涉及 frontend/backend/mobile/desktop/simulation。专家贡献 **meta queries、种子分布、生成 system prompt、评价 rubric**。meta query 指定技术栈与架构约束，从 UI 库、CSS、构建工具、SaaS 与场景种子采样，高温 LLM 扩写具体需求；MinHash 去近重复，LLM 按技术栈合理性、功能可实现性、需求清晰度过滤，阈值未给。专家用下游质量反馈修整模板。（§4.1.2，p.9–10）

生成 prompt 包含功能完整、代码完整、内容真实性和审美指导，并鼓励先规格、TODO、测试、自验证与 skills 使用。作者举早期模型滥用模板式渐变背景为待矫正行为。**Prompt distillation** 的具体披露是采样时给完整指导、训练时选择性删除部分指导，使行为内化；没有公开 teacher/student KL 或 token 概率匹配目标。（p.10）

AaaV（Agent-as-a-Verifier）在 sandbox 部署应用，按专家 rubric 用工具主动交互，每项二值 pass/fail 并要求证据：

- 执行层：文件与语法、依赖安装、构建和服务启动、HTTP 状态、加载时 JS 错误；失败立即拒绝。
- 交互层：Playwright 检查元素、按钮/表单、核心流程端到端完成和状态变化。
- 视觉层：布局、层次、配色和设计质量。

各层总体通过率作为 rejection sampling reward，执行层是硬门槛。不是只看截图/静态代码的普通 judge；但 rubric 权重、阈值、误判率未给。该体系作为后续 RL 的任务/奖励基础，不能把所有采样过滤自动视作线上 RL 过程奖励。（p.10–11）

### 3.3 Terminal-Gym：先真实问答，再演化题目和环境

以完整 Stack Overflow 数据集为原始来源，按时间重建帖子，去掉无 accepted answer、低分、过长问答，按 tag 保留终端操作、系统配置、调试、脚本等。标注质量、任务类别、可验证性、复杂度、环境/执行特点，仅保留可脚本化、适合 terminal、可验证、Linux/Docker 相关且难度适中的帖子，清噪并选择一个高质量答案。时间范围、许可处理、各阈值未披露。（§4.1.3，p.11）

问答被改为结构化任务，明确环境、工具、输入输出与成功标准；按可测试性、完整性、清晰度分四档，仅留前两档。任务含自然语言指令、必要文件/脚本及预期终端行为。后续三阶段：（p.11–12）

1. Agent 合成 Dockerfile 与测试脚本；执行失败返回结构化诊断，迭代修复到通过或达到最大重试数。**确有重试上限，但数值未给；这是环境合成，不是 RL rollout 重试策略。**
2. 有控制地抽象/删除显式 hints、路径和预期环境输出，同时保持语义。所有变体用同一套 LLM 生成测试，避免只适配提示写法。作者称有效，但本文未给量化消融。
3. 排除过易任务，偏好 hints 少且 zero-shot pass rate 低的变体，并参考 reference solver 历史通过率与环境修复次数。solver 身份、每题重复数、接受区间未给；不能把低通过率当已证有效/可学习。

Anything2Docker 和 CVE-Factory 扩展是后续方向，本报告没有其完整新管线或独立实验，不能算已完成的额外精读来源。

### 3.4 数据漏斗与失败边界

| 对象 | 本报告实际可知 | 不可据此声称 |
|---|---|---|
| 原始仓库/PR、有效环境、验证任务、最终采样轨迹、RL 消费轨迹 | 流程和十余语言；各环节数量均未给 | N10 的十万量级不是这里的最终 SWE 题量 |
| 已知失败淘汰 | AppDev 执行失败；低质量 query；terminal 合成超重试限制、过易/不合规格 | 所有 infra 失败为 reward=0、整组丢弃或无限补采 |
| 测试可信性 | golden patch、F2P/P2P、交互证据、题意核对 | 完整抗作弊、隐藏测试隔离、flakiness/替代解审核已实施 |
| 去重/污染 | SWE 宽松许可；AppDev MinHash；其他领域有清理 | 全局 repo/time split、benchmark 去污染、SWE 测试不可见性已证明 |

## 4. 其余后训练领域：完整保留

### 4.1 Cowork 的四条管线

共同原则是 runnable workspace、轮换强 teacher、刻意扰动 scaffold、按产物格式选择 verifier。对非机器可验证结果，多个候选在**推理/动作轨迹和最终产物**两轴作 pairwise 比较，再 rubric 严筛。这里的蒸馏是轨迹来源描述，teacher 名称/采样成本/具体学习目标未给。（§4.2，p.12）

| 领域 | 任务生产 | 通过标准与鲁棒性 |
|---|---|---|
| Deep search / open web | seed question 经 guide-and-rewrite 与实体隐去逐渐变难；开放报告题另设 rubric | 必须基于实际检索证据，不能以模型记忆替代；报告评价事实、透明度、不确定性、风险披露；轮换 teacher、扰动工具布局（§4.2.1，p.12–13） |
| Knowledge-worker office | 从 GDPval 筛 harness 可支持的 canonical tasks；按公开职业分类细分行业/地区/文化，再合成任务、真实支持文件、多精细程度 query 和产物规格 | rubric 含正/负行为、严重错误、地区适当性、推理深度；typed cleanup 去捏造数据/引用/实体（§4.2.2，p.13） |
| Financial tools | 先执行真实工具获得 trace，再反推由工具输出蕴含的任务与答案 | evidence-driven 合成，覆盖检索/计算/推理；多 scaffold 采样（§4.2.3，p.13–14） |
| Spreadsheet | seed workbook 上走原子操作，回收中间状态为新 seed；由轨迹推答案，再由答案推问题，改写表述/难度 | 执行产物、外部引擎重算公式、与 gold workbook 比 cell value；允许形式变体时改用 rubric/agent judge。覆盖一般/竞赛操作、PE/VC/M&A 建模、半结构资料还原（同上） |
| Slides | 两条流：源文档→不同粒度/语言要求的 deck；真实 deck→元素/页/全文件编辑，变化内容/风格/结构与复杂度 | teacher 偏好视觉质量；执行、agent 功能、规则布局、渲染后视觉评分叠加；混不同生成库避免工具库过拟合（§4.2.4，p.14） |

**污染边界。** 报告明确把 GDPval seed 用于训练数据，又评 GDPval-AA；没有给 seed 与测试去重/拆分的可审计说明。这个事实构成评测独立性缺口，不能据此直接判定发生具体污染。视觉 verifier 和多模态办公评测也不等于报告披露了 M2 视觉编码器或完整多模态后训练配方。

### 4.2 推理数据不只扩 query

§4.3（p.14–15）同时扩三轴：query 扩展覆盖稀缺难度与错误分析发现的弱技能；同题多条正确 response 扩大解法空间，作者观察收益主要体现在 OOD；固定训练算力下调 query/response 比例，并按阶段、难度饱和和当前弱项动态分配。质量检查分别覆盖 query 标记和 rollout 交叉比较、verifier 边界 case 分析、多模型答案分歧核错、推理轨迹 rubric。未给各轴数据量、预算、曲线或受控增益，不能推出“多 response 总优于新题”。

### 4.3 通用对话、写作与工具使用

§4.4（p.15–16）用高质量长 CoT 保留通用能力并冷启动 RL。写作强调风格，并接文件系统读写实际文档；简单 QA 在多个候选中做偏好质量选择；多轮强调跨轮一致性、指令/rubric 遵循和长上下文跟踪。工具增强与无工具样本并存，前者用代码解释器/搜索，后者保留独立推理；规则和模型 verifier 加系统质量检查。未单独披露 DPO 配方或 preference reward model 训练过程。

### 4.4 角色扮演、RLHF 与安全披露边界

§4.5（p.16）将 role-play 表述为用户偏好条件下 Worlds×Stories 的长程生成，保持物理、叙事和风格一致性。Role-Play Bench 用多轮 self-play 对失角色、逻辑错误等具体失配扣分，作者称离线指标与线上互动相关。数据来自风格多样 expert 的大规模 self-play，四轴 dispersion sampling、Best-of-N 和周期性片段 judge 重写防模式坍缩；**四轴具体定义未在本报告展开**。

该领域明确提 RLHF：从真实产品隐式/显式反馈出发，用因果推断和分层去偏降噪，监测 entropy 防 reward hacking；没有给 estimator、干预设计、reward 数值或效果表。安全相关还散见真实证据要求、去捏造、CVE 方向和自演化 harness guardrails；**无独立全面安全对齐、拒答、红队评测或安全 RL 配方章节**。不能将 persona 对齐等同完整安全对齐。

<a id="algorithm"></a>
## 5. 训练目标、token 与信用分配

### 5.1 动作边界与 episode

把 LLM 当 policy，模型生成接口之外的工具、memory、上下文变换、分支和 sub-agent 调度都归环境。一次 action 是**一次 LLM completion**，可含 reasoning、工具调用、CM 请求或 sub-agent 通信；state 是本次实际呈给模型的内容，下一状态为 `s[t+1]=f_trans(s[t],a[t],o[t])`（Eq.1，p.17）。训练原子样本为 `(s_t,a_t)`；奖励传播、advantage 和信用分配仍可按完整 episode 计算。一次请求一条样本不代表每次请求具有独立终局 reward，也不要求把重写后的历史拼成一条虚构 append-only tape。（§6.1.1–6.1.3，p.16–17）

### 5.2 CISPO 原式和不完整处

以下按 p.17 Eq.2–3 与 [TeX](sources/R4/tex/section/post_training_rl.tex)记录，最大化目标为：

\[
J_{\rm CISPO}(\theta)=\mathbb E_{(q,a)\sim D,\{o_i\}_{i=1}^G\sim\pi_{\theta_{old}}(\cdot|q)}\left[
\frac{1}{\sum_{i=1}^{G}|o_i|}\sum_{i=1}^{G}\sum_{t=1}^{|o_i|}
\operatorname{sg}(\hat r_{i,t}(\theta))\hat A_{i,t}\log\pi_\theta(o_{i,t}|q,o_{i,<t})\right],
\]
\[
\hat r_{i,t}=\operatorname{clip}\left(\frac{\pi_\theta(o_{i,t}|q,o_{i,<t})}{\pi_{\theta_{old}}(o_{i,t}|q,o_{i,<t})},0,1+\epsilon^{IS}_{high}\right).
\]

`G` 是每 prompt 的 rollout trajectory 数，值未给；`|o_i|` 是原文所称 trajectory token 长度，`sg` 阻断 importance weight 的梯度，`θ_old` 是采样策略而非另一个 KL reference model。**clip 对象是 IS 权重，然后 stop-gradient 后乘 log-prob 梯度**；不是 PPO 对 surrogate 的 min 分支，也不是直接把该 token 的梯度清零。下界 0，上界 `1+ε_high^IS`；具体 ε 未给。

分母为组内全部 `|o_i|` 之和，**不是每条轨迹先均值再平均**。但 §6.1.3 的请求级样本如何组织到 Eq.2 的轨迹级 `o_i`、thinking/工具观察/重写后重复前缀的 mask、实际 loss 分母是否按有效 token 计，报告没有实现说明。不能把该排版公式当完整 train tensor 合同。

p.18 Eq.4：
\[
\hat A_{i,t}=\sum_{p=t}^{T}r_p-B_i.
\]
`B_i` 仅描述为 trajectory-level baseline，**不是已经披露的 GRPO group mean/std，也不能断言有/无 learned critic**。Eq.2 的 `t` 是 token 索引，Eq.4/奖励讨论又按 step 使用；completion/工具步奖励到每 token 的传播规则未展开。作者称 stop-gradient 避免 second-order terms；严格数学上这里只是去掉对重要性权重求导的乘积项，未提供 Hessian 算法，不宜照抄为二阶优化结论。

### 5.3 Reward：过程、完成速度、任务表现

§6.1.5，p.18 Eq.5–7：
\[
r_t^{speed}=h(T_{completion}/T_{baseline}),\qquad
r_t=\alpha r_t^{process}+\beta r_t^{speed}+r_t^{perf},\qquad
G_t=\sum_{\tau=t}^{T}\gamma^{\tau-t}r_\tau.
\]

过程信号罚语言混用、工具格式错，也奖励结构清楚的中间 reasoning；task performance 信号由 §4 的领域 verifier 支撑。`h` 单调递减，completion 是 rollout wall-clock，baseline 是参考时间，鼓励工具/子代理并行。`h`、参考时间如何估计、是否控制任务难度与 infra 拥塞、α/β、重复计入速度的时点都未给。

**原文内部未闭合：Eq.4 是无折扣求和，Eq.6 有 γ；未给 γ 值或解释二式连接。** 不擅自设 γ=1。Reward-to-go 是未来奖励求和，baseline 是控制变量；不能从文字“归一化/稳定”补出组内标准化。也没有 dense reward 或 speed reward 的独立消融、正确率/速度帕累托曲线。

### 5.4 混合领域课程与思考状态

§6.1.6（p.18–19）每个阶段同时取 reasoning/coding/agent/general，早期重推理与通用，后期提高 coding/agent 比例；各域 context 逐步变长，难度转向更难实例。作者将其解释为降低灾难遗忘与顺序域训练的负迁移。没有给比例/阶段数，且 Table 4 的 MMLU-Pro 退化限制了“全面保留”的强结论。

§7.1（p.23–25，Eq.9–10，Fig.7）的 interleaved thinking 为 `(r1,a1,o1,…,rT,aT,oT)`，其中 `r` 在此是 reasoning、不是前文 reward。下一轮 history 保留完整 assistant thinking/action 和 tool observation，使模型可计划、执行、反思；对照是把思考全放前面，或每轮丢掉历史 thinking。论文说做了 stripping 消融却没有数表，末段“stripping … yielding consistent gains”字面与上下文支持保留思考的方向存在歧义，**无法提取明确效应量或无歧义的消融方向**。Fig.7 是序列示意，并非消融结果图；其 “No Thinking” 列仍画 Final Thinking，标签也不能按字面扩成严谨实验定义。

## 6. Forge：调度、前缀和推理

<a id="infra"></a>
### 6.1 架构与黑白盒支持

§6.2.1 Eq.8 将目标写成 throughput×sample efficiency，约束 update variance 与收敛误差；前者是单位时间处理 token，后者是每样本带来的平均表现提升。它是系统设计目标，δ/ε/J* 无操作化数值，不是已证明的收敛定理。（p.19–20）

Fig.4（p.20）三层为：Agent Side 执行环境并产生轨迹→Gateway 路由 completion、Data Pool 异步收集完成请求和 reward→Rollout Engine 生成，Train Engine 消费样本做 CISPO 并同步权重。图示 completion 里有 `prompt_ids`、`response_ids`，reward 有 outcome/process；没有给完整捕获协议。（§6.2.2）

白盒允许框架知道 CM 逻辑并重建训练状态；黑盒只需将实际请求送 Gateway，框架读取每次真实 context，不要求 agent 内部循环可见。支持 memory compression、history rewrite、hierarchical multi-agent。作者称数百 scaffold 和数千工具格式已验证；没有逐 scaffold holdout 结果。（§6.2.3，p.21）

原文白盒段使用“backpropagate through context transformation”表述，但没有可微 CM 计算图，且前文把 CM 放在环境边界。只能确认训练暴露于 CM 后状态，**不能据此宣称梯度穿过任意字符串重写或外部工具执行**。黑盒接入也不意味着 prompt token 重分词、loss mask 和行为概率自动正确。

### 6.2 Windowed FIFO 精确取样对象

§6.2.4（p.21–22，Fig.5）针对长短任务完成时间从秒到小时：严格按原顺序取样会队头阻塞，完全先完成先消费会先偏短/易样本、后集中难样本。作者提出训练端只从**按生成提交次序排列的队列**中一个窗口取**已经完成的轨迹**：`Q=[T0,…,T(N−1)]`，头为 i，允许索引 `[i,i+W−1]`。窗口内可任取已完成项；窗口外完成也不能越界；队头被消费才推进窗口。W 小趋 FIFO，大趋全局 greedy。`W=0.3N` 是例值/作者实践描述，未给扫描曲线。（正文）

例如 i=0、W=4 时 1/2/3 可先于 0 被取走，但 4 即便完成也不能进训练；若 0 长时间不完成，取尽窗口内短项后仍会等待。**此例是阅读者展开原规则**：它限制乱序，牺牲部分吞吐保住队列分布；不是按长度排序、调度最短推理请求、保证每个 batch 精确同分布或直接删除长任务。

Fig.5 的具体例子 N=8、W=4，画出 0–10 除 7 外已训练，此时仅 7 留在可见窗口，11 以后仍阻塞；标注最大乱序 3=`4−1`、max off-policy lag 10=`8+3−1`，起始样本来自 model version 0。该图确实涉及版本，但未定义一次消费/optimizer update/权重发布的对应关系，也没给 partial rollout 的 token-version 计数。**不能把示意数字 10 迁移为任意流水线通用 staleness bound。**

### 6.3 Prefix tree merging 与 40× 的分母

多轮/分支请求拥有共同 token prefix，逐请求独立 forward 会反复计算相同历史。§6.2.5（p.22–23，Fig.6）先合并为树，公共 prefix forward 一次，各响应分支各算；再依 metadata 还原每个样本、独立算 loss。图中 `seq2` 同时作为一个 completion，又成为下一 completion 的前缀，展示的是计算复用。

作者称与独立样本训练数学等价、最高 **40× training speedup**，且节省内存。但没有列 baseline 实现、GPU/数量、序列长度/重合率、batch、耗时明细，不能声称相对 miles/SGLang 的 40× 或端到端训练 40×。**阅读者推论：** 等价要求 token/位置/因果可见性以及 loss 权重语义保持一致；只因文本相同就合并、或顺便改变共享 response 的梯度计数，都不是文中所声称的等价变换。无需由 rh2 自研 attention kernel。

### 6.4 三项推理优化

- **MTP speculative decoding**：RL 过程中用 top-K KL 持续协同训练 draft modules，跟上 policy 分布，保持接受率。K、KL 方向、归一化/尾部处理、系数、梯度流入主 policy 与否没有展开。不能等同领域 teacher→student 的 OPD。（§6.2.6，p.22–23）
- **Prefill/Decode 分离**：两阶段分别调度、用适合各自计算特点的并行布局，减少 MoE 混合排程干扰；没有具体 TP/EP/DP 或硬件映射。（p.23）
- **全局 L3 KV cache**：DFS 支撑，配 group-level rollout，路由权衡排队延迟和 cache 搬迁成本；未给 cache 一致性、eviction、命中率或速度实测。（p.23）

训练 context 上限描述为 192K，不能当单次 completion 的 max_new_tokens；也未给训练轮次/工具次数/wall-clock 限额。版本发布频率、backpressure 上限、retry/cancel、partial rollout、过期丢弃/重算、跨版本 token 处理统一列于 §8。

<a id="evaluation"></a>
## 7. 评测、消融、负结果和自演化

### 7.1 评测条件优先于分数

§8.1（p.26–27）默认 temperature=1.0、top-p=0.95；M2.5/M2.7 开 thinking/interleaving；Claude Opus/Sonnet 4.6 用 extended thinking，GPT-5.4、Gemini-3.1-Pro 用 high effort。开头概称所有 agent benchmark 共用 scaffold，后文**明确例外**如下，不能仅引用前半句：

| 评测块 | 实际设置和预算 |
|---|---|
| SWE-bench Pro、Multilingual、Multi-SWE、NL2Repo | 内部设施；Claude Code 统一 scaffold、覆盖默认 system prompt；**GPT-5.4 使用 native CodeX**；4 trials 平均。scaffold 版本、token/时间 cap 和前三者具体 split 未给 |
| Terminal-Bench 2.0 | Terminus-2 XML，`zai-org/terminal-bench-2-verified`；8 vCPU/16GB、2h timeout，4 trials；未重评的 baseline 引官方结果。未给该 dataset revision |
| VIBE-Pro / HyperTask | 前者 container 部署，用 Claude Code verifier 看交互和视觉、3 trials；后者每题约 100 条 feature/step requirement、专家 rubric、3 trials |
| BrowseComp / Wide Search / RISE | WebExplorer，小改 system prompt/tool description；token 使用超过最大 context 的 30% 时**删除全部 assistant replies 和 tool returns**；RISE 再启 Playwright。不是“保留全历史”的评测 |
| GDPval-AA / office | GDPval-AA 为 Artificial Analysis 对开放 GDPval 的再评；MM Claw、MEWC v2、Finance Modeling Pro 专家 rubric、3 trials；MEWC v2 为内部 100 道困难题 |
| 通用七项 | Artificial Analysis Index v4.0，无工具单样本 pass@1：AIME 2026、GPQA-Diamond、SciCode、IFBench、AA-LCR、HLE、MMLU-Pro |
| MLE Bench Lite | 22 competitions，每题 single A30 sandbox 24h，内部 self-evolution scaffold（Bash+WebSearch），选择最佳 validation checkpoint 在 test 评 medal；最终均值来自 3 次独立 24h trials，见 §7.4 |

所有这些是**评测预算**，不是 RL 训练配置；未报告误差条/置信区间。不同 harness、官方引用结果与内部 rubric 限制横向因果比较。

### 7.2 全部主结果与系列曲线

下表为 Table 4（p.28）两列 M2 结果；保留全域而非只选上涨项目。单位/指标按各 benchmark，不把 rubric 分数统一叫 pass@1。

| Benchmark | M2.5 | M2.7 | 阅读定位 |
|---|---:|---:|---|
| SWE-bench Pro | 55.4 | 56.2 | GPT 57.7、Opus 57.3；scaffold 有例外 |
| SWE-bench Multilingual | 74.1 | 76.5 | Opus 77.8 |
| Multi-SWE-bench | 51.3 | 52.7 | 此表最高；非所有 coding 表最高 |
| NL2Repo | 26.6 | 39.8 | 内部 benchmark |
| Terminal-Bench 2.0 | 51.7 | 57.0 | GPT 75.1；并非接近所有 baseline |
| MLE Bench Lite | 51.5 | 66.6 | 与 Gemini 66.6 持平；Opus 75.7 |
| VIBE-Pro | 54.2 | 55.6 | Sonnet 56.1，Opus 55.6 |
| HyperTask | 59.4 | 67.6 | 内部长程 AppDev |
| BrowseComp | 76.3 | 77.8 | Gemini 85.9 |
| Wide Search | 70.3 | 75.2 | 搜索 |
| RISE | 50.2 | 64.3 | 内部，浏览器 |
| GDPval-AA | 35.0 | 50.0 | 训练 seed 独立性缺口见 §4.1 |
| Toolathlon | 38.3 | 46.3 | 异构工具 |
| MM Claw | 57.6 | 62.7 | 内部办公 |
| MEWC v2 | 49.8 | 63.3 | 100 道内部困难题 |
| Finance Modeling Pro | 33.8 | 57.0 | 内部金融模型 |
| AIME 2026 | 87.2 | 94.2 | 与 Fig.9 AIME 2025 不同 |
| GPQA-Diamond | 85.2 | 89.8 | 无工具 |
| SciCode | 43.0 | 47.0 | 无工具 |
| IFBench | 72.0 | 76.0 | 指令遵循 |
| AA-LCR | 65.0 | 72.0 | 长上下文 |
| HLE | 19.0 | 28.0 | no-tool 子集 |
| MMLU-Pro | 85.2 | 81.8 | **下降 3.4 点** |

Fig.9（p.29）另选十一项绘 M2→M2.5→M2.7：Multilingual 56.5→74.1→76.5；Multi-SWE 36.2→51.3→52.7；MLE 40→51.5→66.6；VIBE-Pro 42.4→54.2→55.6；BrowseComp 44→76.3→77.8；Wide Search 62.3→70.3→75.2；Toolathlon 18.8→38.3→46.3；GDPval-AA 34→35→50；**AIME 2025** 78→86.3→94；GPQA 78→85.2→89.8；AA-LCR 61→65→72。其 BrowseComp M2 数取 HF 官方分数，因此正文“全在我们 scaffold 下”也有例外。十一项全升不等于所有评测全升，MMLU-Pro 不在这张精选图中。

Fig.1（p.1）是另一个 headline 图，含 Artificial Analysis 汇总指数 M2.7=50/M2.5=42，而 Table 4 未列这一行；不是将 Table 4 七个通用分数简单平均的结果。原图文字密集，使用 Table 4 核主数字，不能靠 PDF 文本抽取的交错标签重建名次。

### 7.3 确有负结果，因果证据有限

- **Hybrid SWA**：§2.2.2，Tables 2–3（p.4–6）在预训练及 SFT 后比较 full attention 和 hybrid SWA。预训练 RULER 128K CWE 90→72、MTOB e-k ChrF 44.8→27.2；但 MMLU 85.5→85.6、MATH 60.3→60.3，并非所有行下降。SFT 后 SWE-verified 54.7→50.2、Terminal-Bench 26.7→23.8、BrowseComp-zh 32.8→28.7、telecom 32.5→21.0；另一方面 IFBench 23.1→27.2、XBench-ds 58→63、retail 62.3→67.5。作者强调超过 32K 的退化更明显，不应写成 SWA 所有场景更差。
- **MTP 的限度**：Table 1 是 **17.8B total / 2B activated、500B tokens** 的消融，不是 229.9B M2 的 RL 消融。Baseline→MTP 的 MATH 19.6→21.3、HumanEval 29.7→30.1，但 MMLU 39.8→39.7；作者“consistently improves”有小例外。细粒度专家 32/top2→128/top8，在同规模预算下 MATH 达 24.1、HumanEval 32.5；不能与 MTP 两种独立列相加收益。
- **联合 MTP 优于始终冻结**有定性报告，无数表；训练 CM 分布、混合领域 RL、防 reward hacking、interleaving 和 Windowed FIFO 也没有完整独立受控消融。严谨结论是设计动机与作者观测，不是组件收益已确证。
- **泛化和遗忘**：Table 4 MMLU-Pro 下降 3.4 点；最明显的 agent/office 提高与新数据同时发生，不能据此推出混合 RL 消除了遗忘，或新数据是唯一原因。

### 7.4 自演化是运行工作流，不是新的自更新 loss

§7.2（p.24–26，Fig.8）描述由内部 M2.7 生成的 harness，作者称零人工代码，含层级 skills、persistent memory、guardrails、eval infra。人配置目标、对话引导、审查并决定下一轮；agent 自动看 logs/profile、诊断指标、改代码/配置。作者估计承担日常迭代工作量 **30%–50%**，未披露计量方法。另有**100 轮**内部 programming scaffold 改进循环，出现 loop detection 和更好参数组合，内部评测性能提高 **30%**；基数、相对/绝对口径和 heldout 协议未给，不能写成 +30 个百分点或纯模型权重收益。

§8.3（p.29–30）MLE 案例用 memory file、自我批评和后续优化方向推进迭代。最佳 run 得 9 金+5 银+1 铜，即 15/22≈68.2%；正文最终报告是三个 trial 的 **66.6% 平均 medal rate**，两者分母口径不同。每任务每 trial 配一张 A30 的 24h 沙箱，22×3×24=1,584 A30-hour 只是**按满额运行计算的评测沙箱上限预算**，不含 LLM 服务，非实际花费或 M2 权重训练成本。

**Fig.10 的未解口径。** 横轴为 Maximum Cumulative Effective Runtime (hours)，延伸超过 24h；蓝色 Any Medal 曲线末段约 70%，红色 Any Medal (Real / CV-selected) 约 50%上下，后者并非单调上升。图未明确这些曲线如何对应三个 trial、22 个任务和 Table 4 的 66.6%；不能把最高蓝线当可部署 validation 选择结果，也不能用该图“证实 66.6% 单调累积”。v2 未改图或解释。正文声称最佳 validation checkpoint 选 test medal，仍需作者提供原始运行/选择记录以对齐。

这些案例说明固定模型可执行 ML 工程、修改 scaffold；没有说明 MLE 评测期间持续更新 M2 policy 权重，也没有消除人类的实验选择角色。

## 8. 成本、开放资产与未披露项

本次实际获得的是 v1/v2 报告、TeX 与图表。论文没有给可运行 Forge trainer、完整 post-training dataset、环境镜像清单或配置入口；没有沿官方模型仓库检查训练可复现性，故不对模型仓库全部资产作否定断言。模型开放与训练过程开放必须分开。

| 缺口 | 已查范围 | 对复现/项目的影响 |
|---|---|---|
| 每阶段题量/轨迹量/token、teacher 型号、采样数/温度、SFT optimizer/LR/batch/epochs | §4–5、附录 A | 不能估环境漏斗、teacher 成本或重跑 SFT |
| CISPO G、ε、baseline、γ、reward 尺度与权重、loss mask/分母实现、KL/entropy 主 loss、更新次数与 LR | §6.1 Eq.1–7；§4.5 | 公开目标不等于公开训练语义；role-play entropy monitoring 不等于主 policy entropy loss |
| 行为 logprob/token 捕获、tokenizer 版本、重分词、CM 后遗失/复用 token、分支梯度归属 | §6.1–6.2，Fig.4/6 | 黑盒网关抽象不能替代逐 token 对齐 |
| 超时/坏环境/截断奖励、group 统计/梯度/补采、重试/取消、partial rollout/resume | §4.1、§6.2、附录 A | terminal 环境合成重试不回答 RL 终止语义 |
| 发布频率、weight span、lag 的单位、过期丢弃/重算、buffer 上限 | §6.2.2–6.2.4，Fig.5 | 有 sync weights 示意，不能补为“每 token 用最新权重” |
| GPU 类型/数量、并行/精度、训练时长、总成本、40× baseline 与 workload | §2、§5–6、§8 | A30 是 MLE 评测；不能用于估 10B 激活训练成本 |
| 任务切分/去污染、hidden tests/抗作弊与替代解、评测原始样本和方差 | §4、§8、附录 A | GDPval seed、内部 rubric 和跨 scaffold 比较均有限制 |

旧稿更正：原[证据矩阵 §7.4](../agentic_rl_training_recipe_evidence_matrix.md)基本阶段结论可保留，但“p.12–22”不足以定位 SWE/AppDev（p.7–11）、推理/role-play、思考状态与评测（p.23–30）；应以本笔记逐节定位替代。M1 的 group-relative advantage 不能挪给这里未定义的 `B_i`。矩阵其他段的“MiniMax 80K”不能作为本报告训练 hard cap，R4 明确是 192K context 能力范围。原[infra 映射](../infra_mapping_for_repoharness_rl_serving.md)关于上游承担 prefix/PD/KV 的职责原则可保留；这些不是 Forge 已接入 rh2 或已保证 token 完整性的证据。

<a id="project"></a>
## 9. 对 RepoHarness 项目一的有限映射

映射日期 2026-09-07。已读[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)（更新 2026-09-05）与[项目一建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)（2026-09-07，咨询建议）。实际主资料 HEAD=`ce2009f879cf38071d7898a1387e01d4e27741d6`；miles 集成目录 HEAD=`98a0272e4158b2c20e3a34d210c79b50159af0f6`，来自实际目录读取，不是本 worktree 默认分支。

本次窄查确认：`reference/miles-rh2-integration/miles/rollout/fully_async_rollout.py::FullyAsyncRolloutFn` 持续生产完成组；同 commit 的完整相对路径 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py::DefaultDataBuffer` 用已完成组 FIFO，put 做 ABORTED/dynamic filter，get 做 consume-time staleness、按组最老行为版本判定。它不是按原派发队列建立的 Forge Windowed FIFO。主仓 `rh2/src/repoharness2/adapters/miles/canonicalize.py::canonicalize_sample` 与 `rh2/src/repoharness2/adapters/slime/capture_wire.py::CaptureRegistry` 是现有转换/捕获接口；这里只核职责入口，未重新审计整条 token 链。

| 候选借鉴 | 已有职责/我方增量 | 最小验证及限制 |
|---|---|---|
| 真实任务应绑定可执行环境与任务类型相符 verifier（§3） | rh2 的环境/评分可信入口；并非重造模型训练框架 | 先做选定 taskset 的 golden/no-op/替代解和失败分类验证，量从候选到消费的漏斗；不能照搬未公开阈值 |
| 每次真实请求 state 与生成 action 成对（§5.1） | 上游 rollout/session 与 rh2 现有捕获/转换共同承担 | 固定真实 Claude Code rewrite/compaction/fork trace，比生成动作→训练 token 覆盖、mask 和权重；不能用“黑盒兼容”代替证据 |
| 排程影响所消费任务分布（§6.2） | miles 已有异步队列和 consume-time staleness；rh2 候选是测偏差 | 同一 trace 按派发/完成/消费次序看任务族、长度、耗时、lag、丢弃分布；测出问题后才考虑 window，保留整组准入 |
| 训练前缀复用（§6.3） | attention/训练后端承担；rh2 不写 kernel | 先量真实请求重复率，固定 workload 比 forward/loss/梯度等价和成本；40× 不是预算承诺 |
| 多领域与 artifact verifier（§4–5） | 可供未来 taskset 扩展；office/role-play 暂非首训内容 | 当前 SWE 闭环完成后才用同模型/预算看迁移与遗忘；不扩成首训全域 RL |

可用于项目叙事的是“以真实 harness 请求和可执行 verifier 建立训练证据链”的外部动机；rh2 的吞吐、学习增益、跨 harness 泛化都要自己的实测。未批准新的 reward、调度器、CM 策略或 loss。

## 10. 独立检查与修订记录

主任务 ID `01a07827-1e44-7133-85d7-658445c04597`，实际配置 `gpt-6-astra / high`（派发主线程已核验）。独立审查和处理记录见[09 审查](reviews/09_R4_N10_review.md)。交审固定副本为 `sources/R4/R4_minimax_m2_series.draft-20260907.md`；来源版本 v1+v2，初稿日期 2026-09-07。此段将在收到真实独立审查后补录结果。
