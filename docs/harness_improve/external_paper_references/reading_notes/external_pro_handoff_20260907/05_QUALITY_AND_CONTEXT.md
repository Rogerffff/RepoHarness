# 两批质量检查与项目背景

导出日期：2026-09-07。使用方式与边界见 [交接说明](00_HANDOFF.md)。各篇正文完整保留；本地链接转为仓库引用文字，页内导航转为文字；需要原图/代码时请访问官方来源。


---

## 文档 1 / 4：BATCH1_QUALITY_REVIEW_20260907.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/BATCH1_QUALITY_REVIEW_20260907.md`

# 第一组精读质量检查与后续调整

日期：2026-09-07。对象：01–06 六个独立任务的 7 份笔记、6 份审查记录及实际执行过程。成品入口见 索引〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/README.md`〕，主/子线程 ID 与状态见 执行记录〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH1_RUN.md`〕。

**结论：本批可以作为项目一设计讨论的参考库，值得沿用“独立精读 + 线程内独立审查”的工作方式。重点抽查未发现新的重大技术错误或整块后训练主题遗漏。下一批需要改善检索、去重和审查版本记录，暂不需要增加每篇审查者数量。**

这个结论限定于阅读成果质量。主线程没有逐句复核全部来源，没有复现论文实验或运行 GPU，也没有由这些笔记批准任何项目训练语义变更。

## 1. 实际交付与核查方式

六个任务均结束并回传成品。回收时，7 份笔记共 2,415 行、183,236 个字符；计入 6 份审查为 3,060 行、234,513 个字符。字符包含中文、英文、公式和 Markdown，不是中文字数，更不是质量评分。六任务并行约 22.3 分钟完成，已包含各自审查；不含本主线程的后续验收。

核查分三层：

1. **主线程检查成品。** 阅读七份笔记、六份审查与完成回复，检查引用、未知项、修订是否进入正文、项目映射是否冒充来源事实；对 CalibForge 的保留条件与 SFT 原始表、miles 的 reward/RM/回调与 loss 代码、两篇评测官方文章另作重点核对。
2. **独立来源抽查。** 另派一名干净上下文 Astra / high 审查者，对 MAI、Qwen、KAT 各抽查五组关键结论，合计十五组；从原目录/标题重查后训练覆盖，并回 PDF/TeX、原始公式或表格页面核对。这不是三篇再次全文逐句复审。
3. **独立过程核验。** 另一名 Astra / high 审查者核六个主会话与六个子会话的实际日志，确认成功创建、父子关系、实际模型/effort、读取顺序及修订落地。工具读取范围能证明做过相应检查，不能证明每句话均理解正确。

六个主任务和六个审查子任务均实际使用 `gpt-6-astra` / `high`，审查均以 `fork_turns="none"` 创建。没有发现主作者自查冒充 sub agent 的情况。干净上下文不等于双盲：审查者获得作者提供的文件入口，有时复用提取文本，也与作者交流疑点；这符合本次要求。

## 2. 各任务的效果

