# 项目一外部资料精读库与派工计划

> **2026-09-09 增量**：[Miles v0.1 完整报告（2609.08368v1）](miles_v0_1_2609.08368.md)已完成全文、图表和定点源码阅读，附[作者自查](reviews/miles_v0_1_2609.08368_self_check_20260909.md)，尚未独立审查或复现训练。本文下方的批次总数与候选状态是 2026-09-07 历史快照，不能作为当前全库完成状态；最新情况以各篇正文与检查记录为准。本次只登记该新报告，不改写其他线程的成果或状态。

日期：2026-09-07。状态：**第一组 01–06、第二组 07–12 已完成 14 份笔记及 12 份线程内独立审查。外部 Pro 经用户单独批准完成 O01 SkyRL-Agent 全文精读与作者自查，现有 15 份逐篇笔记；O01 尚未独立复查。原第三批不整批启动，其他候选未因本次阅读自动执行。** 完成与核查范围见 [第一组执行记录](BATCH1_RUN.md) / [质量检查](BATCH1_QUALITY_REVIEW_20260907.md)、[第二组执行记录](BATCH2_RUN.md) / [质量检查](BATCH2_QUALITY_REVIEW_20260907.md)。[外部 Pro 交接包入口](external_pro_handoff_20260907/00_HANDOFF.md)包含可直接携带的全文材料；[第三组准备方案](BATCH3_PLAN.md)仅保留为可重新排序的候选。

**远程读写入口**：本库位于 GitHub 的 `miles-migration` 分支，默认 `main` 不代表这批成果。后续文档请基于 `miles-migration` 维护本目录，沿用单篇文件名和来源编号；O01 最新状态见本索引，其余第三批候选仍未启动。仓库已包含正文、审查、交接包、来源登记及第二批固定初稿。`sources/` 内的原始 PDF/TeX、渲染图和第三方代码缓存未随本次文档提交上传；指向这些附件的本地链接在远程可能不可用，复查请使用各篇的官方 URL、版本和页/节定位。

阅读要求：每个任务覆盖全部后训练正文和附录，任务问题仅作补充重点。前两批实际采用线程内独立 sub agent 审查；外部线程按真实工具能力记录检查。O01 当前只有作者自查，不伪称独立审查；后续独立复查可追加记录。

本库服务项目一：coding / SWE / terminal 的环境供给、可靠高效的 RL / OPD 链路及可信评测。项目二的长期记忆、世界模型等暂不进入主队列。阅读顺序按当前决策价值安排，既读近期报告，也保留直接解释现有方法的早期来源。

## 已交付笔记：优先从这里查

以下新稿是对应来源的后续维护入口；历史摘要保留作线索。精读、作者自查与独立审查按最后一列分别记录；任何阅读完成状态都不表示论文实验或本项目实现已被复现验证。

