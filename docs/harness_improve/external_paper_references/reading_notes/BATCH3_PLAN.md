# 第三批精读准备：任务 13–18

日期：2026-09-07。状态：**仅完成来源与派工准备，第三批未启动，未完成这六篇的全文精读或独立审查。** 前两批现已完成，见 [第二批质量检查](BATCH2_QUALITY_REVIEW_20260907.md)。用户最新决定：由外部 Pro 复查两批、重新选择后续来源并在外部继续精读；本地不继续派发。本文件原顺序与 Codex 提示仅作历史准备材料，外部 Pro 可调整、替换或暂缓，不承担启动授权。

原准备方案选择 B1 的前六项：SAO、CompactionRL、SkyRL-Agent（SA-SWE）、SDPO、OPSD、MOPD。六项各自独立成文、独立审查。**SDPO v2 为 50 页，应按长报告安排；MiMo-V2-Flash v2 为另一份 31 页技术报告，留作后续独立任务，不附带交给 MOPD 任务全文精读。** 本轮发现的是命名与旧稿边界问题，没有发现需要更换六篇来源的标题误配。

导航：[范围与核验](#1-本次核验与派工边界) · [任务总表](#2-六个任务与文件所有权) · [资料卡](#3-逐篇资料卡与待核问题) · [既有成果关联](#4-与第一二批成果的关联) · [可派发提示](#5-可直接派发的逐任务提示) · [MiMo 后续安排](#6-e13-mimo-关联候选的独立边界)

## 1. 本次核验与派工边界

准备依据为 [阅读库 README](README.md)、[来源目录](SOURCE_CATALOG.md)、[公共提示词](TASK_PROMPT.md)、[第一批质量检查](BATCH1_QUALITY_REVIEW_20260907.md) 与 [笔记模板](NOTE_TEMPLATE.md)。项目映射只需参考 [当前状态简报](../../../agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md) 和 [项目一建议 §6](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md)。准备时 checkout 为 `ce2009f879cf38071d7898a1387e01d4e27741d6`；这不是阅读资料已提交或工作区清洁的声明。正式派发时仍须核实实际资料在工作目录中可读。

本次实际做了：

- 联网打开七份 arXiv 摘要页，核标题、选定版本和提交历史；检查三份原文关联的官方 GitHub 入口可访问。
- 对已存的 SAO、CompactionRL、MOPD、MiMo PDF 用 `pdfinfo` 核物理页数，用 `pdftotext` 检查首页版本与章节标题。对 SkyRL-Agent、SDPO、OPSD 在线 PDF 只在内存中读取 metadata，没有新增本地来源文件；检查其 HTML 章节标题以确定阅读范围。
- 阅读指定旧摘要/专题的相关内容，识别可复用骨架、待核事实和过时项目映射。检查本文件引用的本地文件存在。

**上述操作不等于正文、公式、表格或附录已经精读。** 目录范围是防遗漏的准备信息；公式、数字和旧稿主张仍由正式阅读者回原文核验。本次未逐字节比对远端与本地 PDF，未做不同版本正文差分，未验证论文实验或官方代码的运行行为。未找到可复用 TeX 的说法仅限资料目录登记及本次针对文件名/编号的仓库检索，不表示历史上从未取回过 TeX。

以下保留原本地派发规则，供理解已有质量要求；外部阅读应按实际工具能力调整，不能虚构独立审查或因模板自动启动本地任务：

1. 工具实际设置 `gpt-6-astra` / `high`。各任务按 [公共提示词](TASK_PROMPT.md) 完成全部后训练正文与附录，先从原文目录建覆盖表，再回答额外问题。数学、科学推理、通用工具、计算机使用、记忆 agent、偏好与安全等只要原文涉及后训练，都不能因当前 SWE 重点而遗漏。
2. 初稿后按用户既有授权，在本线程内创建一名 `fork_turns="none"` 的独立 Astra / high 审查 sub agent。审查者独立核范围和事实，主作者收到报告后修订；未完成审查与修订不能宣布精读完成。记录主/子线程 ID、实际模型与 effort、来源版本、固定交审稿及处理结果。不扩大为额外侧栏任务或递归团队。
3. 只写自己的正文、审查文件与必要来源附件。共享 README/catalog/模板由主线程维护。正文摘要与导航前置，证据限定紧邻公式和数字，重复未知项集中列明；不设机械字数上限。
4. 文献与工程事实分开；代码若需补查，只追关键机制并绑定 commit。旧稿的 FA/slime 状态与 2026-09 的 miles 候选链分开。本轮不改代码、训练定案、taskset 或 loss，也不下载模型权重、不跑训练、不租 GPU。

5. 下表固定版本是本次准备基准。正式启动时重查官方更新；若后训练、环境、infra、评测或附录有实质变动，保留旧版身份，补读并单列新版增量，不只登记版本号。

## 2. 六个任务与文件所有权

以下输出路径均相对于本目录，**是预定文件名，不是已交付链接**。来源附件目录也只预留所有权，本次未创建。六任务均需独立审查，不因短于 SDPO 而合并。

| 任务 | 主来源与固定版本 | PDF 物理页数 | 预定正文 | 预定审查 | 必要附件专属目录 |
| --- | --- | --- | --- | --- | --- |
| 13 | R15 SAO，2607.07508v1 | 14 | `R15_single_rollout_asynchronous_optimization.md` | `reviews/13_R15_review.md` | `sources/R15/` |
| 14 | R14 CompactionRL，2607.05378v1 | 13 | `R14_compaction_rl.md` | `reviews/14_R14_review.md` | `sources/R14/` |
| 15 | O01 SkyRL-Agent，2511.16108v1 | 16 | `O01_skyrl_agent_sa_swe.md` | `reviews/15_O01_review.md` | `sources/O01/` |
| 16 | N07 SDPO，2601.20802v2 | 50 | `N07_sdpo.md` | `reviews/16_N07_review.md` | `sources/N07/` |
| 17 | N08 OPSD，2601.18734v3 | 15 | `N08_opsd.md` | `reviews/17_N08_review.md` | `sources/N08/` |
| 18 | E7 MOPD，2606.30406v1 | 15 | `E7_mopd_multi_teacher.md` | `reviews/18_E7_review.md` | `sources/E7/` |

页数用于安排阅读工作量，不是质量或耗时保证。SDPO 的 A–F 附录包含方法实现、理论、消融、模板和定性实例，不能按标题把它当两篇 self-distillation 短文之一，也不能为了六任务同时结束省略附录。可让任务 16 优先进入执行队列或单独保留更长回收窗口，任务编号与范围不变。

## 3. 逐篇资料卡与待核问题

### 13 · R15 SAO

**正式来源。** *Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning*，Tsinghua University；[arXiv v1 摘要与提交历史](https://arxiv.org/abs/2607.07508v1)，2026-07-08。[固定版本 PDF](https://arxiv.org/pdf/2607.07508v1) / [HTML](https://arxiv.org/html/2607.07508v1)；TeX 可从摘要页的原始来源入口取得。本次未核定独立的官方 SAO 实现仓库，不能据此断言没有公开代码。

**本地与旧稿。** [本地 PDF](../pdfs/2607.07508v1.pdf) 首页确认为 v1，共 14 页。未找到可直接复用的本地 TeX 路径。[旧独立摘要](../../../../knowledge/summary_single_rollout_asynchronous_optimization.md) 可复用 single-rollout、DIS、critic、Skip-Observation GAE 的问题骨架；[GRPO/DIS/SAO 专题](../../../agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md) §2.3、§6–8 提供项目疑问；[配方矩阵](../agentic_rl_training_recipe_evidence_matrix.md) 只作交叉索引。

**准备已核。** 标题、版本、页数匹配；目录与摘要显示范围还包括推理 benchmark、在线学习模拟、agent step 作为 action 的附录比较和限制，旧稿主要写 SWE，必须扩充。

**待全文核验与额外关注。**

- 精确恢复 DIS 的 ratio、双边边界、支持集/采样分布、硬屏蔽与归一化；区分论文 DIS 与项目 faithful DIS 的额外约定，不把项目实现反写成论文公式。
- single-rollout 取消什么等待、仍保留什么 batch/异步组织；prompt、rollout、token、update 的单位；critic 预训练、冻结参数、更新频率与 GAE 的全部细节、消融和成本。
- 核旧稿的“约 400 步后分化”“约 160 步崩溃”和成绩来源；不得把一个设置中的曲线当通用训练阈值。
- 纳入全部数学/推理与在线模拟结果及附录反例。原文不足以证明“开 compaction 就应转 SAO”，也不证明本项目八卡的成本可接受；这些是项目推论，需单列。
- 旧稿关于 `TrajectoryProjection` 和 slime 缺口的表述有时间性，当前链路映射应优先参照 N11 与最新项目简报。

### 14 · R14 CompactionRL

**正式来源。** *CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents*，Tsinghua University；[arXiv v1 摘要与历史](https://arxiv.org/abs/2607.05378v1)，2026-07-06。[固定版本 PDF](https://arxiv.org/pdf/2607.05378v1) / [HTML](https://arxiv.org/html/2607.05378v1)。本次未核定专属开源配方；正式阅读者应核原文的开放资产声明及其实际入口。

**本地与旧稿。** [本地 PDF](../pdfs/2607.05378v1.pdf) 首页确认为 v1，共 13 页；未找到可复用本地 TeX。[旧摘要](../../../../knowledge/summary_compaction_rl.md) 的 execution/summary、mask、GAE 与结果骨架可复用；[算法专题](../../../agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md) §2.4、§3、§9.5 提供待核推论。

**准备已核。** 标题、版本与页数匹配；章节包括 trainable context compaction、优化、实验设置、主结果、消融和分析。只检查了章节标题与首页，尚未核原始公式及评测表。

**待全文核验与额外关注。**

- 一次任务、rollout、segment、summary 的关系；生成 summary 与复制 summary 的 token mask；上下文重建模板、触发规则、终态和上限。
- PPO 目标中的策略版本、token-level loss 分母、GAE 的跨段距离与近似，以及 observation 如何计数。不能把 SAO 的 DIS 自动并入这篇论文。
- 原文的训练数据、reward、critic warmup、SWE/terminal 预算、抽样题数和评测重复次数；训练开关与评测开关分开，完整保留 single-window 的退化与消融。
- 旧稿所说“当前 lineage 基础已足够/缺何字段”“首训仍应关 compaction”属于历史项目分析。本篇只提出条件化候选实验，不改当前 C 包待定事项。

### 15 · O01 SkyRL-Agent / SA-SWE

**正式来源。** *SkyRL-Agent: Efficient RL Training for Multi-turn LLM Agent*；[arXiv v1](https://arxiv.org/abs/2511.16108v1)，2025-11-20；[PDF](https://arxiv.org/pdf/2511.16108v1) / [HTML](https://arxiv.org/html/2511.16108v1)；论文链接的 [官方 SkyRL 仓库](https://github.com/NovaSky-AI/SkyRL) 可访问。**SA-SWE-32B 是模型名，不能作为正式论文标题。**

**本地与旧稿。** 本次在现有目录与针对编号的检索中未找到本地 PDF/TeX；正式任务可保存原文到自己的 `sources/O01/`。在线 PDF metadata 为 16 页。[horizon masking 专题](../sa_swe_horizon_masking_analysis.md) 保留了论文与代码证据分层，可复用；其自记论文版本为 v1，官方代码为 `6ae5d677d8f0`（2026-08-03），晚于论文，且专题仍标 draft。不能把该代码视为 2025 年论文实验确用版本。

**准备已核。** 正式标题与 ID 对应正确；HTML 目录包含框架、SWE，以及 §5 Deep Research、Memory Agent、Computer Use Agent。后面三个训练案例必须读，不能让原有 horizon 专题定义整篇阅读范围。

**待全文核验与额外关注。**

- 调度器、工具循环、异构后端与错误处理；异步 dispatch 和异步 policy update 是否相同；速度、成本的参照组、单位及硬件。
- SWE 数据/环境、AST 工具、hints、LOO、归一化、horizon masking，以及评测与跨任务泛化；检查旧稿“batch 64 按任务计”等解释是否确有一手证据。
- horizon 成员的 reward/advantage、梯度、loss 分母、batch 计数分开说明。没有公开 loss 公式时，不用当前代码或我方手算补成作者确定方案。
- 官方 `main` 可能继续变化。只有实际需要补查实现时才固定 commit，并保留“论文事实”和“后续官方实现”的时间边界。
- 旧专题的 FA-4/D1b 建议不再是当前执行计划；记忆 agent 在本篇属于原文训练范围，不代表把项目二加入项目一实现范围。

### 16 · N07 SDPO

**正式来源。** *Reinforcement Learning via Self-Distillation*；[arXiv v2](https://arxiv.org/abs/2601.20802v2)，初版 2026-01-28，v2 为 2026-02-16。[PDF](https://arxiv.org/pdf/2601.20802v2) / [HTML](https://arxiv.org/html/2601.20802v2)；原文链接的 [官方代码 lasgroup/SDPO](https://github.com/lasgroup/SDPO) 可访问。SDPO 全称依论文为 Self-Distillation Policy Optimization，正文与仓库措辞应按各自来源记录。

**本地与旧稿。** 未找到本地 PDF/TeX 或独立逐篇旧稿；在线 PDF metadata 为 **50 页**。[项目一建议 §6](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md) 及 [原始讨论](../../../agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md) 中 SDPO 段可作问题线索，不能当原文证据。资料下载/提取只进入未来专属 `sources/N07/`。

**准备已核。** 正式标题、v2 日期、官方仓库和原文目录。目录覆盖无丰富反馈、有丰富反馈、test-time self-distillation；附录 A 实现、B 理论、C 相关工作、D 更多结果、E 实验与模板、F 定性实例。未核公式、实现及实验数值。

**待全文核验与额外关注。**

- rich feedback、成功轨迹作为隐式反馈、自教师条件与更新方式；teacher/student 分布、梯度估计、KL/logit/token 目标、stop-gradient、正则化和 off-policy 扩展。
- 计算与显存、稳定化、强弱模型、遗忘、与 GRPO 组合、反馈类型消融；不能仅总结“把反馈变稠密监督”。
- 科学推理、工具使用、竞争编程和 test-time 学习的任务设置、数据分割、预算/选择标准与失败案例，连同附录全部覆盖。
- 测试时是否更新权重、使用哪些题内信息、与 best-of-k/多轮对照是否共享预算，必须具体说明；不能把 test-time 自蒸馏称作普通多轮推理。
- 与 OPSD/MOPD 的比较先列各自原文事实，不合称同一算法。迁移 SWE 需另核公开反馈与私有评分材料边界，不能建议直接把 hidden grader 内容交给模型。

### 17 · N08 OPSD

**正式来源。** *Self-Distilled Reasoner: On-Policy Self-Distillation for Large Language Models*；[arXiv v3](https://arxiv.org/abs/2601.18734v3)，初版 2026-01-26、v2 为 2026-03-05、v3 为 2026-03-20。[PDF](https://arxiv.org/pdf/2601.18734v3) / [HTML](https://arxiv.org/html/2601.18734v3)；摘要直接链接的 [官方代码 siyan-zhao/OPSD](https://github.com/siyan-zhao/OPSD) 可访问。选择 v3，与目录一致；本次没有做 v1/v2/v3 内容差分。

**本地与旧稿。** 未找到本地 PDF/TeX 或独立逐篇旧稿；在线 PDF metadata 为 15 页。[项目一建议 §6](../../../agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md) 与 [原始讨论中的 OPSD 段](../../../agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md) 只作线索。[本地 Prime-RL 同名实现](../../../../reference/prime-rl/src/prime_rl/orchestrator/algo/opsd.py) 文件存在，其类注释称 SDFT；**尚未证明它就是本论文的实现**，不可凭文件名建立对应关系。

**准备已核。** 正式标题、版本、页数、官方仓库。目录包含不同 divergence、生成风格、逐 token clipping、长度、全词表与 sampled-token 比较；附录有实验设置、token 类别、policy-gradient 解释和 STaR 对比。尚未核这些内容的公式与结论。

**待全文核验与额外关注。**

- verified reasoning traces 等特权信息的来源/生成成本、teacher 与 student 条件、权重共享与更新/冻结、student rollout 采样分布、完整训练阶段。
- divergence 方向、全词表/采样 token 目标、clipping 两种对象、mask/长度与 stop-gradient；保留 v3 全部方法与附录推导的适用条件。
- 数学任务、基线与 token efficiency 的分母、生成预算、数据污染/分割、消融和限制；不得将数学证据写成长程 SWE 已验证。
- 和 SDPO 的反馈来源与学习时点分开；公开/私有上下文仅在项目映射处讨论。Prime-RL 若不能确证论文对应，只作为同名工程线索列明，不能用它补论文披露。

### 18 · E7 MOPD

**正式来源。** *MOPD: Multi-Teacher On-Policy Distillation for Capability Integration in LLM Post-Training*；Peking University、Xiaomi 等，作者机构以论文首页为准；[arXiv v1](https://arxiv.org/abs/2606.30406v1)，2026-06-29。[PDF](https://arxiv.org/pdf/2606.30406v1) / [HTML](https://arxiv.org/html/2606.30406v1)。本次未核定独立官方代码仓库；正式任务核开放声明，不把 miles 示例当论文官方实现。

**本地与旧稿。** [本地 PDF](../pdfs/E7_mopd_multi_teacher_2606.30406.pdf) 首页确认为 v1，共 15 页。[旧摘要](../../../../knowledge/summary_mopd_multi_teacher_opd.md) 自称依据 TeX，但未找到可复用的本地 TeX 路径；其“本仓库无本地 PDF”已明确过时。可复用三阶段、两种蒸馏目标、同源/跨源消融与模型整合的提纲。

**准备已核。** 标题、版本、页数；目录包含 pipeline、algorithm、infrastructure、实验、309B 模型、分析、discussion，以及附录 A Training Details、B Evaluation Details。MiMo 在该论文里的实验/方法段属于本任务必须完整阅读的原文内容；这不等于附带精读 E13 技术报告。

**待全文核验与额外关注。**

- 共享 SFT、领域 RL teacher、student 初始化/冻结、domain 路由、每轮更新、多轮演进的完整关系；Math、IF、SWE 都须覆盖，不能只摘 SWE。
- PG 与 top-k 两种 loss、reverse KL、修正项、clip、采样单位及训练分母；核旧稿“只改 advantage 即可”和“teacher 开销几乎隐藏”的具体前提与证据。
- 基线正式名称、归一化成绩与原始成绩、样本效率、硬件/teacher 服务成本、SWE 环境版本/预算和全部附录参数。
- 旧稿将一个跨源 teacher 消融提升为“同源是硬前提”“不能借更强外部 teacher”，属于应收紧的外推风险；须回原文区分实验失败、作者解释和普遍必要条件，不预设纠错结论。
- 旧稿“我们本来就是 SFT→专家分叉”“超参可作直接起点”“miles 已有 OPD 就能直接用”的项目判断不能沿用为当前定案。结合 N11 已核路径，区分上游能力、实际接线与本项目未决定的方案。
- E7 与 E13 中术语、公式和配置若不同，分别标来源和版本；不得拿另一篇较详公式默默填补本篇未披露项。

## 4. 与第一、二批成果的关联

第一批以下文件实际存在，可直接查阅；关联用途是避免重复解释与错误合并，不能替代第三批原文核验。

| 第三批任务 | 第一批已完成稿中的可查位置 | 第二批回收后的关联方向（当前只列预期文件名） |
| --- | --- | --- |
| 13 SAO | [miles](N11_miles_agentic_rollout.md) §5–6 的 loss/OPD 与异步消费；[MAI](R1_mai_thinking_1.md) §4、§7 的 GRPO 分母/异步；[KAT](N01_kat_coder_v2_5.md) §5.1–5.2 的 PPO/critic | `R13_kimi_k3.md` 的 partial rollout 与训练目标；`R4_minimax_m2_series.md`、`N10_minimax_forge.md` 的调度和长尾 |
| 14 CompactionRL | [miles](N11_miles_agentic_rollout.md) §3.3、§6.3 的树/partial；[KAT](N01_kat_coder_v2_5.md) §5.6 的长上下文蒸馏与截断 | `R13_kimi_k3.md`、`E10_intern_s2_preview.md` 的长轨迹、token 捕获与 harness 语义 |
| 15 SkyRL-Agent | [miles](N11_miles_agentic_rollout.md) §3–4、§6 的运输、错误与异步边界；[Qwen](R3_qwen3_coder_next.md) §5.2 的预算惩罚对照；[Verified 审计](N13a_swe_verified_audit.md) §3–5 的评测解释限制 | `E5_swe_smith.md`、`O03_r2e_gym.md` 的环境/任务来源；`N10_minimax_forge.md` 的成本分母 |
| 16 SDPO | [KAT](N01_kat_coder_v2_5.md) §4.2、§5.2 的 near-miss/hindsight；[CalibForge](E2_calibforge.md) §4–5 的 solver 校准与离线 SFT，防止把反馈使用统称 RL | `E10_intern_s2_preview.md`、`R13_kimi_k3.md` 的蒸馏与失败轨迹处理 |
| 17 OPSD | [KAT](N01_kat_coder_v2_5.md) §5.5–5.6；[miles](N11_miles_agentic_rollout.md) §5.2；[MAI](R1_mai_thinking_1.md) §3.3、[Qwen](R3_qwen3_coder_next.md) §3.7 说明不能把不同专家合并都叫 OPD | `E10_intern_s2_preview.md`、`R2_nemotron_3_ultra.md`、`R13_kimi_k3.md` 的 teacher/student 与后训练阶段 |
| 18 MOPD | [KAT](N01_kat_coder_v2_5.md) §5.5；[miles](N11_miles_agentic_rollout.md) §5.2；MAI §3.3 与 Qwen §3.7 的非等同边界 | `R2_nemotron_3_ultra.md`、`R13_kimi_k3.md`、`E10_intern_s2_preview.md` 的整合方法；`O03_r2e_gym.md` 的 SWE 数据口径 |

第二批尚在执行，上表不作可点击本地链接，也不预写它们的技术结论或完成状态。任务可独立启动；只有成品实际回收并确认章节后，再在正文加入具体关联链接。六篇完成后可由主线程另做简洁比较表：采样主体、教师/critic、反馈、ratio/KL、mask/分母、预算和证据限制；本次不预设比较结果。

## 5. 可直接派发的逐任务提示

下列每段可作为独立任务消息。主线程通过工具实际指定 Astra / high；若隔离 worktree 不含未提交资料，先提供必要原文与旧稿的只读入口。提示中的路径均为仓库相对路径，运行时可在任务消息补实际读取位置，不把本机绝对路径写入成品。

### 任务 13 提示

你负责任务 13：完整精读 R15《Single-Rollout Asynchronous Optimization for Agentic Reinforcement Learning》，固定 2607.07508v1。先读 `docs/harness_improve/external_paper_references/reading_notes/TASK_PROMPT.md`、`NOTE_TEMPLATE.md`、`BATCH3_PLAN.md` §1/§3 的任务 13/§4，以及当前 `docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`。本地原文为 `docs/harness_improve/external_paper_references/pdfs/2607.07508v1.pdf`；正式入口 https://arxiv.org/abs/2607.07508v1 。旧稿为 `knowledge/summary_single_rollout_asynchronous_optimization.md` 与 `docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md` 的相关节。

从原文目录建立覆盖表，读完全部后训练正文与附录，包含数学/推理、在线学习模拟、附录比较与限制；SWE/DIS 问题不能限制范围。额外核 ratio/支持集/硬屏蔽/分母、single-rollout 与异步样本单位、critic 预训练/冻结/更新、Skip-Observation GAE、消融与成本，区分论文与我方 faithful DIS。输出仅为 `docs/harness_improve/external_paper_references/reading_notes/R15_single_rollout_asynchronous_optimization.md`、`reviews/13_R15_review.md`（审查路径同在 reading_notes 下）及必要 `sources/R15/` 附件。按公共提示词安排一名干净上下文 Astra / high 审查 sub agent，固定交审稿，收到审查并完成修订再交付；不启动额外侧栏任务，不改代码或训练定案。关联第一批已有文件，第二批未回收文件不造链接。

### 任务 14 提示

你负责任务 14：完整精读 R14《CompactionRL: Reinforcement Learning with Context Compaction for Long-Horizon Agents》，固定 2607.05378v1。先读 `docs/harness_improve/external_paper_references/reading_notes/TASK_PROMPT.md`、`NOTE_TEMPLATE.md`、`BATCH3_PLAN.md` §1/§3 的任务 14/§4，以及当前项目简报。原文为 `docs/harness_improve/external_paper_references/pdfs/2607.05378v1.pdf`，入口 https://arxiv.org/abs/2607.05378v1 。复用线索为 `knowledge/summary_compaction_rl.md` 与 `docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md` 的相关节。

按原目录覆盖全部后训练正文与附录，不只读 compaction 机制。额外核 execution/summary/replay 的 token mask、上下文重建、PPO 策略版本、全局分母、跨段 GAE 近似、critic/data/reward/预算、全部消融和 single-window 退化；不要自动并入 SAO 的 DIS。只写 `docs/harness_improve/external_paper_references/reading_notes/R14_compaction_rl.md`、同目录 `reviews/14_R14_review.md` 与必要 `sources/R14/` 附件。按公共提示词完成一名干净上下文 Astra / high 子审查与修订，记录交审版本和处理。不精读 SAO 或其他长报告来扩大任务，不改共享索引、代码、compaction 或 loss 定案。

### 任务 15 提示

你负责任务 15：完整精读 O01《SkyRL-Agent: Efficient RL Training for Multi-turn LLM Agent》，固定 2511.16108v1；SA-SWE-32B 是它的模型名。先读 `docs/harness_improve/external_paper_references/reading_notes/TASK_PROMPT.md`、`NOTE_TEMPLATE.md`、`BATCH3_PLAN.md` §1/§3 的任务 15/§4 及当前项目简报。正式原文 https://arxiv.org/abs/2511.16108v1 ，官方代码 https://github.com/NovaSky-AI/SkyRL 。本地未登记 PDF/TeX，必要原文附件保存到你的 `sources/O01/`。旧稿 `docs/harness_improve/external_paper_references/sa_swe_horizon_masking_analysis.md` 仅覆盖专题，而且代码版本晚于论文。

先按原目录覆盖框架与所有训练/评测内容，必须包括 §5 Deep Research、Memory Agent、Computer Use Agent；当前项目边界不准成为遗漏后训练案例的理由。额外核 SWE 配方、horizon reward/advantage/梯度/分母/batch 计数、工具与 hints、调度/后端、错误处理和成本比较。代码补查绑定 commit，不用后续 `main` 填论文未披露。只写 `docs/harness_improve/external_paper_references/reading_notes/O01_skyrl_agent_sa_swe.md`、同目录 `reviews/15_O01_review.md` 与必要来源附件。按公共提示词完成一名干净上下文 Astra / high 子审查、固定交审稿与修订后交付，不改代码、共享索引或当前终态/masking 定案。

### 任务 16 提示

你负责任务 16：完整精读 N07《Reinforcement Learning via Self-Distillation》，固定 2601.20802v2；本篇 50 页，按长报告处理。先读 `docs/harness_improve/external_paper_references/reading_notes/TASK_PROMPT.md`、`NOTE_TEMPLATE.md`、`BATCH3_PLAN.md` §1/§3 的任务 16/§4、当前项目简报及 `project1_design_advice_20260907.md` §6。原文 https://arxiv.org/abs/2601.20802v2 ，官方代码 https://github.com/lasgroup/SDPO 。未找到本地独立旧稿/PDF/TeX，必要来源附件保存到 `sources/N07/`；项目建议与对话只作提问线索。

按原目录精读全部后训练正文与附录 A–F，不跳过理论适用条件、实现、消融、实验模板和定性实例。覆盖无丰富反馈、有丰富反馈、test-time self-distillation 的全部领域。额外核教师条件/更新、gradient/KL/logit/token 目标、stop-gradient、off-policy、稳定化、遗忘、反馈消融、预算与 test-time 是否更新权重；不得只写“利用反馈”。只写 `docs/harness_improve/external_paper_references/reading_notes/N07_sdpo.md`、同目录 `reviews/16_N07_review.md` 与必要附件。按公共提示词安排一名干净上下文 Astra / high 子审查，记录固定交审稿，修订后交付。不要附带全文精读 OPSD/MOPD，不改训练或评分可见性定案；中断时记续读位置与未完成项。

### 任务 17 提示

你负责任务 17：完整精读 N08《Self-Distilled Reasoner: On-Policy Self-Distillation for Large Language Models》，固定 2601.18734v3。先读 `docs/harness_improve/external_paper_references/reading_notes/TASK_PROMPT.md`、`NOTE_TEMPLATE.md`、`BATCH3_PLAN.md` §1/§3 的任务 17/§4、当前项目简报及项目一建议 §6。原文 https://arxiv.org/abs/2601.18734v3 ，官方代码 https://github.com/siyan-zhao/OPSD 。未找到本地逐篇旧稿/PDF/TeX；必要来源附件保存到 `sources/N08/`。`reference/prime-rl/src/prime_rl/orchestrator/algo/opsd.py` 仅是待核对应关系的同名工程线索，不能当论文实现证据。

按原文覆盖全部后训练正文与附录 A–D。额外核特权轨迹来源与成本、teacher/student 条件与更新、采样主体、divergence 方向、全词表/采样 token 目标、两类 clipping、生成风格/长度、token 类别和 STaR 比较；完整保留数学结果、预算、消融与限制。与 SDPO 的差别依据各自原文，不把数学结论外推成 SWE 已验证。只写 `docs/harness_improve/external_paper_references/reading_notes/N08_opsd.md`、同目录 `reviews/17_N08_review.md` 与必要附件。按公共提示词完成一名干净上下文 Astra / high 子审查、固定交审稿和修订，不改共享索引或训练定案。

### 任务 18 提示

你负责任务 18：完整精读 E7《MOPD: Multi-Teacher On-Policy Distillation for Capability Integration in LLM Post-Training》，固定 2606.30406v1。先读 `docs/harness_improve/external_paper_references/reading_notes/TASK_PROMPT.md`、`NOTE_TEMPLATE.md`、`BATCH3_PLAN.md` §1/§3 的任务 18/§4/§6 与当前项目简报。原文 `docs/harness_improve/external_paper_references/pdfs/E7_mopd_multi_teacher_2606.30406.pdf`，入口 https://arxiv.org/abs/2606.30406v1 。旧稿 `knowledge/summary_mopd_multi_teacher_opd.md` 的“无本地 PDF”已过时，其其他事实仍回原文核实。

按原目录覆盖全部后训练正文与附录 A/B，包括 SFT、Math/IF/SWE 专家 RL、蒸馏、MiMo 实验、基础设施、成本和全部分析。额外核教师/学生关系、两种目标/clip/归一化、路由、跨源消融、样本效率与多轮迭代，审慎核旧稿的“同源硬前提”“只改 advantage”“项目已走专家分叉”等过强表述。E13 是另一份 31 页报告：可为 E7 术语关系定点查 E13，须记录读了哪些段落，**不附带全文精读 E13，不把它标完成，也不用它填 E7 未披露项**。只写 `docs/harness_improve/external_paper_references/reading_notes/E7_mopd_multi_teacher.md`、同目录 `reviews/18_E7_review.md` 与必要 `sources/E7/` 附件。按公共提示词完成一名干净上下文 Astra / high 子审查与修订后交付，不修改共享索引、训练实现或定案。

## 6. E13 MiMo 关联候选的独立边界

[正式标题及提交历史](https://arxiv.org/abs/2601.02780v2) 为 *MiMo-V2-Flash Technical Report*，Xiaomi LLM-Core Team；v1 2026-01-06、v2 2026-01-08。[本地 PDF](../pdfs/E13_mimo_v2_flash_2601.02780.pdf) 文件名没有版本，但首页明确是 **v2**，共 **31 页**，与摘要页所示版本一致。本次未找到独立逐篇旧稿或可复用本地 TeX。

本次只看首页和目录，已知必须覆盖的后训练范围包括 §4.1–4.6 的 MOPD/SFT/RL/公式/评测/infra、附录 B 的 SWE-bench reward hacking 与 C 的 context management；架构和预训练如何影响后训练亦须交代。这些足以构成单独长报告任务，不能因为 E7 已谈 MiMo 而视作重复来源。建议后续单独排任务 19（编号最终由主线程维护），预期正文 `E13_mimo_v2_flash.md`、审查 `reviews/19_E13_review.md`，本轮不创建这些文件或线程。

E13 早于 E7；目录中括注“origin of the MOPD term”不是正式论文标题。本次只能确认时间先后及两篇摘要均谈 MOPD，**没有完成术语首创性的文献追溯**。后续两文关联时分别引用，先核方法关系再决定是否有实质差异。