| 成品 | 主要价值与已核要点 | 线程内发现/补充及处理 | 后续使用限制 |
| --- | --- | --- | --- |
| MAI-Thinking-1〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R1_mai_thinking_1.md`〕 | 环境漏斗、GRPO 分母、专家合并、异步版本、通用/安全训练都具备原文定位。保留了正文与附录的预算冲突 | 3 项：补 generative QA 课程、可验证奖励的多 epoch 经验，收紧 Qwen3 judge 用途；均落正文 | 很长，核心结论到第 58 行才出现；不同 PDF 的差异与未披露字段仍需保留 |
| Qwen3-Coder-Next〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R3_qwen3_coder_next.md`〕 | 两条数据管线、四专家、WebDev、packing 与安全附录覆盖充分；最后蒸馏未被强行指定为 OPD | 3 项：安全表比例合计疑点、文档索引效率表述、slide 方向；均落正文 | 原文模板数、比例合计等疑点未解决；不能从框架习惯补训练配方 |
| KAT-Coder-V2.5〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N01_kat_coder_v2_5.md`〕 | AutoBuilder、PPO/GAE、hindsight critic、GRM、MOPD 与文末奖励表拆得清楚；负结果保留 | 1 项：静态定位的描述不能直接写成已披露豁免规则；已收紧 | 公式公开不等于 KL/teacher/预算等实现全部公开；harness 多样性收益未被单独隔离 |
| CalibForge〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E2_calibforge.md`〕 | 两份旧稿升级后区分任务校准、离线轨迹 SFT、不同运行预算；包含所有附录失败案例与资产检查 | 4 项：实际评分分母、早停与两图关系、轨迹发布声明/资产缺口、检查时点；均已修 | 作者的 RL 收益未被验证；有效 batch、成本、轨迹资产等缺口不能自行填补 |
| miles〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N11_miles_agentic_rollout.md`〕 | 区分上游 U、集成 I、在线 W；实际追到 session、reward/OPD、异步消费、loss 与 eval 的接口边界 | 5 项：缺版本分支、预填 reward 跳过 RM、group RM 回调时点、loss 符号/数值保护、增量恢复条件；均有独立复读 | 工程专题会随 commit 过期；官方能力不能直接等同当前 rh2 已接入，静态阅读未验证真实运行 |
| Verified〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13a_swe_verified_audit.md`〕 / signal-noise〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N13b_coding_eval_signal_noise.md`〕 | 分开保存两次审计，抽样分母、动态案例、历史建议变化、测试误杀和错误放行都有覆盖 | 无强制修订；有实际网页交互和关键结论检查记录 | 审计对象和筛选方式限制外推，不能解释为所有 split 或整个社区的共同判决 |

合计 **16 项纠错或补充建议**，不是 16 个重大错误。它们在最终正文都有对应变化，审查并非只增加“已通过”标签。E2 前三项有独立回读、第四项作者定点核改；N11 五项均有独立回读；其他任务也明确区分独立发现与作者修订，未冒称全部又做了一轮全文审查。

## 3. 是否被固定问题限制了阅读范围

**在本批可核查的证据中，没有发现这种问题。** 最有说服力的不是覆盖表长，而是正文实际保留了派工重点之外的内容：

- MAI：通用推理、helpfulness、安全、诚实性、风格、长上下文、工具使用和红队，不只 SWE 环境与异步训练。
- Qwen：WebDev 的视觉/交互筛选与 UX、单轮能力、安全附录、packing 的 split/drop 消融，不只 agent RL 与 SWE 成绩。
- KAT：参考文献之后的奖励技术表也被读取；没有把浮动到文末的表当作无关尾页。
- CalibForge：附录的合法替代解误杀、交付工件失败、预算与全部 SFT 表得到独立总结。
- 评测两篇：审查者实际打开四个 Failure modes 标签、下拉菜单和全部案例，并检查方法图；没有只读默认静态网页文本。

因此应保留“先按原文结构列覆盖，再用项目问题补重点”的顺序。把问题单扩得越来越长不能替代这一顺序。覆盖仍有证据上限：本次没有逐句重读所有后训练段落，后续发现遗漏时应补对应篇，不把本次检查当作永久无错证明。

## 4. 几个能检验笔记价值的具体问题

这些例子说明成品已经能处理容易误读的设计问题；不是新增项目定案。

| 容易误读的问题 | 本批保留下来的正确区分 | 证据入口 |
| --- | --- | --- |
| 三个模型团队都用了多专家 OPD 吗？ | MAI 是专家轨迹 SFT 合并后再 RL；Qwen 最后蒸馏算法未披露；KAT 明确给出 MOPD。不能写成统一配方 | R1 §3、R3 §3、N01 §5；原图/公式定位在各篇 |
| MAI 的 265,617 是最终消费题量吗？ | 这是环境/评分验证漏斗的一个终点，后续质量改写后数量未给，不能等同最终训练消费 | R1 §6.2，原文 p.42；独立抽查通过 |
| KAT 的 >90% 表示测试通过率吗？ | 指预期测试被收集到的比例；构建率、测试收集、测试通过是不同变量 | N01 §4，原文 p.4；独立抽查通过 |
| CalibForge 的 multi-solver 是 GRPO group 吗？ | 是不同模型对同一任务的结果分歧保留条件；实际学习为离线多轮 SFT | E2 §5；本次回原文 p.5 Eq.(1)–(2) 及 p.25 Table E1 核查 |
| CalibForge 64 卡、累积 4、batch 128 是否必然算错？ | 表值确实如此；未给并行布局，不能擅改 batch，也不能直接判算错 | E2 §5.2；本次目视 p.25 原表 |
| miles 开启 OPD 开关就会自动得到 teacher 分数吗？ | 被分析的 session 路径预填 reward，普通下游 RM 仅处理 reward 缺失者；需先核具体接线 | N11 §5.2；U 的 `miles/rollout/inference_rollout/inference_rollout_common.py` |
| group RM 时 sample callback 是否包含整组评分耗时？ | sample task 完成后先触发 callback，整组 gather 后才做 group RM；不能混成同一时点 | N11 §6.1；同文件 `generate_and_rm_group` |
| Verified 的 59.4% 能当全库比例吗？ | 来自筛选出的 138 道难题子集，不能直接外推全部任务 | N13a §4；[官方原文](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/) |
| Pro 的“约 30%”是否是污染率？ | 是公开 split 的任务质量问题；两条深入审查共享前置筛选，不是新的污染率估计 | N13b §3–4；[官方原文](https://openai.com/index/separating-signal-from-noise-coding-evaluations/) |

这些区别比再罗列一份“值得实现的 infra 功能清单”更有用：它们能阻止设计讨论误用样本单位、错误归因或未披露的训练方法。

## 5. 应调整的地方

### 5.1 将首屏改为摘要与导航

回收稿的 R1、R3、N01 核心结论分别到第 58、49、42 行才出现，前面主要是版本与覆盖表。长期检索时不方便。后续稿在标题下先用约 200–300 字说明阶段链、最有用事实和最重要边界，再放可点击的主题链接；详细覆盖表继续保留。字数仅作表达建议，不能因此删掉关键后训练内容。

**本轮处理**：已为七份成品在共享 README 建立“常见问题 → 章节”索引，并更新模板。未批量重写七份技术正文；本批首屏摘要可在后续维护时补入。

### 5.2 压缩重复说明，保持完整覆盖

部分稿在方法、成本、未知项、项目映射和结尾重复同一“未披露/未证因果”说明；审查稿也有重写全文覆盖解释的倾向。保留紧邻关键公式和数字的限定，其他未知项集中成一张表并引用。审查继续覆盖全部来源，报告只需覆盖结论、关键核验和实际发现，不必复制整篇方法。

不设固定页数或统一压缩比例。论文很长时，400–500 行可以合理；两篇短文没有 RL 方法时，也无需用大量空栏反复证明没有 RL。**已将这些原则写进模板和公共提示词。**

### 5.3 让审查版本可辨认

当前成品没有直接记齐审查子线程 ID，本次依靠会话日志恢复。E2/N11 在审查期间也有正文更新，虽然后续处理透明，日后追溯仍麻烦。

下一批只需记录主/子线程 ID、来源版本、固定初稿副本名或已有 commit、审查与修订日期。交审版本保持稳定，修订另记即可。**不要求强制内容 hash、多轮全文重审或新管理系统。** 本次六组 ID 已统一补入执行记录；流程要求已加入公共提示词。

### 5.4 保留来源复用，避免重复劳动

审查者可以共享原文提取文本与渲染页，但应独立从原目录检查范围，并在关键图表、公式和疑点处回原页。完整性应通过章节范围与缺口补读保证，不靠反复下载或打印全部已读文本。

动态网页的 tabs、下拉案例、SVG 方法图和工具输出截断须显式检查。本批 N13 已做得较好，现已纳入后续公共要求。代码专题首次引用关键符号应给完整仓库相对路径与版本，减少同名文件歧义。

### 5.5 清理共享状态与当前结论

本次验收前，共享 README、SOURCE_CATALOG 和 BATCH1_RUN 仍写“已启动/未完成”；这是主线程索引过期，六个工作线程已实际交付。现在均已更新，旧摘要保留，后续查询优先进入对应新稿。

另修正 E2 审查的重复章节编号；N11 审查首段按其末尾已完成的 R4 独立复核更新为当前状态，同时保留历史发现与处置过程。这两项是展示与状态维护，不改变论文事实或训练实现。

## 6. 后续任务建议

继续原计划 07–12 比扩大并发或增加每篇 reviewer 更合适：Nemotron Ultra、K3、MiniMax M2/Forge、Intern-S2、SWE-smith、R2E-Gym，覆盖模型团队方案和开放环境生产线。保持 4–6 个独立任务一组便于回收；这个数量是工作安排，不是平台上限或额度保证。本轮未启动下一组。

后续综合只需逐渐补一张跨来源比较表：环境筛选、训练目标、失败/截断、异步与版本、评测和成本，每格引用具体笔记与披露边界。先用已有笔记支持项目一当前需要的决策，不把读完整个文献库设为开始实验的前置条件。

**本次完成的维护**：新增本报告；更新两级 README、执行记录、来源目录、笔记模板和公共派工提示词；修正两份审查的状态/编号。七份技术笔记继续保留作者经审查修订的内容。后续新增来源或版本变化，按对应篇定点补充。

收尾核验：六个正式任务重新查询均为 `completed`、无任务错误；本目录主文档/审查与上级索引合计 20 份 Markdown 的 265 个本地文件引用均可解析到存在的文件，代码围栏闭合，未发现本机绝对路径，`git diff --check` 通过。该结构检查未检验远端 URL 持续可用，也不承担论文事实正确性判断；技术结论的核查范围以 §1–4 为准。


---

## 文档 2 / 4：BATCH2_QUALITY_REVIEW_20260907.md

原始维护路径：`docs/harness_improve/external_paper_references/reading_notes/BATCH2_QUALITY_REVIEW_20260907.md`

# 第二批精读质量检查与外部交接

日期：2026-09-07。对象：任务 07–12 的七份最终笔记、六份独立审查、固定初稿与实际任务记录。入口：成品索引〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/README.md`〕、任务与审查身份〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/BATCH2_RUN.md`〕。

**结论：第二批已完成，可以加入项目一参考库。两批累计 14 份笔记、12 份线程内独立审查。第二批的 15 项审查发现或补充建议均已进入最终正文；主线程定点回查没有发现新的实质错误。摘要导航、固定交审稿和版本差异说明比第一批改善。第三批不启动，后续选题和阅读转交用户安排的外部 Pro。**

这是阅读成果检查，不是论文实验复现或训练实现验收。主线程没有再次逐句重读七份原文及全部笔记，不能把“定点未发现问题”理解为全文永久无错。

## 1. 完成情况与核验范围

六个正式任务的最新工作回合均为 `completed`，`error=null`。界面中的 `notLoaded` 表示任务未加载到界面，不是任务失败。七份最终笔记、六份审查和七份固定初稿均存在于主资料目录，不只留在独立 worktree。

本次直接核对了六组实际会话记录：六个作者任务与六个审查子任务均为 `gpt-6-astra / high`；每个作者创建一名 `fork_turns="none"` 审查者，父子关系正确，子任务没有递归扩团队。任务 09、12 的同一审查者另有定点复核回合；E5 的 SkyRL 接线补充也由原审查者核对。其余“作者收到发现后修订”没有被冒写成第二轮独立全文复审。

本次主线程实际检查：

1. 阅读六份完成回复、六份审查报告，检查七份笔记的摘要、覆盖、章节组织及重要方法段落。
2. 逐篇比较固定初稿与最终稿，核对 15 项修订或补充是否落入正文。Intern-S2 的 §1–11 与固定初稿相同，改动只涉及交付审查记录；Forge 正文也没有因配套论文的发现被无故改写。
3. 回一手来源定点核查：Ultra p.29 的多数 agentic MOPD 使用单轮 rollout；K3 §4.1.2 的同步迭代、暂停和完整 K 组；M2 的 CISPO 分母和 stop-gradient；Forge 原文的窗口规则与 40× 声明边界；Intern-S2 的 Eq.29/36、BKL 定义与分母；SWE-smith 当前评分选项；R2E-Gym 当前 reward 与重试实现。来源采用作者保存的官方 PDF、TeX、官方网页快照和绑定 commit 的代码。
4. 检查成品引用与文档结构，更新过期状态。没有重新审计每一条阅读工具调用的顺序，也没有新派完整重读任务或运行 GPU/环境实验。

七份笔记共 2,440 行、182,339 个字符，和第一批七份的 183,236 字符接近；字符包含中文、英文、公式和 Markdown。六个任务并行约 18 分钟完成，包含各自审查、不包含本次主线程检查。不同来源、篇幅和任务难度不可控，这些数量不用于宣称模型效率提升或估计额度费用。

## 2. 各任务结果与实质修订

| 成品 | 最值得复用的内容 | 线程内发现或建议及当前处理 |
| --- | --- | --- |
| R2 Nemotron 3 Ultra〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R2_nemotron_3_ultra.md`〕 | RLVR、教师训练、两轮 MOPD 与 MTP boosting 分开；三类策略概率、KL 方向、单轮与完整多轮训练边界清楚 | 1 项：撤回安全数据生成中未披露的“先回应/后推理”顺序。另补资产访问状态与项目代码路径，不计入发现数 |
| R13 Kimi K3〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R13_kimi_k3.md`〕 | 九个 RL 专家、K2.5 优化继承、MOPD、同步 partial rollout、AgentENV、部署训练及完整能力域 | 3 项：on-policy 明确为学生策略采样；重写 cosine/WSD 的实际对照条件；保留图中 Mythos 5 与正文 Fable 5 的模型身份边界 |
| R4 MiniMax M2〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/R4_minimax_m2_series.md`〕 / N10 Forge〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/N10_minimax_forge.md`〕 | 分开保存长报告与官方文章；CISPO、任务生产、窗口调度、前缀合并与全部办公/通用后训练 | 3 项均在 R4：重试上限只证明停止修复，不证明后续淘汰；SampleEfficiency 释义归属 N10；请求、训练数据和权重同步流分别描述。原审查者已定点复核 |
| E10 Intern-S2-Preview〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E10_intern_s2_preview.md`〕 | 两专家与 OPD、reasoning/agentic 两类训练、token 捕获、R3/BKL、Memory Decoder 与科学/时序结果 | 无强制修订。重点分母和数值一致性检查经独立审查及本次定点回源，未发现新问题 |
| E5 SWE-smith〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/E5_swe_smith.md`〕 | 仓库→候选任务→成功轨迹→SFT 的数量漏斗；难度评分器训练；成本与后来的 RL 接线 | 2 项：`f2p_only` 仍可能保留相关文件内的 P2P 判定；Flask 只在许可表和案例中出现，不能据此断言进入主训练仓库集。另补历史 SkyRL 接线并保留“没有专属受控 RL 收益证据”的边界 |
| O03 R2E-Gym〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/O03_r2e_gym.md`〕 | 编辑 agent、测试 agent 和 verifier 三种 SFT；候选选择与推理预算；论文和当前资产分离 | 4 项必改、2 项建议：EF 消融分别重训；追加测试采样的起点与图文差异；三次总尝试；reward 空映射及退出码边界；YES/NO 缺失的非有限概率路径；生成模型与采样预算未知。均已由原审查者定点复核 |