| 来源 | 常见问题的查阅位置 | 检查记录 |
| --- | --- | --- |
| [R1 MAI-Thinking-1](R1_mai_thinking_1.md) | §3–4 专家合并与 GRPO；§5 其他后训练；§6 SWE 漏斗；§7 异步；§8 评测 | [01](reviews/01_R1_review.md) |
| [R3 Qwen3-Coder-Next](R3_qwen3_coder_next.md) | §3 专家与蒸馏；§4 两条数据管线；§5–6 loss 披露与 packing；§7 评测 | [02](reviews/02_R3_review.md) |
| [N01 KAT-Coder-V2.5](N01_kat_coder_v2_5.md) | §4 环境；§5 PPO、GRM、MOPD；§6 harness/infra；§7 评测 | [03](reviews/03_N01_review.md) |
| [E2 CalibForge](E2_calibforge.md) | §4 任务校准与筛选；§5 离线 SFT；§7 消融与失败案例；§8 开放资产 | [04](reviews/04_E2_review.md) |
| [N11 miles agentic rollout](N11_miles_agentic_rollout.md) | §3–4 token/session；§5 loss/OPD；§6 fully async；§7 eval；§10 当前 rh2 接入边界 | [05](reviews/05_N11_review.md) |
| [Miles v0.1 技术报告](miles_v0_1_2609.08368.md) | §3 rollout/TITO；§4–5 trainer/权重；§6 OPD/数值对齐；§7 diffusion；§9 GLM 案例；§10 代码对账 | [作者自查，待独立复查](reviews/miles_v0_1_2609.08368_self_check_20260909.md) |
| [N13a SWE-bench Verified 审计](N13a_swe_verified_audit.md) | §3–5 抽样分母、失败模式与污染；§6 建议边界；§8 项目映射 | [06](reviews/06_N13_review.md) |
| [N13b Coding 评测信号与噪声](N13b_coding_eval_signal_noise.md) | §3–4 两条审查路径与分母；§5 全部动态案例；§6 建议变化；§8 项目映射 | [06](reviews/06_N13_review.md) |
| [R2 Nemotron 3 Ultra](R2_nemotron_3_ultra.md) | §3–4 全域训练、教师和 SWE；§5 MOPD/MTP；§6 效果；§7 infra；§8 评测；§10 未披露 | [07](reviews/07_R2_review.md) |
| [R13 Kimi K3](R13_kimi_k3.md) | §3–4 九专家/继承/MOPD；§5 数据环境；§6 partial rollout/AgentENV；§7 评测 | [08](reviews/08_R13_review.md) |
| [R4 MiniMax M2](R4_minimax_m2_series.md) | §3–4 数据与全域后训练；§5 CISPO/reward；§6 Forge；§7 评测与负结果 | [09](reviews/09_R4_N10_review.md) |
| [N10 MiniMax Forge](N10_minimax_forge.md) | §3 黑/白盒；§4 Windowed FIFO；§5 前缀合并/40×边界；§6 算法；§7 证据 | [09](reviews/09_R4_N10_review.md) |
| [E10 Intern-S2-Preview](E10_intern_s2_preview.md) | §4 reasoning RL/R3/BKL；§5 agentic/token；§6 OPD；§7 其他后训练；§8 评测 | [10](reviews/10_E10_review.md) |
| [E5 SWE-smith](E5_swe_smith.md) | §2–3 任务漏斗；§4 SFT；§5 消融；§6 成本/污染；§7 后来 RL 接线 | [11](reviews/11_E5_review.md) |
| [O03 R2E-Gym](O03_r2e_gym.md) | §2 环境；§3 三类 SFT；§4 推理打分；§5 harness；§6 评测；§7 当前资产；§8 冲突/未知 | [12](reviews/12_O03_review.md) |
| [O01 SkyRL-Agent / SA-SWE](O01_skyrl_agent_sa_swe.md) | §3 generation 流水线；§4–5 SWE 工具、LOO/horizon；§6 评测/成本；§7 搜索/记忆/GUI；§8 当前代码差异 | [15：作者自查，待独立复查](reviews/15_O01_self_check_20260907.md) |

## 1. 入口与已有资产

- [逐条资料目录与旧稿复用表](SOURCE_CATALOG.md)：32 份本地 PDF、在线入口和新增候选；包含原文路径、旧稿位置与重复关系。
- [逐篇文档模板](NOTE_TEMPLATE.md)：后训练、环境、infra、评测的具体提取字段。
- [独立任务公共提示词](TASK_PROMPT.md)：可与下方任务表直接组合派工。
- 原始 [资料索引](../README.md) / [PDF manifest](../manifest.json) 继续负责原始资料登记；本目录负责阅读成果。暂不迁移、删除旧文件。

盘点结论：

| 资产 | 实际状态 | 处理方式 |
| --- | --- | --- |
| manifest 的 32 份 PDF | 全部存在；29 份在 `pdfs/`，3 份在上一级文档目录 | 保留原路径；每篇独立产出，不批量重新下载 |
| 根目录 `knowledge/` | 16 份受 Git 跟踪的摘要，15 个来源；CalibForge 两稿同源 | 多数已有较好的方法与实验骨架，回原文补证据、纠错和更新项目映射 |
| 两份独立专题 | K3 + AgentENV、SA-SWE horizon / masking | 可复用已覆盖主题，不能代替整篇相关内容精读 |
| 综合分析与原始对话粘贴 | 配方矩阵、infra 映射、MAI / Ultra 共读段、K3 长文等 | 作为提纲和线索；模型回答本身不作为论文证据 |
| README 在线入口 | 超出 PDF manifest；有模型卡、博客、代码、重复条目和一个入口多篇 | 按具体原始来源拆开，不能把索引行数当论文数 |

以上是派工前的资产盘点，不表示逐条验真所有旧摘要。前两组已用上表新稿补足对应来源；其余来源仍按原盘点状态处理，不能据此补上“精读完成”标签，也不能断言以前无人精读过。

需要优先处理的资料问题：

