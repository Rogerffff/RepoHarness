# 第二组精读执行记录

日期：2026-09-07。状态：**任务 07–12 全部完成，七份笔记与六份独立审查已发布到主资料目录，并完成主线程定点检查。** 15 项审查发现/建议均已写入正文，详见 [第二批质量检查](BATCH2_QUALITY_REVIEW_20260907.md)。用户最新安排：第三组不启动，后续选题与阅读转到外部 Pro。

第三组的来源与提示保留为 [任务 13–18 候选材料](BATCH3_PLAN.md)，不是已批准的下一组；两批成果的 [外部交接入口](external_pro_handoff_20260907/00_HANDOFF.md)已整理。

## 当前状态与专属产出

本次六个任务均采用独立 worktree，实际运行配置为 `gpt-6-astra` / `high`。下表是回收后的完成状态。原文、最新模板、项目背景与旧稿通过主资料目录只读提供，避免遗漏未提交材料。

| 正式任务标题 | 正式线程 ID | 已核实状态 | 已交付成品与审查 |
| --- | --- | --- | --- |
| 精读 07：Nemotron 3 Ultra 后训练 | `01a07827-1e2f-78c3-8c14-1d222dda34c7` | 完成、审查修订已交付 | `R2_nemotron_3_ultra.md`；`reviews/07_R2_review.md` |
| 精读 08：Kimi K3 后训练 | `01a07827-1e44-7133-85d7-65aee3707e7f` | 完成、审查修订已交付 | `R13_kimi_k3.md`；`reviews/08_R13_review.md` |
| 精读 09：MiniMax M2 与 Forge 后训练 | `01a07827-1e44-7133-85d7-658445c04597` | 两份成品完成、审查修订已交付 | `R4_minimax_m2_series.md`、`N10_minimax_forge.md`；`reviews/09_R4_N10_review.md` |
| 精读 10：Intern-S2-Preview 后训练 | `01a07827-1e43-76b3-a7b5-927d16ceab97` | 完成、审查修订已交付 | `E10_intern_s2_preview.md`；`reviews/10_E10_review.md` |
| 精读 11：SWE-smith 环境与训练 | `01a07827-1e3f-7bb0-85d6-7ac47489ae64` | 完成、审查修订已交付 | `E5_swe_smith.md`；`reviews/11_E5_review.md` |
| 精读 12：R2E-Gym 环境与训练 | `01a07827-1e42-70f2-ac37-48ca0e1af7a7` | 完成、审查修订已交付 | `O03_r2e_gym.md`；`reviews/12_O03_review.md` |

七份笔记中，MiniMax M2 论文与 Forge 官方文章分别成文，共用任务 09 的一名审查者；审查须分别核对两来源完整覆盖。其他任务各一份笔记、一份审查。

## 实际审查身份与完成证据

六个正式任务的最新回合均为 `completed`，`error=null`；六个作者与六个子任务的实际会话配置均为 `gpt-6-astra / high`。每个作者仅创建一名 `fork_turns="none"` 独立审查者，子任务没有再派 agent。以下 UUID 来自真实父子会话元数据；K3 原稿只记 canonical ID 的限制保留，本表补足主线程后来核得的身份。

| 任务 | 独立审查子任务 UUID | canonical ID | 主任务耗时（含子审查） |
| --- | --- | --- | --- |
| 07 | `01a0782d-89ca-7723-ac6f-947eb979e7d7` | `/root/r2_independent_review` | 11.8 分钟 |
| 08 | `01a0782e-ae04-7be0-a07d-d3db47b99845` | `/root/review_r13` | 13.8 分钟 |
| 09 | `01a07831-76f5-7ae1-8211-2dc348e68bbd` | `/root/review_r4_n10` | 17.5 分钟 |
| 10 | `01a0782f-d4e7-7691-ade5-f3ce907e50cb` | `/root/e10_independent_review` | 14.9 分钟 |
| 11 | `01a0782d-eba9-79a3-81cb-51d5e1e7ace7` | `/root/review_e5` | 13.1 分钟 |
| 12 | `01a0782e-169c-7b10-939b-bff6f99d0f9a` | `/root/review_o03` | 12.3 分钟 |