合计 **15 项，不是 15 个重大错误**。没有出现审查发现只在末尾标“接受”、正文仍留旧说法的情况。R2E-Gym 当前代码的条件性风险仍明确标为静态路径，未冒称实际触发或论文历史实验错误。

## 3. 对第一批流程调整的评估

### 已经改善

- **七份均在第 3 行给实质摘要，第 5 行给导航。** 读者先看到训练主线和证据边界，再进入来源与覆盖表，检索比第一批先读几十行元数据更直接。
- **六个任务均保留固定初稿和审查处理。** 能判断被审的是哪个版本，也能区分独立发现、作者补查与定点复核。K3 作者仅取得 canonical ID，本次主线程从真实父子会话恢复 UUID，统一记入执行表。
- **版本变化没有只登记版本号。** K3 比对 v1/v2 的实质内容；M2 核两版 TeX 的技术部分；R2E-Gym 区分 arXiv、官网附件及当前数据/代码。版本差分工作的完整结论依赖各作者及审查记录，本次没有重做所有差分。
- **没有明显被固定问题限制阅读。** 正文保留 Ultra 的安全、多语与 MTP；K3 的视觉、专业工作、偏好和部署训练；M2 的办公、角色扮演与负结果；Intern-S2 的科学、多模态、Memory Decoder 和时序；两份环境论文也完整区分辅助模型训练与主 agent 训练。该判断来自现有覆盖证据和正文检查，不是新一轮全源无遗漏证明。

### 仍需调整

1. **下一阶段的价值在跨来源比较。** 单篇已经足够详细，再按目录顺序扩量可能继续重复类似大模型配方。外部 Pro 应先判断已有结论能支持哪些项目决策、缺什么证据，再选全文精读、局部补读或暂缓。
2. **不能把原文缺披露误判成漏读。** 失败/截断处置、实际 mask、有效训练样本分母、teacher 成本和完整运行预算在不少来源中仍未知。若全文与附录确实没给，应保留未知；需要补证据时追官方代码或后续技术说明，不凭通用经验填参数。
3. **继续减少重复限定和过时状态。** 七份正文规模并未明显压缩，仍有少量跨节重复；不值得为统一篇幅重写技术内容。共享索引本次再次落后于任务进度，已统一更新。O03 审查首段的“尚不代表作者处理”改为历史初审语境，保留原发现及末尾复核结果。
4. **审查可以独立，工具能力不能虚构。** 外部 Pro 若没有实际创建独立 agent 的能力，记录为作者自查或另开上下文复查，不沿用“已通过 sub agent 审查”标签。后续稿仍先按原文结构建立范围，再用项目问题加重点。

## 4. 对两批成果的使用建议

这两批已能回答许多以前容易混淆的问题：多专家合并不总是 OPD；单轮 agentic MOPD 不等同完整多轮 RL；有可计算 reward 或 GRPO 示例不等于论文验证了 RL 收益；局部训练加速不等于端到端学习成本下降；同名 mask 的分母、概率参照及训练作用可能不同。

让外部 Pro 优先形成“项目决策问题 → 已有来源/章节 → 冲突或未知 → 值得补读的来源”的表，比马上再排六篇更有用。旧第三批中的 SAO、CompactionRL、SkyRL-Agent、SDPO、OPSD、MOPD 保留为有准备材料的候选；是否优先于环境筛选、terminal、评测或其他系统论文，由外部 Pro 结合证据缺口重新判断。

本轮只更新研究文档与交接材料，没有修改训练代码、批准新算法或启动第三批。项目一的训练闭环不以读完整个文献目录为前置条件。

## 5. 交接与验证

外部 Pro 交接说明〔仓库引用：`docs/harness_improve/external_paper_references/reading_notes/external_pro_handoff_20260907/00_HANDOFF.md`〕提供项目范围、两批成果清单、复查任务与后续成文要求。同目录有两批完整笔记、12 份审查、候选目录，以及质量检查和项目背景的可携带文本。包内不含大型 PDF、代码 clone、模型权重或本地会话日志；原文复查使用各篇官方链接与版本。

当前成果只读一次性导出，不替代本目录单篇文档的维护入口。结构检查与导出核验的范围在交接说明中记录；远端链接未来是否持续有效不由本次本地检查保证。

收尾实测：主资料库的 36 份 Markdown 共 495 个本地文件引用均指向存在的路径，48 个页内导航均可解析，代码围栏闭合，未发现本机用户目录路径；`git diff --check` 通过。固定初稿中的历史相对链接按正式笔记目录解释，未纳入本轮可点击导航检查，也未修改这些副本。七份导出文件保留 14 份笔记、12 份审查及所列上下文全文，源文档中的官方 Markdown/自动链接 URL 保持一致，压缩包内容与导出文件逐字节一致。链接检查最初把 URL 后的中文和相邻导航也当成 URL，产生误报；改为解析实际链接目标后通过，没有据此修改原始来源链接。


---

## 文档 3 / 4：CURRENT-STATE-BRIEF.md

原始维护路径：`docs/agentic_RL/repo_harness_rh2_workstreams/CURRENT-STATE-BRIEF.md`

# RepoHarness rh2 · 当前状态简报（给外部模型 / 新接手者）

更新：2026-09-05。用途：让一个**没有任何上下文**的模型或人在 15 分钟内知道"这个仓库是什么、做到哪了、什么已定、什么未定、该读哪些文件、哪些文件已过时"。本文是**导航与快照**，不是权威定案——所有定案以下文列出的权威文档为准；本文与它们冲突时以它们为准，并请顺手修本文。