1. CalibForge 两稿合并取长补短；CalibForge / Envs-FORGE / MOPD 旧摘要的“无本地 PDF”已过时。
2. K3 在专题/矩阵与粘贴长文中，对算法公式披露和继承关系的表述不同。先核具体版本与原文，再判断，不按篇幅选可信版本。
3. Kimi K2.5 的更新入口和 R7b 是同一论文的版本关系；尚未核实本地 PDF 是否对应 README 所说的更新版。
4. E12 MiniMax-M3、E13 MiMo-V2-Flash 已有 PDF，但未找到独立逐篇稿；E8 ECHO 只有勘误与综合增量，不能误标完成。
5. Agentica 的 DeepSWE 模型与 Datacurve 的同名 benchmark 分开登记；同名不能合并。
6. 旧调查中的 KAT 引文曾误指 Qwen。目录给出独立 arXiv 入口；正式阅读时再核标题、版本及内容。

## 2. 已完成的 12 个独立任务（分两组执行）

以下保留已执行的任务拆分，12 个任务均已完成。历史上按每组 6 个任务并行，是便于回收的安排，不是平台并发上限。用户已决定把后续选题和精读转至外部，不继续本地派发。

编号沿用原索引的 R / E；O 表示本次整理的已有在线入口，N 表示补充候选。它们是文献编号，不是训练闸门或严重性等级。

| 任务 | 来源与产出文件 | 类型 | 额外关注点（不限制完整后训练阅读范围） |
| --- | --- | --- | --- |
| 01 MAI | R1 → `R1_mai_thinking_1.md` | 新建，复用综合段 | SWE 环境从原始来源到可训练任务的漏斗；可解性/评分隔离；失败处置；训练和环境成本分别是什么 |
| 02 Qwen Coder | R3 → `R3_qwen3_coder_next.md` | 新建，复用矩阵 | 任务/环境/轨迹数量分别是什么；训练各阶段关系；harness 多样性与收益的证据边界 |
| 03 KAT | N01 → `N01_kat_coder_v2_5.md` | 新补来源、独立精读 | 环境构建、近成功轨迹、RL / MOPD、harness randomization 分别有何证据与消融 |
| 04 CalibForge | E2 → `E2_calibforge.md` | 两稿合并升级 | solver 校准到底筛掉什么；任务质量与可学习性如何区分；成本与 SFT 证据如何限制 RL 外推 |
| 05 miles | N11 → `N11_miles_agentic_rollout.md` | 版本化官方文档/代码专题 | TITO、重分词、session 运输、异步消费的官方约定；本项目 pin 实际承担什么，上游能力不等于本地已采用 |
| 06 评测审计 | N13 → `N13a_swe_verified_audit.md`、`N13b_coding_eval_signal_noise.md` | 两篇官方短文，同一线程 | 被审计的具体任务与版本、抽样和失效原因；怎样影响 held-out 选择与成绩解释；两篇各自成文 |
| 07 Nemotron Ultra | R2 → `R2_nemotron_3_ultra.md` | 新建，复用综合段 | 专家训练、RLVR、MOPD 的阶段/teacher 关系；SWE 环境、失败屏蔽、routing 与成本 |
| 08 K3 | R13 → `R13_kimi_k3.md` | 专题与长文核对后重整 | 先解决版本/公式披露分歧；再拆清 expert、MOPD、partial rollout、预算和环境隔离 |
| 09 MiniMax M2 / Forge | R4 → `R4_minimax_m2_series.md`；N10 → `N10_minimax_forge.md` | 一份长报告 + 配套官方文章 | 数据生产与真实 harness；Windowed FIFO、样本选择/长尾分布、成本和收益分母；两来源各自成文 |
| 10 Intern-S2 | E10 → `E10_intern_s2_preview.md` | 旧稿升级 | 黑/白盒 harness、token 捕获、expert 分叉、OPD 的具体语义及原文未披露项 |
| 11 SWE-smith | E5 → `E5_swe_smith.md` | 旧稿升级 | 真实仓库任务生产、验证、镜像复用、数量漏斗和总成本；SFT 结果不能写成 RL 已验证收益 |
| 12 R2E-Gym | O03 → `O03_r2e_gym.md` | 旧稿升级 | 可执行 SWE 环境与轨迹生成、训练方法、benchmark 分割、可复用开放资产和成本 |

