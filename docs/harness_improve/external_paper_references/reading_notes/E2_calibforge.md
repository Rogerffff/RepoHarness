# E2 CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks：后训练与项目一精读

## 1. 来源、版本与阅读范围

- **资料类型与正式标题**：论文，*CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks*。
- **作者**：Fanzhe Meng、Guoxin Chen（共同一作）、Jiale Zhao、Shuang Sun、Zhiyu Lin、Wayne Xin Zhao、Ruihua Song、Ji-Rong Wen、Kai Jia。首页列机构为中国人民大学高瓴人工智能学院、Independent Researcher、AweAI Team；不能只把团队账号当全部机构。
- **版本**：[arXiv:2608.06352v1](https://arxiv.org/abs/2608.06352v1)，提交时间 2026-08-06 17:53:18 UTC；PDF 首页另印 `Date: Aug. 07, 2026.`。2026-09-07 查 arXiv submission history，仅列 v1。二者是提交日期与文内日期的区别，本篇没有以新版本替换旧版本。
- **原文**：[本地 PDF](../pdfs/E2_calibforge_solver_calibration_2608.06352.pdf)、[官方 PDF](https://arxiv.org/pdf/2608.06352v1)。本地 27 页，首页带 v1 标记；物理页 2–27 与印刷页 2–27 一致，首页按物理页 1 定位。下文 `p.` 一律指此 PDF 物理页，`§`、附录字母、表图号指原文。
- **阅读日期与范围**：2026-09-07。完整精读方法、实验、A–F 全部附录、图表与提示词；§1、§4、§5 阅读其论证边界；参考文献用于核出处，不把其中各篇论文算作已精读。本篇没有纯预训练或架构专章，也没有另外的数学 RL、多模态 RL、偏好优化或安全对齐实验；安全任务和 prompt 的安全约束见本篇 §4.4、§6.2。
- **旧稿**：[summary_calibforge.md](../../../../knowledge/summary_calibforge.md) 与 [summary_calibforge_solver_calibration.md](../../../../knowledge/summary_calibforge_solver_calibration.md)，仅作检查线索，保留原文件；主要更正见 §9.3。
- **配套资产版本**：GitHub CalibForge `4a219dcd321879c4f7f72953184e49891fb19d52`（2026-08-07）；AweAgent `b38414e5dc9c7c51f2ec48318b718af0c8852060`（2026-08-18）；HF 数据 `fb1e75441a94b8bb0ced08acd6b59e711704d70a`；30B 模型 `59a534b076a76b7a5e617f68e97666b4c8063cac`；35B 模型 `51f563b3ca294e28f430e58dc98509c4867fb19b`。后发布代码是独立证据层，未宣称就是论文实验 commit。实际读取的官方网页/代码快照及 URL 见 [source_manifest.json](sources/E2/source_manifest.json)。未下载权重、整套环境或运行训练。

### 1.1 先按原文建立的覆盖图

论文没有单独目录页；下表由原文实际标题及附录结构建立，再据此整理笔记。没有用项目关注点筛掉后训练内容。

| 原文章节 / 页码 | 阅读深度与内容 | 本篇位置 |
| --- | --- | --- |
| 首页 / Fig.1，p.1；§1 Introduction，p.2–3 | 完整阅读问题、贡献、SFT 与迁移主张 | §2、§7 |
| §2.1 Overview，p.3；Algorithm 1，p.4 | 精读控制流、验证循环、早停与丢弃 | §3、§4.1 |
| §2.2 Candidate Task Authoring and Validation，p.4–5 | 精读研究、联合构建、fail-first、自解 | §4.1 |
| §2.3 Adversarial Solver Calibration，p.5；Eq.(1)–(2) | 精读反馈与两种保留判据；公式页面目视复核 | §4.2、§5.1 |
| §3.1 Experimental Setup，p.6 | 精读模型、预算、蒸馏、基线、评测和去污染 | §3、§4.3、§5–7 |
| §3.2 Main Results，p.7；Table 1、Fig.3，p.7–8 | 精读各底座结果、迁移及 pass@3 与平均准确率区别 | §7.1–7.2 |
| §3.3 Analysis of Synthesized Data，p.7–11；Table 2、Fig.4–7 | 精读领域、标签、环境/测试复杂度、轨迹统计 | §4.5 |
| §3.4 Effect of Solver Calibration，p.11–12；Table 3、Fig.8–9 | 精读四臂消融、首次状态、修订漏斗与长尾 | §7.3–7.4 |
| §4 Related Work；§5 Conclusion，p.13 | 完整阅读与任务合成、课程、solver 自我反思的区别；未扩展精读所引文献 | §2、§9 |
| References，p.13–17 | 出处导航阅读；不是遗漏的训练附录 | §1、§11 |
| A From a Clue to a Calibrated Task，p.18–19 | 精读完整传感器日志任务、24 次搜索、环境与校准实例 | §4.4 |
| B How Solver Feedback Revises Tasks，p.19；B.1 / B.2，p.20–21；B.3，p.21–22 | 精读三种修订与前后结果，包括合法替代解误杀 | §4.4 |
| C CalibForge-Eval，C.1，p.22；C.2，p.23–24 | 精读工具表和完整 system/user prompt；不是 authoring prompt | §6 |
| D Benchmark Decontamination，p.24–25 | 精读预处理、阈值、结构匹配及未给全的规则 | §4.3、§9 |
| E Supervised Fine-Tuning Details，p.25；Table E1 | 精读全部超参，原始表页面目视核验 | §5.2 |
| F Failure Analysis of Trained Models，F.1，p.25–26；F.2，p.26；F.3，p.26–27 | 精读全部负结果与各次运行，不把精选案例当错误率统计 | §7.5 |

## 2. 核心问题与结论

**CalibForge 研究的是训练前的任务构造与校准，不是在线 RL。** 可启动的环境、初始状态测试失败、作者自己的解能通过，只证明了一部分可执行性和可解性；它们不保证任务能区分指定 solver 的能力。作者让独立 solver 在候选环境中执行，根据最终测试结果决定保留，根据反馈和完整轨迹改写题意、环境或 verifier，再重新验证和探测（§2，p.3–5）。这里的“对抗式”指任务作者试图构造有挑战但仍可解的任务，不是训练两个网络的对抗损失。

所谓 **solver-relative learnable zone**（相对于指定求解模型组合的可学习区间）是操作性标签：异构 solver 中有成有败，或指定强 solver 成功、弱 solver 失败。它不是对目标 student 的通过概率估计，更不是已经测出的梯度质量。作者最终用 DeepSeek-V4-Pro 收集成功轨迹，对两个 Qwen 底座分别做全参数 SFT（§3.1，p.6；附录 E，p.25）。

最直接的方法证据是匹配每臂 1,300 个任务的四臂实验：No Solver / Single Solver / Multi Solver / Contrast Solver 在 Qwen3-30B-A3B-Instruct 上的 TB2 准确率分别为 22.47 / 24.34 / 29.21 / 31.09%。Multi 的保留轨迹比 No Solver 少，因此“只是轨迹更多”不足以解释增益；这并未控制作者 API 成本、训练 token 总量或固定任务内容（Table 3，p.12）。

全量 5,431 题的监督训练在 TB2 达到 32.58%（30B）和 47.57%（35B），并在 SWE-bench Pro、Doc2Repo 上有迁移收益（Table 1，p.7）。不能把跨底座最大增益、不同 benchmark 的分数或不同任务集规模揉成同预算优势。论文未报告 RL、OPD、动态课程或低卡数训练结果，也没有总体生产成本；“可迁移到 rh2”必须另作目标模型和预算下的小实验。

## 3. 后训练全流程与模型关系

```text
clue → 外部技术研究 → 任务规格 → instruction + Docker 环境/初始文件 + tests
     → structural validation + author self-solving
     → 固定外部 solver 组合执行 → verifier outcomes + 完整轨迹
        ↳ 未满足保留条件：author 修订 → 两阶段重验 → 再探测
        ↳ 满足条件：保留任务 → benchmark 去污染（蒸馏前）
     → DeepSeek-V4-Pro 每题 2 次蒸馏尝试 → 仅成功且通过格式/长度过滤的轨迹
     → 两个独立 student 的 full-parameter multi-turn SFT → 各自 10 epoch 最终 checkpoint
     → TB2 + 两个仓库级迁移 benchmark
```

图中两种校准模式是可选构造策略，最终任务集汇合；两个 student 独立训练，不是 30B 先教 35B，不是串行 expert 或 teacher/student 联合更新。校准时修改的是任务，未报告更新 author、solver 或 teacher 参数（§2；§3.1）。

| 角色 / 阶段 | 模型与输入输出 | 已知预算与参数更新 |
| --- | --- | --- |
| Author / self-solver | DeepSeek-V4-Pro；clue、外部资料、反馈 → 新任务/修订与自解 | author 独立总 token/时间/修复次数未给；无模型训练描述 |
| Multi-solver panel | DeepSeek-V4-Flash、GLM-5、Kimi K2.5，各自独立环境、相同指令 | 每 solver 每次 ≤100 交互步、≤30 分钟；候选 ≤50 校准轮 |
| Contrastive panel | strong=DeepSeek-V4-Pro；weak=DeepSeek-V4-Flash | 同上；能力强弱是指定关系，不是全任务上严格排序 |
| Single-solver 消融 | 与 author 同模型的独立 DeepSeek-V4-Pro subagent | 有 pass/fail **和轨迹**反馈；无跨模型分歧或强弱目标（§3.4，p.11） |
| Distillation teacher | DeepSeek-V4-Pro，reasoning effort=`high`，CalibForge-Eval | 每题 2 次，≤200 步、≤1 小时/次；保留过测试的轨迹，再过滤 |
| Student A | Qwen3-30B-A3B-Instruct → CalibForge-30B-A3B | 全参数 SFT、10 epochs；官方模型卡进一步标底座 `Qwen/Qwen3-30B-A3B-Instruct-2507` |
| Student B | Qwen3.5-35B-A3B → CalibForge-35B-A3B | 相同训练配方，独立 SFT；不据名称推断未写明的 mid-training / RL 历史 |

这里的 distillation 是 teacher 生成成功轨迹后离线监督模仿。没有 teacher 全词表概率、KL 方向、top-k 蒸馏、teacher 更新、student on-policy 采样或同 tokenizer 约束的报告，不能称为 OPD。

## 4. Coding / SWE / terminal 数据与环境

### 4.1 从 clue 到可信候选的已知流程

Author 在草稿 sandbox 中使用搜索、shell 与文件编辑。围绕 clue 到官方文档、GitHub 仓库/issue、Stack Overflow 查具体工程问题，比较多个方向的相关性、独特性和可实现性；规格包含工具与依赖、输入和边界情形、期望行为、失败模式。先试装依赖、访问资源、观察工具行为，再联合生成指令、Dockerfile/初始文件和测试。进入验证前检查初始环境不暴露解答工件，测试不施加题意未声明要求（§2.2，p.4）。这是 author 检查流程，不能等同已完成独立泄漏或安全审计。

两阶段有效性 `V(τ)` 要求：① 构建上下文齐全、环境能初始化，初始状态**所有测试失败**；② 从候选 Dockerfile 启动隔离 test sandbox，author 自解并验证题意、环境和测试一致。任一失败就修复，再走两阶段。Algorithm 1 的验证修复 `while` 没有显式次数上限；`Rmax=50` 只限制后续校准 `for`，不是整个构造过程的完整预算（p.4；§3.1，p.6）。

| 阶段 / 对象 | 数量与单位 | 进入下一阶段 / 排除方式 | 成本口径和缺口 | 原文位置 |
| --- | --- | --- | --- | --- |
| 初始 clue / 外部来源 | 总数未给 | 研究并选择技术方向；可回退重做 | 搜索/API 总量未给；附录 A 的 24 次是单例 | §2.2；A |
| 构建成功、通过自解候选 | 总数未给 | 必须满足 `V(τ)=1`；失败修复 | 不能从 96% 反推精确原始任务数 | Algorithm 1；Fig.8 |
| 校准保留任务 | 最终 5,431 题：multi 1,263，contrastive 4,168 | 满足指定 `Cγ`；50 轮仍不满足则丢弃 | 未给两分支完整候选量/失败量 | §3.3，p.7 |
| 去污染后用于蒸馏的任务 | 论文把最终 collection 报作 5,431；没有逐阶段扣除表 | 对任一测试集标记污染则移除 | 未列去污染剔除数量和其与上述 collection 的精确计数衔接 | §3.1；D |
| Teacher 原始尝试 | 每任务 2 次；全量 5,431 题按协议对应 10,862 次计划尝试 | 测试全部通过后再作长度、工具调用、特殊 token 过滤 | 10,862 是按协议计算的计划数，非已公开成功/实际完成日志数 | §3.1，p.6 |
| 最终 SFT 轨迹 / 训练消费 | 全量训练轨迹总数和 token 数未给；四臂消融分别见 §7.3 | 成功轨迹监督训练、10 epochs | 不能把任务数、轨迹数或 epoch×任务数当实际训练样本/token 数 | Table 3；E |
| 环境镜像 | 公共数据每题有镜像引用；独立镜像 digest 总数未核 | dataset 的 task.toml、image_mapping 提供入口 | 没有拉取运行，未测构建复用率/磁盘/CPU 成本 | 官方数据卡，§8 |

### 4.2 校准中的反馈、修改权限与状态解释

每轮为各 solver 从候选 Dockerfile 建独立 sandbox，发相同 instruction；结束后 verifier 读最终状态，所有测试过才记 `y_i=1`。返回 pass/fail、步数、完成/超时状态、自评、失败诊断和全交互轨迹。**只有经验证的结果用于保留条件；自评与轨迹用于诊断和修订**（§2.3，p.5）。不能把“solver 说完成了”当 `y_i=1`。

| 已观察结果 | 作者给出的诊断方向，均非唯一原因 | 允许的修订 |
| --- | --- | --- |
| All pass / both pass | 可能过易或有浅层解法 | 去除流程提示、增加真实诊断需求等 |
| All fail / both fail | 可能太难、题意不全或任务有问题 | 查可解性、说明与验证逻辑，不直接解释为模型弱 |
| strong fail / weak pass | 可能泄漏、非确定性或误导表达 | 查题意与 verifier；附录 B.3 的实际原因是合法替代解被误杀 |
| Multi 有成有败 / strong pass weak fail | 当前指定 solver 设置下满足 `Cγ` | 保留这个版本；不是对未来任意策略的永久可学习证明 |

每次可修订任一任务组件，甚至重做研究或技术方向；修后重新两阶段验证再探测。因此接受率提升包含**任务改变**，不是固定题集成功率提升。正文未提供重复测同一 solver/同一版本的置信区间、flakiness 重试协议、基础设施错误与模型失败如何分开影响二元 outcome 的完整规则（§2–3、A–C 已查）。

### 4.3 来源、去污染与切分边界

任务从具体工程资料构造，不是仅重排现成 benchmark prompt。原文未给所有 clue 的来源清单、采集日期范围、源仓库/派生族分组划分、训练内部 dev/test 切分或语义去重清单；HF 数据只有公开 `train` metadata split。文件名中的日期不能替代正式数据采集协议。

去污染发生在蒸馏与训练之前，逐 CalibForge candidate 对照 TB2、SWE-bench Pro、Doc2Repo（§3.1，p.6；D，p.24–25）：

1. 指令与评测指令有精确 14-gram 重合则去掉。
2. 指令与可获得 verifier/test code 小写化、tokenize、去 benchmark 样板，将 URL、绝对路径、数字替换为规范占位符，再算 5-shingle Jaccard（连续 5 token 集合的交并比）。指令核心阈值 0.30，测试代码阈值 0.45。
3. 合并共享输出路径、重叠测试函数和高风险任务族等结构证据；被任一 benchmark 标记就移除。

附录 D **没有写出阈值与结构信号的完整布尔组合、任务族名单、精确 tokenizer/boilerplate 规则或剔除计数**，虽正文称补充材料给 full matching rule，也不能据此声称可以逐位复现污染筛选。它控制显式构造数据与评测的某些重合，不证明基座/teacher 预训练无污染，也不等于所有基线数据已按同一规则重新去污染。

### 4.4 模板之外必须保留的构造与修订案例

**A：二进制传感器日志恢复（p.18–19）。** clue 属 Data Processing & ETL，带 Binary Parsing / Data Recovery 等能力线索及 `xxd`、`hexdump` 提示。作者做 24 次搜索，比较表格/列式数据、数据库/Git、压缩/文本、媒体/网络、遗留格式等方向；这些被认为太浅、过度工具特定或设置成本大，是该 author 的个案判断，不是这些领域客观无价值。最终选损坏二进制日志：Ubuntu 24.04、Python、日志及格式说明，恢复 CSV，检查 CRC-16、值域、时间顺序、覆写区间，共 11 个 verifier tests。Pro 通过、Flash 失败而保留；strong 自评提到格式说明内存在 CRC 示例不一致，说明一个通过案例也不等于规格已无缺陷。

**B.1：交易记录恢复，both pass → 去流程提示（p.20）。** 初始强/弱分别 8/17 步过关，指令已给固定字段位置、两种损坏模式和日期修复示例。改为要求自己检查结构/无效字段，保留交付目标；复测 strong pass / weak fail。它展示从“照步骤实现”转成诊断，不等于应一概删去接口或验收信息。

**B.2：客户库导出比较，all fail → 补语义（p.20–21）。** GLM-5 / Kimi K2.5 / Flash 初始分别在 50/15/26 步失败。三个 solver 都把新增 `tier` 列同时算 schema change 和 record modification；verifier 只期望前者。作者补充“只比较双方共有字段判断记录变化”，复测 GLM-5 与 Flash 过、Kimi 失败。这里修的是题意与测试的一致性，不是降低工程问题难度。

**B.3：旧密码库安全修复，inverted → 放宽实现绑定（p.21–22）。** 初始 Pro 40 步失败、Flash 38 步成功。Pro 将敏感字段整体作认证加密，满足任务安全属性；测试却指定逐字段 `nonce:ciphertext:tag` 布局。修后 verifier 不依赖字段名/对象布局，检查认证加密、上下文绑定与旧数据迁移，复测变成 strong pass / weak fail。该案例支持用合法替代解检查误杀；它没有证明全库 verifier 安全或误奖励率为零，也不是模型的安全对齐训练。

附录 A/B 展示的是精选可解释实例，没有随机审计分母或各类问题比例。

### 4.5 数据画像与轨迹复杂度

16 类覆盖包括软件工程、系统管理、安全、调试、数据科学、模型训练、数据处理、科学计算、数学、机器学习、个人助理、优化、游戏、文件操作、数据查询、视频处理。它们都是终端任务内容，不能另行写成论文训练了 16 个领域 RL expert（§3.3；Fig.3–4）。

Fig.4（p.8）的 CalibForge 任务占比：SWE 25.5%、系统管理 11.9%、科学计算 9.4%、安全 8.6%、文件操作 7.3%、数据科学 8.2%、调试 6.4%、数据处理 5.7%、其余 17.0%。比较例：SETA-Env 74.6% 为系统管理、CLI-Gym 67.0% 为调试、Endless Terminals 40.6% 为文件操作。共同 taxonomy 改善可比性，不等于给出了盲标注一致性统计。

Capability tag（能力标签）共有 3,885 种，每题中位 5 个；**不同标签中** 51.6% 仅出现于一题，82.2% 至多出现于五题（p.8–9，Fig.5）。分母是 distinct tags，不是“51.6% 任务唯一”。长尾支持表面能力覆盖广的描述；标签同义归并、标注模型与可靠性未详述，不能把标签数当独立技能数。

| 指标 | 集合级统计 | 每题中位数 | IQR | P90 |
| --- | ---: | ---: | --- | ---: |
| 初始工件 | 19,911 | 2 | 1–4 | 8 |
| 不同文件类型 | 362 | 1 | 1–2 | 4 |
| 不同环境依赖 | 615 | 2 | 1–4 | 7 |
| verifier 测试函数 | 45,953 | 7 | 5–11 | 15 |

来源：Table 2，p.9；Fig.6，p.10。文件类型/依赖的集合列是 distinct 数，工件/测试函数是集合计数，不要一律当“所有任务计数的和”。更多测试也不自动等于覆盖正确。

Fig.7（p.10）在同 teacher 协议下报告每轨迹中位数：CalibForge 21 步 / 5.3k thinking tokens；CLI-Gym 28 / 4.0k；TermiGen 13 / 3.2k；SETA-Env 15 / 1.6k；TerminalTraj 12 / 1.3k；Endless Terminals 9 / 0.9k。作者解释环境修复任务有更多执行/再验证，因此步数不能独自衡量推理深度。更多 thinking tokens 是**实际生成量的分布统计**，不代表独立增加了分配预算，也不直接证明推理质量更高。

## 5. 训练目标与实际训练语义

### 5.1 两个公式是任务保留条件，不是训练 loss

令 `τ` 为候选任务，`V(τ)` 表示结构校验与自解均通过；`γ` 指定 solver 组合和保留条件，`y_i∈{0,1}` 为第 i 个 solver 的全部验证测试是否通过，`𝟙[·]` 是指示函数。原文 Eq.(1)–(2)，p.5：

\[
C_{\mathrm{multi}}(\mathbf y)=\mathbf 1\!\left[0<\sum_{i=1}^{K}y_i<K\right],\qquad
C_{\mathrm{con}}(y_s,y_w)=\mathbf 1[y_s=1\land y_w=0].
\]

本文 multi 的 `K=3` 是三个不同模型的独立尝试，**不是** GRPO 同 policy 的每题采样数；contrastive 的 `s/w` 是指定 strong/weak。`Cγ=1` 表示接受当前任务版本，不是把该 indicator 当 student reward/advantage。

论文未给 SFT loss 数学定义。能确定的是 full-parameter multi-turn SFT、只保留 teacher 通过测试且满足过滤要求的轨迹（§3.1；E）。不能用 LLaMA-Factory 常用默认值填成“所有 assistant token 都进 loss”或“tool observation 一定 mask”：assistant/thinking/tool response 的 mask、特殊 token 处理细则、packing、截断阈值、token/trajectory loss 分母都未报告。

这里没有 actor/critic、group baseline、IS ratio、clipping、KL/entropy loss、reference policy、off-policy 修正或组补采机制。失败 teacher 轨迹未作为负例训练；长度/无效工具/特殊 token 过滤会影响保留，但原文没给各过滤项数量及具体规则。训练组统计和梯度处置问题对本 SFT 实验不适用，不能偷换成 rh2 的组准入语义。

### 5.2 原文披露的全部 SFT 配置

| 配置 | 原文值 |
| --- | --- |
| 框架 / 训练方式 | LLaMA-Factory；全参数、多轮 SFT |
| Optimizer | AdamW，β₁=0.9，β₂=0.999 |
| Learning rate / schedule | `1.0e-5` / cosine |
| Warmup ratio / weight decay | 0.05 / 0.0 |
| Max gradient norm | 1.0 |
| Epochs / 报告 checkpoint | 10 / 最后一个 epoch checkpoint |
| Per-device train batch / gradient accumulation | 1 / 4 |
| Global batch size | 128 |
| Context length | 131,072 |
| Precision / GPUs | bf16 / 64×NVIDIA H20 |

来源：附录 E 与 Table E1，p.25；原始页已目视核验，以上不是 OCR 修补值。**待澄清关系**：若把 64 卡全部当独立 data-parallel rank，则 `64×1×4=256`，与 global batch 128 不同；论文未给并行布局，故不能断定作者一定算错，也不能擅自补成 TP=2 或改表为 256。此缺口影响准确复现实验 batch。

没有训练 wall-clock、GPU-hours、FLOPs、实际 optimizer updates、总 token、推理 GPU、sequence/expert/tensor parallel 布局、MoE routing、offload 或 LLaMA-Factory commit。表中 64×H20 是训练设备配置，不是 64 GPU-hours，也不能当作本项目 8 卡可行性证据。

## 6. Rollout 与 infra

### 6.1 生产、蒸馏与评测三套预算

| 工作负载 | 模型 / harness | 尝试预算 | 资源 / 重复与缺口 |
| --- | --- | --- | --- |
| task authoring / validation | Pro；草稿与自解 sandbox | 未给统一总预算；校验可循环 | 附录 A 的搜索次数不是全库预算 |
| solver calibration | 每轮 multi 3 模型或 contrastive 2 模型，各自 sandbox | 每 attempt 100 步、30 分钟；每候选 50 轮且早停 | 原文未报告同模型同版本额外重复估计；不能把 50 轮当 50 次同题独立评测 |
| SFT teacher 蒸馏 | Pro high；CalibForge-Eval | 每题 2 次，200 步、1 小时/次 | CalibForge 与所有任务集基线共用 teacher 和 rollout 上限 |
| TB2 评测 | 各 student/base；CalibForge-Eval | 500 步、1 小时/题 | 每 sandbox 16 CPU、32 GB RAM；3 runs，mean±SEM |
| SWE-bench Pro | 官方 scaffold；731-task public set | 文中未列步数/token/时间 | 1 run；Resolved Rate |
| Doc2Repo | 官方 scaffold；从规格生成完整仓库 | 文中未列步数/token/时间与任务总数 | 3 runs；Pass Rate、mean±SEM |

来源：§3.1，p.6。训练 context 131,072 不等于所有 rollout 的上下文上限。校准 solver 的 temperature/top-p、thinking effort、单次生成长度，以及 student 评测解码参数均未在论文完整列出。

单个候选若耗尽 50 轮，按协议最多对应 multi 的 150 个 solver attempts 或 contrastive 的 100 个 solver attempts；若每次都用满 30 分钟，分别是 75/50 solver-attempt 小时。**这是读者推导的名义累计尝试预算，不是墙钟耗时或实测成本**，不含 author、自解、构建、修复、API token。实际是否同时执行以及完整生产重试上限未披露。

论文只给任务级交互控制流，不报告 RL rollout/trainer 异步队列、backpressure、权重发布、staleness、partial rollout/resume、KV/prefix 复用、GPU 利用率或吞吐基线。此处不能反推 miles/SGLang 一类 RL 系统配置。

### 6.2 CalibForge-Eval 工具与完整 prompt 的关键约束

C.1 / Table C1（p.22）仅三种工具：`execute_bash(command, timeout?)` 在持久 task runtime 执行并返回输出/状态；`str_replace_editor` 支持 `view/create/str_replace/insert` 及各操作参数；`finish()` 无参数，结束交互后才用 verifier 评最终环境。它没有论文所述 web search 工具；author 的工具面与蒸馏/评测工具面不能混在一起。

C.2（p.23–24）system prompt 全文的有效约束包括：识别精确交付物、路径、格式、接口和版本；修改前勘查；优先任务已有流程；定点编辑并保持交付目录干净；用任务相关检查确认最终状态；对慢下载/构建设置工具 timeout、看日志后调整；对数据工件实际读取检查 schema/content；失败后诊断，不盲重试；不靠隐藏 grader 或硬编码答案。用户 prompt 仅包装 instruction、workdir 与最终状态评分说明；必须调用 `finish`，文字宣称完成不足以结束。安全和范围部分是执行指导，不是经过测量的拒绝训练/安全对齐方法。

附录 C 公开的是 **CalibForge-Eval system/user prompt**，不是完整 author / calibration / revision prompt 模板。附录 A/B 有任务修订示例，不能把它们写成完整生产 prompt 已公开。

### 6.3 配套代码补充：明确与论文实验版本分层

核查范围限于关键运行入口、任务加载和评分，不复刻整个 AweAgent。以下固定到 `b38414e…`（2026-08-18），文件快照均在 [sources/E2](sources/E2/source_manifest.json)：

| 文件 / 符号 | 代码实际披露 | 与论文口径的关系 |
| --- | --- | --- |
| [recipe README](sources/E2/aweagent_recipe_README.md)；[run.py](sources/E2/aweagent_recipe_run.py) 的 `_load_config` / `main` | 支持选择题单、模型、步数、并发、agent/verifier timeout、全局 CPU/内存；保存结果、轨迹、resolved config | 是公开运行入口；不证明这些默认值用于论文实验 |
| [terminal_bench_v2.yaml](sources/E2/aweagent_configs__tasks__terminal_bench_v2.yaml) | CalibForge、500 steps、agent timeout 3600；runtime 默认 4 CPU/8Gi；并发 50、max_retries 3 | 资源可被 task.toml 覆盖；与论文 16 CPU/32 GB 不可直接等同；代码并发/重试不是论文生产预算 |
| [task.py](sources/E2/aweagent_aweagent__tasks__terminal_bench_v2__task.py) 的 `TaskInfo.from_directory` / `get_instances` | 读 instruction、task.toml、tests，要求 docker_image；加载异常记录 warning 并跳过 instance | 复现须核实际加载题数，不能只相信请求题单分母 |
| 同文件 `requires_patch_extraction` / `requires_git_snapshot` | 两者都为 False，任务直接作用于运行时状态 | terminal 不能一概换成 SWE 的 patch export/replay |
| [evaluator.py](sources/E2/aweagent_aweagent__tasks__terminal_bench_v2__evaluator.py) 的 `TerminalBenchV2Evaluator.requires_same_session` / `_run_verifier` | 声明 same-session；上传 tests 后运行 `/tests/test.sh`，读 reward.txt 或 reward.json；`accepted = reward_value > 0`，score clamp 到 [0,1]；超时记 0、无 reward 文件默认 0，并带细节 | 泛化 reward 文件约定，不是代码逐项断言“所有测试过”；论文 `y_i` 的全过定义不能直接由此替代；本次未独立运行完整 runner/防篡改验证 |

官方 recipe README 的 “CalibForge Evaluation Setting” 示例显式 `--max-steps 200`，但同页默认配置、实际 YAML 和论文 §3.1 的 TB2 evaluation 是 500。应保留此**示例/默认/论文差异**，不能把 200 步蒸馏预算写成论文 TB2 测试预算。README 用 `--cpu-milli 16000 --memory-mb 32768` 表示 16 CPU / 32 GiB；论文写 32 GB，精确单位按各自来源保留。recipe 记录 TB2 checkout `69671fbaac6d67a7ef0dfec016cc38a64ef7a77c`，这只 pin 当前公开 recipe，不补成论文原始 commit。

README 另给 Pro high 在 TB2 的 AweAgent reproduction：58/89、59/89、60/89，66.29±0.65%；这是作者框架后续复现数据，不是论文 student 表的新增受控对照，也不是本次亲自复现。Terminus-2 是此后代码额外支持的 scaffold，不能写成 CalibForge 论文混 harness 训练。

## 7. 评测与消融

### 7.1 测量口径与主表完整结果

**按作者声明的口径**：TB2 是三次运行任务准确率的 mean±SEM，不是 pass@3；SWE-bench Pro 声明使用 731-task public set、评测一次并报告 Resolved Rate；Doc2Repo 为三次 Pass Rate 的 mean±SEM。论文未列 Doc2Repo 题数及官方 scaffold commit/预算；TB2 Figure 3 各类题数合计 89，当前公开 recipe 也以 89 为分母。SEM 描述运行间均值误差，不是跨 task 的置信区间，更不是多训练 seed 的误差。

**实际评分分母/聚合方式未完全核清（独立审查新增）**：731 是论文声明的数据集规模，不能直接当成 Table 1 每行已核的有效分母。若单次分数严格为整数 solved/731，则 30.94% 与 3.26% 均无匹配整数；最近分别为 226/731=30.91655%（两位小数应 30.92%）和 24/731=3.28317%（应 3.28%）。同样，若 TB2 三次均评 89 题、二元等权，则均值应是整数/267；35B base 的 39.10% 介于 104/267=38.95% 与 105/267=39.33%，不能由此舍入得到。其他部分行可匹配，不能据此宣称所有分数错误。原文没有给每次有效题数、原始 success counts 或额外聚合规则；未知是否存在任务排除、统计处理或排版问题。本篇原样保留报告分数及其算术差值，将 **dataset size 与 scored denominator 分开**，不猜一个新分母。

| 底座 / 训练数据 | TB2 Acc. % | SWE-Pro Resolved % | Doc2Repo Pass Rate % |
| --- | ---: | ---: | ---: |
| Qwen3-30B-A3B-Instruct base | 7.87±0.00 | 3.26 | 5.94±0.88 |
| + Endless Terminals | 19.48±3.00 | 21.84 | 18.26±2.39 |
| + CLI-Gym | 23.22±2.70 | 28.81 | 29.91±1.53 |
| + SETA-Env | 23.22±0.75 | 29.91 | 24.91±1.84 |
| + TermiGen | 23.60±1.12 | 27.77 | 34.11±2.64 |
| + TerminalTraj | 26.22±0.75 | 26.28 | 24.36±0.96 |
| + CalibForge | **32.58±1.12** | **30.94** | **35.98±1.82** |
| Qwen3.5-35B-A3B base | 39.10±1.09 | 41.29 | 44.92±1.14 |
| + TermiGen | 40.07±0.99 | 43.37 | 44.54±1.58 |
| + TerminalTraj | 40.82±0.75 | 43.91 | 47.20±1.89 |
| + CalibForge | **47.57±0.99** | **44.32** | **48.77±0.90** |

来源：Table 1，p.7。所有基线重蒸馏各自**完整公开任务集**，共用 teacher 和 SFT recipe；SETA-Env 指 2026-01 release 的 1,375 题。35B 只重训 30B 上最好的 TermiGen、TerminalTraj，未覆盖所有基线。全量表不是相同任务数、轨迹数、token 数或训练算力的比较。

### 7.2 增益与因果限制

- 相对各自底座：30B 在 TB2 / SWE-Pro / Doc2Repo 增加 **24.71 / 27.68 / 30.04 个百分点**；35B 增加 **8.47 / 3.03 / 3.85 个百分点**。不是相对百分比增长，也不是某一个模型同时拥有所有“最大”增益。
- TB2 相对对应底座块最强训练数据基线 TerminalTraj：30B +6.36，35B +6.75 个百分点。OOD 最强基线不同：30B SWE-Pro 比 SETA-Env +1.03、Doc2Repo 比 TermiGen +1.87；35B 比 TerminalTraj 分别 +0.41 / +1.57。小差值无正式显著性检验，不宜写成已确定统计优势。
- Fig.3（p.8）每类画的是三次尝试中至少成功一次的 **pass@3 已解题数**及相对 base 的净增加，不是 Table 1 的均值准确率。30B 增加 SWE 6 题、Security 5 题、SysAdmin/Debugging 各 4 题等；两模型在图中各类均提升或持平，但部分类别仅 1 题，不能证明每类真实通过概率都不下降。
- §3.2 作者将数据源视为主要实验差异，支持这些数据在该训练配方下有用。数据量、组成、生成/校准预算、保留轨迹长度未全部匹配；仅凭 Table 1 无法把增益全部归因于校准判据。35B TermiGen 的 Doc2Repo 44.54 低于 base 44.92，也说明特定数据源并非所有任务均提升。

### 7.3 四臂校准消融

| 构造方式 | 共同任务数 | 过滤后 SFT 轨迹 | TB2 Acc. % | 相对 No Solver（百分点） |
| --- | ---: | ---: | ---: | ---: |
| No Solver | 1,300 | 2,466 | 22.47 | — |
| Single Solver | 1,300 | 2,493 | 24.34 | +1.87 |
| Multi Solver | 1,300 | 2,425 | 29.21 | +6.74 |
| Contrast Solver | 1,300 | 2,561 | 31.09 | +8.62 |

来源：§3.4，p.11；Table 3，p.12。四臂同 Qwen3-30B-A3B-Instruct、teacher 蒸馏与 SFT 配方。No Solver 仍有 authoring、validation、自解，缺的是外部 solver；Single Solver 是同模型的独立 solver，能用结果**和轨迹**引导修订。不能把它简化成“只多一个打分器”。

这组数据排除了“Multi 只是拿到更多成功轨迹”的解释，且对比校准分数最高；但 **Multi 和 Contrast 的模型组合、探测预算及保留关系同时不同**，不能孤立成“只改 indicator 就有 +8.62”。原文没有作者搜索/API token、每臂校准总轮数、训练 token/steps 等预算匹配，也没有报告训练多 seed 或 Table 3 的误差条。§3.1 说 TB2 一般三次均值，Table 3 单独未列重复明细。

另一个必须保留的计数疑点：Table 3 的 Multi 1,300 题多于最终公开 multi 1,263 题；可能涉及独立构造批次或筛选差异，但 §3.1–3.4、D/E 与公开数据卡未解释其关系。不能写成“从最终 multi 子集中无放回抽 1,300 题”。

### 7.4 初次探测、修订效果与成本长尾

Fig.8（p.12）统计 contrastive runs 的首次**verified solver probe**：目标关系 19%、both pass 61%、both fail 16%、inverted 4%；最终 run-level accepted 96%、discarded 4%。候选进入前均已通过结构验证与自解。因此作者关于“仅验证无法保证在目标能力区间内”的解释有实证支持；96% 指修订后被保留的运行，不是训练准确率、初始候选固定版本可解率或所有生成 clue 的产出率。图没有给精确样本总数。

Fig.9（p.12）按**完整 calibration run 中记录的 probe 数**累计保留：一次 15%、≤5 次 53%、≤10 次 76%、≤20 次 93%、最终 96%；未保留比例依次 85/47/24/7/4%。首次目标关系 19% 与一次即完成保留 15% 确实被原文标为两种统计口径，**但这不足以解释差异**：Algorithm 1（p.4，行 9–10）规定首次满足 `Cγ` 就立即 return task；若同一批运行且一次 probe 对应一次循环，这两项应相同。原文未给逐 run 数据、probe 记账规则或纳入/排除标准来解释 4 个百分点差异。因此保留为流程与统计之间未解决的一致性缺口，不编造重试/二次验证原因将其抹平。

作者从此解释短预算会偏向几次修订即可恢复的任务，长尾需要更多校准。此推论合理但没有“把 Rmax 改为 5/20/50 后下游学习与总成本”实验，也没有固定候选、纯过滤对比主动修订的完整训练对照，不能将 96% 写成已证明最优预算。

### 7.5 全部训练后模型失败案例

附录 F（p.25–27）从两个模型各三次 TB2 运行选出可核动作、工件和 verifier 的案例；其目的为解释失败机制，不是随机抽样统计。

| 案例 | 六次结果 | 轨迹与 verifier 证据 | 作者诊断 / 解读边界 |
| --- | --- | --- | --- |
| F.1 `regex-log` | 30B 三次全失败；35B 三次全成功 | 30B 在临时脚本反复试正则却到超时仍未写要求的 `/app/regex.txt`；35B 写文件并按 Python `re.findall` 指定接口验证 | 中间推理进展不等于完成交付；不能归因成只是不懂正则 |
| F.2 `password-recovery` | 30B 三次全失败；35B 三次全成功 | 两次 30B 把 `PASSWORD=` 前缀算入密码长度，提交局部片段；另一次超时无文件；35B 组合分散片段并查 23 字符、首尾及字符集 | 局部合理证据不能替代全局约束检查；不是“35B 所有取证任务都可靠” |
| F.3 `db-wal-recovery` | 两模型各三次全失败 | 六次都在复制/解密 WAL 前用 SQLite 打开 `main.db`，只得 5 条基础记录并移除不可读 WAL，丢失另 6 条；30B 无有效交付，35B 重构 JSON 通过基本 schema 却未过 11 条完整性与实际解密检查 | 观察动作可能改写恢复证据；保留状态应先于应用打开。安全有效性不能只看 schema 通过 |

这些负结果保留了“更强 student 也共同失败”的证据；未报告相应修复训练或干预消融。不能把它们外推成项目二长期记忆/世界模型已经必要，当前直接对应状态保存、交付接口与错误分析。

## 8. 成本、开放资产与复现程度

### 8.1 成本不能合并为一个已知总数

| 成本阶段 | 确定知道 | 尚未得到 |
| --- | --- | --- |
| 外部研究、任务作者、自解与重建 | 有草稿/独立 sandbox 和修复循环；A 有 24 搜索单例 | 全库候选/搜索/构建量、API 费用、CPU-hour、墙钟 |
| 校准 probes | 100 步/30 分钟/solver/attempt、最多 50 轮；contrastive 漏斗 | 模型价格/输入输出 token、总 probes、并发与总费用；Fig.9 不能替代原始成本 |
| Teacher 蒸馏 | 2 次/题、200 步/1 小时/次；Pro high | 各来源完整成功率、全量过滤后轨迹/token、API 费用 |
| SFT | 两 student 配方，64×H20、10 epochs、131,072 context | 训练时长/GPU-hour、并行布局、总 tokens、每成功能力增益成本 |
| 评测 | TB2 sandbox 16 CPU/32 GB、500 步/1 小时，三次；其他协议见 §6.1 | 总 CPU/API/GPU 花费、OOD 精确运行配置 |

论文未提供可比较的端到端吞吐、GPU 利用率、美元/保留任务或美元/benchmark 增益。不能由个案和单次上限推导“便宜”，也不能由 64×H20 推导必须 64 卡才可用该数据。

### 8.2 实际公开到什么程度

| 资产 | 已核入口与版本证据 | 开放与复现边界 |
| --- | --- | --- |
| 论文与附录 | v1 PDF；27 页；方法、prompt、超参与案例 | 无完整 authoring/revision prompt、构造日志或训练配置文件 |
| [CalibForge GitHub](https://github.com/AweAI-Team/CalibForge/tree/4a219dcd321879c4f7f72953184e49891fb19d52) | Git tree 仅 `.gitignore`、README、assets 目录和一张图；[快照](sources/E2/calibforge_README.md) | 是资料入口，不包含完整 authoring/calibration/revision pipeline 实现 |
| [HF dataset](https://huggingface.co/datasets/AweAI-Team/CalibForge/tree/fb1e75441a94b8bb0ced08acd6b59e711704d70a) | [数据卡](sources/E2/dataset_README.md)、API 文件清单核得 5,431 个 instruction 和 5,431 个 test.sh；metadata、image_mapping、任务目录公开 | 每题有指令、Dockerfile/初始材料、测试、task.toml 与镜像引用；未拉镜像核可访问性/可运行性；未取得完整 solver revision 日志；GitHub README 的 Released Data 声称同时提供成功蒸馏轨迹，但本次未在 pinned HF 卡和文件清单中定位可独立消费的 SFT/rollout 文件，具体发布位置/格式待核 |
| [30B 模型](https://huggingface.co/AweAI-Team/CalibForge-30B-A3B/tree/59a534b076a76b7a5e617f68e97666b4c8063cac) / [35B 模型](https://huggingface.co/AweAI-Team/CalibForge-35B-A3B/tree/51f563b3ca294e28f430e58dc98509c4867fb19b) | 两模型卡、config/tokenizer 与 safetensors 分片文件清单可访问；[30B 卡](sources/E2/model30_README.md)、[35B 卡](sources/E2/model35_README.md) | 发布存在性已核；卡片另给 262,144 configured maximum positions 与 SGLang `--tp 8 --dp 1` 启动示例，两者不等于 131,072 SFT context 或训练并行布局；未加载权重、验生成行为或复现分数 |
| [AweAgent recipe](https://github.com/AweAI-Team/AweAgent/tree/b38414e5dc9c7c51f2ec48318b718af0c8852060/recipes/terminal_bench_v2) | 运行入口/配置/任务/evaluator 见 §6.3 | 可复用蒸馏/评测 scaffold；README 明说是基于 DeepSeek-V4 描述的独立实现，不是 DeepSeek 官方实现；不补全论文生产与 SFT 细节 |

**许可状态以读到的声明为限**：两个模型卡 metadata 写 Apache-2.0；dataset README 徽章标 CC BY 4.0，但所 pin 文件清单没有根 `LICENSE`、card metadata 没有 `license` 键，仅部分内嵌项目含许可文件。本篇记录该声明/文件缺口，不宣称所有嵌入源码和镜像依赖都因此统一按 CC BY 4.0 许可。未作逐工件法律审查。

## 9. 证据边界、未知项与旧稿纠正

### 9.1 把事实、作者解释、阅读者推断分开

- **原文确定事实**：两个 retention predicates；每 solver 执行预算；最终 collection 数；四臂任务/轨迹计数；Table 1/3/E1；附录所列案例和 prompt。
- **作者解释**：分歧/强弱对比定位可学习区间；both-pass 主导说明有效性检查未控制区分度；更多 thinking tokens 配更少交互步说明步数不充分；反馈可修复很多 mismatch。证据限于当前固定 solver 与案例/实验。
- **本篇推断**：solver 家族重叠（author/self-solver/strong/teacher 多用 Pro）可能带来 solver/scaffold 偏好；反复改到 weak-fail 可能对 panel 过拟合；一次 outcome 不足以估稳定通过率。原文未测这些风险的效应量，不能当作者已证实的负面结果。
- **不支持的延伸**：目标 checkpoint 的 nonzero-advantage ratio 已提升、在线 RL 已验证、OPD 已验证、8 卡成本已验证、全库 verifier 无误杀、去污染已彻底、作者平台完整开源。

### 9.2 最影响复现与项目映射的未知项

| 未知 / 冲突 | 实际查阅范围 | 可以下的结论 |
| --- | --- | --- |
| 19% 首次目标 vs 15% 一 probe 完成 | Algorithm 1 行9–10、§3.4、Fig.8–9 | 统计标签不同并不能消除与立即早停逻辑的一致性疑点；缺逐 run 解释 |
| 1,300 Multi 消融 vs 1,263 最终 multi | §3.1–3.4、Table 3、D/E、数据卡 | 未解释批次/抽样/过滤关系 |
| batch 128 与 64×1×4 | Table E1 原页；附录 E | 并行度/有效 batch 关系待澄清，不擅改数 |
| “full” 去污染组合规则 | §3.1 与 D，p.24–25 | 给阈值和信号，未给足可执行组合/名单/剔除数 |
| 全量 teacher 轨迹漏斗和 token mask/loss 分母 | §3.1、E、资产入口/文件清单 | 只确定成功轨迹经三类过滤再 SFT；不把框架默认行为当事实 |
| 同 solver 重复、错误分类、复测稳定性 | §2–3、A–C；公开 recipe 的有限源码 | 原文没有稳定性估计和生产错误细则；后发布 eval code 不补生产协议 |
| 生产/蒸馏/训练/评测总成本 | §3.1、§3.4、A、C/E、官方 README | 只有局部上限和硬件，不能报总美元/GPU-hour |
| 评分实际分母、OOD harness/预算与统计显著性 | §3.1、Table 1、Fig.3、F；整数计数算术核验 | 731与89是声明集合规模；部分百分比不匹配简单二元等权分母，缺原始计数/排除/聚合解释；另缺配置、训练 seeds 与显著性检验 |
| 数据和镜像可运行性/完整许可证 | pinned HF 卡与全文件名清单；未拉取执行环境 | 公开路径存在，性能/安全/全工件许可未核 |

### 9.3 对两份旧稿的更正与降级

| 旧说法 / 容易误读处 | 本次处理及原文证据 |
| --- | --- |
| “本仓库无本地 PDF” | 已过时，现有 27 页 v1 PDF，直接核全文；保留旧稿文件 |
| 标题仅《CalibForge: Adversarial Solver Calibration》、机构仅 AweAI-Team | 恢复完整正式标题与首页机构；提交日 8 月 6 日与文内 8 月 7 日并列 |
| Single Solver “只给 pass/fail 反馈” | §3.4 明说 pass/fail outcome **and trajectory**，补正 |
| “附录给了 prompt 模板”可能被理解成 authoring pipeline prompt | C.2 是 Eval system/user prompt；A/B 是案例，非完整生产模板 |
| “匹配任务数证明校准本身贡献 +6.7~+8.6” | 保留结果，限定为四种构造方案的 SFT 对照；没有完全控制构造模型/API成本、训练 token 或候选来源 |
| “19% → 96%；15% 一次达标”无口径说明 | 分别列首次 verified outcome 与 completed-run probe 数，并指出其与 Algorithm 1 立即早停之间仍有未解释差异 |
| “难度失配大多可修” | 限定为被记录 contrastive runs 的任务修订后接受率，不推广到所有任务源/当前 policy |
| “每轮最多 50 次校准”式表述 | 正确为每候选最多 50 **轮**，每轮每 solver 各有一次尝试；不是 50×50 |
| “SWE-Bench Pro 被后续审计削弱” | 本任务原文和指定资产不支持这条外部审计结论，不作为 E2 已核事实；另有独立评测审计来源才能引用 |
| “截至某日尚无独立复现” | 本轮没有系统检索独立复现，不保留为当前已核结论；AweAgent reproduction 是作者发布 |
| “必须额外记录完整 lineage/状态机、按 T0 单独论证” | 四态诊断可保留作设计候选，不由此新建治理平台或新训练准入定案；当前映射见 §10 |

## 10. 对 RepoHarness 项目一的意义

映射日期 **2026-09-07**。读取 [CURRENT-STATE-BRIEF](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md)（2026-09-05）和 [项目一设计建议](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)（2026-09-07）相关内容；主资料目录 HEAD 已知为 `ce2009f879cf38071d7898a1387e01d4e27741d6`，文档存在未提交内容，因此以有日期的文档分别归因。简报描述已搭本地链、216 题候选 ingestion；较新的建议 §4.1 仍列上下文重写、token 覆盖、预算、评分和生命周期等未闭合面。不能只用 9 月 5 日快照宣称 9 月 7 日训练链完整可信；建议是咨询文本，不替代 06 计划/C 包批准。本任务没有再做代码审计，以下是**设计层候选映射**。

当前基线是 miles + SGLang + 外部 coding harness（简报为 Claude Code 接入）；上游承担训练/推理内核、fully async、通用权重同步以及已有 TITO/OPD 等能力。rh2 的项目工作集中在环境/评分可信、harness 到真实训练消费的边界及实证。CalibForge 没提供理由重造这些上游组件。

| 候选借鉴 | 来源依据 | 归属 / 增量 | 条件、成本与最小验证 |
| --- | --- | --- | --- |
| 先复用一小批公开 terminal 任务作为迁移探针 | 5,431 Harbor-style tasks；§3.1、公开数据卡 | 上游资产可复用；rh2 只适配所选环境/评分，不自建大规模作者管线 | 先选可本地 CPU/Linux 复现的构建调试/数据工件题；验证初始、参考完成、合法替代解、重复评分；报告可运行率与每有效任务成本 |
| 把环境有效性与目标模型学习机会分开 | `V(τ)` 与 `Cγ`；Fig.8 | rh2 离线数据诊断候选，不增加逐轨迹资格证书 | 固定本项目模型/harness/budget，在已有候选上重复探测，记录 pass-rate 与错误类型；外部 Pro/Flash 分歧不能替代目标 policy 结果 |
| 用反馈修题或修 verifier，优先处理明确缺陷 | B.1–B.3 | 应用层可归属的窄增量，沿用任务版本记录 | 仅训练/dev 侧小批任务，比较修前后 no-op、参考解、替代解与目标 policy；花费和保留率单列，final test 不参与修订 |
| 评测同时看最终工件与错误机制 | C、F；公开 same-session evaluator | 外部 harness 可承担工具交互；rh2 对冻结状态/评分边界负责 | 对三类错误抽样分析：未交付、局部证据、破坏可恢复状态；terminal 是否可冻结重放要按任务定，不能盲套 SWE patch 模式 |
| 等任务量对照需补等预算证据 | Table 3 与成本缺口 | 我方实验设计增量，不是新训练算法 | 若做校准比较，同时记录 API/CPU/GPU、成功轨迹与训练 tokens；与静态分层基线比较独立学习收益/成本 |
| 对比校准直接进入 RL/OPD loss 或在线课程 | 论文无相关训练实验 | **暂不适用** | 先有目标 policy 组内 reward 分布与独立学习证据；不改变 faithful DIS、staleness 或组准入既有语义 |

项目建议 §3.5 所述同策略独立二元采样中，n=8 的混合成败概率 `1-p^8-(1-p)^8` 只是本项目讨论学习机会的简化分析，**不是 CalibForge 公式或实验结果**。它的前提不保证适用于异构 solver panel 或异步跨版本采样；CalibForge 未证明自己的 task acceptance 会提高该概率。

可以支持项目叙事的是：为何环境能运行/参考解通过不足以证明目标模型有学习机会；为何 verifier 应允许合法替代解；为何测量应区分任务、轨迹、token、成本和真实学习。还不能写进已完成贡献的是“我们造出了更优 curriculum”“提高 RL sample efficiency”或“自研异步训练系统”；这些必须有本项目受控实测且诚实归因上游。

## 11. 快速定位与关联阅读

- 校准控制流与公式 → 本篇 §3、§4.2、§5.1；原文 Algorithm 1（p.4）、Eq.(1)–(2)（p.5）。
- 任务构造/验证/去污染 → 本篇 §4；原文 §2.2、附录 A/B/D。
- Teacher / SFT 配方 → 本篇 §3、§5.2；原文 §3.1（p.6）、Table E1（p.25）。
- Harness / 三套预算 / 代码差异 → 本篇 §6；原文 C（p.22–24）；固定版本 [source_manifest](sources/E2/source_manifest.json)。
- 主结果 / 消融 / 校准漏斗 → 本篇 §7.1–7.4；原文 Table 1（p.7）、Table 3 与 Fig.8–9（p.12）。
- 负结果 → 本篇 §7.5；原文 F.1–F.3（p.25–27）。
- 与 E3 Envs-FORGE、E4 Endless Terminals、E5 SWE-smith 的关联：分别比较是否真正 RL、是否动态更新任务、预算和环境复用；这里仅列来源名，不把未读内容当 E2 事实。旧稿仅通过 §1 两个有效链接保留。

## 12. 独立检查与修订记录

2026-09-07，按本任务授权在本线程创建一名 **GPT-6 Astra / high** 独立 sub agent，使用干净上下文（`fork_turns="none"`）。审查者先独立读取全部正文与 A–F 附录、建立覆盖表，再对照初稿，并核对九份固定来源快照；公式、消融/漏斗和训练超参表另作原页目视检查。正式记录：[04_E2_review.md](reviews/04_E2_review.md)。

审查未发现 P0/P1，发现一项 P2 和三项 P3，已逐项处理：

| 发现 | 正文修订与证据 |
| --- | --- |
| F1 / P2：声明题数与部分评分不满足简单整数分母 | §7.1 新增 SWE-Pro 731、TB2 3×89 的可复算反例；§9.2 记实际分母/聚合缺口；Table 1 报告值不改 |
| F2 / P3：19%与15%不能仅用“不同口径”解释 | §7.4 对照 Algorithm 1 行9–10立即早停；§9同步保留未消除一致性问题 |
| F3 / P3：轨迹发布声明遗漏 | §8.2 并列 GitHub README“已发布成功轨迹”声明与本次未定位独立HF轨迹资产的事实；不声称一定未发布 |
| F4 / P3：解答泄漏/未声明要求检查时序 | §4.1 改为“进入验证前检查”，与 §2.2 p.4 的联合构建后、验证前顺序一致 |

审查者已回读确认 F1–F3 的修订；主作者按原文核改 F4，并在审查文件末尾追加逐项处置和证据。自查另纠正关联来源编号，并核验主表差值、公式/代码块配对、本篇相对链接与来源快照 SHA256。没有运行训练或修改实现。全体后训练正文与附录的阅读、独立审查及修订均已完成；未披露/未核实项仍按 §9.2 保留，不等于实验已复现。