---

## 1. 三十秒定位

- **项目**：RepoHarness（rh2 架构）= 面向 SWE agent 强化学习的**环境生产线 + 训练治理层**。它不造训练内核、推理服务和 agent 本体：训练后端用 **miles**（SGLang 团队维护的 slime fork，fully-async RL），推理用 SGLang，agent 用 **Claude Code**（经 vendored 的 slime agent adapter 接入）。RH2 自己负责三件事：① **环境可信**（任务包/镜像/评分材料的可信入口与隔离）；② **reward 可信**（fresh grader、评分投影、反作弊边界）；③ **哪些轨迹能进 policy loss**（身份、eligibility、组准入、逐 token 对齐、staleness）。
- **目标实验**：在 8×RTX PRO 6000（sm_120，PCIe，无 NVLink）上用 GRPO（n=8）+ faithful DIS（重要性采样校正，默认候选 loss）训练 Qwen3-30B-A3B 做 SWE 任务；首训目标是**验证闭环可信**，不是主张能力提升。
- **现状一句话**：本地训练链已按 Wave1~Wave3 搭完（身份铸造、可信输入、组准入、sandbox 双 profile、评分投影、staleness 唯一权威、关停链、最小冷恢复、多 engine 最小正确性、CP>1 支持），正在等 codex 对最后一个反例的窄复核，之后进入 **W8（eval 运输链）→ C 包决策 → W7（实验包）→ 租 GPU 做资格作业**。**首训用哪批任务（taskset）尚未决定**——数据线（T2-d/T2-e/W2b）与训练链并行，目前有 216 题 SWE-Gym Lite 的可信 ingestion 产物，但未选定首训题单。

## 2. 已定 vs 未定（决策状态表）

| 决策包 | 状态 | 内容摘要 | 权威文本 |
|---|---|---|---|
| D0（2026-09-02） | 已批 | miles = 唯一开发与 GPU 资格候选（迁移结论等 GPU）；W1a 中立身份边界；W2a 可信输入/public-private 所有权；删除授权官僚设计但保留真实正确性挡板；A8 配置真实性 | `06-first-training-local-execution-plan.md` §1、§1.5 |
| D1（2026-09-02） | 已批 | 三终态（FATAL / ABORTED / DROP_GROUP）高层原则；组准入 = 全员 KEEP_FULL；A3 删 S1_TIER_CAP；unused handler 语义；两阶段 staleness（后被 B-1 改判为 consume-time 唯一权威） | 同上 §4、附录 A |
| A9（2026-09-02） | 已批 | private grading 材料共址于可信 RolloutManager 进程；模型执行始终在隔离 sandbox；不承诺进程被攻破后的内存隔离 | 同上 §1 A9 |
| D2 + B（2026-09-04，v2） | 已批 | D2-1 fresh grader + 冻结产物后立即释放容器；D2-2 唯一正式 rollout profile + 独立 grader profile，创建期强制 + 启动前探针 + run 级记录（**不再有逐轨迹能力事实**）；D2-3 可信评分投影（改测试路径 ≠ 篡改，控制面不重放）；D2-4 删 projection 扫描资格语义；B-1 staleness 以 miles consume-time 为唯一权威，N 为 profile 参数；B-2 drop + drop 事件 + no-progress；B-3 **最小**冷恢复（不建 joint commit/复合版本）；B-4 update interval=1；B-5 retract + 多 engine 最小正确性（W10）；B-6 落账 | `miles_spike/decision_package_D2_B.md`（v2） |
| **C 包** | **未定** | 首训 taskset 与规模档（D3，Claude 推荐纯 SWE-Gym Lite 150~200 题闭环档）；A5 timeout/truncation 处置；loss 终选（faithful DIS 为默认候选）；staleness N 起始值（建议 2）；GPU 拓扑与 engine 数（GPU matched comparison 定）；阈值/预算/停止规则；harness 工具面（subagent/compaction/fork）；eval 补充面 | 06 §4 C；`miles_spike/first_training_readiness_alignment_claude.md` §2.1（D3 建议） |

**三条长期原则**（外部建议若与之冲突会被直接拒绝）：
1. **不建授权官僚**：不写"owner 是否批准训练"的闸门/manifest/解封仪式（06 §6）；能否训练由 owner 判断。保留的是训练科学有效性校验（fail-closed、typed 错误、run-fatal）。
2. **不为边界情况建平台**：不建 ledger/WAL、通用规则引擎、常驻 supervisor、粘滞路由、dead-engine 恢复、监控平台；能删的机制优先删（2026-09-04 就删掉了每轨迹能力事实证明系统、第二套 staleness 阈值、projection marker 扫描）。
3. **红线**：不 fork miles 核心语义；miles 侧只允许窄 commit（现 0001–0016，全部存档并由 manifest 钉死）。

## 3. 该读什么、按什么顺序（含新鲜度）

**A. 权威且新鲜（先读）**
1. `06-first-training-local-execution-plan.md` — 执行计划权威：§1 决策包 A、**§1.5 改判记录**、§2 对旧计划的替换条款、§3 工作包表 W0~W10、§4 决策包 D1/D2/B/C、§5 下一步、§6 防御清理原则、**附录 A 终态判定**（注意 2026-09-04 修订注记）。
2. `miles_spike/decision_package_D2_B.md`（v2）— D2/B 已批全文，含 §0 "v1 的四处根本性缺失"（了解我们踩过的坑）。
3. `miles_spike/spike-log.md` — append-only 账本，决策表**新行在上**；每一批实现/复核/修复都有一行。想知道"某事为什么这样"先查这里。
4. `miles_spike/wave1/*.md` — 各工作包实现报告（w0、w1a、w1b_slice1/2、w2a、w3a、w3b、w4、w5a、w5b、w9、w10、wave3_precleanup），每份含 T1 决策、偏离、开放问题、测试证据，末尾有 append-only 的复核修正节。
5. `miles_spike/integration_base_manifest.json` + `miles_spike/patches/README.md` — miles 集成基座事实（pin f2b7c7929、分支 rh2-integration-v3、上游选材、16 个语义 patch 及 sha256、期望 tree、双 lane 期望计数）。
6. `collaboration-protocol.md`、`review-standards.md`、仓库根 `CLAUDE.md` — 协作/审查规则（T0/T1/T2 分级、五段收尾报告、A~N 审查维度）。

**B. 设计背景（需要理解"为什么"时读）**
- `docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`（主架构）、`repo_harness_final_review_before_implementation.md`（范围与治理定案）。
- `docs/agentic_RL/training_design/repoharness_sao_dis_grpo_ppo_analysis.md`（为什么 GRPO + faithful DIS）、`repoharness_validation_experiment_design.md`（E 系实验定案，顶部有 miles 迁移修订注记）、`RL训推不一致与重要性采样基础.md`。
- `miles_spike/formal_first_training_readiness_scope.md`（codex 就绪范围稿，顶部横幅说明已被 06 取代）、`gpu_spike_scope_v1_claude.md`（GPU 上必须验什么、为什么本地验不了）。

**C. 已过时或仅作历史（不要据此判断现状）**
- `00-project-status.md`：2026-07 快照，顶部有 2026-09 注记；"FA 自建线"章节已冻结。
- `05-fully-async-execution-plan.md`（slime 自建 FA 线，剩余面已被 06 §2 取代）、`04/03/01`、`s0/ s1/ s2/ fa/` 目录：历史阶段流水。
- `README.md`：V4 时代描述；`AGENTS.md` 的"当前进度"章节部分过时（其协作协议摘要仍有效）。
- `rh2/experiments/miles_gpu_spike/`：未审的实验脚本草案，W7 会从范围反向重生成（W10 已删其单 engine 硬约束）。

## 4. 代码地图（rh2/src/repoharness2）

