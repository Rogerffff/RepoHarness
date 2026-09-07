# 任务 09：R4 / N10 独立全文审查

审查日期：2026-09-07。结论：两份固定初稿已覆盖全部后训练正文及技术图表，未发现整块主题遗漏或重大算法、数字错误。发现一处把停止条件扩大为淘汰条件的事实表述，另有两处低优先级的来源归属/流程表达建议。以下 §1–4 保留独立审查发现；§5 记录主作者收到报告后的实际修订。

## 1. 身份、版本与边界

- 主任务 ID：`01a07827-1e44-7133-85d7-658445c04597`。
- 审查任务 ID：`01a07831-76f5-7ae1-8211-2dc348e68bbd`；canonical agent name：`/root/review_r4_n10`。子任务 ID、父子关系及实际 `gpt-6-astra / high` 由主作者根据会话日志 `SubAgentActivity/session_meta/turn_context` 核验后回传；不是从继承的环境变量猜测。主任务实际配置同为 `gpt-6-astra / high`，由派发方核验。
- 本审查从干净上下文接受原文与文档入口；先读取原文目录、全文与图表，再对照固定稿。没有再委派子代理。
- R4：`arXiv:2605.26494v1`，2026-05-26，35 页；另核 `v2`，2026-07-30，35 页。读取两版官方 TeX、PDF 提取文本及版本差异，并复用原页渲染。页码按 PDF 物理页，p.2 起与印刷页一致。
- N10：[官方 Forge 文章](https://huggingface.co/blog/MiniMax-AI/forge-scalable-agent-rl-framework-and-algorithm)，2026-09-07 固定 HTML/文本及五张图；页面日期 2026-02-13，JSON-LD `datePublished/dateCreated=2026-02-13T04:18:07.300Z`、`dateModified=2026-02-13T08:46:39.885Z` 已核。
- 被审固定稿：[R4 初稿](../sources/R4/R4_minimax_m2_series.draft-20260907.md)、[N10 初稿](../sources/N10/N10_minimax_forge.draft-20260907.md)，日期均为 2026-09-07。文中行号均指这两份固定稿；其内部链接以正式文件所在的 reading_notes 根目录为基准，未将归档副本的相对位置误判为正文链接错误。
- 公共要求、模板及第一批质量复查均已读取；项目窄查主仓 HEAD `ce2009f879cf38071d7898a1387e01d4e27741d6`，miles 集成 HEAD `98a0272e4158b2c20e3a34d210c79b50159af0f6`，实际 `git rev-parse` 与指定值一致。
- 仅写本审查文件；未改正文、来源或代码，未运行训练或声称复现实验。

## 2. 从原文独立建立的覆盖结论

| 来源范围 | 独立核查内容 | 对照结论 |
|---|---|---|
| R4 摘要、§1–3 | 架构与预训练概要；完整阅读影响后训练的 hybrid SWA 负结果、MTP 复制初始化/短暂冻结/联合训练；Tables 1–3、Figs.1–2 | R4 §2、§7.2–7.3 覆盖，未把小规模架构消融充作 M2 RL 消融 |
| R4 §4.1 全部三分支、Fig.3 | SWE 六阶段与任务类型；AppDev 专家 query/prompt distillation/AaaV；Terminal-Gym 来源、四档筛选、三阶段合成与难度校准 | R4 §3 覆盖；仅重试上限之后的处置表述需收紧，见 F1 |
| R4 §4.2 全部四领域 | 搜索证据与开放报告 rubric、GDPval office 合成、金融工具反推、workbook walk/重算验值、幻灯片生成与编辑/视觉验收；共同 teacher/scaffold 扰动及双轴 pairwise 筛选 | R4 §4.1 覆盖，已保留 GDPval seed 与评测独立性缺口 |
| R4 §4.3–4.5、§5 | 推理 query/response/compute allocation 与四层质量检查；长 CoT 写作/QA/多轮与有无工具；persona、self-play、Best-of-N、RLHF 去偏/entropy；SFT rejection sampling 与 interleaving | R4 §2、§4、§5 覆盖；没有遗漏非 SWE 后训练，也没有补造完整安全训练配方 |
| R4 §6.1、Eqs.1–7 | 请求级 action/state、episode 信用分配、CISPO 分母与 stop-gradient、baseline/奖励、四域分阶段混训 | R4 §5 覆盖；token/step 索引、mask、baseline、折扣和实现缺口保留充分 |
| R4 §6.2、Eq.8、Figs.4–6 | 三层系统、黑白盒、消费调度、前缀树、MTP top-K KL、PD 分离、L3 cache | R4 §6 覆盖；两处小建议见 F2–F3 |
| R4 §7、Eqs.9–10、Figs.7–8 | thinking 持久化及 stripping 语句歧义；人类主导决策、自演化 harness 与内部 100 轮案例 | R4 §5.4、§7.4 覆盖，没有把 scaffold 编辑说成新自更新 loss |
| R4 §8–9、Table 4、Figs.9–10 | 五块全部评测与预算、23 行主结果、十一项系列曲线、MLE 三次 trial 和曲线口径；结论 | R4 §7–8 覆盖，包括负结果与跨 scaffold 例外 |
| R4 References、Appendix A | 查阅目录/引用用途和附录全文；两版附录都只有贡献者名单 | 无隐藏技术附录遗漏；v2 技术内容未增删 |
| N10 引言、§1–2.3、arch/black_rl | 三目标、token 一致性、长尾、CM、黑盒实例、规模与曲线 | N10 §2–3、§7 覆盖 |
| N10 §3.1–3.3、window/tree_merge | 窗口范围、队头推进和图中 lag；前缀共享与还原；三项推理优化 | N10 §4–5 覆盖，正确指出窗外索引措辞缺口 |
| N10 §4.1–5 | 三域混训、完整 CISPO HTML TeX、speed/perf 与 process 的文字/公式缺口、结论 | N10 §6–7 覆盖，没有用后来的 R4 填成早期公开事实 |
| N10 HTML/其余资产 | 封面及四张技术图均目视；核全部技术标题、math 块中的原始 TeX、图片入口与交互元素 | 未发现正文 tabs/details/select/iframe/video 或隐藏动态技术案例；评论与推荐不是额外方法附录 |

R4 十幅图全部目视；Tables 1、3、4 与关键 RL 公式回原页，Table 2 对照官方 TeX 与 PDF 文本。两版逐文件比较只发现 `app.tex` 不同；PDF 文本增量只在版本水印与贡献者名单，技术图资产相同。初次合并读取出现截断后，已分文件补读，不以截断结果冒充全文。

## 3. 关键核验

1. **算法与分母。** R4 p.17 Eqs.2–3、N10 §4.1 都是组内输出长度总和作分母，clipped IS 权重 stop-gradient 后乘 advantage 和 log-prob；不等于每轨迹均权平均，也不是 PPO 的 clipped surrogate。R4 p.18 Eq.4 的 baseline 未定义成 GRPO group mean/std。初稿均正确保留这些区别。
2. **奖励与 mask。** R4 Eq.4 无折扣、Eq.6 含 γ，N10 优势式只有 speed+perf 而正文另提 process；初稿未替作者补齐。请求级样本与轨迹公式之间、reward step 到 token、thinking/tool/CM masks、失败组统计和梯度/补采均无完整实现披露，初稿没有冒称已知。
3. **模型与数据关系。** 轮换 teacher 轨迹、AppDev 删除部分生成指导的 prompt distillation、MTP draft top-K KL 是不同机制；没有多 policy experts 合并或领域 OPD 的证据。R4 明确每阶段内混四域，N10 仅介绍 reasoning/general QA/agent unified training，初稿未混成同一版本训练配方。
4. **调度与加速。** W 限制训练消费原始派发队列中的完成轨迹，G 是每题 rollout 数，二者不能混用；图 N=8/W=4 的 lag=10 缺少 optimizer/发布映射。40× 缺硬件/workload/端到端分母，N10 原词 40× 与 R4 up to 40× 已区分。两稿正确把训练前缀计算复用与 loss 权重保持分开。
5. **评测与退化。** Table 4 全部 M2.5/M2.7 数字核对无误；MMLU-Pro 85.2→81.8 为下降。SWE 的 GPT-5.4 使用 CodeX、其余 Claude Code；Terminal-Bench 的 8 vCPU/16 GB/2h/四次及官方 baseline 引用；搜索超过 30% context 删除全部 assistant/tool 历史；无工具通用七项与 AIME 2025/2026 区分均已保留。
6. **MLE 和自演化。** 每题一张 A30、24h、22 题、三次 trial；最佳 run 15 枚奖牌与三次平均 66.6% 不能混为同一统计量。Fig.10 红色 CV-selected 与蓝色 any medal、超过 24h 的横轴未对齐正文，初稿已明确。30%–50% 日常工作量、内部 100 轮/30% gain 也没有被扩写成模型训练算力节省或 +30 个百分点。
7. **全域与负结果。** SWE code review 无 runnable 环境的例外、AppDev execution 硬门槛、GDPval 种子、非机器可验的比较/视觉信号、persona RLHF 均覆盖。SWA 短任务反例与 MTP 表中 MMLU 小幅下降也保留；没有用作者“全面提升”的总结覆盖负项。
8. **项目责任。** 窄读 `reference/miles-rh2-integration/miles/rollout/fully_async_data_buffer.py::DefaultDataBuffer` 的 put/get、`fully_async_rollout.py::FullyAsyncRolloutFn` 的生产循环，以及主仓 capture/canonicalize 入口：确为完成入池顺序 FIFO、put ABORTED/dynamic filter、get consume-time staleness，并非 Forge 窗口。当前简报及 2026-09-07 建议支持先测消费偏差、不先新造 scheduler；笔记未把上游能力据为原创或批准新训练语义。

## 4. 实际发现与建议

### F1 — 需修订：达到 terminal 合成重试上限不等于已披露淘汰

- **定位**：R4 固定稿第 105 行，§3.4「已知失败淘汰」中的「terminal 合成超重试限制」。
- **证据**：R4 §4.1.3 p.12，官方 `tex/section/post_training_data.tex` 第 104 行，Stage 1 仅说失败后迭代修复，直到测试通过或达到最大重试限制。没有说明达到上限后的保留、隔离、丢弃或人工处理。
- **影响**：正文 §3.3 已正确区分环境合成重试与 RL rollout；汇总表却把停止条件升级为明确数据淘汰条件，容易被误用为数据漏斗语义。
- **建议**：从「已知失败淘汰」中移出这一项，改为「环境合成达到重试上限会停止修复；后续处置未披露」。其他明确过滤条件继续保留。

### F2 — 低优先级：明确 sample efficiency 解释来自 N10 或阅读者释义

- **定位**：R4 固定稿第 193 行，§6.1「后者是每样本带来的平均表现提升」。
- **证据**：R4 §6.2.1 p.19–20 / Eq.8 使用 `SampleEfficiency` 名称，详细定义了 throughput，但未给该句样本效率定义；N10 §1 明确写平均每样本的性能提升，并列数据分布、质量、算法和 off-policy 程度。
- **判断**：含义合理，非算法错误；问题是该句只引 R4，且来源节强调不混入早期博客细节。
- **建议**：注明「术语解释见 N10 §1」或标为阅读者解释；也可直接略去这句释义，只保留 R4 的概念目标与非收敛定理边界。

### F3 — 低优先级：把架构分层箭头改为真实请求与训练两条流

- **定位**：R4 固定稿第 195 行，§6.1「Agent Side…→Gateway…、Data Pool…→Rollout Engine 生成，Train Engine…」。
- **证据**：R4 Fig.4 p.20 及 §6.2.2：请求经 Gateway 往返 Rollout Engine；Gateway 将数据送 Data Pool，Train Engine 从池消费并向 Rollout Engine 同步权重。没有 Data Pool→Rollout Engine 的生成链。
- **判断**：上下文可能只是列三层，N10 §3.1 已写清；但连续箭头会被自然读成执行顺序。
- **建议**：用两句区分「Agent↔Gateway↔Rollout Engine」与「Gateway→Data Pool→Train Engine；Train Engine→Rollout Engine 同步权重」，避免把分层排布误写成单条时序。

N10 未发现必须修订的事实错误。两份稿的其他未知项，经所列全文/图表范围核查，均未发现原文已披露却被写成未知的关键训练配置。此结论不等于已审计 Forge 内部实现或所有链接资产。

## 5. 主作者处理记录

主作者于 2026-09-07 收到完整审查后执行修订，交审固定副本保持不变。

| 发现 | 处理与修订证据 |
|---|---|
| F1 | 采用。R4 §3.4 的明确淘汰项移除 terminal 重试上限，另列「环境合成停止」，写明达到上限停止修复、后续处置未披露。回读 §4.1.3 p.12，未添加任何 discard/quarantine 规则。 |
| F2 | 采用。R4 §6.1 明确 R4 只使用 SampleEfficiency 名称；平均每样本表现提升的释义单独标来自 N10 §1，不计入 R4 单独披露。 |
| F3 | 采用。R4 §6.1 改为 Agent↔Gateway↔Rollout Engine 的请求流、Gateway→Data Pool→Train Engine 的训练流及 Train Engine→Rollout Engine 权重同步；与 Fig.4 p.20 分开对应。 |

N10 无必须修订的事实错误，仅补独立审查结果/身份记录。两稿仍保留未知训练配置与 MLE 图文口径、stripping 语句歧义、奖励公式缺口等，未把「审查完成」写成实验复现或来源永久无误。同一审查者的定点复核已完成，见 §6；发布验证另记于 §7。

## 6. 同一审查者定点复核

2026-09-07，审查者 `01a07831-76f5-7ae1-8211-2dc348e68bbd`（`/root/review_r4_n10`，实际 `gpt-6-astra / high`）应主作者请求复核 F1–F3。检查正式 R4 §3.4/§6.1、正式稿相对固定初稿的完整 diff，以及本报告 §5；回读 R4 §4.1.3 Stage 1、§6.2.1–6.2.2 官方 TeX、Fig.4 p.20 原页及 N10 §1 定义。

| 项目 | 复核结果 |
|---|---|
| F1 | 已准确落实：明确淘汰栏移除重试上限，另列环境合成停止；后续处置仍标未披露，没有新增 discard/quarantine 规则。 |
| F2 | 已准确落实：平均每样本提升的释义明确归属 N10 §1，并说明不是 R4 单独披露；保留概念目标而非收敛定理的限定。 |
| F3 | 已准确落实：请求、训练消费、权重同步三条方向与 Fig.4 和正文一致，已消除 Data Pool 后才生成的误读。 |

R4 相对固定初稿仅有上述三项和审查状态更新；N10 的完整 diff 仅显示末节审查状态更新，没有事实内容改动。三项发现均可关闭，本次未发现修订引入的新问题。本次是定点复核，不是第二轮全文重审；原报告的证据边界与来源未解问题继续有效。审查者仅追加本节，未改两份正文或固定初稿。


## 7. 发布与结构核验

2026-09-07，主作者在独立全文审查、F1–F3 修订及同一审查者定点复核完成后，将 `R4_minimax_m2_series.md`、`N10_minimax_forge.md`、`reviews/09_R4_N10_review.md` 及 `sources/R4`、`sources/N10` 专属附件复制到主资料库相同相对路径。来源附件共95个文件，包含原PDF/HTML/TeX、必要图表和固定初稿；没有修改共享索引、其他任务笔记或训练代码。

发布位置的两份笔记、审查和两份 SOURCE 说明共5份文档、28个本地文件链接均可解析；未含本机绝对路径，正文导航锚点有效。已逐文件比较发布副本与 worktree 专属成品及全部95个来源附件，内容一致。正文无尾随空白，限定路径的 `git diff --check` 无报错；因这些文档为新文件，另用逐行检查补足未跟踪文件的空白检查。未运行训练、下载权重、提交或推送 Git。

结构核验不验证远端链接永久可用，也不构成论文实验复现。任务09精读与独立审查/修订已完成，来源未披露和图文未解口径仍以两篇正文为准。