选择这一批的原因：既补模型团队完整案例，又尽早形成数据、运行链路和评测的参考文档；已有笔记的升级也能较快验证模板是否真的解决检索问题。此顺序不是论文质量排名。Composer 2、SAO、CompactionRL 等同样重要，只是本地已有专题线索，接在下一批。

## 3. 后续候选（由外部 Pro 重新排序）

**原第三组不整批启动，原顺序不再作为自动执行队列**。其中任务 15 / O01 SkyRL-Agent 已由外部 Pro 单篇精读并自查；SAO、CompactionRL、SDPO、OPSD、MOPD 仍是未启动候选。SDPO v2 为 50 页长报告；MiMo v2 为另一份 31 页报告。原准备范围见 [BATCH3_PLAN](BATCH3_PLAN.md)，它及交接包保留历史快照，不覆盖本索引的最新 O01 状态。

以下是任务组，不表示每组交给一个线程。**一篇长报告通常独立一个线程；短文章可以同线程读 2–3 篇，但每篇仍有独立 Markdown。** 代码库入口则允许一份边界清楚、绑定版本的专题，避免给每个 release / issue 单独建空洞笔记。

| 顺序 | 来源 | 目的与组织 |
| --- | --- | --- |
| B1 训练目标与长程语义 | R15 SAO、R14 CompactionRL、O01 SA-SWE（已交付）；N07 SDPO、N08 OPSD；E7 MOPD、E13 MiMo | 分篇核公式、样本单位、mask、归一化、截断/恢复；完成后再做方法比较表 |
| B2 环境生产与筛选 | E3 Envs-FORGE、E4 Endless、E8 ECHO、O04 SWE-Gym、O05 Scale-SWE、O11 SWE-rebench V2 | 分篇整理生产漏斗、可执行性、solver 过滤、污染及单位成本；不预定当前 taskset 格式 |
| B3 最新训练案例与 harness | R9 Composer 2、R5 GLM-5、R5b/5c GLM 博客、E12 MiniMax-M3、E11 Cascade 2、R6b DeepSeek-V4、E1 Harness Interplay、N16 Harness-Bench | 长报告分篇；博客分篇；区分官方宣称、控制变量实验和我方推断 |
| B4 当前系统的直接对照 | R0 Polar、R10 Let It Flow、R11 RollArt；N04 Prime 官方实践、O25 M2.1；O27 Harbor、O23 AEnvironment、O26 OpenEnv | 明确谁负责 token、调度、sandbox、reward、版本；先读报告/官方文档，需要时只追关键代码 |
| B5 数据和评测闭环 | N03 Socratic-SWE、N06 benchmark hardening、N14 Terminal-Bench 版本、N15 Datacurve DeepSWE、O12 长程终端评测、O21 NVIDIA SWE 数据、O28 SWE-rebench 工程经验、O19 Prime 环境计划 | 测试可信度、任务供给、分割与预算协议；多篇发布文各自成文，平台运行协议可成专题 |
| C 背景与后续扩展 | R6a DeepSeek-V3.2、R7a K2、R7b K2.5、R8 M1、R12 ROLL；E6 Surge、E9 Qwen 架构；O02 DeepSWE 模型、O06 SETA、O08 AgentRL、O09 OpenClaw-RL、O10 DAPO/Dr.GRPO/RLOO、O29 Muse、O35 RLVE、N02 SSR、N09 hindsight、N12 工程错误案例、N17 reward hacking | 继续覆盖已有库；长报告仍逐篇读。架构文/跨域案例只提取相关部分，缺后训练披露就明确写缺，不硬凑 |
| 暂存入口 | O13–18 的团队页/配套博客/模型卡/releases、O20 权重同步、O22 接口事件、O24 CUDA-Agent、O30–32 模型卡、O34 新仓库观察项 | 团队页/releases 是导航；已有任务配套材料附在对应笔记；模型卡先看是否有足够独立披露，再决定专题深度 |

O07 = E4，O33 = R7b 的版本线索，N05 = O35，不重复开任务。N10 已在第二批完成。其余候选的未核 URL 与暂存理由见目录。阅读排队不等于建议项目实现对应功能，更不把全库读完作为开始项目一实验的前置条件。

## 4. 已执行的本地任务方式（历史记录，不触发后续派发）

当前 Codex 的独立任务工具支持直接设置：

```json
{
  "model": "gpt-6-astra",
  "thinking": "high"
}
```