| 包 | 职责 | 关键文件 |
|---|---|---|
| `contracts/` | 公共 schema（改动 = T0） | `eligibility.py`（七维事实 + 三档资格）、`fa_runtime.py`（Outcome v2、终止类别五族）、`finalization.py`（receipt）、`trajectory.py`、`handshake.py` |
| `envpack/` | 可信输入 | `ingest_swegym_lite.py`（完整 loader，四面含 golden，**只能由 trusted controller 调**）、`training_view.py`（TrustedTaskController → RolloutTaskView / HostGradingView，opaque digest 锚）、`trusted_prep.py` + `prepared_tasks.py`（一次性 prep → prompts.jsonl + runtime-private grading artifact + 外部 manifest SHA）、`termination_facts.py`（只读派生） |
| `grading/` | fresh grader | `manager.py`（SWEGradingManager：root trusted setup → 权限布置 → 候选非 root 只跑测试；自证读回）、`trusted_projection.py`（候选 delta vs 控制面拆分）、`queue.py` |
| `governance/` | 资格与准入 | `gate.py`（七维 eligibility，security 维 = 执行级事实，第七维 = 版本事实合法）、`admission.py`（KEEP_FULL / DROP_GROUP / FATAL 薄处置纯函数，disposition 未注入即 fail-fast）、`wrapper.py`（finalize_rollout） |
| `adapters/slime/` | 执行编排（vendored slime 之上） | `generate.py`（RolloutOrchestrator：materialize → 屏障 → 冻结产物 → 评分 → 交付；sandbox 创建路径也在这里）、`bringup.py`（BringupService：启动核对、prepared 任务面、profile、关停链入口）、`sandbox_profile.py`（唯一正式 rollout/grader Docker profile、探针、egress relay）、`capture_wire.py`（模型调用捕获与 abort）、`engine_router_client.py`（abort 广播）、`prepared_task_face.py`、`attempt_timing.py` |
| `adapters/miles/` | miles 接线 | `generate_fn.py`（Rh2MilesGenerateFn 入口）、`identity.py`（六字段身份铸造，PENDING/ABORTED 状态规则）、`canonicalize.py`（30 字段 fail-closed 映射）、`group_admission.py`（miles dynamic filter = 唯一组准入点，叶版本绑定）、`faithful_dis_loss.py`（custom loss，CP>1 已接）、`attempt_assignment.py`、`drop_events.py` |
| `shutdown/` | 关停链 | `chain.py`（有界十步）、`resource_closure.py`（估计口径）、`run_residue.py`（launch trap） |
| `training/` | 标量权威 | `faithful_dis.py`（DENOMINATOR_SEMANTICS_V1，**不得改**） |
| `rh2/src/slime/` | vendored slime agent 层，与 pin 逐字节一致，**不得改** | — |
| `reference/miles-rh2-integration/` | miles fork 分支 rh2-integration-v3（pin + 16 patch）；改动只能以窄 commit + 存档 patch 形式 | `miles/rollout/fully_async_*`, `miles/utils/rh2_*` |

**测试与验证**（在 `rh2/` 目录）：
```bash
uv run pytest tests/ -q                                             # 默认 pin base（2026-09-05：1761 passed / 310 skipped）
RH2_MILES_PATH=$PWD/../reference/miles-rh2-integration uv run pytest tests/ -q   # integration base（2071 passed）
bash scripts/miles_integration_lanes.sh                             # 正式双 lane：tree/patch digest/pin 校验 + 精确计数（lane A 358/310，lane B 668/0）
```
真实 Docker 测试（sandbox profile、grader 权限）在本机 Docker 上真跑；GPU 相关（CP=2 真机、多 engine e2e、retract 代价）只能在租卡时验。

## 5. 诚实的边界与开放项

- **Wave3 闭合口径**：只声称 exact official-file 边界（official test 文件在位内容不可改、应缺路径不可重建；当前 profile 对 official patch 删除/改名后仍缺失的路径 fail-closed，216 题冻结集为新增 8/删除 0/改名 0）。**通用 evaluator 控制面**（glob-only 辅助文件、conftest.py/pytest.ini/plugin）尚未定义，须由最终 environment adapter 在 taskset 确定后声明并实测——在此之前不得据本地绿灯宣称首训 reward 可信。
- **数据线未闭合**：T2-d（v2 评分正链：official test_patch 后写 + vendor eval_cmd + SWE-Gym parser 的真实镜像验证）、T2-e（四门 runner）、W2b（真实数据进训练）、held-out 冻结、GPU pass-rate 预筛。官方 swebench 4.1.0 对 SWE-Gym 11 仓库零覆盖，216 题 eval 常量来自 vendored fork。
- **租卡前必闭合**：R1 容器可写层预算强制（现只记录未强制）；launch.sh 的重启入口（`RESUME_FROM`）；W7 judge 消费 `run_restarted`/`engine_versions_after_publish` 事件；P2-2 新 run 必须唯一 run_id；W9 的真机 CP=2（含 `normalize_advantages=false` 约束）。
- **不做清单**（明确）：microVM、透明代理、LLM claim-check、完整红队、pending replay/精确 cursor/exactly-once、joint checkpoint、复合版本身份、粘滞路由、dead-engine 恢复、通用 quota/monitor 平台。

## 6. 术语速查

- **fa_formal / fa_audit_only / s1_compat**：执行模式。formal = 正式训练链（真身份、真准入、真 profile）；audit_only = 探针；s1_compat = 冻结的旧兼容路径。
- **六字段身份**：`rh2_prompt_group_id / rh2_group_index / rh2_rollout_execution_id / rh2_member_slot / rh2_physical_attempt_id / rh2_physical_attempt_seq`。
- **三终态**：FATAL（结构/账实矛盾，停 run）、ABORTED（未形成 present 对象的 task-local 故障，miles handler 按 drop 处理）、DROP_GROUP（完整但不合格，复合 filter 整组丢弃）。
- **faithful DIS**：在采样支持集上重归一化的重要性采样校正；标量权威 `training/faithful_dis.py`；custom loss 经 miles `--custom-loss-function-path`。
- **weight-version spans**：每 token 的行为策略版本区间（miles patch 0008/0009），staleness = 消费时已发布版本 − 组内最老版本。
- **prepared artifact**：trusted-prep 产出的 prompts.jsonl + runtime-private grading artifact + 外部 manifest SHA；rollout actor 只读它，不调完整 loader。
- **runtime_profile_digest**：run 级 sandbox profile 参数摘要，样本只盖这一个键供 join（不是逐轨迹能力事实）。

## 7. 给外部模型的提问边界

有价值的输入：首训 taskset 与规模档的取舍（D3）、evaluator 控制面的通用定义、GPU profile/拓扑与 staleness N 的实验设计、eval 补充面、faithful DIS vs PPO 在首训的取舍证据。
不需要的输入：重新设计训练后端或 harness、引入新服务/平台/依赖、为边界情况增加治理层、把已批的最小合同（B-3、D2-2）重新复杂化。


---

## 文档 4 / 4：project1_design_advice_20260907.md

原始维护路径：`docs/agentic_RL/repo_harness_rh2_workstreams/project1_design_advice_20260907.md`

# 项目一设计建议：把真实 Coding Agent 后训练做成有证据的闭环

日期：2026-09-07。性质：设计建议，不是实施批准，不替换 06 计划或 C 包。本轮扩大讨论到环境、数据和评测，但没有修改实现、配置或既有决策，也没有新增训练结果。

阅读依据：用户提供的五份 Pro 对话、当前简报、现有环境生产设计、前两轮独立代码审查。主审通读项目设计对话；三个独立子任务分别全文阅读设计、方向调查与模型调查，交叉检查建议。外部事实只核验影响本方案的部分原始来源，没有复核所有模型发布和排行榜数字。

## 1. 判断：同意先做项目一，但必须定义有限的完成边界

**同意暂停项目二，集中完成项目一。** 当前的主要缺口是：已有实现还没有在当前正式路径上形成可信环境、正确训练消费、端到端效率和独立学习收益的共同证据。项目二会新增能力定义、环境生成、奖励和泛化假设，很容易把当前未闭合问题带进另一项研究。

我赞同外部 Pro 的三点：复用上游应诚实归因；环境有效性、当前学习机会、实际学习收益是不同层次；只跑通几步训练不足以成为项目最终成果。

