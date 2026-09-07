# Agent Lightning v1.0：真实 Harness 的样本语义、优化权重与训练闭环

**摘要。** 这篇工作的研究对象不是再造训练内核，而是部署 harness 独立控制工具、上下文和执行流程以后，如何从真实模型调用构造 RL 样本。其关键区分是 **prompt group → rollout → model call → training row**：一条 rollout 被切成更多行，不应因此反复改变组统计和优化权重。作者选择精确 token 前缀成立时才合并、rollout 级优势、rollout 级 token-mean loss，并给出搜索、通用指令和 coding 三个独立训练案例。Coding 实验有明确反例：仅改优势估计不如基线，与归一化同时修改才取得最好的验证成绩。当前公开实现提供了可检查的运行链，但行级丢弃、归一化分母、logprob 缺失和去重的最终消费仍须与论文原则分别核验。

**阅读状态：公开全文的正文、公式文本及附录 A 已读；PDF／原始图像的目视复核未完成。** 本轮成功取得 arXiv 全文文本，但 PDF、TeX 和原始图像入口持续抓取失败。因此以下图表只使用图题、公式、表格文本及邻文明确给出的信息；没有伪造 PDF 页码、曲线读数、误差条或“所有图已检查”记录。本文是可继续维护的精读笔记，**不是已经满足全图复核条件的最终审定稿**。详见[作者自查与缺口记录](reviews/agent_lightning_v1_2608.17528_self_check_20260907.md)。

