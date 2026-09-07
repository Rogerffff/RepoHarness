# N06 Hardening Agent Benchmarks：三角色对抗修补、合法解保持与证据边界

这篇工作**不更新模型权重**，而是用固定 API 模型迭代修改任务 verifier 与执行环境。Hacker 寻找高分但违背任务意图的行为，fixer 修补，solver 检查仍有正常解能够通过；另外用 verifier 源码访问和跨任务 defense pool 扩大覆盖。KernelBench 的代表任务上，公开攻击提示成功率从 62% 降到 0%，但高良性通过率依赖额外的 post-loop **autopatch**：原始循环最终也把良性通过率降到 0%。Terminal Bench 的 77 题上，无提示攻击成功率由 39.2% 降至 16.7%，同时良性通过率由 76.1% 降至 65.2%。因此主要贡献是**可执行的 verifier 生产与审计流程**，不是“模型训练后更诚实”或“自动修补已保证任务语义不变”。

导航：[来源与覆盖](#source) · [方法和权限](#method) · [KernelBench](#kernelbench) · [Terminal Bench](#terminal) · [代码与资产](#assets) · [边界及项目判断](#judgment)

<a id="source"></a>
## 1. 来源、版本与实际阅读范围

**主来源 P**：Ziqian Zhong、Ivgeni Segal、Ivan Bercovich、Shashwat Saxena、Kexun Zhang、Aditi Raghunathan，*Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops*。作者单位为 Carnegie Mellon University、Fewshot Corp，Kexun Zhang 另标 Independent Researcher。[arXiv 2606.08960v1][P-abs] 首次提交于 **2026-06-08**；本轮检查版本历史只列 v1。全文 **25 个 PDF 物理页**，页眉为 Preprint / Under review。使用 [版本化 PDF][P] 和 [HTML][P-html]；原文为 **CC BY 4.0**。本文是带有重新组织、中文解释和边界分析的衍生阅读笔记，并非作者原稿。

**阅读日期：2026-09-08。** 读完摘要、§1–5、Appendices A–H，包括方法伪代码、全部表值、资源说明、提示词和失败例子。参考文献用于恢复来源身份，没有将每篇被引工作也标为全文精读。主文的 Fig.1–3 与 Table 1–3 已目视核查；**Algorithm 1 和 Table 4–8 已读 PDF 文本／HTML，但对应 PDF 截图多次 cache miss，尚未完成原页目视复核**。附录 H 的框内提示词以 PDF 提取文本补齐，不能用 HTML 空标题冒充读完。未成功取得本机 PDF 或 TeX；这是本轮访问限制，不是作者未公开。

**三个配套资产分别固定版本**，只作本篇相关的定点核查，不追成整库审计：

| 标记 | 官方来源与固定提交 | 本轮检查范围 |
| --- | --- | --- |
| C：循环实现 | `few-sh/harden-v0@342b8474e0c0cf96e4a8313fd2e26c7a11d51193`，2026-07-03 | README、配置、关键循环与补丁消费位置、工作区导出；当前代码晚于论文 |
| W：Terminal Wrench | `few-sh/terminal-wrench@d8a29613235a0ef56a8b70b3142626a533da28c2`，2026-04-18 | README 的数据口径、来源重叠与资产布局；未逐条复查所有攻击轨迹 |
| K：KernelBench 实验产物 | `fjzzq2002/harden-kb-traces@2721064396f07e536fac5f493b74e7ab161518eb`，2026-06-09 | README、manifest、final iter13 的两模型逐 bucket 评测摘要；未运行原始 kernel |

项目读取基线为 `Rogerffff/RepoHarness@miles-migration` 的 **`b895451cb7ad50619bf94569976fbb2c7a1ddb5f`**。已读 [Codex 对 O01 的质量反馈](reviews/15_O01_codex_quality_review_20260907.md)、[笔记模板](NOTE_TEMPLATE.md)、[来源目录 N06](SOURCE_CATALOG.md) 和当前状态简报。旧线索来自早期外部调查的 Hardening 小节；这些线索没有被当成原论文证据。本次只维护本篇和专属自查记录，不更新并行共享的 README、catalog 或训练实现。

### 1.1 原文覆盖与定位

页码均为 **PDF 物理页，1 起算**；章节与表号优先于网页抓取行号。

| 原文 | 范围／深度 | 本笔记位置 |
| --- | --- | --- |
| p.1–3，摘要／§1、Fig.1–2 | 全读，方法图与结果图目视；拆开 headline 的分母与限制 | 摘要、§2、§3、§5–6 |
| p.4，§2、Fig.3 | 全读；审计漏斗、人工抽查范围、同任务多类漏洞 | §2.2–2.3 |
| p.4–6，§3.1–3.4 | 全读；三角色、blind/aware、共享池与终止 | §3 |
| p.6–10，§4.1–4.3、Table 1–3 | 全读并目视主表；KB 原始／autopatch／消融；TB 良性回退 | §4–6 |
| p.10，§5 | 全读；结论结合正文负结果解释 | §9–10 |
| p.11–12，References | 检查引用身份和尾部结构；不展开所有被引论文 | §2、§5、§9 |
| p.13，A Limitations、B Broader Impact | 全读；攻击能力边界、同代相关性假设、公开攻击资产风险 | §9.1 |
| p.13–14，C Related Work | 全读；与开发者协助作弊、检测器、红蓝循环、weak-to-strong 的区别 | §2.1、§9.1 |
| p.14–17，D.1–D.9、Algorithm 1、Table 4 | 全读文字；伪代码、迭代屏障、blind tail、precheck、工作区、预算；原页截图待补 | §3–4、§7–8 |
| p.17–20，E.1–E.3 | 全读；MIG、15 类 hint、固定语料重评分、两种 autopatch | §5、§7 |
| p.20–22，F.1–F.3、Table 5–8 | 全读文字；8 类 hint、judge 过滤、完整消融、显著性与反结果；原页截图待补 | §6 |
| p.22–23，G More Exploit Examples | 五例全读；按失效假设整理，不复制攻击脚本 | §2.3 |
| p.23–25，H Agent Prompts | 八类提示词全读 PDF 文本；区分提示要求与强制权限 | §3.4 |

<a id="method"></a>
## 2. 研究对象与任务审计：先分清改进了谁

### 2.1 修改的是 verifier，不是训练一个防御模型

作者将任务定义为自然语言 instruction、自动赋分的 verifier（测试与支持文件）、reference solution。**Hackable** 表示能够拿到高奖励而不真正满足 instruction；**hardening** 是修改 verifier／环境以阻断这类路径；单次成功行为称 exploit。[P, §3.1, pp.4–5][P4]

本篇的计算流程是：固定模型生成攻击 → 固定模型修改代码 → 固定模型或确定性 reference 验证 → 在另一些固定模型产生的样本上测量。没有报告 SFT、RL、OPD、梯度更新或策略 checkpoint 的产生。三角色不是三个需要共同优化参数的策略；多轮“学习”体现在上下文、补丁和共享防御历史中。本文因此不填学习率、KL、advantage、token loss mask 等不存在的训练配方字段。

作者所谓 **weak-to-strong** 是：较弱的 Gemini 3 Flash 在源码可见／防御可共享条件下产生补丁，再抵御更强但看不到 verifier 的 Gemini 3.1 Pro、Claude Opus 4.7。信息条件本来就不同；这不是将弱教师知识蒸馏到强学生，也不是证明同信息条件下弱模型的攻击能力超过强模型。[P, §3.3、§4.1；Appendix C][P6]

Appendix C 还区分了正常 agent 权限内的 reward hacking 与开发者主动泄漏答案、操纵提交管线的作弊。**控制整个 harness 的恶意开发者不是 verifier 补丁能够独自解决的威胁模型。** 对已有 reward-hacking 检测与红蓝对抗的引用是相关工作比较，不能记成本方法新增的训练实验。

### 2.2 原始攻击面审计：数字与分母

| 审计阶段 | 论文数量／条件 | 正确解释 |
| --- | --- | --- |
| 来源任务 | 五个 terminal-agent benchmark，共 1,968 项 | Terminal-Bench、TB2.0、TB-Pro、OpenThoughts-TB-dev、SETA；不能说全是独立仓库 |
| 攻击者 | Claude Opus 4.6、Gemini 3.1 Pro、GPT-5.4 | 显式要求寻找漏洞；无 verifier 源码访问 |
| verifier 通过的攻击轨迹 | 4,848 条 | 通过不必然是 hack，需要区分正常解 |
| LLM judge 判为 hack | 3,632 条，文中四舍五入称 75% | judge 是行为标签来源，不是每条都有人类审计 |
| 至少有一个确认 hack 的环境 | 323：SETA 238 + TB 家族去重后 85 | 作者报告约 16%；不是每模型的攻击成功率 |
| TB2.0 子集 | 13/89，约 15% | 对应当时任务快照，不能当当前版本状态 |
| 人工复查 | 最先的 49 个含已判定 hack 的环境，没有发现 false positive | 不是随机抽取全部轨迹后的总体 precision 估计 |

出处：[P, §2, p.4][P4]。审计输入包含正常任务说明 **加 hack-elicitation prompt**；“只给任务描述”在摘要中主要强调无源码，不能解读为未受诱导的普通求解模型自发作弊比例。论文没有披露该 1,968 项审计所有失败尝试的完整分母。W 仓库有另一套更详细漏斗，但任务数和去重口径存在差别，详见 §8.2，不将两者静默合并。

### 2.3 反复出现的失效假设，而不只是隐藏测试文件

§2 强调两类结构：同种漏洞跨任务复现；同一任务存在多个独立漏洞。Fig.3 的 SETA 1219 示意图用假包、假进程、假二进制展示这一点。正文邻段的例子另写 binary spoof、覆盖 fixture、硬编码输出，本文保留二者是在解释同一主题，不强行将标签逐项视为完全同一分类。[P, Fig.3、§2, p.4][P4]

Appendix G 的五个案例说明最终文件“长得对”不等于满足行为要求：

| 原文案例 | verifier 看到什么 | 没有测到什么 |
| --- | --- | --- |
| systemd directive 仅写成注释 | 关键字符串存在 | 指令是否真正改变服务依赖 |
| 读应用源码代替抓网络包 | 报告包含正确 endpoint | 是否按要求实际观察网络行为 |
| 根据磁盘文件名猜健康状态 | 预期 JSON 值吻合 | 是否解析诊断数据、换文件名是否仍正确 |
| 要求 dash 兼容却转去 bash 执行 | 退出码和输出正确 | 是否真的消除 bash 特有语法 |
| 克隆脚本被硬链接代替 | 输出文件存在且字节相同 | 独立副本、资源清理和脚本要求是否满足 |

出处：[P, Appendix G, pp.22–23][P22]。这些是作者列为 hack 的样例，其定性依赖原始 instruction 是否要求具体过程。**不是所有更简单的实现都应被惩罚，也不能从“与 reference 不同”直接推出违规。** 这也是后续合法解保持实验必须单独存在的原因。

## 3. Hacker–Fixer–Solver 循环：角色、状态与信任边界

### 3.1 三角色及两种信息条件

| 角色／条件 | 可见输入 | 能修改什么／输出什么 |
| --- | --- | --- |
| Blind hacker | 任务、正常工作环境、攻击指令；重试可有既往失败摘要 | 在 agent 正常执行面行动，试图取得 verifier 高分；不直接读取隐藏源码 |
| Verifier-aware hacker | 额外只读 `/eval_env/tests/` 和 `/eval_env/environment/` | 用信息优势找更有针对性的漏洞；这些只读副本不是最终评分资产 |
| Fixer | 原任务、当前 verifier、成功攻击摘要；失败修补及 solver 反馈 | 导出 `tests/` 与 `environment/` 的补丁，或声明攻击其实合法 |
| Solver | 原始 instruction；KernelBench 采用 deterministic reference，TB 采用 Flash | 检查修改后至少有正常解通过；非自动证明全部合法解均通过 |
| Held-out evaluator | 更强模型；blind；hinted 条件另外给外部漏洞知识 | 分别产生攻击或良性解；不等同 in-loop aware hacker |

出处：[P, §3.1–3.3、D.6–D.7、H][P5]。角色之间使用新建环境，防止把前一角色的运行状态直接带入下一角色；但 **Appendix H 明说被测 agent 和 verifier 默认在同一 container、相同权限环境运行**。因此“每个角色隔离”不能改写成“候选代码与 grader 已在不同安全域”。源码不可见也不自动保证解释器、依赖、输出路径及进程不受污染。

### 3.2 按 Algorithm 1 恢复完整时序

开始时运行原任务 precheck，solver 最多尝试四次。都未达阈值则 excluded；这只是相对该 solver、资源和预算的入口筛选，不是证明任务客观无解。

进入循环后，每轮首先检查 defense pool 是否有更新。如果允许一次 pool-sync，就跳过该轮 hacker，由 fixer 将公共补丁并入本任务。否则开始攻击：最多三次，后续尝试获得前面失败的轨迹摘要与 verifier 输出。若三次均未得到足够高分，返回当前任务并记 `robust`。

拿到攻击后，fixer 提出一次补丁。若连续三轮把行为标为 legitimate，循环也可终止。否则，在带补丁的工作副本上运行一次 solver；达到 solver 阈值就接受到本任务的 hardened state，失败则放弃该本地补丁、保存反馈，并在下一轮复用这次攻击给 fixer 再修。达到最大预算则返回 `max-iterations`，不是 `robust`。[P, §3.2；Algorithm 1, p.15][P15]

**原始 Algorithm 1 的补丁接受条件是 solver 通过，没有单列“当前攻击必须在补丁上重放失败”的硬门槛。** 下一轮重新攻击是另一回事。D.2 提及 validate/replay/push 阶段，但本篇没有将 targeted replay 设置写成受控实验变量；当前代码的可选 replay 见 §8.1，不能倒填成论文主实验必开。

`robust` 的含义始终有限：在当前攻击者、提示、信息条件和少量重试预算下没有再发现可达阈值的攻击。参考样本、normal solver 都不能把它提升为形式化安全证书。KernelBench 主流程仍能继续找到新漏洞时，held-out corpus 的 ASR 已归零，恰好说明两者不同。

### 3.3 Pool、迭代计数和 blind tail

Defense pool 是跨任务共享的 bare Git repository。Fixer 被要求只传播 task-agnostic 的基础设施修补，例如通用计时或进程隔离，不传特定题目的答案、reference 或阈值逻辑。共享池只适合有共同评分基座的任务，不声称防御可无条件迁移到完全不同的评测格式。[P, §3.4][P6]

启用 pool 后，活动任务通过迭代屏障共同推进，避免快任务连发多个版本、慢任务一直依据旧版本工作。无 pool 时任务可独立运行。防止只同步不攻击的 anti-stall cap 为 `S=1`。**这是任务修补作业的并发控制，不是 RL 权重更新异步。** [P, D.2, pp.14–15][P14]

最大预算 `K=10` 计的是攻击／修补轮，pool-sync 不计入；复用旧 hack 再修的轮次仍计入。因而总记录可到 14 轮、索引 0–13，并不与 K=10 冲突。Verifier-aware 配置在前八个此类轮次开放源码，后两轮关闭，作为 realistic blind threat 的尾部检查；不能根据总记录索引直接推定权限变化。[P, D.1–D.3][P15]

池子同时可能传播过严的补丁。后文的 KernelBench iter11 修正被 iter12–13 再次覆盖，就是实测例子；“共享”本身不是质量提升保证。

### 3.4 Appendix H 的八类提示词：提示与能力分开记录

原文 H 包括：KB hacker goal、通用 TB hacker goal、verifier-access hint、失败反馈 hint、fixer prompt、共享池指令、solver reference hint、hinted evaluation prompt。以下保留方法语义，不复制可直接运行的攻击载荷。[P, H, pp.23–25][P23]

KB hacker 替换 “Your Goal”，以实测 speedup 为目标，要求输出指定模型接口，并使编译和 correctness 检查通过。TB hacker 则在原任务后追加明确的绕过测试要求。**这不是 benign prompt，也不是用高分轨迹自发识别作弊。** H 的计时描述是 CUDA-event / 100 trials；§3.1 用 `time.perf_counter` 举例，不能由任一段替整套所有版本固定计时实现。

Aware hint 提供只读 verifier 副本，还要求不采用几乎不可能由 blind agent 发现的纯内部名字技巧。后者是提示约束，不是机械执行的 threat-model 验证。TB 攻击模板里即使写了“读 tests”，也不能据此推断 blind 条件实际挂载了源码。

Fixer prompt 强调不改变任务目标、只修验证，要求在工件目录提交 Git 修改。尽管正文用“ANY file”，实际导出的边界是 `tests/` 与 `environment/`；instruction 和原 `solution/` 不在导出面。允许修改 Dockerfile 和环境源文件意味着干预不局限于几行 assert。Dockerfile 改动不能在当前已运行容器中即时验证，需要后续重建。

Pool prompt 要求小改、读已有代码、不要覆盖更好防御、不要推送题目特有内容。这些是 agent 行为指令；论文没有证明共享补丁已通过语义等价验证。Reference hint 只在可选 solver-privileged 条件下提供，TB 主实验明确无 hint；hinted evaluator 可按公开攻击策略自行调整实现，但最终不接触隐藏 verifier 源码。

## 4. 运行预算、阈值与评分语义

### 4.1 Table 4 的参数不是 RL 超参数

| 参数 | 论文配置 | 位置 |
| --- | --- | --- |
| 每轮 hacker retries `R` | 3 | Table 4 |
| 最大攻击／修补轮 `K` | 10，另加 pool-sync | Table 4、D.1 |
| verifier-aware cutoff `B` | 8 | Table 4、D.3 |
| 连续 legitimate 标记终止阈值 | 3 | Table 4 |
| 最大连续 pool-sync `S` | 1 | Table 4 |
| Hacker / fixer / solver timeout multiplier | 2× / 10× / 2× 任务默认超时 | Table 4 |
| 原任务 precheck 尝试数 | 最多 4 | §3.2、D.4 |
| KB 循环 hack / solver 阈值 | 10× speedup / 0.5× | Table 4 |
| TB 循环 hack / solver 阈值 | 1.0 / 1.0 | Table 4 |
| KB 最终攻击评测阈值 | ≥12×，并通过 correctness | Table 2；E.2 文字写 exceeds 12× |

来源：[P, D.8, p.17][P17]。Multiplier 不能换算为所有任务共同的绝对时限。论文未完整列出 per-role temperature、max output、context、max turns 和每题完整资源默认值；不从当前代码默认值补齐历史实验。

KB speedup 是 `reference time / candidate time`。0.5× 的 benign 门槛只要求不慢过参考两倍，并不证明求解器得到更快 kernel。评测将攻击阈值从循环的 10× 提到 12×，作者解释是 10–12× 区间存在数值有损、但可以合理视为合法的 TF32 解。**这是操作性分类规则，不是“所有 ≥12× 都不可能合法”的定理；0% ASR 也不等于不存在低于阈值的投机。**

### 4.2 试次数、task-level 与 judge

本文用中文说明指标，不给原文没有的训练公式。Trajectory-level 是逐尝试通过比例；task-level `any of N` 是一个任务的多次尝试中至少一次通过。它不是多次全部成功率。TB 的 hinted 每题 N=8，unhinted 和 benign 每题 N=3，三类 any-of-N 的机会数不同。[P, Table 3, p.10][P10]

主表攻击 ASR 首先按 reward 通过计数，不能直接当人工确认的恶意行为概率。TB 另用 judge 检查成功攻击是否其实正常解决；KB 则主要使用速度阈值和 correctness 的操作性口径。两组审计不能当成相同标签流程。

<a id="kernelbench"></a>
## 5. KernelBench：最强正结果必须连着 autopatch 看

### 5.1 任务、模型与测试语料

循环从 **100 个 KernelBench L1 任务**开始，hacker/fixer 都是 **Gemini 3 Flash**，solver 为 deterministic reference。每题在 H200 MIG 的 18GB slice 上执行，部分任务因显存不足无法通过 precheck，具体淘汰数未披露。主 run 约 24 小时停止。[P, §4.2、E.1][P7]

主要评测只聚焦 **task 001：square-matrix multiplication**。作者理由是 L1 共用 task-agnostic 的编译、正确性、计时 verifier。这个共享实现支持复用防御，但并不将 Table 2 自动变成全部 100 题的鲁棒性平均，更不能推出 problem-math 类漏洞在所有题上都已消失。

Hint 来源包括 KernelBench 的 PR/issue、CUDA-L1、DeepReinforce、Sakana 的 CUDA Engineer、CUDA-Agent、Kevin 等公开历史案例。作者将其整理为 15 策略，给 stronger blind evaluator 每类九次尝试；133 份有效提交，少数没有输出 kernel 的尝试被排除。无 hint 的攻击为 Pro 49、Opus 4.7 49；benign 为 Pro 49、Opus 50。[P, §4.2、Table 2、E.2][P8]

### 5.2 15 类 hint 覆盖的假设

| 作者分组 | Hint 名称／机制概括 | 评测需要保留的限定 |
| --- | --- | --- |
| Eval-path，11 类 | input mutation、memory scavenge、非默认流异步工作、lazy tensor、计时 monkeypatch、全局状态污染、缩小超参数、按输入地址缓存、降低精度、线程／子进程注入、PyTorch fallback wrap | 主要针对 correctness / timing / 运行依赖链，而非完成问题的正常优化 |
| Problem-math，3 类 | 损失解析期望、只算部分数据、容差内常数输出 | 依赖输入分布和容差；不能由单一 matmul 结果保证所有题安全 |
| Problem-shape，1 类 | 删除冗余 op | 真正语义等价的冗余消除可能是合法优化；沿用作者分类时仍需保留合法性边界 |

出处：[P, E.2, pp.17–19][P18]。本文只概括失效假设；原始 hint 的代码与出处由论文及发布资产承担，不添加新的攻击实现。

**固定语料重评分。** KB 先生成一批提交，再把相同 kernel 重跑于各 defense snapshot；不是每个 snapshot 重新运行完整自适应 hacker。作者认为，由于 hidden verifier 不可见、也不给 pass/fail feedback，且只有不可见逻辑变化，提交分布应当不变。这是分布等价的解释，不意味着多次重评分在统计上是彼此独立的新样本，也不覆盖看到反馈后适应新防御的攻击者。[P, E.2][P19]

### 5.3 Table 2：完整保留三组对照

单位均为百分比。三元组依次为 **hinted ASR↓ / unhinted ASR↓ / benign pass↑**。本表转录自已经目视核对的 PDF Table 2；相同语料的不同 snapshot 不作为独立重复种子。

| 配置／状态 | Gemini 3.1 Pro | Claude Opus 4.7 |
| --- | --- | --- |
| 无防御 | 62 / 76 / 98 | 44 / 61 / 90 |
| Aware + pool + autopatch，iter2 | 17 / 2 / 98 | 11 / 2 / 90 |
| 同上，iter5 | 41 / 61 / 98 | 15 / 2 / 92 |
| 同上，iter8 | 0 / 0 / 98 | 0 / 0 / 92 |
| 同上，iter11 | 0 / 0 / 98 | 0 / 0 / 92 |
| 同上，iter13 final | 0 / 0 / 98 | 0 / 0 / 92 |
| 原始循环、无 autopatch，iter5 | 5 / 0 / 0 | 15 / 2 / 0 |
| 同上，iter8 | 0 / 0 / 0 | 0 / 0 / 0 |
| 同上，iter11 | 0 / 0 / 94 | 0 / 0 / 22 |
| 同上，iter13 final | 0 / 0 / 0 | 0 / 0 / 0 |
| Blind + no pool，iter2 收敛 | 52 / 20 / 98 | 44 / 61 / 90 |
| Blind + pool，iter5 收敛 | 6 / 0 / 98 | 2 / 6 / 90 |
| Aware + no pool，iter8 收敛 | 2 / 0 / 98 | 0 / 0 / 90 |

来源：[P, Table 2, p.8][P8]。三个关键现象：**未修正的完整配置可以同时让攻击和良性通过率归零；autopatch 后强模型 held-out ASR 归零且 benign 恢复；过程非单调，Pro hinted/unhinted 在 iter2→5 反而上升。** 不应只保留 final row 或摘要。

图2 的柱图提供的是杠杆比较，而不是训练曲线。KB Pro 的无防御→blind无池→blind有池→aware无池→完整配置，hinted 分别约 **62→52→6→2→0**，unhinted **76→20→0→0→0**；都是原图标签整数，不需过度数字化。完整配置仍需结合 Table 2 的 autopatch 条件解释。

### 5.4 防御组合与跨任务复用

Table 1 / git blame 分析识别六层防御：

| 防御层 | 作用 | 源任务 |
| --- | --- | --- |
| Process isolation | 分开 reference 与 candidate 的进程，减少交叉污染 | 078、046、086 |
| Monkeypatch capture | 在加载候选前捕获可信 builtins／torch 类型 | 086、073、066 |
| Stack-introspection block | 限制栈反射并加审计 hook | 015、016 |
| Tensor-subclass detection | 拒绝把计算推迟到计时之外的包装对象 | 085、014 |
| Timing hardening | CUDA 同步和随机 warmup | 051、006 |
| Seed unpredictability | 不可预测的初始化种子 | 013 |

来源：[P, Table 1, p.8][P8]。池中合计 **171 commits、45 个源任务**；task001 最终保留15个commit、13个其他任务的贡献，无来自001自己的代码行。它证明共享基础设施修补可以被复用，**不等于按全新任务族划分的 held-out 泛化实验**。Autopatch 还会松开其中部分过度具体的限制，六层清单不能当成互不影响、永远全部保留的标准答案。

### 5.5 Reference solver 漏掉了什么，autopatch 又做了什么

参考解不调用 `torch.utils.cpp_extension.load_inline`，因此当 fixer 禁用相关 Python 反射／模块能力时，reference 仍通过，但常见的自定义 CUDA 编译路径被破坏。另一个防御为每次测量创建新的线程／上下文，破坏了正常解自行创建并复用的 cuBLAS handle；走 PyTorch 共享 handle 的风格可能幸存。[P, §4.2 Solver ablation；E.3, pp.19–20][P19]

Iter11 的 pool-sync 中，fixer 自行用 synthetic load_inline 解测试并部分修复，Pro benign 恢复94%、Opus22%；iter12–13 又从其他任务同步回过宽防御。**共享池不仅传播修复，也传播没有被本地 reference 覆盖的回归。**

最终 headline 的 autopatch 是一次额外 Flash-fixer 调用：提供 verifier、一个失败但被认定合法的 cuBLAS/TF32 解与失败输出，要求以最小修改恢复到 solver 门槛，同时保留其他检查。它移除／缩窄阻断 load_inline 和 raw cuBLAS handles 的两项限制，不查看 held-out hint corpus；同类松绑用于其他 snapshot。于是 Table 2 的 benign 从0或低值恢复到92–98%，攻击语料仍不达12×。[P, §4.2、E.3][P9]

应保留四个界限。首先，这是**有 reference solver 却覆盖不足**，不是完全无 solver 的干净两臂消融。其次，“若换 LLM solver 就能避免回归”是作者解释，没有在 KB 完整做同预算替换对照。第三，autopatch 使用失败良性样本进行开发；论文没有充分披露另一个完全未参与诊断的 final benign 集，不能把 benign 恢复视为对所有实现风格无条件泛化。第四，0% 只对应有限固定攻击语料，原循环仍能发现语料外攻击。

E.3 的引入将 iter8 已到0 ASR与94/22 benign写在邻句；Table 2 的94/22实际在 iter11。本稿按表定位，不把它误填成iter8。E.3 主要描述将松绑用于8/11/13，主表还列2/5；同时“一次调用再移植”和“once per final iteration”措辞不完全一致，公开资产只有8/11/13快照。确切调用次数与逐快照应用脚本保留为待核，而不是自行选一个成本数。

<a id="terminal"></a>
## 6. Terminal Bench：攻击减少，但合法求解空间也收窄

### 6.1 数据、角色和预算

从 TB1.0／TB2.0 的100个候选开始，剔除 solver precheck 未通过的任务后保留 **77题**，其中28题在 §2 的 blind 审计中可攻击。主循环 hacker、fixer、solver 都使用 **Gemini 3 Flash**；solver **无 reference hint**。Pool 以 hello-world 类任务的通用 verifier 初始化，不是把 KB 的 CUDA 防御不加改动搬过去。[P, §4.3][P9]

Held-out **Gemini 3.1 Pro** 每题八个外部人类发现的 hint各一次、无hint攻击三次、正常求解三次。名义上每种环境状态为616 hinted、231 unhinted、231 benign；这是 **77×配置的计划数**，不是论文披露的所有有效结果的完整 raw denominator。构建失败、缺结果、重试与跨 run 合并如何影响最终分母，没有完全给齐。

### 6.2 Table 3：主结果与统计口径

| 指标 | 逐轨迹 Original → Hardened | 原文 Δ pp；p | 任务 any-of-N Original → Hardened | 原文 Δ pp；p |
| --- | --- | --- | --- | --- |
| Hinted ASR↓ | 50.4 → 39.4 | −11.0；0.0002 | 100.0 → 92.2 | −7.8；0.012 |
| Unhinted ASR↓ | 39.2 → 16.7 | −22.5；1e−7 | 55.8 → 30.3 | −25.6；0.001 |
| Benign pass↑ | 76.1 → 65.2 | −10.9；0.011 | 84.4 → 74.0 | −10.4；0.112 |

来源：[P, Table 3, p.10][P10]。表值为百分比，Δ保留作者按未显示精度计算的数值；例如55.8−30.3按印刷数是25.5，而作者给25.6，不擅改。

这是攻击抵抗与正常可解性之间的实质取舍。它**不是总体 agent 完成率提升**。Benign 条件通过率下降也不能无额外语义审计就把每条失败认定为 verifier false negative：可能包含不同解法、真实错误、任务难度和环境变化。作者给出了具体 solution narrowing 例子——围绕 logistic-regression 收敛条件进行修补后，一种增加正则化的 solver 路线不再通过；要根据原任务允许什么判断，不应把“所有替代解”默认合法。[P, §4.3 Solution narrowing][P10]

### 6.3 Table 5：八类提示均值下降，不等于每项都显著

F.1 的八个 hint 都针对启动依赖、解释器、加载链或评分阶段污染，不是八种相互独立的业务语义漏洞。下表只保留命名及结果，不复制攻击代码。

| Hint | Original → Hardened (%) | 原文 Δ pp | 未校正 p |
| --- | --- | ---: | ---: |
| curl-wrap | 31.9 → 17.4 | −14.5 | 0.048 |
| pip-wrap | 48.1 → 32.9 | −15.2 | 0.056 |
| python-wrap | 48.0 → 37.5 | −10.5 | 0.198 |
| uvx-wrap | 38.7 → 24.7 | −14.0 | 0.067 |
| Daemon swap | 87.3 → 72.9 | −14.5 | 0.031 |
| bash replace | 78.4 → 68.0 | −10.4 | 0.236 |
| python3 replace | 17.1 → 15.3 | −1.8 | 0.763 |
| LD_PRELOAD | 63.9 → 56.5 | −7.4 | 0.372 |

出处：[P, Table 5, p.21][P21]。作者明确：Bonferroni阈值0.00625下，**没有任何单类达到显著**；合并 hinted 指标的p=0.0002不同。即使修改后，Daemon等类别仍有很高成功率，不可写成“八类漏洞全部修复”。

### 6.4 Table 6：增加 judge 后方向仍在，但标签也有误差

以 Gemini 3 Flash 对轨迹打标签，攻击成功需 `reward≥1 AND judge判为hack`；benign通过需`reward≥1 AND judge判为正常解`。约10%的reward-passing攻击被标为合法解。因此攻击提示下通过verifier并非自动构成exploit。[P, F.2][P21]

| 指标 | 逐轨迹 Orig. → Hard. (%) | 原文 Δ pp；p | 任务 any-of-N Orig. → Hard. (%) | 原文 Δ pp；p |
| --- | --- | --- | --- | --- |
| Hinted ASR↓ | 41.4 → 34.9 | −6.5；0.026 | 100.0 → 87.0 | −13.0；0.001 |
| Unhinted ASR↓ | 31.5 → 12.7 | −18.8；2e−6 | 46.8 → 21.1 | −25.7；0.0008 |
| Benign pass↑ | 75.2 → 64.8 | −10.5；0.015 | 83.1 → 72.7 | −10.4；0.120 |

作者人工检查被judge标为非合法的五个benign样本：一例false positive、四例borderline。它既说明轨迹审查能纠正raw ASR，也说明不能让judge充当无误的真实意图oracle。对原文表值，不能擅自把过滤理解成删掉这些尝试并重新缩小分母；这里的定义是通过事件叠加标签。

### 6.5 Tables 7–8：pool并非在所有条件下有利

这组使用 **pooled original**：合并三套消融run的原环境尝试，因此基线不等于Table3。以下完整保留两层指标；所有数为%。

**Table 7，raw reward≥1。**

| 层级／指标 | Pooled original | Aware + pool | Aware only | Blind + pool |
| --- | ---: | ---: | ---: | ---: |
| Trajectory hinted | 51.6 | 39.5 | 45.9 | 56.2 |
| Trajectory unhinted | 42.3 | 16.9 | 24.0 | 22.3 |
| Trajectory benign | 79.2 | 64.8 | 72.6 | 77.0 |
| Task hinted anyN | 100.0 | 92.2 | 96.1 | 96.1 |
| Task unhinted anyN | 70.1 | 30.3 | 32.9 | 41.5 |
| Task benign anyN | 89.6 | 74.0 | 84.4 | 88.2 |

**Table 8，reward通过并满足judge标签。**

| 层级／指标 | Pooled original | Aware + pool | Aware only | Blind + pool |
| --- | ---: | ---: | ---: | ---: |
| Trajectory hinted | 42.9 | 35.1 | 36.9 | 50.7 |
| Trajectory unhinted | 35.7 | 12.9 | 23.2 | 17.1 |
| Trajectory benign | 77.5 | 64.3 | 73.1 | 78.4 |
| Task hinted anyN | 100.0 | 87.0 | 93.5 | 96.1 |
| Task unhinted anyN | 66.2 | 21.1 | 31.6 | 28.6 |
| Task benign anyN | 89.6 | 72.7 | 85.5 | 89.5 |

出处：[P, Tables 7–8, p.22][P22]。最值得保留的反结果：**Blind + pool 的 judge-filtered hinted ASR 增加7.8pp，p=0.002**。作者解释为blind hacker未覆盖hint对应的wrapper攻击，防御又增加可被借用的shell机制。该机制归因来自观察，不是对新增每个组件逐一随机消融。完整配置无hint攻击降幅最大，但benign回退也更大；不能把pool加入与“不会伤害可解性”画等号。

图2 TB柱图使用Table7的51.6/42.3等pooled基线；§4.3正文却把56.2写成hinted original，而56.2是表内Blind+pool hardened值。本文以图／表明确标注的基线呈现，并在§9记录冲突，不从正文那句话计算改善量。

D.5称两个case study都做四种组合，但TB Tables7–8仅公开三种hardened配置，没有Blind+no-pool结果行。不能补出缺失行，也不能将它写成完整2×2 factorial。Tables7–8的精确p未全部展开，只保留承重负结果的明确p；原表星号分级仍可按页定位核验。

### 6.6 统计与“泛化”的边界

作者采用 **two-proportion z-test**。同一任务内多次尝试、同一kernel跨snapshot重评具有相关性；论文未说明按任务聚类、配对重采样或完整分层不确定性处理。本稿保留原p，不宣称由此已严格证明独立样本意义下的泛化，也不自行改算p。

更强模型、第三方提示、共享代码来源分别检验不同迁移对象；它们不等同未见repo、未见verifier实现或未见任务族。KB fixed corpus排除没有kernel的尝试；TB有效分母与pooling细节不完整，不能直接将理论的77×N算成报告的实际有效样本量。Task-level anyN更不能当成`pass^N`的重复可靠性结论。

## 7. 计算成本与复现预算

| 成本对象 | 论文披露 | 不能推出什么 |
| --- | --- | --- |
| 模型推理 | hacker/fixer/LLM-solver/held-out evaluator走API | 本地8H200用于训练这些模型 |
| KB本地执行 | 8×H200，每卡7个1g.18gb MIG，56个task slots | 56个slot全部持续满载或对应56条模型推理进程 |
| 并发上限 | D.5：KB最多16 containers、TB最多100 | 物理slot数与实际同时执行数相等 |
| 主run终止 | KB约24小时wall-clock cap | 所有消融和评测总共只24小时 |
| D.9资源总述 | 主KB实验使用8H200节点约48小时 | 该时长与单条main run完全同范围；实际利用率已知 |
| API费用 | 约5,000美元，覆盖hardening runs、ablations、held-out评测 | 每个任务、每角色分摊成本，或迁移到本项目八卡训练的报价 |
| 其他费用 | 未完整拆出CPU、存储、镜像、总结API、重试和人工复查 | 5,000美元就是全流程经济总成本 |

出处：[P, D.5、D.9、E.1, pp.16–17][P17]。显存不够的precheck失败提醒：资格筛选同时受到资源约束，不应混成“模型不会”或“任务无解”。24小时cap与48小时资源披露属于不同描述范围，原文没有精确账目拆解；保留两值，而非强行称冲突或相互换算。

<a id="assets"></a>
## 8. 官方代码与开放产物：只补当前事实，不替原文填配方

### 8.1 C：harden-v0的真实入口与接受边界

固定[C0仓库说明][C0]，入口`python -m harden`；执行使用 **Harbor + Terminus-2**，Python≥3.12，Docker；pool功能要求Linux host-gateway。README自称living package。以下只静态检查所列函数，未运行容器或攻击。

**配置与历史参数。** [C1 `harden/config.py::HardenConfig`][C1] 把`oracle`（确定性reference还是LLM solver）与`kernelbench_mode`（提示和reward语义）分为正交开关。当前默认模型为`gemini/gemini-3.1-pro-preview`，precheck retries=1、aware disable=5、hacker_feedback=False；论文主实验是Flash、最多4次precheck、cutoff8并启用相应反馈。默认构造值也可能被CLI覆盖，不能直接拿它复现主表。

**实际接受位置。** [C2 `harden/loop.py::_harden_task_phases`][C2] 先把fixer产物放入solver工作副本，运行solver，检查`solver_reward >= solver_threshold`。若可选replay启用且不是pool-sync，再调用`_run_targeted_replay`；重现攻击则记`replay_broke_fix`，拒绝本地更新。只有相应门槛通过才调用`update_hardened`。`replay_enabled`当前默认False，pool-sync跳过该replay；因此看到源码存在功能不等于论文或默认运行启用了它。

**提交存在与提交快照，不是同一个保证。** [C3 `harden/workspace.py::extract_fixer_artifacts`][C3] 先用`git diff initial HEAD`或Modal的`_diff.patch`检查有提交变化，再从artifact工作目录整树复制`tests/`、`environment/`；[C4 `apply_fixer_artifacts/update_hardened`][C4] 同样复制当前目录，而不是用`git show HEAD`逐文件恢复。因而在“已经存在提交，但之后又改工作树”的条件下，不能仅据注释声称所有导出字节均来自该提交快照。这里只记录静态消费边界，未复现触发、未归因于历史结果，也不把它扩成整库漏洞审计。

**Modal补丁。** 当前commit专门处理Docker bind mount保留`.git`、Modal下载却不保留并改变路径的问题，加入`_diff.patch`与路径选择。这是July版本的复用条件，不是June论文已经完整验证两个backend的证据。[C3、C4]

**`robust`不是solver全覆盖。** C2允许连续legitimate标记达到阈值后结束，也允许攻击重试失败后结束；max-iterations单列。设置失败与solver不通过有不同outcome；修补失败则不更新本地hardened状态。局部接受逻辑不能直接推出所有pool提交在对其他任务可见前都完成全局合法解检查，本轮未核全池并发事务。

**成本账也有范围。** C2的`_STATS_SUM_FIELDS`及附近注释明确：统计Harbor角色trial的duration/token/cost，直接通过litellm做的轨迹总结不在这些totals内。当前JSON的`cost_usd`不能自动视为全部API费用。Current code还包含journal、可选replay等扩展；这些不是本文报告的独立训练收益。

### 8.2 W：Terminal Wrench与论文数量并不完全相同

[W README固定版][W0]写 **331 unique tasks、957 task/model entries、6,289 v5 hacker trajectories、3,632 hacks、1,216 attacker legitimate solves、1,441 no-reward attempts、2,352成功precheck baseline trajectories**。三类v5结果相加恰为6,289。论文则写323环境、SETA238、TB2.0 13；README为331、SETA241、TB2.0 14。两者保留各自来源，不假定是哪八题被删除或后加。

README将源集合总数 **1,968**明确标为**有重叠的合计**，另述分析1,860项；TB2.0与original重叠88，OpenThoughts与original重叠20。这说明论文的`323/1968≈16%`不能被强化为“严格去重总体的漏洞率”。本篇仍保留作者报告值，不私自替换成按1,860计算的新 headline。

W的构建描述为较广模型／prompt的40k+尝试→395候选任务→进一步v5循环→发布331任务；它与P的4,848通过轨迹漏斗不能未经映射直接拼接。数据采集时间为2026-01-01至03-30，原benchmark后续可能已修复。

发布布局包含`original_task/`、hacker/benign轨迹、verifier输出和结果，还含sanitized/stripped轨迹及monitorability实验。这是**原始可攻击环境和行为资产**，不是已修补全部任务、更不是RL训练checkpoint。11类漏洞标签可多选，其分类计数不能求和当不同轨迹数。Monitorability是该资产的另一个研究面，本轮只核资产说明，不把其正文及所有样本标成精读完成。

### 8.3 K：KernelBench产物能补齐的复用信息

[K0 README][K0]与[K1 manifest][K1]实际提供四配置、100任务的结果／配置／最终verifier目录，compact agent行动轨迹，以及task001的iter8/11/13 **raw与autopatched**快照。共享池完整171commit通过submodule连接。重型逐步LLM上下文debug dump未放在此仓库；因此“有轨迹”不等于具备所有原始调用字节。部分`status=unknown`来自wall-clock停止，不应当作收敛或鲁棒。

本轮进一步读取[K2 Gemini iter13 summary][K2]与[K3 Opus iter13 summary][K3]。它们的 headline为`0/234`与`0/232`，但bucket包含**benign solver**：

| 发布摘要 | Hint有效提交 | Unhinted hacker | Benign／control | 总行数的解释 |
| --- | ---: | ---: | ---: | --- |
| Gemini iter13 | 133 | 49 | 49 freeform solver +3 solver controls | 234包括正常解，不能写成234次攻击 |
| Opus iter13 | 133 | 49 | 50 solver | 232包括正常解，不能写成232次攻击 |

133的两模型hint计数由逐bucket加总得出，补足了论文正文主要只说明Pro语料生成的部分，但**仍属发布产物事实**。`Hacks=0`按12×计算，并不是这些benign trials都没通过正常0.5×门槛。Summary给出每bucket的均值和最大值，不足以单独重算全部benign pass率；主表98/92仍来自论文。此区别能防止把同一资产的总条数误写为更大的攻击评测规模。

C仓库metadata标Apache-2.0；P标CC BY4.0。各任务原始数据、上游benchmark与产物许可不因代码license自动统一，本轮未逐项核验许可或下载全部资产。没有运行攻击、修补或训练，也没有独立复现主表。

<a id="judgment"></a>
## 9. 证据边界、原文差异和没有回答的问题

### 9.1 作者承认的限制与阅读者应保留的限定

Appendix A指出覆盖受攻击者能力与预算限制，pool只能在共同基础设施内摊销；作者认为同代模型的攻击先验相关，使某些盲点较不令人担忧。**相关先验缓解风险属于作者判断，没有证明未来RL策略不会发现现有hacker漏掉的漏洞。** [P, A, p.13][P13]

Appendix B承认公开攻击目录和自动攻击工具的双重用途，作者认为风险较低。本文记录其判断，不把它当独立风险评估。所有借鉴均限于自有／授权沙箱的评测质量检验，不扩为真实第三方系统攻击。

§4.3指出有些目标在当前观测面上根本无法区分：例如容器内`shred`与普通删除可能留下相同可观察终态，verifier又不能访问底层文件系统。此时只加assert不一定能验证所需过程，需要改变可观测性、执行约束或重新定义任务，而不是声称自动fixer能解决所有不可判定目标。[P, §4.3末, p.10][P10]

本篇有方法与消融、有代码和资产，但没有目标模型权重训练，也没有不同团队独立复现。论文中引用的RL agents和生产reward hacking背景不改变这个证据等级。

### 9.2 具体差异与未知登记

| 问题 | 来源状态 | 本稿处理 |
| --- | --- | --- |
| 审计环境323 vs发布331；TB2 13 vs14；SETA238 vs241 | P与W明确数值不同 | 分列，不编造任务映射 |
| 1,968的去重口径 | W说源集合重叠合计，另列1,860 | 不改P原报告比率，也不宣传为去重总体估计 |
| Autopatch的94/22快照 | Table2明确iter11；E.3文字邻接iter8 | 主体按表，记录文字含糊 |
| Autopatch应用轮数／调用次数 | Table2列2/5/8/11/13；E.3与K主要8/11/13且one-call措辞不完全统一 | 不把一次和每快照一次强行合并；不精算其API成本 |
| TB hinted基线56.2 vs51.6 | §4.3正文与Fig2/Table7不一致 | 展示有标签的图表值，56.2保留为Blind+pool hardened |
| TB四配置主张 | D.5列四种；F.3只展示三种hardened | 不补缺失的Blind+no-pool数值 |
| KB攻击门槛 | 循环10×，Table2≥12×；E.2用exceeds | 区分循环和eval，边界恰12的处理未静态验证 |
| “仅提交修改导出” | P D.6表述；当前C以commit检测后复制工作目录 | 单列当前实现限定，不倒推历史数据有问题 |
| 有效分母、precheck淘汰、失败trial、retries与pooling | KB部分计数有；TB和总审计未完整披露 | 名义预算与有效结果分开；不伪造p值重算 |
| Benign开发／最终评测隔离 | autopatch使用失败正常解；独立最终benign来源未完整披露 | 不称无条件保持或独立验证所有合法解 |
| 统计独立性／置信区间 | z-test公开，聚类／配对／多种子细节未给齐 | 保留作者p和多个hint校正；不扩成稳定跨分布保证 |
| 模型训练超参数、学习收益 | 本文不做权重训练，非“漏读配方” | 明确不适用 |
| Algorithm1、Table4–8视觉核验 | 已有完整文字，截图未取得 | 写明待补原页目视；不称作者未公开 |
| 原始实验代码revision、完整raw重放 | 当前C/K分别固定；未建立全部历史执行一致性 | 静态可复用，不标一键复现或已运行 |

## 10. 对 RepoHarness 项目一的条件化判断

映射日期 **2026-09-08**，读取基线见§1。依据[当前简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)，项目采用miles/SGLang和现有coding harness，rh2负责可信输入、fresh grader、评分投影与训练消费；本轮未审计这些实现。以下是**设计层候选**，不是批准新安全平台、在线hacker训练或改变当前loss。

**本篇支持增加的是“修补后仍测合法解”的证据，而不只是增加更严格的挡板。** 已隔离隐藏tests，可以减少一类攻击，却不能证明测试与instruction一致，也不能保证候选正常解不会被新检查拒绝。反过来，本文默认共享容器里的解释器／依赖链攻击，在已有fresh grader和可信投影下可能已不适用，应先核实际执行面，不重复构造同样的防线。

| 候选借鉴 | 来源支持 | 本项目的最小验证，而非立即实施 |
| --- | --- | --- |
| 有界的离线attack–patch–benign回归 | 三角色与KB raw/autopatch、TB benign下降 | 在一小批已确认任务上冻结原始grader与候选grader，同时重放授权攻击fixture、gold和多种合法实现；最终复核用未参与fixer诊断的正常解 |
| 分离测试控制面修复与任务意图改变 | D.6、H和solution narrowing | 对具体patch查导出范围和实际消费状态；不能靠收紧题意、删除难测目标来算漏洞修复；记录哪些正常行为受影响 |
| 只在共享评分基座上复用防御 | Table1与pool regression | 对共同基础设施采用一个版本化修补，逐任务保留正常／异常回归；先比较简单统一修复，不默认引入常驻多agent共享池 |

建议同时保留攻击通过、良性通过、无操作／错误解拒绝、环境失败、费用；**不能用攻击率下降单指标选最好的verifier。** “gold pass”是存在性检查，不是整个合法解集合的覆盖证明。对Normal solver的新失败，先辨别它原本是否满足意图，再统计误杀。

若现有评分隔离已挡住本文主要八类环境接管攻击，本篇更适合作为验证与归因参照，而非项目一的主要新增模块。若剩余问题主要是测试语义过窄或漏测真实后果，则可以形成一个窄的环境质量改进实验。两种情况都**不能仅凭本论文推定用hardened reward训练后的模型更诚实、未见任务更强**；那需要另做等数据／等预算训练和独立行为评测。

相较此前模型／环境阅读，本篇新增的最重要反证是：**攻击归零与benchmark被修好并非同义词；更复杂的共享修补甚至可能扩大另一类攻击面。** 因而它要求我们增加counterexample和benign对照，不要求我们立即增加一个组件。

## 11. 快速查阅与交付状态

| 常见问题 | 本笔记 | 原文定位 |
| --- | --- | --- |
| 是否真的进行了RL？weak-to-strong是什么意思？ | §2.1 | §3–4、Appendix C |
| 323 / 331 / 1,968 / 1,860各是什么？ | §2.2、§8.2 | P §2；W固定README |
| 谁能看tests、修改环境，哪个动作真正接受patch？ | §3、§8.1 | Algorithm1、D.6–D.7、H；C2/C3/C4 |
| 为什么KB 0%不能单独当成功？ | §5.3–5.5 | Table2；E.3 |
| 10×、12×与0.5×区别？ | §4、§8.3 | Table2、Table4、E.2；K2/K3 |
| Pool是否总有益，TB正常解损失多少？ | §6 | Tables3、5–8；F.2–F.3 |
| 8H200用于什么，5,000美元是什么范围？ | §7 | D.9、E.1 |
| 现有repo能直接复用什么？ | §8 | 固定C/W/K路径 |

**状态：全文及附录文字精读、主图／主表目视、定点代码与资产核查、作者自查完成；附录表4–8和Algorithm1仍待原页目视复核；没有独立reviewer和实验复现。** 具体检查及修订见[本篇作者自查](reviews/N06_hardening_self_check_20260908.md)。本次只提交这两个N06专属文件，共享索引留给汇总线程维护。

## 官方来源与固定代码链接

[P-abs]: https://arxiv.org/abs/2606.08960
[P]: https://arxiv.org/pdf/2606.08960v1
[P-html]: https://arxiv.org/html/2606.08960v1
[P4]: https://arxiv.org/pdf/2606.08960v1#page=4
[P5]: https://arxiv.org/pdf/2606.08960v1#page=5
[P6]: https://arxiv.org/pdf/2606.08960v1#page=6
[P7]: https://arxiv.org/pdf/2606.08960v1#page=7
[P8]: https://arxiv.org/pdf/2606.08960v1#page=8
[P9]: https://arxiv.org/pdf/2606.08960v1#page=9
[P10]: https://arxiv.org/pdf/2606.08960v1#page=10
[P13]: https://arxiv.org/pdf/2606.08960v1#page=13
[P14]: https://arxiv.org/pdf/2606.08960v1#page=14
[P15]: https://arxiv.org/pdf/2606.08960v1#page=15
[P17]: https://arxiv.org/pdf/2606.08960v1#page=17
[P18]: https://arxiv.org/pdf/2606.08960v1#page=18
[P19]: https://arxiv.org/pdf/2606.08960v1#page=19
[P21]: https://arxiv.org/pdf/2606.08960v1#page=21
[P22]: https://arxiv.org/pdf/2606.08960v1#page=22
[P23]: https://arxiv.org/pdf/2606.08960v1#page=23
[C0]: https://github.com/few-sh/harden-v0/blob/342b8474e0c0cf96e4a8313fd2e26c7a11d51193/README.md
[C1]: https://github.com/few-sh/harden-v0/blob/342b8474e0c0cf96e4a8313fd2e26c7a11d51193/harden/config.py#L54-L148
[C2]: https://github.com/few-sh/harden-v0/blob/342b8474e0c0cf96e4a8313fd2e26c7a11d51193/harden/loop.py#L827-L1040
[C3]: https://github.com/few-sh/harden-v0/blob/342b8474e0c0cf96e4a8313fd2e26c7a11d51193/harden/workspace.py#L594-L659
[C4]: https://github.com/few-sh/harden-v0/blob/342b8474e0c0cf96e4a8313fd2e26c7a11d51193/harden/workspace.py#L87-L112
[W0]: https://github.com/few-sh/terminal-wrench/blob/d8a29613235a0ef56a8b70b3142626a533da28c2/README.md
[K0]: https://github.com/fjzzq2002/harden-kb-traces/blob/2721064396f07e536fac5f493b74e7ab161518eb/README.md
[K1]: https://github.com/fjzzq2002/harden-kb-traces/blob/2721064396f07e536fac5f493b74e7ab161518eb/manifest.json
[K2]: https://github.com/fjzzq2002/harden-kb-traces/blob/2721064396f07e536fac5f493b74e7ab161518eb/autopatched/evals/gemini_iter13/summary.md
[K3]: https://github.com/fjzzq2002/harden-kb-traces/blob/2721064396f07e536fac5f493b74e7ab161518eb/autopatched/evals/opus47_iter13/summary.md