**但不完全赞同它最后把“诊断驱动任务供给”预选为主成果。** 设计对话〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/tmp/项目设计外部pro.md`〕第 705、762–780、881 行的窄路线——当前链资格验证、一项可归属改进、独立学习结果——更符合现状。第 1042、1313–1347 行新增供给更新、三臂训练、跨仓库/来源/harness 的组合很有价值，但应由瓶颈决定，不应成为默认最低要求。

旧 CaRR/verl 项目已有异步训练经历，只说明“又接了一套异步框架”不能重复成为卖点；不说明必须改做 curriculum 才有进阶。进阶可以来自真实黑盒 harness 的复杂行为、环境与评分责任、静默训练错误的定位，以及更扎实的受控结果。复杂度本身不是进阶。

建议项目定位：

> **RepoHarness：面向真实 Coding Agent 的可靠、高效后训练系统。基于 miles/SGLang，把可执行任务、真实 harness、可信评分和训练消费连接起来，并以受控实验验证一项自身改进怎样降低学习成本。**

第一版采用：一个目标训练模型、一个主 harness、一条主 RL 配方；SWE 为深入完成的主任务，terminal 优先复用现成资产作小规模迁移探针；需要主张跨任务族或联合训练时，再扩成第二训练面。至少完成一项可归属的效率或可靠性改进，并给出独立任务上的学习结果。数据生成、反馈蒸馏、多 harness 混训不全部纳入完成条件。

## 2. 个人贡献应如何划分

| 层面 | 归属与项目应证明的东西 |
|---|---|
| fully async、训练内核、推理引擎、通用权重同步、TITO/R3/OPD 基础能力 | 上游能力；项目证明正确使用、适配和调优，不写成原创 |
| 环境来源、构建与验证、评分材料和候选工件边界 | 自己负责的应用层设计；用有效率、审计结果和成本证明价值 |
| 黑盒 harness 的上下文变化、分支、身份、mask、组统计、版本和训练消费 | 自己负责的跨层集成与语义验证；区分上游问题、集成误用和特定需求 |
| 真实任务上的性能诊断、最小改进、学习与成本对照 | 最应补齐的结果层贡献；不能用代码行数、patch 数或测试数量代替 |

[miles 官方当前说明](https://github.com/radixark/miles)已经覆盖上述多项通用能力，其 [TITO 文档](https://miles.radixark.com/docs/user-guide/agentic-rollout)还专门描述保留实际推理 token 的 session 路径。它们不等于本仓库当前 vendored adapter 已经正确走上相同路径。修 REALIGN 等问题前，应先核验能否窄接入现有上游机制，而不是默认再造一个轨迹系统，也不因此立即升级整个 fork。

“维护真实 coding RL 的环境、数据生命周期和静默失败边界”确实对应研究工程职责。例如 [Anthropic Code RL 官方岗位](https://job-boards.greenhouse.io/anthropic/jobs/5370690008)明确覆盖这些工作。这里只借它说明工作内容有价值，不据此推断个人项目满足该职级；旧对话的中国岗位链接本轮未成功取得完整正文，不重复宣称当前招聘状态。

## 3. 环境和数据：做一条窄而可重复的生产链

### 3.1 SWE 与 terminal 的分工

| 任务族 | 首版范围建议 | 应如何评分 | 它提供的额外证据 |
|---|---|---|---|
| SWE | 仓库内 bug 修复为主，包含不同 bug 机制、文件跨度、测试框架和资源成本 | 在可信初始状态上重放候选代码，以目标测试和回归测试评分 | 定位、修改、测试及长多轮执行能形成真实学习 |
| terminal | 先选本地可复现的代码/构建调试、CLI 数据处理、文件工件任务 | 检查最终文件、数据或可冻结状态，包含应满足及不应破坏的条件 | 训练和环境抽象没有被写死为“提取 patch 后跑 pytest” |

两者共享任务版本、公开输入、隔离执行、终态、工件与评分结果的现有接口；任务解释、材料冻结和 verifier 各自实现。不为了第二任务族先造通用环境平台。需要长期在线服务、外部账号、GPU 科学计算的 terminal 题先排除在首版范围外。

实施顺序是 SWE 先闭环；terminal 在现成资产和预算允许时，用小批验证接口和评分，决定只作评测还是加入少量训练。它是贴合用户 coding 范围的优先补充，不要求为此从零建设第二条生产线。若只评测，就写“迁移评测”；若声称 SWE/terminal 联合后训练，就必须有 terminal 实际进 learner 的证据。两域结果单列，不用未经定义的混合平均分掩盖一域退化。

### 3.2 现有 216 题是候选资产，不是必须保住的目标数字

当前简报明确其为可信 ingestion 产物，T2-d/e、真实评分、环境资格和 held-out 尚未闭合。先抽取覆盖不同 repo/parser/资源条件的小批，例如 10–20 题，走真实目标 Linux 环境的完整流程，再估计批量成本。

若这条来源能低成本闭合，就扩大；若兼容和环境重建成本明显失控，可以换用维护更好的现成来源，复用已有消费契约。不要因为已经清洗了 216 题而接受错误评分，也不要在还未证明缺任务时先建设大规模合成器。

### 3.3 每个环境应证明什么

| 要证明的事实 | 最小证据 | 容易犯的错误 |
|---|---|---|
| 可以复现 | 固定源码、依赖、镜像和 CPU/内存/存储/网络预算，在目标执行环境运行 | 本机可启动就算训练环境通过 |
| 评分有区分力 | SWE 的应失败基线、参考修复、F2P/P2P；terminal 的空操作与参考完成状态 | 只检查 golden 能过；或所有任务都机械要求 no-op 为 0 |
| 评分与需求一致 | 风险抽样检查不完整修复、合法替代解、描述遗漏和额外隐含限制 | 把测试通过直接当作业务需求已被完整定义 |
| 评分稳定且边界有效 | fresh reset 下重复；针对实际 parser、插件、配置、输出伪造和测试控制文件做小型正反例 | fresh grader 等于完整防作弊；一次确定性运行等于零噪声 |
| 失败可解释 | 区分可归责模型的失败、预算终止、基础设施瞬态故障、配置或内部错误 | 错误都给 0，或模型失败都按 infra 丢掉 |
| 来源可追溯 | repo/base/PR/派生关系和许可信息；公开输入与评分/参考材料分离 | 同一个 bug 换 prompt 后跨越 train/test |

其中“误奖励率”需要人工或独立审计标签。只有设计的几个攻击样例时，应报告这些样例内的结果，不能宣称整个任务集误奖励率为零。

沿用现有环境生产骨架〔仓库引用：`docs/harness_improve/environment_production_and_quality_pipeline_design.md`〕，但其中旧 command-filter 等内容已被后续决策替换，不能因重读旧设计而恢复。离线构建与验证可以充分；运行时只保留真实身份、材料和评分边界所需的检查，不携带一整套逐轨迹资格证书。

### 3.4 数据多样性和扩容

先按 repo、PR/bug 派生关系和任务生成族切分，再生成或筛选。分别准备训练池、可反复使用的开发集、最终测试集。跨 repo 测泛化，同 repo 不同问题测范围内提升；两种口径都可以报告，但不能互相冒充。时间更新有助降低已知泄漏，不保证基座预训练无污染。

多样性先看 bug 类型、工程子系统、依赖关系、修改跨度、测试机制、交互长度与成本，而不是只数语言和题数。一个仓库的一千个相似变异，不能当作一千份独立工程经验。

建议来源顺序：现成任务基线 → 按实际缺口做仓库复用式合成 → 少量真实 PR 补充。合成探针可以从 3–5 个仓库、两种生成方式、100–300 个候选开始；这些只是建议规模，不是必须完成的产量。记录候选存活率、人工/API/CPU 成本、去重后机制覆盖，以及进入训练后的收益。

[SWE-smith 官方实现](https://github.com/SWE-bench/SWE-smith)支持把可运行仓库与多种任务生产方式分开，是摊薄环境成本的合适参照；原论文主要训练成果为 SFT，当前代码也链接 RL 使用。不能从“可复用”推出产物无需在本项目实际 harness/grader 下验证。

### 3.5 把有效性、难度和学习收益分开

无效环境需要修复或隔离；可信但当前难解的任务不应因此获得“无训练资格”的永久标签。固定目标模型、harness 和预算后，测通过率、失败机制、时间与 token，作为采样依据。

在独立同策略二元采样的简化下，n=8 组出现成败混合的概率为 `1-p^8-(1-p)^8`。这只描述 reward 对比出现的机会，不证明中间难度的任务迁移收益最大；实际异步跨版本采样也不必满足同一个 p。`0/8`、`8/8` 都应保留不确定性，用软分层、少量探索和周期复测，避免永久剔除长题和困难题。

如需更新供给，第一版用一次或少数几次离线更新即可：分析训练/dev 失败 → 决定补什么 → 验证并冻结下一批 → 继续训练。最终测试不能参与选择下一批任务。

## 4. Infra：优先解决实际训练消费与无效成本

### 4.1 首训之前必须关掉的缺口

依据两轮交叉审查〔仓库引用：`docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/external_infra_review_crosscheck_20260906.md`〕，优先事项是：

1. **生成动作到训练 token 的覆盖**：REALIGN、rewrite、FORK 后哪些旧响应保留、如何计权；共享前缀不能重复强化。真实 Claude Code 请求和合成边界均需覆盖。不能靠 `clear_thinking=False` 假定已修。
2. **轨迹、组和概率语义**：member reward、fan-out、execution 分母、sampling support、behavior logprob、weight spans 与 R3 来源；固定样本参考计算及目标 GPU 的实际消费验证。
3. **预算与失败归因**：25 次请求上限的终止出口、限流等待越过 deadline、截断处置生产注入；内部装配错误不能靠无限补采隐藏，模型失败也不能随意洗成 infra。
4. **真实评分与作业生命周期**：所选任务的 parser/控制面、receipt 失败清理、当前 W8 eval、C/W7 配置、最小恢复与有界退出。只承诺已经实际验证的支持范围。

这些是正确性底线，不能拿有已知错误的版本做长时间训练，当成容易打败的性能基线。修复前后的问题，用最小反例和少量真实消费证明即可。

### 4.2 一项最值得展示的系统成果

目前最有事实基础的正确性主题是：**黑盒 harness 改写上下文后，训练覆盖和权重语义如何保持明确。** 这比再增加身份字段更能展示算法与系统边界理解，但仍要查上游现状和真实发生率，不先宣称新算法。

性能主改进则由测量选中一项：R3 捕获的同步解码与双份表示、环境准备与重复权限操作、额外 actor forward、评分排队或不合理资源占用。不要预先宣称这些一起能加速几倍。优化 actor forward 时要保留必要的同权重对拍；缓存环境准备只复用不可变部分，每次执行和评分状态仍需正确隔离。

第一轮 trace 至少能分解环境准备、排队、prefill/decode、工具执行、评分、buffer 等待、learner、权重发布及中断重算。总吞吐不能由各段百分比简单相加解释：异步阶段重叠，优化是否改变关键等待路径需实测。

[MiniMax Forge 的官方技术说明](https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm)强调先完成先消费与长尾等待之间的分布取舍。它支持检查本项目的调度偏差，不代表必须照搬 Windowed FIFO 或另写 scheduler。

### 4.3 最小可观测性：回答问题，不建监控平台

```mermaid
flowchart LR
  A[候选任务与来源] --> B[环境与评分验证]
  B --> C[派发逻辑组]
  C --> D[真实 harness 生成动作]
  D --> E[评分与轨迹投影]
  E --> F[准入及消费时版本检查]
  F --> G[训练 token 与参数更新]
  G --> H[固定开发集诊断]
  G --> I[最终独立评测]
  H -.仅训练和开发信息.-> A