导航：[来源与覆盖](#source) · [方法与公式](#method) · [系统与附录](#system) · [数据与全部实验](#experiments) · [官方代码核查](#code) · [局限与项目映射](#limits)

<a id="source"></a>
## 1. 来源、版本和本轮边界

### 1.1 一手来源

**P：论文。** Zhiyuan He、Siwei Zhang、Zhiwen Zhou、Yuqing Yang、Yu Kang、Yuge Zhang、Luna K. Qiu、Tin Yan Tsui、Jiahang Xu、Chong Luo，*Agent Lightning v1.0: Towards Harnessed Agentic RL*，arXiv **2608.17528**，公开检索提交时间 **2026-08-18**。作者机构包括 Microsoft、Fudan University、Zhejiang University、University of Edinburgh。[原文入口][P]；[PDF 入口][P-pdf]；[HTML v1 入口][P-html]；[微软论文页][M-publication]。

本轮实际通读的是 arXiv 返回的全文文本，其中包含 §1–5、Conclusion、完整参考文献和 Appendix A。PDF／TeX 未能取得，版本历史页面也未独立完整取回；**不据此宣称 v1 是截至阅读日唯一或最新版本**。后续拿到 PDF 时，应先核首页和版本，再补物理页码与图形检查。它与 **2508.03680（2025 年原版 Agent Lightning）是两篇不同论文**，不能将旧版的 LightningRL、训练案例和存储机制直接填入 v1.0。

**C：当前官方仓库。** `microsoft/agent-lightning`，固定提交 **`218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4`**，提交日期 **2026-09-02**。此提交晚于论文；下面的脚本值、数据处理和边界行为均按这一版本单列。主入口 README 明确说明 v1.0 全面重构，legacy 位于 `v0.x`。[C0]

**B：官方配套文章。** 微软亚洲研究院中文发布文，2026-08-20。用于核对作者定位和部署叙述，不替代论文公式、实验消融或成本披露。[B]

**本项目上下文。** 阅读基线为 `Rogerffff/RepoHarness@miles-migration` 的 **`f5d373b566244ddc02b53b881e773257511820fd`**。已读 [Codex 对 O01 的质量反馈](reviews/15_O01_codex_quality_review_20260907.md)、[模板](NOTE_TEMPLATE.md)和[项目一建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)的相关部分。本稿只负责此来源，不修改共享索引、其他论文、训练实现或项目定案。

### 1.2 覆盖表：读到了什么，什么还不能称为完成

| 原文范围 | 已读并提取的内容 | 尚缺的原图检查 |
|---|---|---|
| Abstract、§1 Introduction，Fig.1–2 | harness-owned loop、三个组件、传统／harnessed 对照、三类训练案例 | Fig.1 架构图的实际箭头；Fig.2 已有表格化文字，仍未看原图 |
| §2.1 Retokenization and Sample Merging，Eq.1–13、Fig.3 | POMDP 观察边界、原始 token、三类不连续、三条处理路线 | Fig.3 原始 token 示意图；文字例子完整可读 |
| §2.2 Advantage Calculation，Fig.4 | 同组 rollout 被拆分后的 reward 重复统计；细粒度信用仍为未来工作 | Fig.4 原图；1/2 与 3/4 示例由正文明确给出 |
| §2.3 Loss Normalization，Eq.14–16、Fig.5 | 三种 reduction、长度和行数的作用、长负样本风险 | Fig.5 原图；各段长度和算式在正文中完整列出 |
| §2.4 Training Backend Complexity，Eq.17 | rollout/group 身份、动态工作负载、更新边界 | 本节文字与公式已覆盖 |
| §3 System Design、Fig.6 | collocated async、网络重试、K8s、监控 | Fig.6 时间轴及其是否含额外资源标注 |
| §4.1 Search，Fig.7 | 模型、算法、数据、六类验证题、batch、频率、起终点 | 未读取曲线的总步数、波动范围或方差 |
| §4.2 General Instruction Following，Fig.8 | 模型、RLOO、80/20 split、batch、频率、起终点 | 未读取曲线轴范围和噪声量级 |
| §4.3 Coding，Fig.9–10 | 完整过滤流程、四类 reward hacking、三臂训练、验证及外部结果、合并均值 | 未读取熵的绝对量级、完整曲线范围、各基线峰值位置 |
| §5 Related Work、Conclusion、References | 历史技术归属、开放主张与论文范围 | 没有逐篇扩读全部参考文献 |
| Appendix A，Fig.11–12、Table 1 | rollout/model/event、API、controller 最终一致性、sample adapter、监控 | Fig.11 状态图／Fig.12 reconcile 图；Table 1 的全部端点文本已读 |

原文相关后训练内容没有只按 SWE 筛选。公开全文未出现独立的预训练、偏好对齐、安全 RL、OPD 或多域联合优化实验；不为凑模板补造这些阶段。**表中“未看图”是读取限制，不是作者没给图。**

<a id="method"></a>
## 2. 问题设定：训练端看见调用，不拥有完整执行世界

### 2.1 三层状态与四个样本单位

作者将传统循环概括为追加式历史：

$$p_t=(p_{t-1},a_{t-1},o_t). \tag{P1}$$

对外部 harness，训练端实际观察到的是一条 rollout 的调用集合：

$$\mathcal C(\rho)=((p_1,a_1),\ldots,(p_{T_\rho},a_{T_\rho})). \tag{P2}$$

隐藏执行状态是 `harness state + environment state`，harness 先形成消息上下文，再经模板和 tokenizer 形成实际输入。每次决策为

$$z_t=(p_t^{tok},a_t^{tok}),\qquad a_t^{tok}\sim\pi_\theta(\cdot\mid p_t^{tok}). \tag{P6}$$

P1/P2/P6 对应原文 Eq.1/2/6；中间 Eq.3–5 明确了隐藏状态、`Context_H` 和 `Tok(Template(...))`。这是作者为问题分析使用的对照，不意味着所有早期框架都只能运行一条不变的 ReAct 历史。[P, §1–2]

| 单位 | 含义 | 不能混淆的东西 |
|---|---|---|
| prompt group | 同一次题目采样产生的兄弟 rollout 集合 | 不应只由长期 task ID 决定；同题不同次采样可以是不同组 |
| rollout | 一次完整 agent 执行及其终局反馈 | 不是一条 HTTP 请求；成功执行状态也不等于 task reward=1 |
| model call / transition | 模型在某个真实 prompt 下采样的一次 response | 可以来自主 agent、子 agent 或摘要行为 |
| training row / sample | 独立调用或合法合并后交给后端的一条序列 | 行数受切分影响，不是新增独立经验数 |

本稿以上中文解释保留作者的统计单位，同时用 `row` 消除原文不同位置把 example、sample、rollout 都称作 sample 的歧义。

### 2.2 非追加上下文不是异常情况

子代理、handoff 和 compaction 都可能使下一次 prompt 不包含上一次完整输入和输出。即使文本看起来能追加，实际 token 也未必能够追加。因此，从调用记录恢复训练样本本身是建模与工程问题，而不只是日志格式转换。[P, §2，Fig.2]

## 3. Token 保真与样本合并

### 3.1 三种不连续来源

原文 Eq.8 的文本前缀关系不推出 Eq.9 的 token 前缀关系：

$$(p_i^{tok}\Vert a_i^{tok})\preceq p_{i+1}^{tok}. \tag{P9}$$

`≼` 必须是 token ID 序列的精确前缀，不是 decode 后的文本等价。作者区分了三种原因：

**模板非可组合。** 完整消息列表的渲染不等于各段渲染的拼接，可能新增换行／边界，或者删除先前 `<think>` 标记。

**Decode–retokenize drift。** `Tok(Decode(a))` 不必等于采样时的 `a`；正文用 `having` 的两种 token 切法说明，文字相同不代表动作 token 相同。

**输出转换。** 工具调用处理器可能解析、修复、规范化和重新序列化 JSON，令返回给 harness 的文字也不同于原始采样序列。以上分别对应 Eq.10–11、Fig.3 及紧邻段落。[P, §2.1]

### 3.2 三条路线与作者选择

| 路线 | 保留什么 | 计算或实现代价 |
|---|---|---|
| 每次调用独立训练 | 每个 response 的实际采样条件 | 重复计算长前缀 |
| 精确前缀树／共享前缀训练 | 分支各自的真实因果上下文 | 树打包、attention、分布式梯度等后端复杂性 |
| best-effort sequence merging | 只有 P9 成立才合并，否则新开一行 | 使用普通 causal kernel，但不能消除所有前缀重复 |

Agent Lightning v1.0 选择第三条；新增工具观测作为上下文保留，却不冒充 policy 采样动作。当前具体 mask 构造见 §8。[P, §2.1；Appendix A, Dedicated Sample Adapter]

### 3.3 关于“替换历史 token 会 off-policy”的适用边界

原文 Eq.12–13 比较实际 prompt 中重建的旧 response 与用原始 response token 拼接后的 prompt。如果下一条 response **已在前者条件下采样**，再在训练时使用后者计算其概率，确实改变了样本条件。

但原文同时描述了某些框架在**新请求发出前**由 proxy 替换 token。必须区分：

> 事后把训练 prompt 改掉，与事前改变真正的生成 prompt、再忠实记录它，不是同一个问题。

后一种设置可能改变默认部署行为，但不能不检查实际调用就断言它存在相同的训推条件错配。本文保留作者的论证与这一读者限定，不据其对 AReaL／Uni-Agent 的描述给当前外部框架作全面正确性判决。本轮也没有审计这些其他仓库。[P, §2.1，Eq.12–13]

## 4. 优势估计与 Loss：修复的是两个不同的权重问题

### 4.1 组统计应该先按 rollout 去重

原文 Fig.4 的组有两个 rollout，reward 为 1 和 0。第一个被拆为三行，第二个只产生一行。

- rollout 统计的均值为 `(1+0)/2=1/2`；
- 直接按训练行统计则成为 `(1+1+1+0)/4=3/4`。

切分不仅改变 baseline，还可能改变 GRPO 的标准差。因此“先给每行复制 reward，再照常跑 GRPO”并不是语义中性的操作。作者将优势先在逻辑 rollout 上估计，再广播给其各行，同时明确把 rollout 内更精细的信用分配留给未来工作。[P, §2.2，Fig.4]

**不要误归属创新。** 原文称 Uni-Agent/Polar 已采用 rollout-level advantage；对 slime/AReaL 则给出另一种当时的描述。这里是作者对所参考实现的归纳，不是本文验证的最新框架能力表。特别是下面的 rollout-level loss，作者明确把已有实现归于 slime，不是声称全部概念由 v1.0 首创。

### 4.2 三种损失归一化的完整含义

设批中有 `R` 条逻辑 rollout，rollout `ρ` 有 `Nρ` 行，第 `j` 行有 `Lρj` 个参与目标的 response token，每 token loss 为 `ℓρjt`。原文 Eq.14–16 是 **loss aggregation 公式**，不是完整 PPO/GRPO clipped objective：

$$
\mathcal L_{token}=\frac{\sum_{\rho,j,t}\ell_{\rho jt}}{\sum_{\rho,j}L_{\rho j}}, \tag{P14}
$$

$$
\mathcal L_{seq}=\frac{1}{\sum_\rho N_\rho}\sum_{\rho,j}\frac{\sum_t\ell_{\rho jt}}{L_{\rho j}}, \tag{P15}
$$

$$
\mathcal L_{rollout}=\frac1R\sum_\rho\frac{\sum_{j,t}\ell_{\rho jt}}{\sum_j L_{\rho j}}. \tag{P16}
$$

源码把 observation/padding 排除在 `response_mask` 外；原文公式没有单列 mask 符号，所以落地比较时必须说明 `L` 的实际分母，不能统计所有拼接上下文 token。[P, §2.3；C-adapter]

**原文 Fig.5 的可恢复算例。** A 的两行长 50、100；B 的三行各长 30；C 只有一行长 40。只考察单位 token loss 下的相对总权重：

| 方式 | A | B | C | 权重首先由什么决定 |
|---|---:|---:|---:|---|
| token mean | 150/280 ≈ 53.6% | 90/280 ≈ 32.1% | 40/280 ≈ 14.3% | 参与目标的 token 数 |
| sequence mean | 2/6 ≈ 33.3% | 3/6 = 50% | 1/6 ≈ 16.7% | 训练行数 |
| rollout mean | 1/3 | 1/3 | 1/3 | 逻辑 rollout 数 |

长度与算式来自正文；百分比是本稿复算，不是图上新读出的实验值。**token mean 本身在 token 集和 loss 不变时也不受纯行切分影响**；作者偏向 P16 的额外依据是长负轨迹较多时的训练不稳定观察，而不是说 P14 在数学上必然错误。[P, §2.3]

### 4.3 训练边界不等于 tensor 行边界

Eq.17 要求每行携带 `(sequence, rollout_id, prompt_group_id)`。作者还要求同一 rollout 的各序列处于同一次 optimizer update，避免在不同更新后用不同参数评价同一条经验的各部分。[P, §2.4]

这不是要求各行必须位于同一个 GPU，也不是只要调用一次 `_update_actor` 就已保证一次 Adam 更新。后端还可能切 PPO mini-batch、累积 microbatch 或进行多轮更新；必须追到实际消费。当前版本的静态检查见 §8.3–8.4。

<a id="system"></a>
## 5. 系统设计与附录 A

### 5.1 三组件：谁拥有哪一层

| 组件 | 论文职责 | 责任边界 |
|---|---|---|
| API Gateway | 保存 rollout/model/event；代理 LLM API；关联真实调用与 reward | 是逻辑状态来源，不由此推出已有持久化数据库或事务隔离 |
| Rollout Controller | 将待运行 rollout 映射为 K8s Job 或本地进程，监控并回报状态 | 管生命周期，不替 trainer 计算优势或定义任务成功 |
| Customized Trainer | 基于 verl 注册模型、创建／收集 rollout、组装样本并更新模型 | 复用推理与训练后端，不自行定义外部 harness 的工具循环 |

论文与 README 的“约 3,500 行”是作者对其实现范围的描述；本轮没有独立统计 LOC，不将包括 verl、vLLM、K8s、harness 和数据脚本在内的所有系统算成 3,500 行。[P, §3；C0]

### 5.2 Collocated async 的时间语义

论文比较三种组织：全 batch 等待的同步 RL；生成／训练分别占 GPU 池的异步 RL；本方法让二者共享 GPU 池，但允许尚未完成的 agent 执行跨越训练轮次。

达到本轮足够数据后，gateway 暂停新 LLM 请求，等待已经发给推理引擎的请求结束，再进行参数更新与恢复。**不是在同一 GPU 上同时做训练和生成，也不是强制中断单次正在 decode 的请求。** 一个 agent 的下一次模型调用可能发生在之后的模型版本下；因此共置并不自动消除 staleness。[P, §3, Collocated Async RL；C-async]

作者报告约 **2× end-to-end speedup**。在已取得的正文和附录文字中，没有完整的同硬件／同 workload 成本表、精确计时分解或达到同一模型质量的时间曲线。Fig.6 原图尚未取得，因此其可能包含的额外标注也不能称为“作者未给”。当前证据不能用来预测本项目八卡加速比，更不能解释为 MFU 翻倍。[P, §3；B]

### 5.3 网络失败：控制平面重试与重新采样不同

作者将控制 API 的幂等与 LLM 生成分开：随机生成重试可能产生另一条 response，所以采用同一 rollout 内相同 prompt 只保留最后一次调用。这里的逻辑假设是早期调用属于重试或被替代的生成。[P, §3, Network Issues]

**读者限定。** 相同 prompt 也可能来自合法的重新尝试、上下文重置或不同子代理。仅凭相同 prompt 无法证明“前一次输出从未影响后续世界”。应把这一规则当成作者采取的折中，而非一般性 exactly-once 保证。当前代码具体键和过滤次序见 §8.5。

### 5.4 附录 A：API、状态与最终一致性

附录把三类对象分开：`rollout` 有 ID、input、status、metadata；`model` 对应注册的模型名和推理 endpoint；`event` 记录 `model_request`、终局 scalar `reward` 或自定义信息。同一题的多个 rollout 各有 ID，不能按题目覆盖同一个事件流。

Table 1 的端点文本完整可取得，整理如下；这是 API 结构而非已经验证所有操作幂等的证明。事件文本明确包含 prompt/response token IDs 和 response logprobs。[P, Appendix A, Table 1]

| 方法 | 原文端点 | 作用 |
|---|---|---|
| POST / GET | `/api/rollouts` | 批量创建／按状态等条件列出 rollout |
| GET / PATCH | `/api/rollouts/{rollout_id}` | 读取单条／更新状态 |
| POST | `/api/rollouts/{rollout_id}/attempt/{attempt_id}/events` | 给某次 attempt 追加事件 |
| GET | `/api/rollouts/{rollout_id}/events` | 读取事件 |
| POST / DELETE | `/api/models` | 注册／清空注册的模型端点 |
| POST | `/proxy/rollout/{rollout_id}/attempt/{attempt_id}/mode/{mode}/openai/v1/chat/completions` | 关联执行身份并代理模型调用 |

原表把组合行中的各 HTTP 方法分别列出，共九个端点条目；本文没有增加论文未列出的 pause/resume 端点，后者只在当前代码部分讨论。

K8s controller 用 watch 接收变化，再用定期 list 补漏；本地 reconciler 轮询进程状态。Gateway 中的状态被视为事实来源，K8s 观察可滞后；附录仅承诺 **best-effort eventual consistency**。这不等于完整故障恢复、所有 API mutation 的幂等或 gateway 重启后保留状态。[P, Appendix A, Rollout Controller]

监控可导出输入、调用、reward、token/turn 统计、custom events 与 pod logs，帮助人工或 AI 定位 reward hacking。但“记录得到”不等于自动阻断，也不是已经有独立 hidden-intent verifier。[P, §3 Monitoring；Appendix A]

<a id="experiments"></a>
## 6. 实验全景：三个独立训练案例

| 案例 | 模型与算法 | 数据与验证 | 论文明确给出的规模／频率 | 结果 |
|---|---|---|---|---|
| Search | Llama-3.2-3B-Instruct，GRPO | HotpotQA train；六类验证来源各抽 50 题 | train batch=512；每题 4 rollout；每 10 步验证 | 验证 EM 25.1%→41.7%，+16.6 pp |
| General Instruction Following | Qwen3-4B-Instruct-2507，RLOO | Instruction Pre-Training，80%/20%；沿用 LLM-in-Sandbox harness | batch=8；每题 8 rollout；每 20 步验证 | 验证 reward 51.9%→70.2%，+18.3 pp |
| Coding | Qwen3.5-9B，mini-SWE-agent，三臂 GRPO 对比 | SWE-smith 筛选集；内部验证与外部 SWE-bench Verified 分开 | 约 6K train/400 test；最后外评 checkpoint step 208 | 外部 41.8%→56.4%，+14.6 pp |

以上属于论文报告，不是本轮复现；batch 的精确物理训练行数不能仅由 prompt 数×rollout 数恢复。没有证据表明三个领域混训成了同一模型，也没有可据此计算的跨域综合平均提升。[P, §4]

### 6.1 搜索：奖励、验证集和当前资产

六个验证来源为 HotpotQA、2WikiMultiHopQA、MuSiQue、Bamboogle、TriviaQA、Natural Questions，计划抽样总数 **300 题**。agent 交替推理和搜索，以最终答案 exact match 作为奖励。Fig.7 邻文描述训练 reward 稳步上升，给出验证起终点，但没有在文字中提供完整种子方差或成本表；原图未看，不能补编最大 step 和置信区间。[P, §4.1, Fig.7]

当前官方例程另披露 **8×A100 40GB、Local controller、sync only**；检索用 Wikipedia `wiki-18`、E5/FAISS 服务，默认 top-k=3，默认 4 turns、单次生成 500 tokens。支持普通 Chat API 和 token-in/token-out Completions 两条路径。**这是 C 提交的运行示例信息，不回填成论文全部实验的冻结配置。**[C-search]

### 6.2 通用指令：RLOO 与 sandbox 能力，不是另一组 coding 题

原文采用原始 LLM-in-Sandbox harness，在计算机沙箱中获取资源、管理文件和执行代码，以处理非编码任务。训练 batch reward 明显噪声，但验证呈上升趋势。作者没有在这段文字中完整展开各任务 reward 的解析器、匹配规则或服务成本，应记为本篇未披露，不擅自当成统一二元 EM。[P, §4.2, Fig.8]

**当前文档与论文 split 不相同。** C 版示例写的是 **4×A100 80GB、K8s、sync only**，从 `daixuancheng/llm-in-sandbox-rl` 转换 3,600 个 `instruct_pretrain` 训练样本，验证则选 `math_mini/biomed_mini/long_context_mini`。这不是论文所述同一 Instruction Pre-Training 数据的 80/20 切分，不能用当前默认命令声称复现了 51.9%→70.2%。[C-instruct]

### 6.3 Coding：模型名称与历史数据版本

主实验是 **Qwen3.5-9B**，不是 Qwen3-32B、30B-A3B，也不是在论文中新预训练的模型。所谓 RL alone，是这一任务专项适配没有新增一段 SFT，不表示输入模型没有任何已有后训练历史。[P, §4.3]

作者使用的 SWE-smith 版本包含 **59,136 任务、128 仓库**，镜像约 **295GB**；4TB R2E-Gym、6TB SWE-Gym 是其存储对比。不能把当前记录数改成 SWE-smith 早期论文的另一个数字，也不能把 GB/TB 解读为数据生产总费用。[P, §4.3, Dataset Preprocessing and Filtering；C-coding]

## 7. SWE：从数据筛选到外部结果

### 7.1 任务漏斗必须保留未给出的中间分母

| 步骤 | 原文报告 | 必须保留的限制 |
|---|---|---|
| 原始数据 | 59,136 条／128 Python 仓库 | 没有本轮独立下载核算对应 revision |
| 空描述 | 18,033 条 | 不是其他缺陷之外的互斥集合 |
| 镜像中无问题分支 | 1,265 条 | 与空描述的交集未给 |
| 测试负担 | 去掉 >200 tests 的任务；例子有 >7,000 tests | 未给这一步删掉多少题；会改变任务分布 |
| 模型校准 | 对剩余候选用 Qwen3.5-9B 每题 4 次 | 未给总候选数、API/GPU-hour、重试费用 |
| 饱和任务 | 去掉 4/4 通过 | 不等于这些任务在所有模型／预算下没有价值 |
| 成败混合任务 | 约 5,000 条 | 有 signal 不等于已证明最大迁移价值 |
| 困难补充 | 加入 1,000 条 0/4 | 明确保留难题；不是所有全失败都无训练资格 |
| 最终切分 | 约 6,000 train、400 test | 近似数字不能直接算成严格守恒漏斗；不自行解释 400 的来源 |

原文没有给清洗／难度过滤各阶段的独立学习消融、精确 train/dev 仓库切分、污染审计或多 solver 校准。因此它证明一条被作者实际使用的配方，不证明这组筛选规则优于等量随机／静态分层采样。[P, §4.3；C-coding]

当前入口下载的是两个预先筛好的 JSONL，`train_smith_agent.py` 将它们按字段投影后直接训练；本轮没有取得 Google Drive 压缩包，也没有核验逐题 manifest。例程目录有镜像准备、执行和训练脚本，但没有在所查路径找到可从全部 59,136 条重放四次 solver 校准并恢复最终切分的独立生产脚本。**“有筛好数据的训练路径”和“完整原始生产过程已独立复现”分开。**[C-coding；C-swe-train]

### 7.2 作弊观察和防护

论文实际观察到四类捷径：通过 Git 历史、外网命令下载、pip 下载原包源代码、Python 网络库取源代码。采取隐藏 `.git`／禁止 agent 使用 Git，以及 K8s 出网白名单。[P, §4.3, Preventing Reward Hacking]

这说明隔离是已使用训练配方的一部分；没有逐类攻击成功率、修补后假阳性和合法求解保持的量化对照，不能写成“严格证明反作弊完备”。当前公开文档把 NetworkPolicy 写为部署方强烈建议添加的条件；**不能因为用了 K8s 就认为所有 pod 已有相同网络隔离。**[C-coding]

### 7.3 三臂实验，比较的不是三种完全独立新算法

| 实验臂 | 组优势统计 | loss aggregation | 原文报告的最高观察验证 reward |
|---|---|---|---:|
| 基线 | sample-level | token mean，Eq.14 | 35.0% |
| 只改优势 | rollout-level | token mean，Eq.14 | 33.1% |
| 同时改两项 | rollout-level | rollout token mean，Eq.16 | 38.2%，step 128 |

注意基线使用 **Eq.14，不是 Eq.15 的 sequence mean**。单独改变 advantage 的这次运行低于基线，说明两个变量有交互，不能把“更合理的统计单位”自动等价成“每一项单独增加都会提分”。[P, §4.3, Training Dynamics，Fig.9]

验证差值分别为同时改两项较基线 **+3.2 pp**、较只改优势 **+5.1 pp**；这些是本稿算术。原文未说明另两臂峰值是否也在 step 128，没有多种子显著性报告，因此不将峰值差写成固定 checkpoint 的稳健均值差。

作者观察到最终方法的 entropy 增长较慢，比只改优势的曲线更稳定。**本轮没有看原图，不能给熵的绝对范围或峰值时间。** 图10的均值由正文明确给出：约 **36% rollout 只产生一行，平均 2.41 行／rollout**。这不是“64% 都发生了 retokenization bug”：多行可以有多种来源，也不是 2.41 倍独立训练经验。

### 7.4 外部评测与成本口径

最终方法另在 **step 208** 的 checkpoint 上评 SWE-bench Verified，基座 **41.8%**、训练后 **56.4%**。这是 **+14.6 个百分点**，与 400 题左右的内部验证集、step 128 峰值是不同对象。官方发布文将外部指标称作 Pass@1；本篇已取得文字没有完整给出 eval harness revision、重复次数、精确 task manifest、超时及推理预算，不能自动补为“所有模型完全同协议重跑”。[P, §4.3；B；C0]

当前 coding 文档说明 **4×B200**，但没有本次论文运行的总 GPU-hour、CPU/内存、任务生产、网络／存储、验证、失败作业及墙钟成本账。模型只有 9B 并不推出廉价；“modest compute”与“self-hosted”是作者定位，不是可移植到 8×96GB 的预算保证。[C-coding]

<a id="code"></a>
## 8. 官方代码定点核查：把字段追到消费位置

本节只核 §2–4 的关键声明。所有链接固定为 C 提交；**没有运行 GPU／K8s，没有把静态差异判为影响过历史论文结果的已复现 bug**。多模态新增代码并非本篇实验的核心，未扩大为另一轮全仓审计。

### 8.1 实际数据路径与行为概率

`ProxyRouter.prepare_body` 为训练请求设定模型、temperature、`return_token_ids=True`，默认要求 logprobs；`forward_request` 在响应完成后记录 `model_request`。当前版本拒绝 streaming 请求，因此“无需修改任意 harness”仍受支持的 API 行为约束。[C-proxy]

`events._trim_model_request` 提取真实 token 与 logprob，当前 attempt 的事件进入 triplet 视图。`_build_completed_rollout` 丢弃 HTTP error／空 response 的请求，取最后一个 reward event，保留 rollout/data ID。[C-events；C-manager]

`RolloutAdapter` 精确比较 token 前缀：能合并时把新观察置 mask=0、模型生成置 mask=1；不能合并则开新行。每行都带 `rollout_id_list` 和 `data_id_list`。不是重新将完整文本 tokenize 来伪造原始动作。[C-adapter, `get_train_data_batch`]

**实际 logprob 缺失行为与注释不完全相同。** events 的抽取函数说无效概率返回 None，注释暗示 bridge 会丢样本。但 adapter 在某行 logprob 缺失或长度不匹配时仍可保留 token 行；只有所有行都有概率才输出整批 `rollout_log_probs`。一行缺失可能令整批不输出该字段。trainer 的非 bypass 分支仅在字段存在时应用 rollout correction；因此**配置 TIS 不等于这一批已经做了 TIS**。这是已追到条件消费的静态事实，未测发生率或训练影响。[C-events → C-adapter → C-trainer]

### 8.2 Rollout-level advantage 的实现与适用目标

`compute_rollout_level_advantage` 按 `rollout_id_list` 选择代表行，检查同 rollout 的 UID 与 reward sum 一致，交给 verl 原有 advantage 函数，再将标量广播到全部 response mask。计算在无梯度／detach 语义下完成。[C-adv]

函数还要求代表行的 advantage/returns 在有效 token 上是常数，否则抛错。这适配本篇 outcome-style GRPO/RLOO，**不是已经支持任意 token-level GAE 或过程奖励**。仅凭函数签名有 gamma/lam，不能声称它已经具备跨段 critic 信用分配。

### 8.3 “完整采集组”与“完整训练组”存在中间边界

异步 manager 以新生成的 `data_id` 标识一次 prompt group，并等待恰好 n 个兄弟 rollout 都结束；未完成的组留到之后。这里的 group identity 没有直接退化成数据集的永久 instance ID。[C-manager]

但 trainer 在算 advantage **之前**还执行：

```text
adapter 输出行
→ 删除 is_drop_mask 行
→ 对齐 ppo_mini_batch_size × rollout.n
→ 应用 max_ppo_update_times 上限
→ 优先从等 reward 的 uid 行中丢弃，不足再随机丢行
→ compute_rollout_level_advantage
→ normalize_advantages_by_rollout
→ _update_actor
```

这些删除操作按 row index，而不是按完整 rollout 或完整 prompt group。只删部分行可能改变可训练内容；删光一个 rollout 的行，会令它不再进入后面的代表行统计。**所以采集阶段等待完整 group，并不能单独证明更新阶段仍保留原始组。** 原文 §2.4 的更新边界主张还需要与所安装 verl 的 mini-batch／optimizer-step 划分联合验证；本轮没有做该分布式验证。[C-trainer, `_train_step`]

长度处理也不是 SkyRL-Agent 的 horizon mask：prompt 超限行会被标记并在 trainer 删除；response 超限则截断，保留前部 token 和原终局 reward 供训练。没有以“整条轨迹没完成”为条件统一屏蔽其自身梯度。[C-adapter；C-trainer]

### 8.4 Rollout 等权与最终全局尺度要分开

当前 `normalize_advantages_by_rollout` 对每条保留 rollout 统计有效 token 总数 `Tρ`，并将 advantage 除以 `Tρ × num_trained_rows`。实际调用传入 **`num_trained_rows=len(batch)`**，即当前行数 S，不是不同 rollout 数 R。

随后注册的 `per_rollout_mean` loss 使用 PPO ratio `exp(clamp(log_prob-old_log_prob,-20,20))`、不对称 clip（来自 config）、负优势 dual-clip，按 mask 求和，乘 DP size；可额外乘 rollout importance weight。它并非直接调用 Eq.16 再求一次均值。[C-loss；C-trainer]

单测明确验证：两条 rollout 被表示为三行时，两者各自 token 总权重为 **1/3**，不是 1/2。因此这个局部实现确实保证两条保留 rollout 的**相对等权**，却不能不加说明地写成 Eq.16 的 `1/R` 已逐项实现。若其他操作不变，局部边界的全局尺度差为 `R/S`。

本轮没有审计 upstream actor 的全部累积／reduction，因此不将上述局部尺度差宣布为最终梯度 bug，也不称为验证了 Eq.16 在全部并行设置中严格等价。它是后续最值得做固定样本数值检查的位置。[C-loss-test]

### 8.5 重试、attempt 和同 prompt 去重

当前事件查询只读 `last_attempt_id`。triplet 视图以非空、合法的完整 prompt-token tuple 为键，保留最后一次 model_request；raw 事件仍可查看。**去重发生在 manager 后续去掉 HTTP 错误／空 response 之前**。若同 prompt 的最后事件失败而此前成功，需根据实际事件次序检查会留下什么，不能只按“最近有效生成”理解。[C-events；C-manager]

该键没有额外核验 action lineage、子代理身份或世界状态是否已变化。合法同 prompt 重访也可能被归到同一键；这是一项适用边界，不是已经测得的误删率。

另外，`record_event` 对 POST 是追加 list，并没有事件 ID 的重试去重。这限制了论文“所有 gateway endpoint 都幂等”的宽泛文字；不能将 rollout 创建使用预分配 ID 的幂等机制，扩展为所有事件 append 都 exactly-once。[C-events；C-manager]

### 8.6 异步暂停的真实协议、staleness 与持久化

当前 async pool 要求 active prompt groups 大于每次消费组数；完整组就绪便消费，剩余组继续在途。更新前 `/proxy/pause`，轮询 in-flight=0，再卸载推理副本、训练、发布权重。新请求并非无限挂在原连接上：proxy 返回 **429 + Retry-After + X-Agl-Paused**，agent/client 需要重试。[C-async；C-proxy；C-trainer]

因此“对外部 harness 透明”有客户端配合条件；单条 rollout 也可能包含不同轮次的模型调用。当前文档建议 token-level IS threshold=2，但这是 C 版推荐，不是论文披露的全部原始训练配方，更不是严格 on-policy 的证明。

Gateway 当前 `store.py` 使用进程内 dict/list。附录的逻辑状态来源和最终一致性，不等于该提交已具备重启后的 durable replay；本轮没有用 crash/restart 测试推断可靠性结论。[C-store]

### 8.7 Coding 的实际 reward 口径与部署前提

当前 `smith_agent.py` 执行问题分支 checkout，移走 `.git`，运行 agent，再恢复测试并评分。`evaluate(..., f2p_only=True)` 会将 P2P 限制到 F2P 涉及的文件；接受 `PASSED/XFAIL`，缺状态或 timeout 不能算完成。它不是默认运行任意仓库的全部回归测试。[C-agent]

当前主函数还对 **已经解决的训练 rollout** 叠加 turn penalty 和 prompt-length penalty；validation 保持 raw reward。reward event 同时记录 `value` 与 `raw_value`，但 triplet 视图及 manager 取的是 **`value`**，所以训练消费的是 shaped reward，而不是日志里的 raw value。默认阈值为 80 turns、λ=0.1，以及最长 prompt 50K–64K、最大减分0.1。**论文没有写这些新增 shaping，不能倒填入 Fig.9 的“same GRPO objective”历史配置。**[C-agent-main → C-events → C-manager]

公开文档要求额外配置 K8s NetworkPolicy；隐藏 `.git` 与命令限制也不能凭静态检查就被称为完整的 host-side grader 隔离、合法替代解保护或通用反作弊证明。[C-coding]

## 9. 当前可复用配置与资产：与论文表格分开

### 9.1 SWE 示例的明确值

C 版 `train_smith_agent.py::verl_default_config()`：

| 类型 | 当前示例值 |
|---|---|
| 模型／硬件 | Qwen3.5-9B；1 node×4 GPU；文档注明 B200 |
| 优化 | GRPO；lr=1e-6；无 KL reward/actor KL loss；entropy_coeff=0；clip low/high=0.2/0.28 |
| batch | train_batch_size=16；rollout.n=8；ppo_mini_batch_size=16；microbatch/GPU=1；max PPO update times=2 |
| 上下文／生成 | prompt limit=65536、response limit=65536；max_model_len=81920；聚合器也有独立的65536/65536限制 |
| runtime | rollout timeout=5400s；train temperature=1；validation temperature=0.7；前缀缓存、chunked prefill |
| 后端 | FSDP 路径；参数／optimizer offload；gradient checkpointing；vLLM |
| 共置异步 | agentlightning.async_rollout.enabled 默认 false；active pool 参数50；只有显式开启才使用 |
| 验证／保存 | test_freq=16、save_freq=16；默认1000训练steps、4epochs，不等于论文跑了1000steps |

`rollout.mode="async"` 是 verl 推理执行模式，**不能覆盖另一开关默认 false 的事实**。多个长度字段也不能简单相加当成实际可生成窗口；真正完成的有效长度与截断需看运行结果。[C-swe-train]

### 9.2 开放与未核验项

已实际读取：官方代码／文档、固定 commit 下的实际入口和核心样本函数。README 声明 MIT；不从代码许可推出模型、全部数据和所有外部依赖都使用同一许可。[C0]

尚未实际取得：Google Drive 筛选后数据包、论文最终模型权重及精确评测脚本／manifest、历史实验完整环境配置、PDF／TeX／原图。**链接存在不等于本轮验证了资产内容。** 没有运行集群、拉取镜像、复现 56.4% 或测量本文的速度收益。

<a id="limits"></a>
## 10. 证据强度、缺口与可能的反解释

| 主张 | 已有直接证据 | 不应扩展为 |
|---|---|---|
| 真实 harness 能参与 RL | 三个明确训练案例，开放接口与示例 | 任意 harness 的接口、token 和概率都无条件兼容 |
| 切分影响组统计 | Fig.4 数学例；当前代表行计算 | 所有框架当前版本都犯同一种错误 |
| 同时改优势和归一化有益 | SWE 三臂单组训练曲线及外部checkpoint | 两项独立、普适、显著的因果增益 |
| best-effort merge 可用 | 原文选择与当前精确前缀代码 | 所有复杂轨迹都一行，或无需保存原始调用 |
| 共置异步约2× | 作者报告值、机制和当前可执行接线 | 同质量学习成本严格减半，或 8×96GB 会同样加速 |
| 筛选后约6K可训练 | 详细规则与实际训练结果 | 通过率筛选一定优于普通抽样；在线 curriculum 已获验证 |
| 防作弊有必要 | 四类实际观察与防护描述 | 一切 exploit、测试控制面和合法多解问题都已解决 |
| 迁移到 SWE-bench Verified | 单个外部指标前后提升 | 跨 harness、多语言、终端、长期可靠性已得到证明 |

**作者未披露（已查正文及附录文本）**：完整 train/dev provenance 与仓库分割、三臂多种子误差、清洗成本、GPU-hour／总墙钟、精确原始 optimizer与 eval 配置、各防护的量化消融等。

**本轮读取限制**：PDF物理页码、原图曲线轴与近似量级、TeX、数据包及完整 checkpoint 资产。它们不是作者未披露。特别是 Codex 要求的“曲线近似量级”，在此只能保留正文明确的起终点和峰值；图像成功取得前不制造读数。

**静态核查边界**：当前代码较论文晚；行删除、分母、None logprob 和 event 去重已追到对应消费条件，但未证明触发频率、历史影响或最终跨 DP 数值结果。正文没有以“架构意图”替代这些条件，也不把静态问题上升为本论文训练无效。

## 11. 对 RepoHarness 项目一的条件化启示

映射日期2026-09-07；只对应既有 miles/SGLang/真实 coding harness 和 rh2 边界，不批准换框架或重写架构。

**第一，个人贡献可以来自成熟上游之上的跨层优化。** 本篇的示范不是“必须独创 PPO”，而是将真实执行带来的统计问题写成公式、形成训练对照、再连接独立任务结果。这与当前项目一的有限完成边界相容，不要求先建设动态任务生产平台。

**第二，原始身份、组统计、训练行和优化分母应分开验证。** 可先用固定小样本构造同一 rollout 的不同合法切分，检查 mask/token 不变时 loss 与梯度是否符合本项目声明的目标；再检查过滤是否改变了原组。无需先支付完整 SWE RL 成本。目标必须采用本项目实际算法，不直接把 P16 或 v1.0 的行对齐机制抄作标准。

**第三，数据筛选和 anti-hacking 是训练配方的一部分，但不是自动合理。** 本篇保留少量0/4任务，并限制高测试成本，给出了可用而非无限复杂的配方。项目需要测规则删除了哪些 repo／机制／长题；不能把中等通过率或较少测试直接等同更高研究价值。

**第四，共置异步值得作为资源组织的对照，而不是新的强制迁移。** 先比较当前 miles 执行成本和单节点限制；论文没有提供足够预算信息来决定我们必须从分离训推切回共置，也没有证明更多控制面能解决当前主要瓶颈。

| 候选验证 | 最小可辨识对照 | 由谁负责 |
|---|---|---|
| 样本切分与统计一致 | 固定token/reward：1行与合法多行；优势、mask、分母分别测 | 在现有adapter/消费点验证，不再造通用IR |
| 过滤是否改变有效任务分布 | 报告过滤前后 rollout/group/repo、长度及reward组成 | 任务与训练消费结合的我方工作 |
| 概率缺失与stale处理 | 明确 None/mismatch 发生时实际 drop、降级还是报错，验证消费分支 | 上游规则与本地接线共同核验 |
| 可信SWE闭环 | 固定model/harness/grader，报告数据成本及一项学习结果 | 我方实验责任，不用框架功能清单代替 |

本篇没有直接证明多 harness 混训、OPD 或诊断驱动任务生成的增益；这些仍是其他来源与本地探针要回答的问题。

## 12. 快速查阅与续读位置

| 问题 | 本文位置 | 原文位置 |
|---|---|---|
| 为什么同文本不能直接拼训练序列？ | §3 | §2.1，Eq.8–13、Fig.3 |
| sample-level 和 rollout-level 究竟差在哪？ | §4 | §2.2–2.3，Fig.4–5、Eq.14–16 |
| paper 的 async 是否严格 on-policy？ | §5.2、§8.6 | §3 Collocated Async RL；另见 C-async |
| 三臂实验基线到底用哪种 loss？ | §7.3 | §4.3，Fig.9 |
| 6K任务如何来、哪些中间数字没给？ | §7.1 | §4.3 Dataset Preprocessing and Filtering |
| 当前代码如何处理缺失 logprob？ | §8.1 | C-events → C-manager → C-adapter → C-trainer |
| 当前 reward 最终消费 raw 还是 shaped？ | §8.7 | C-agent-main → C-events → C-manager |
| 正式图形复核还差什么？ | §1.2、§10 | PDF Fig.1–12、Table1 的原始版面及版本首页 |

**后续只需优先补原始PDF与图形，不必重复整篇检索。** 对图7–10记录横纵轴、近似变化范围和异常段；对图6检查速度对照的额外标注；核对有无新增版本／补充附录，再据此更新覆盖状态和页码。当前作者自查不冒充独立审查。

## 来源链接

[P]: https://arxiv.org/abs/2608.17528
[P-pdf]: https://arxiv.org/pdf/2608.17528
[P-html]: https://arxiv.org/html/2608.17528v1
[M-publication]: https://www.microsoft.com/en-us/research/publication/agent-lightning-v1-0-towards-harnessed-agentic-rl/
[B]: https://www.microsoft.com/en-us/research/articles/agent-lightning-v1-0-%E5%BC%80%E6%BA%90%EF%BC%9A%E9%9D%A2%E5%90%91%E7%9C%9F%E5%AE%9Eagent-harness%E7%9A%84%E8%BD%BB%E9%87%8F%E7%BA%A7%E5%BC%BA%E5%8C%96%E5%AD%A6%E4%B9%A0%E6%A1%86%E6%9E%B6/
[C0]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/README.md
[C-coding]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/docs/75-example-coding-agent.md
[C-search]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/docs/65-example-search-r1.md
[C-instruct]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/docs/70-example-llm-in-sandbox.md
[C-async]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/docs/35-asynchronous-training.md
[C-config]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/docs/20-trainer-configuration.md
[C-proxy]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/server/proxy.py
[C-events]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/server/routes/events.py
[C-manager]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/agl_rollout_manager.py
[C-adapter]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/rollout_adapter.py
[C-adv]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/rollout_level_advantage.py
[C-loss]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/per_rollout_loss.py
[C-loss-test]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/tests/verl/test_per_rollout_loss.py
[C-trainer]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/verl/trainer.py
[C-swe-train]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/examples/swe_smith/train_smith_agent.py
[C-agent]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/examples/swe_smith/agents/smith_agent.py
[C-agent-main]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/examples/swe_smith/agents/smith_agent.py#L875
[C-store]: https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/agentlightning/server/store.py