这是 `create_thread` 的任务级参数，不改全局偏好。官方模型文档也列出 [GPT-6 Astra 支持 high](https://developers.openai.com/api/docs/models/gpt-6-astra)。临时子 agent 和侧栏独立任务是两套工具：本批用侧栏独立任务精读，各任务再在自己的线程内创建审查 sub agent；两层的实际配置均已核实。

执行安排：

1. 主线程先从 `list_projects` 选当前仓库，再创建项目独立任务，逐个设置模型和推理程度。Git 项目默认隔离 worktree；若用户明确要求直接写当前工作目录，则改为 local，并严格划分文件所有权。
2. 发送“公共提示词 + 指定资料入口/旧稿 + 指定产出文件 + 本篇重点”。独立线程不依赖本聊天的隐含上下文。
3. **worktree 不自动携带未提交/未跟踪的资料。** 派工时提供当前资料目录的只读入口，或把所需来源和本计划复制进任务工作目录；不要为此要求先提交整个仓库。对项目映射绑定当前集成分支/commit，不能让新 worktree 的默认分支冒充当前 miles 状态。
4. 阅读线程只写分配给自己的逐篇文件、审查文件及必要来源附件，不改共享 README / catalog、训练代码或实验定案。先在独立 worktree 完成；本轮派工允许各线程审查修订后，将自己的专属成品复制回主资料目录的相同相对路径，避免主线程结束后成果只留在 worktree。共享索引由主线程更新。
5. 主线程用 read / wait 读取结果；若线程创建尚在准备，等拿到正式 threadId 后再派发后续消息。每篇完成后回收 Markdown，检查证据、文件引用与未知项，再放到此目录并登记链接。
6. 每个线程先安排一名干净上下文的 sub agent，从原文目录和附录独立检查覆盖，再核对初稿的关键事实、公式、预算、结果、成本、项目推断。主作者修订并记录处理情况。主线程回收时再抽查重点，不额外为每篇派两名完整重读 reviewer。

所有任务共享账号额度。增加线程只提高并行度，不提供独立额度，也无法预先保证剩余额度能完成多少长报告。逐批回收使已经完成的笔记可直接复用；额度不足时按各篇已记录的阅读位置续读，不从头重做。

## 5. 成品标准与维护

**目标是常见设计讨论只查笔记就能找到实验对象、方法细节、预算口径与证据边界；需要核验时能直接跳到原文位置。** 不是要求读者再次打开原文才补得齐摘要缺掉的上下文。

- 精读全部后训练正文和附录；原文涉及的一般推理、数学、多模态 RL、安全对齐等也应总结，不能因为当前只做 SWE 就遗漏。纯预训练/架构等非后训练部分可以概要阅读，但列明范围和理由。不能把“只提取了几个词”写成全文精读。
- 关键事实附 PDF 物理页 + 章节/表/图/公式，网页附标题/段落，代码附 commit + 文件/符号。原文未给出的字段写“未披露（已查哪些部分）”。
- 数量带单位和分母，成本拆分环境生产、teacher/API、训练、评测。对比成绩带模型、harness、版本和预算。
- 论文事实、作者解释、读者推论、项目建议分清。旧模型摘要和当前仓库代码都不能替原论文补写“它使用了什么算法”。
- 当前项目映射只在文末一节，带日期与前提。上游已承担的功能注明“复用/验证上游”；只有我方必要增量才写候选改动，并提出一个可验证的小实验。
- 不设机械字数要求；短模型卡允许短笔记。长报告不能用几十行概括所有训练细节。开放资产记录实际可访问状态、版本和使用限制。
- 标题后给简短摘要和可点击的章节导航，完整来源与覆盖表随后保留。关键限定紧邻对应数字/公式；其他重复的未知项集中列一次。详见第一组检查后的模板更新。
- 审查文件记录主/子线程 ID、来源版本及被审初稿的版本标识。审查期间保持该初稿稳定，修订另记处理；不要求新增自动 hash 检查或多轮全文重审。
- 旧稿先保留，完成新稿时记“复用了哪些旧稿、纠正了什么”；新稿成为后续维护入口。暂不批量删除旧摘要或改动其他历史引用。
- 文献版本、代码 commit 与一次性来源快照服务复核；不另建自动 hash 闸门、审批流程或文献管理平台。

前两组保留原有独立审查状态；O01 为外部全文精读与作者自查完成、待独立复查。其余候选继续由用户逐篇确认，阅读任务不修改训练实现，也不把候选建议写成项目实施定案。
