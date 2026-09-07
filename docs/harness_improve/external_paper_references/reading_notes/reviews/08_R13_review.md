# R13 Kimi K3 独立精读审查

审查日期：2026-09-07。结论：固定初稿覆盖了要求范围内的后训练正文、部署训练、评测与附录；未发现重大算法错误、关键数字误抄或整块主题遗漏。发现两项轻微措辞问题，另有一项图表身份边界建议补充，详见 §3。此结论是阅读审查，不是训练复现或实现正确性证明。

## 1. 审查身份、版本与独立性

- 主任务 ID：`01a07827-1e44-7133-85d7-65aee3707e7f`；派工主任务 ID：`01a077c4-9f0d-7ef0-a40a-688b42f1b294`。
- 独立审查 agent ID：`/root/review_r13`，为调度器返回的 canonical ID；未获单独 UUID，不把根任务环境变量当作子任务 ID。
- 实际调度配置：`gpt-6-astra` / `high`，干净上下文 `fork_turns="none"`，由父调度器配置与记录确认；本审查未再派 agent。
- 被审固定版本：[R13_kimi_k3.draft_20260907.md](../sources/R13/R13_kimi_k3.draft_20260907.md)，371 行，日期 2026-09-07。该副本中的相对链接按正式笔记目录解析；审查期间正文保持固定。审查者只写本文件。
- 来源：[本地 47 页报告](../../pdfs/k3_tech_report.pdf)、[arXiv 官方记录](https://arxiv.org/abs/2607.24653)、[v1 PDF](../sources/R13/arxiv_v1.pdf)、[v2 PDF](../sources/R13/arxiv_v2.pdf)及完整两版源 TeX。官方记录确认 v1 为 2026-07-27、v2 为 2026-08-07。下文页码均指本地报告物理页。
- 依赖核验仅限 K3 明确引用的 K2.5 策略优化：K2.5 v1 p.8 §4.4.2 Eq.(1)，同时对照 [原页](../sources/R13/k25_page-08.png)及 `sources/R13/k25_tex/4-pipeline.tex`。没有把 K2.5 全文配方认作 K3 事实。

执行顺序：先读公共任务、模板和第一批质量要求，再从 `main.tex` 的包含树独立建立下表，读完原文对应部分后才通读固定初稿。未先读作者的旧笔记、覆盖底稿或旧结论。原文提取、公式页和图表页可复用，但判断由本审查独立作出。

| 原文范围 | 独立检查内容 | 初稿覆盖结论 |
| --- | --- | --- |
| §1–3 | 架构/预训练概要；细查参数单位、上下文课程、视觉初始化、路由、精度及 cosine/WSD 条件 | §1–2 已覆盖；比较条件有一处措辞修订 |
| 全部 §4.1 | SFT、三域九专家、effort 课程、partial rollout、GRM、MOPD、QAT、draft 训练 | §3–4 完整，无阶段或教师关系颠倒 |
| 全部 §4.2 | 白盒 harness、图谱合成、可验证搜索/专业/视觉任务、kernel、个人助理、AET、webdev，含图9–10 | §5 完整；未将不同域 verifier 规则不当合并 |
| §5.1–5.2 | KDA/KCP、MoonEP、内存与视觉 encoder 概要；核影响后训练的状态、梯度和路由机制 | §6.4 已概要覆盖，未冒充 rh2 应自建能力 |
| 全部 §5.3–5.4 | 共置、CPU/NVMe/KV 生命周期、限流、非 policy forward、三类 sandbox、prefix 一致性、kernel 与 fleet 调度 | §6 已覆盖；正确区分 RL 与在线 serving |
| 全部 §6、四份输入表 | 主套件配置及例外、所有能力域、内部评测、网络安全与失败、第三方快照、费用图 | §7–8 完整；图13标签可补明确身份边界 |
| 全部 §7–8 | 六类案例、预算、模拟芯片、MiniTriton 输给基线的点、结论 | §7.6 覆盖；没有把案例与模型训练曲线混淆 |
| 附录 A–F | A 为贡献名单；B–E 阅读推导并核正文关系；F 全读，含 options、preserved thinking、typed tools、pure-JSON mask | §1–2、§6.3–6.4 覆盖，无独立后训练附录遗漏 |

版本核验重新对两份 PDF 逐页提取并去空白比较，差异确实只出现在 p.1、41、42；本地报告与 v1 技术正文一致，但不是同一字节文件。两版源文件差异落在 §2 归因/引用、§5.2.3 引用、§5.3 开头说明、首图绘制、贡献与参考文献；§4、§6 所有表、§7、技术附录无实质增删。首图 v1 PDF 的数值与 v2 TeX 数据逐 panel 对照相同。v2 的判断以源 TeX 为准，未拿有 Poppler 警告的提取文本证明全文无变化。

## 2. 关键核验与没有发现的问题

1. **模型关系。** §4.1.1–4.1.3：旧 Kimi 领域模型生成初始 SFT 数据；K3 三个 broad domains × low/high/max 得九个 RL policies；各域先 max 再预算退火。专家轨迹供 SFT 和 MOPD，但报告没确定一个额外串行 SFT 阶段。初稿全部正确，并把 MoE 896/16 与九个独立 policy 分开。
2. **继承算法。** K3 p.13 明确 follows K2.5；K2.5 原页同时存在 ratio Clip / 文字 log-ratio 边界、正则求和作用域、minimize 与目标符号的歧义。初稿没有把它修成伪精确 K3 loss；K2.5 生成 token 分母与 K3 prompt 数 N 的区分正确。原式没有 value/GAE 或标准差归一化项，但这不证明内部不存在任何未披露变体。
3. **组与预算。** p.13 的活跃 NK、完成比例 λNK、未完成下轮优先恢复、同题 K 全完成才送优化都已保留；不能据此声称取消所有同步阶段。一般任务计 thinking tokens，agentic 计累计输出含工具参数；超预算覆盖 reward 为 −1，并非已披露 drop 或即时硬终止。GRM 的 verbosity 自动输比较是另一机制。
4. **MOPD/QAT/draft。** p.14 Eq.(15) 的 teacher/student 方向、学生 effort 条件、stop-gradient 和裁剪正确；反向 KL 只在未裁剪等限定下作数学解释。top-k 无明确优势得到保留。QAT 的 routed expert MXFP4/激活 MXFP8与高精度 shared experts 区分正确。Eq.(16) 是接受率负对数；draft 仅更新 draft 层及融合投影，target 冻结，七步展开和 `[0 0 I]` 初始化均正确。
5. **数据、评分与量纲。** kernel 数值错误零分、匹配 expert 性能 0.5、趋近 roofline 趋近1；webdev 构建/运行/伪造零分；AET 最终状态、公开诊断与 hidden 场景分离；个人助理按事件评分均有覆盖。51,219,741 是训练及评测 sandbox 创建总数，1,505,678 是镜像数；133/49 ms 为最低延迟、98% 为等待占生命周期、6.5× 为 workload overcommit，初稿没有换成题量、均值或总节省。
6. **状态与模板。** §5.3 的 write-back、CPU KV pool 释放、NVMe offload、gradient-buffer 非 policy forward未被混成统一持久状态。§5.4 命中需 MLA 与所有 KDA group 具有同一边界，非每512 token必有 checkpoint。附录F的 preserved thinking不等于全历史 token 都进 loss；pure-JSON fallback 是明确 mask 的特例，初稿没有扩张。
7. **评测、图表与负结果。** 表2数值、DeepSWE 67.5/mini-SWE-agent 67.3、Terminal 跨 harness best、H20/Harbor条件、BrowseComp 91.2/90.4、ZeroBench pass@5、Faithfulness 1−幻觉率、Webdev 净胜31.0点已核。图8无数值刻度且有波动；图10单例进度不是总体成功率；图13(b) medium/high/max 黑线属于 Sol；图15含落败点。内部14/36和外部0/41网络安全结果未合并，研究级推理及行为纪律短板保留。
8. **案例与项目映射。** kernel最多24h、nano芯片48h及RTL模拟>8700 tokens/s、MiniTriton L20/梯度参照等口径准确。项目映射窄读了两份状态文档及初稿所引四个符号；主仓 `ce2009f879cf38071d7898a1387e01d4e27741d6`、miles集成 `98a0272e4158b2c20e3a34d210c79b50159af0f6` 均现场核对。fully-async、OPD输入、KEEP_FULL/零方差、consume-time staleness及可信投影的责任划分与初稿相符。没有运行GPU或全仓审计。

## 3. 实际发现与建议

### R1：摘要将 on-policy 简写成“在线”不够准确（轻微，建议修订）

固定初稿第3行称“多教师在线蒸馏”。“在线”主要描述时间/更新方式，不能精确表达由学生当前策略生成监督所用前缀和 token 的采样关系，也不能据此确定教师在线更新。原文 §4.1.3 正式名称为 Multi-Teacher On-Policy Distillation；初稿 §4.4 本身已经解释正确。

建议摘要改成“多教师 on-policy 蒸馏（MOPD；由学生策略采样）”，与正文语义对齐，不改其后公式或继承结论。

### R2：cosine/WSD 比较加入了未披露的“固定硬件”（轻微，建议修订）

固定初稿第292行写“固定硬件/参数分别优化后cosine优于WSD”。原文 §3.2 p.10–11、`tex_v1/3-pre-training.tex` 的条件是固定 minimum learning rate，并强调同模型规模和训练 token 预算下两者最优 peak learning rate、batch size 不同，因此分别做 scaling-law search。该段未给硬件控制条件。“参数分别优化”也应明确为超参数，以免混成网络权重。

建议改为“在相同模型规模与训练 token 预算、固定最低学习率并分别搜索各自最优峰值学习率和 batch size 的比较中，作者观察到 cosine 最终 loss 低于 WSD”。这是预训练观察，不外推为 RL schedule 结论。

### R3：费用图的比较模型标签值得单独保留（证据边界补充，不认定初稿误报）

固定初稿 §8 第298行正确解决了 K3 medium 的误读，但图13(b)另有 `Claude Mythos 5 (max)` 标签，并以1M/3M/10M tokens标三个点；主表2和正文主基线使用 `Claude Fable 5`。证据见 [p.32 原页](../sources/R13/page-32.png)及 `tex_v1/figures/score_cost_charts/browsecomp_score_cost_linear.pdf`，v2沿用同图。

应补一句：费用图包含 Mythos 5/Opus 4.8/Sonnet 5 等标签，不能未经说明把 Mythos 5 曲线换名成主表的 Fable 5。这里可能是图采用了另一比较基线，**现有证据不足以断言作者图错或两名称是同一模型**；无需更改已有 K3费用和medium归属结论，也不必追索无关模型资料。

本审查没有把视觉上难以精读的费用点位当作新的数值冲突；没有发现支撑“成本点抄错”的充分证据。

## 4. 未消除的来源限制

跨迭代行为概率版本、旧权重KV有效性、完整token mask与loss reduction、MOPD teacher刷新/冻结和tokenizer接口、SWE数据漏斗/污染筛选、总训练成本及组件等预算消融仍无法从已查全文恢复。初稿将它们明确列为缺口，没有用常见框架默认值补全。附录B–E审查深度为理解推导及核对笔记概述，不是对每项数学证明另作形式化验证。

## 5. 作者修订处置（由主作者收到审查后追加）

审查交付时：R1、R2待作者修订；R3待作者选择补充或说明不采纳。本审查者尚未声称修订已落正文。主作者应在此逐项记录实际处置、日期与证据；无需重写固定初稿。

### 2026-09-07 作者处置与交付核验

主作者在收到完整审查文件及审查者完成确认后修订正式正文，固定初稿未变。三项均采纳：

| 发现 | 处置 | 定点依据 |
| --- | --- | --- |
| R1 | 摘要改为“多教师 on-policy 蒸馏（MOPD；由学生策略采样）” | K3 §4.1.3/Eq.(15)，原公式与下文语义保持 |
| R2 | 删除“固定硬件”，明确同模型规模/训练token预算、固定最低LR，独立搜索peak LR/batch | §3.2 p.10–11，`tex_v1/3-pre-training.tex`；同时说明未给硬件控制条件 |
| R3 | §8追加Mythos5图标签、1M/3M/10M点及Fable5正文的身份边界，不判同名或作者错误 | 图13(b) p.32，v2沿用同图 |

审查者另指出原PDF链接在隔离worktree缺目标文件。该链接 `../../pdfs/k3_tech_report.pdf` 对最终主资料发布位置正确，主目录的原PDF已实际确认存在；无需把本地报告链接替换成不同文件身份的arXiv v1。发布核验按最终主目录位置检查。固定初稿归档的内部相对链接继续按正式笔记基目录解释，未为链接重排篡改被审版本。

以上是主作者修订与回源核验，不冒称审查者做过第二轮全文复审。残余未披露项沿用§4。

发布后核验：2026-09-07 已把正式笔记、审查及专属 `sources/R13/` 复制回主资料目录同相对位置；共113文件逐字节对照一致。正式笔记与审查共23个本地文件引用在最终位置均存在，导航6个锚点齐全，数学块开闭配对，无本机绝对路径；新增正文/审查的whitespace检查无诊断。未修改共享README、SOURCE_CATALOG、其他任务笔记或代码；未commit/push、训练、租GPU或下载权重。