六任务并行总墙钟约 18 分钟，不能把单任务耗时相加当用户等待时间；不含主线程后续检查，也不据此推算费用。07/08/11 的作者修订、09/12 的同一审查者定点复核、11 的 SkyRL 补充检查，分别按实际发生情况记录在对应审查中。未声称全部又做第二轮全文独立复审。

## 来源与复用范围

| 任务 | 原文入口 | 可复用旧稿与额外关注 |
| --- | --- | --- |
| 07 | [Nemotron Ultra 本地 PDF](../../NVIDIA-Nemotron-3-Ultra-Technical-Report.pdf) | 旧综合分析与配方矩阵；重点核多教师阶段、RLVR/MOPD、SWE 与其他后训练、失败样本和预算 |
| 08 | [Kimi K3 本地 PDF](../pdfs/k3_tech_report.pdf)、[arXiv](https://arxiv.org/abs/2607.24653) | [K3/AgentENV 专题](../k3_agentenv_relevance_notes.md)、配方矩阵与旧粘贴长文；先核版本及算法披露分歧 |
| 09 | [M2 本地 PDF](../pdfs/R4_minimax_m2_series_2605.26494.pdf)、[arXiv](https://arxiv.org/abs/2605.26494)、[Forge 官方文章](https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm) | 配方矩阵与 infra 映射；重点核 Windowed FIFO、训练目标、长尾与吞吐分母，全部后训练领域仍在范围内 |
| 10 | [Intern-S2 本地 PDF](../pdfs/E10_intern_s2_preview_2608.13505.pdf)、[arXiv](https://arxiv.org/abs/2608.13505) | [旧稿](../../../../knowledge/summary_intern_s2_preview.md)；核正式标题、黑/白盒 agentic RL 与 OPD 关系、全部科学/通用后训练 |
| 11 | [SWE-smith 本地 PDF](../pdfs/E5_swe_smith_2504.21798.pdf)、[arXiv](https://arxiv.org/abs/2504.21798)、[官方实现](https://github.com/SWE-bench/SWE-smith) | [旧稿](../../../../knowledge/summary_swe_smith.md)；环境/任务/轨迹漏斗、验证、成本，论文 SFT 与后来 RL 示例分开 |
| 12 | [R2E-Gym arXiv](https://arxiv.org/abs/2504.07164)、[官方实现](https://github.com/R2E-Gym/R2E-Gym) | [旧稿](../../../../knowledge/summary_r2e_gym.md)；补正式原文，分清训练收益、推理时候选选择和后来的 DeepSWE 更新 |

这些额外关注点不是阅读边界。每个任务须按原文正文、全部后训练附录、图表、必要网页交互建立覆盖，再检查旧稿遗漏与误解。

## 本次已下达的质量要求

- 标题后给简短摘要与可点击导航；详细来源和覆盖随后。重要限定紧邻数字/公式，其余重复未知项集中整理。
- 初稿完成后，实际创建一名 `gpt-6-astra` / `high`、`fork_turns="none"` 的独立 sub agent。先从来源检查完整范围，再核对笔记，不以固定问题数限制审查。
- 记录主/子线程 ID、来源版本、固定初稿标识和审查/修订日期。交审版本保持稳定；收到结果后修订，并记录发现的实际处理。
- 不强制重复下载、重算 hash 或整篇二次复述。表格、公式、疑点、提取截断处回原页核查。
- 新旧版本存在时，实际检查后训练/数据环境/infra/评测的实质变动，补读并单列新版增量，不能仅记版本号。对已初步报告版本差异的 08/09/12 另发了定点提醒。
- 完成后仅将各自专属笔记、审查及必要 `sources/` 子目录发布到主资料目录；不改共享索引、其他作者文件、训练代码或实验定案。
- 尚未收到独立审查、存在未读章节时，保留续读位置，不标精读完成。

启动证据：创建请求成功返回准备中的 clientThreadId；主线程从新建会话元数据取得六个正式 ID，再用 `read_thread` 逐一确认 `active` / `inProgress` 和实际阅读进展，并核六份 `turn_context` 的模型与 effort。没有将 clientThreadId 传给正式线程工具，也不依赖列表是否显示新任务。

公共要求见 [任务提示词](TASK_PROMPT.md)、[笔记模板](NOTE_TEMPLATE.md)；前批经验见 [第一组质量检查](BATCH1_QUALITY_REVIEW_20260907.md)。