```

上图回流不包含最终测试答案或模型在最终测试上的逐题反馈。

使用已有事件和一份离线分析脚本，按逻辑组、execution、生成动作和训练 token 分别计数。报告派发→完成→可评分→准入→实际消费的数量及所耗成本；按任务族、长度、时间和原因看丢弃分布。分叉多出 leaf 不是多采了一次独立经验。

`accepted`、非零 reward 方差、非 singleton support 都是诊断量，不是“确定产生有效学习”的证明。不要为每组另算昂贵全参数梯度来凑一个万能指标。实际消费组/GPU-hour、生成/训练 token 覆盖、DIS 接受比例、支持集分布和参数更新事实分别报告，最终用 held-out 学习结果判断收益。

## 5. 训练设计：一条主配方，一个主要对照

先冻结目标模型的准确 checkpoint/tokenizer，避免把 Qwen3-30B-A3B 与名称相似的 Coder checkpoint 混为一谈。小模型可调试接线，但不能替代目标 MoE 的 R3、显存和并行验证。

基线建议从当前 GRPO n=8、faithful DIS 候选出发，由 C 包完成 loss、预算、staleness 和 harness 支持面的最终选择。第一版以可执行终局结果为主要 reward，不同时加入 rubric、过程奖励、长度惩罚和多个 auxiliary loss。SWE 与 terminal 都应先有清楚的任务完成定义。

组内固定任务版本、harness 和预算；不同任务族先在组间混合。先量基础模型是否会正常用工具、是否已具备可利用的解题能力；需要时做高质量完整轨迹 SFT。SFT 不仅能学工具语法，也可能承担大部分能力提升。若主张 RL 的增量，必须与其直接初始化 checkpoint 比，而不是将 SFT+RL 的全部收益归到 RL。

| 实验 | 固定什么，改变什么 | 应得到的证据 |
|---|---|---|
| 正确性资格 | 冻结请求/轨迹/权重，比较投影与独立计算、合法打包或分片 | 目标语义正确；不是训练收益结论 |
| 正确基线 B0 | 经过验证的静态任务池、主 harness、固定训练配方 | 能实际学习，以及主要成本分布 |
| 主改进 B1 | 相同基座和初始化，只改变选定的一项系统或数据机制 | 相对合理基线的自身贡献 |
| 最终评测 | 对 B0/B1 和初始化使用相同任务、harness、评分和推理预算 | 学习是否改善，成本/退化和不确定性是什么 |

纯系统优化先做固定工作量或轨迹实验，再做有限在线验证。异步线上很难同时固定完成顺序、消费量、版本和墙钟时间，应分别解释：相同工作量是否更快；固定总预算是否得到更好模型。不能只看相同步数。

若供给确实是瓶颈，再替换主增量为静态分层 vs 诊断重配，或普通扩容 vs 诊断扩容。不同扩容策略要给相同生成/校准预算和相同 learner 预算的视角；任务数相同不等于 token 和成本相同。不默认把系统优化、三臂数据研究、多 harness 和蒸馏做成全组合。

至少为关键比较保留一次独立训练重复；预算允许再扩大。评测随机种子只能估计固定 checkpoint 的采样波动，不能替代独立训练重复。没有重复时，应明确结论只是单次运行观察。

## 6. 多 harness、OPD/OPSD/SDPO 应怎样加入

**第二 harness 先用于评测。** 在主路径学到东西以后，用相对简单的 coding harness 运行相同 checkpoint，先排除 adapter、工具协议和预算差异。工具格式变化、上下文/执行方式变化、信息或能力变化分别解释；不能把多了子代理或更强宏工具称为纯接口变化。

固定 harness 下只更换 checkpoint，已经能证明该条件下的权重提升。第二 harness 增加迁移证据，不是让前一项结果变得合法的条件。若迁移差距明显且值得解决，再做多 harness 训练，组内仍保持一致；第三 harness 留给确实要主张未见接口泛化的实验。

**蒸馏先回答它修什么瓶颈。** 对 train/dev 的同一批失败，比较等预算普通再尝试与加入合法执行反馈后的修复。如果反馈能明显救回，再比较完整修复轨迹 SFT 和反馈蒸馏。

[SDPO](https://arxiv.org/abs/2601.20802)将反馈条件下的自身预测变成监督；[OPSD](https://arxiv.org/abs/2601.18734)使用特权上下文形成自教师，其原文主要证据在数学推理。它们都不是“把失败日志加入 prompt”就等于完成训练实现，也不能从已有结果直接推断长程 SWE 上必有效。

若做 token 级 OPD，要取得学生所采 token 的教师概率，确认 tokenizer/支持集、教师版本、反馈可见性和额外 forward 的成本；仅有外部模型生成 API 不一定满足。全零 reward 组可能对蒸馏仍有信号，不能被 GRPO 专用方差过滤提前全部丢弃；应窄接目标相关消费，不伪造 reward、不绕过真实数据资格。

不把自博弈出题模型、多专家 MOPD、训练压缩策略、新过程信用算法作为项目一第一版要求。

## 7. 评测：足够独立、成本可控、结论与范围匹配

### 7.1 三层即可

| 层 | 内容 | 用途 |
|---|---|---|
| 工程正确性与诊断 | 小型真实轨迹、正常失败、截断、分支、评分异常、退出/恢复 | 证明系统是否执行声明的训练；不能代替能力评测 |
| 内部任务评测 | 开发集用于选配置；冻结 final held-out 测 SWE，并独立列 terminal | 学习曲线、跨 repo/任务族表现、失败机制、成本和能力保持 |
| 外部公共坐标 | 优先一个可复现 SWE 集；预算允许再加一个 terminal 集，固定版本和协议 | 让外部读者校准结果；不是所有新 benchmark 都要跑 |

公共集合选当前可运行、对目标模型有区分力且预算允许的版本。旧 benchmark 在最强模型上饱和，不说明对当前 30B 模型无用；但污染和任务质量问题仍须交代。新的 benchmark 也不自动更适合作为训练内循环。

[DeepSWE 官方运行入口](https://deepswe.datacurve.ai/run)与 [Terminal-Bench 官方版本说明](https://www.tbench.ai/news/terminal-bench-4-0)可作候选来源。后者当前 4.0 将 agent timeout 统一为 8 小时，明显不能不经估算就成为八卡首轮硬要求。缩小子集或预算可以做自有实验，但必须标明版本、子集及限制，不与官方完整榜单分数直接混比。源码公开或任务较新都不构成本项目“零污染”的证明。

不要根据 final test 上基础模型成功与否筛掉难题。预算与难度在 dev 上确定；若发现 test 环境无效，按与模型成绩无关的统一规则处理，对所有 checkpoint 一致，并公开排除数量与理由。

### 7.2 最少报告什么

- 相同推理预算下的任务成功率、任务级配对变化；SWE/terminal、来源和主要任务族分列。
- 成功和失败尝试都计入的生成 token、模型请求/工具次数、墙钟及总成本；不要只报告成功案例耗时。
- 环境无效、模型失败、预算终止、系统错误的分布。真实 infra 故障采用预先统一的有界重跑规则，原始尝试与成本保留，不选择性重试某个 checkpoint。
- 简短代码生成/工具协议和原任务能力保持探针，观察专项训练是否明显退化；不用同时跑全部通用榜单。
- 任务级或有充分族数时的分层 bootstrap/配对区间。重复 seed 不充当新增独立题，少数 repo 的众多变异也不当作独立泛化样本。

样本量建议以期望可辨别的差异和成本决定。粗略举例，独立二元任务、成功率接近 50% 时，100 题单个比例的 95% 正态近似区间半宽约 9.8 个百分点，200 题约 6.9；这不是配对增益的最终区间，也没计入 repo 相关性。几十题上提高几个点只能是探索信号。

优先增加独立任务覆盖，再选事先冻结的 30–50 题做多次采样估计稳定性。`pass^3/pass^20` 可以辅助描述重复可靠性，但不应成为项目一的新硬目标。

评测记录保持简洁：checkpoint、task/split、harness/template、工具与上下文策略、采样和预算、镜像与 grader 版本、资源配置、seed、结果与排除规则。它用于复现，不做 owner 授权 manifest。

## 8. 怎样突出亮点，以及何时可以收口

建议最终只集中展示三张图：

1. **任务与训练消费漏斗**：候选环境到实际训练的数量、成本和丢失原因；按长度/任务族展示是否偏删。
2. **一项改进的效率—质量对照**：正确基线上端到端吞吐、资源和无效成本的前后变化，附训练语义/分布检查。
3. **固定 held-out 学习曲线**：初始化、合理基线、主改进，横轴至少有实际消耗 GPU 小时；补充包含环境/教师/API 的成本口径及不确定性。

GPU 成本计入分配给 rollout 和 learner 的全部时间，冷启动、失败和最终 drain 不能从总账消失；CPU、存储、环境生产、教师调用另列并汇总。有 teacher/data 策略的比较同时给 learner 预算与全流程预算，不把某一个代理吞吐称为学习收益。

当前总租卡预算、API 预算和投递时间未定，不给拍脑袋总 step 或天数。先完成目标模型/任务的短资格和基线测量，再为正式基线、主改进、必要重复与最终评测保留预算；不要把钱先花在大规模制题和全因子消融上。

建议执行顺序：

| 顺序 | 完成后的可见成果 | 此时不扩大什么 |
|---|---|---|
| 1 | 选定首版范围；代表性 SWE 环境真实评分、train/dev/test 划分、已知覆盖与归因缺口明确修复 | 不先做 PR 大采集和新 curriculum |
| 2 | 当前 W8、C、W7 与真实数据线闭合；目标 GPU 正确性和真实基线完成 | 不用旧 P3 或本地绿灯代替 |
| 3 | profile 选择一项主要改进；若采用 terminal 补充，小集合完成独立评分和接口验证 | 不同时加多个 loss、harness 和任务生成器 |
| 4 | 正确基线与主改进的受控训练/评测；视目标与预算决定 terminal 混训和第二 harness 验证 | 不在看到 test 后改主假设 |
| 5 | 最小复现、公开结果、成本与失败分析、简历材料 | 不为了多一个名词推迟交付 |

“第一版做好”的标准是：声明的执行面确实可靠；有可重复环境资产和清楚的评分边界；至少一项自身改进有可复核结果；有独立学习证据和诚实限制；外部读者无需读内部阶段账本即可复现主要结论。若没有学习提升，应定位原因并缩小声明，不能用 loss 有限来替代；也不必为了追求某个预设增益继续无限扩系统。

简历建议写三种成果，而不是功能清单：

> **训练正确性**：基于 miles/SGLang 和现有 adapter，解决［具体黑盒上下文/轨迹消费问题］，以［真实请求、参考计算和 GPU 对照］验证声明范围内的训练语义。
>
> **效率与可靠性**：在［硬件、模型、harness、任务范围］上，通过［自身改进］将［实际消费吞吐或无效成本］从 A 改善到 B，说明任务分布与质量变化。
>
> **环境与学习**：建设［来源与范围］的可重复任务验证流程，在［冻结评测、预算］下实现［结果与区间］，公开成本、失败归因和复现入口。

方括号和数字必须由完成后的证据填写。若没有跨 harness 实验，就不写跨 harness 泛化；若没有多机结果，就不写大规模可扩展性。项目二不应成为投递前置。

旧 DeepSearch 项目可简写方法迁移、rubric、多轮搜索训练及实际诊断；新项目突出真实 coding 执行、评分、消费和受控结果。若两者仍高度重复，压缩旧项目篇幅比给新项目加一套研究任务更合理。对 agent 生成的代码，用户本人应能解释关键路径、一个故障根因及一项实验取舍；这比介绍由多少 agent 写了多少代码更能证明独立能力。

## 9. 外部调查中应保留与修正的结论

| 建议 | 本轮判断 |
|---|---|
| 环境有效性、当前学习机会、实际收益分开 | 采纳，是数据与训练设计的主线 |
| 静态池不够时，有限轮离线更新 | 采纳为条件扩展，不提前建设在线共演系统 |
| 动态供给天然应成为项目一主成果 | 不采纳为既定结论，先看真实瓶颈 |
| SFT 只负责基本语法 | 不成立；需要把完整轨迹 SFT 当有竞争力的学习基线 |
| 必须未见第三 harness 才能证明模型提升 | 不成立；它决定泛化范围，不否定固定系统下的权重提升 |
| 某同量级模型论文证明本项目八卡可低成本复现 | 不成立；上下文、训练时长、教师、硬件和方法必须分别核对 |
| 在已知错误评分基线上完整训练，以证明资格层价值 | 没必要；错误用审计与最小复现，性能/学习比较使用正确基线 |
| 每个数据资产配完整资格证书、每轨迹再验证一遍 | 不默认采用，沿用现有边界，避免恢复已删除的治理复杂度 |
| 认知控制、主动试验、长时记忆、影子部署都纳入评测 | 属于项目二的大部分动机，当前不纳入 |

两篇特别容易误读的环境论文也已核对：[CalibForge](https://arxiv.org/html/2608.06352v1)的主要受控结果是匹配任务数的 SFT，保留轨迹数并不完全相同，训练使用 64×H20；不能当作动态 RL 或八卡成本证明。[Envs-FORGE](https://arxiv.org/html/2608.14312v1)确有 GRPO，但原文承认尚未隔离完整供给策略中各组件的作用。它们支持尝试任务校准，不支持预先认定更复杂的选择器必优于静态分层。

本轮最重要的取舍是：**把项目一做成范围有限、结论可靠的后训练项目；系统、数据或反馈的主创新由实验选中。当前先完成已有真实链路，是方向收敛，不是降低技术标准。**
