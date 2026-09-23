# A：链路正确性与运行效率

更新：2026-09-09。状态：I01 首版 B 已实施、已提交 `297f1f59`；[Codex 修后针对性复核](i01_b_impl_20260909/codex_review.md#7-修复后的针对性复核2026-09-09)通过，R1/R2 已关闭，运输测试已补齐，本批无未解决的阻塞 finding；C 暂缓，目标 GPU 验证仍待原定 spike。I02–I36 按 [七组决策清单](decision_batches_20260908.md)推进；[第一组预算与截断](batch1_budget_20260908/README.md)三项原则已确认：turn 控制行动机会，较宽墙钟只作强制终止保护；正常 turn 截断保留真实评分，墙钟超时整组不训练。预算数值未定；预算实现与审查状态见下一段。I13 退出语义窄改判于 09-09 确认，待实施。当前工作分支：`miles-migration`。共同边界见 [执行入口](README.md)，对方进展见 [B](env_data_eval.md)。

当前进展：[I15/I16 重评分条件](batch2_failures_20260908/i15_i16_sampling_and_retry_20260909.md#8-重评分条件的具体边界2026-09-09-后续讨论)已于 09-09 获用户完整确认：仅测试前镜像就绪/获取与新 grader 创建/启动中的已识别可重试服务/传输故障，同工件最多追加一次，共享有界总预算且先收口旧工作。I13、首版完整组＋原因观测同样已批，实现待办。用户基本同意 Claude 实施已定项与本任务继续决策并行；Codex 已复核其建议，补充[可开工范围、代码区域与测试 oracle](decision_batches_20260908.md#41-直接准备实施的明确部分)及[实施节奏建议](decision_batches_20260908.md#7-现在怎样开工2026-09-09供-claude-编写当批计划)。预算批 A `6bb5ffe4` 沿用通过；批 B `510c9b23` 修后针对性复核通过，D-1 `756b8fd6` 通过。C `34531b74`、D-2 `5c8fa4f7` 已提交但待修：[Codex 联合审查](budget_loop_impl_20260909/combined_review_20260909/README.md)确认四项 P1，另有一项限定取消/关停接缝的 P2。六项明确保留分支未新增批准。

## 1. 目标与范围

负责让当前 miles + SGLang + 真实 coding harness + rh2 链路正确、可诊断、可运行，并为后续性能实验提供基线。包括主动发现遗漏、核实已有 finding、准备决策与修法、协调实现和独立审查，以及验证实际训练消费。

范围不局限于旧报告列举的问题，也不把报告中的所有严重度和删除建议直接当成实施结论。先用当前代码和生产路径复核；区分已确认错误、待决设计、已知未完成入口、误报及需要 GPU 验证的假设。

## 2. 首轮阅读与交付

先读 [当前简报](../CURRENT-STATE-BRIEF.md)、[06 计划](../06-first-training-local-execution-plan.md)、[D2/B 定案](../miles_spike/decision_package_D2_B.md)，再对照以下审查：

- [Codex 原审查](../miles_spike/external_infra_review_20260905.md)。
- [Claude 总报告](../tmp/external_review_20260905/00_FINAL_REVIEW.md)及其切片。
- [Codex 对 Claude 的交叉复核](../miles_spike/external_infra_review_crosscheck_20260906.md)：包含真实遗漏和对部分方案的纠正，不可省略。

首轮产出一个紧凑的处理表：问题/当前证据、是否近期影响运行、修复或递延理由、既有授权或需决定的部分、验证方式。复用已有复现，不为已经清楚的问题重建庞大审查体系。高风险审查的独立角色要求按 [审查标准](../review-standards.md)执行。

同时告知 B：当前可用于基座诊断的真实执行入口是什么、已知限制是什么、需要 B 提供哪些任务与评分反例。不要等全部训练修复完成才交付诊断入口。

## 3. 优先检查的主题

1. 生成动作与实际训练覆盖：REALIGN、消息改写、分支、共享前缀计权、token/logprob/版本来源；不只证明剩余 token 对齐。
2. 终止与失败：多重预算、排队 deadline、截断策略注入、内部错误被补采隐藏、实际退出与清理；具体任务归因与 B 联合验证。
3. 训练消费：member/组身份、reward 与 advantage、mask 与分母、sampling support、MoE replay、消费时版本和目标 GPU 路径。
4. Eval 和作业接线：W8 结果真正完成且绑定准确 checkpoint，W7 的启动、测量、结果解释，以及最小恢复。
5. 性能与维护：先测同步处理、重复准备、重复 forward、排队与资源占用，再选有证据的优化；删除无用机制时保留真实语义和必要诊断。

这些是调查主题，不代表已经批准特定修法、新的过滤规则或大规模删除。具体任务 parser、题目质量与评测分布由 B 主责；通用 runtime/评分运输的实际改动由双方按批次确定唯一修改者。

## 4. 近期交接需求

以下是分叉前列出的需求，尚未构成对方承诺：

- 需要 B 给出代表性开发题、实际 parser/测试命令、参考修复与失败样例，以及资源需求。
- 交付给 B 的最小结果：可调用执行入口、模型接入方式、输出/错误含义、已验证范围及版本。
- 两边联合准备一次窄端到端作业。GPU 的训练资格检查归 A，基座能力诊断归 B，资源安排合并。

## 5. 当前进度

- 2026-09-07：主会话创建分叉准备文件；本文件没有记录任何新增代码修复、基座测试或 GPU 结果。
- 2026-09-08：合并 Codex 原审查、交叉复核与 Claude 七份切片，纳入 Claude 09-07 勘误。完成 [36 个主题的问题导读及旧 ID 映射](issue_inventory_20260908/README.md)，覆盖 Claude 96 个编号条目；这不是 96 个独立已确认 bug，也不表示批准原删除方案。
- 本轮将远端文档从 `5b6e1262` 快进至 `17d9899c6d4b61938f74bd9121da8dee9b621a8d`，补回六份正文、六份作者自查。保留原有 index/catalog/manifest 修改。`rh2` 跟踪源码与原审查基线相比无变化；miles 集成仍为 `98a0272e4158b2c20e3a34d210c79b50159af0f6`。
- 收尾时共享目录另已同步至 `ac0e2e64163fbe49411540e901df439aea16b6b0`，追加 R5c GLM-5.3 预读与自查。该文原博客全文仍未取得，不能计入完成精读；源码再次核对未变。
- 主审重跑四个已有轻量 CPU 探针，均退出 0，再次复现 token 覆盖、deadline 排队、评分归因歧义、singleton accepted≠梯度等现状。没有训练实现/配置/标准测试改动，没有 Docker/GPU 作业，也没有提交或推送本轮文档。
- I01 补充核查了此前漏查的 miles 进程内 TITO；已完成单条 run8 成本重放、真实 Qwen tokenizer/matcher 与消息树反例。见 [补充讨论](i01_options_20260908/miles_tito_followup.md)。训练分段方案与未来 thinking 保留策略分别待定。

## 6. 用户决定

- 2026-09-09 最新消息“同意，后续决策我也会交给claude来检查”：确认上一轮 I16 §8 的具体阶段/类别与边界，次数和范围均已批，不再次询问；用户同时基本同意并行流水线实施，要求先检查 Claude 建议，优先启动已决/无需新决定/纯观测且少受后续决定影响的工作，由 Claude 编写计划并实现。没有因此批准 Claude 原稿中的所有节奏细则，也没有批准所有后续语义、整仓重构或资源作业。
- 2026-09-09 后续批注，用户确认 I15 首版继续完整组、完善监控以暴露具体原因后修复，并将可变组外部资料调查留后续；确认 I16“符合条件的评分基础设施失败，最多追加一次同工件评分”的方向，追问符合哪些条件是否需要决策。故次数与窄方向已批，具体允许阶段/类别表仍在确认；不能写成重评分已全面批准/实现，也不能再次索取相同方向的许可。详见补充说明 §8。
- 2026-09-09，用户批注确认 I13 推荐，原话：“我同意你的建议，这里最后退出对于训练来说影响不大，记录好诊断即可。”据此登记中间等待超时的窄改判；其它真实失败、未知残留、必要记录失败与最终期限要求保持。已补充 B-6 和 06 改判记录，实施未完成。同条消息要求详细解释 I15/I16，并未批准新重试、可变组或 staleness 规则；当前提出的有限重评分仍是候选。
- 2026-09-08，用户在第一组说明的三条批注中确认：保留 turn 和资源墙钟，不提前决定预算数值；正常 turn 截断保留，正常进入后续流程；turn 作为资源/行动机会预算，墙钟只作较宽强制终止保护，墙钟超时整组不训练。依此补充 06 A5；不扩展为所有未来 horizon producer 或安全分支都已批准。用户关于“超时通常可认为 infra”的判断，Codex 补充：处置可以排除，但原因不能仅靠超时推定。该归因建议与用户批准的训练处置分别记录，见 [第一组 §7](batch1_budget_20260908/README.md#7-外部参考支持哪些判断不支持哪些推断)。
- 2026-09-08，I01 后续消息原话：“I01可以确定B 作为首版路线，C 暂缓，不排专门的 B/C 对比实验。”据此确定精确前缀合并、漂移保留旧行的 B 路线；现有阈值 0 作为接入办法，保持原推理上下文及 execution/member 计权。复用本机证据，真实后端验证并入原定 spike。**方案已定不等于实现完成**；I18/I19 和其它预算/准入语义未因此批准。用户同时要求加快 I02–I36 的讨论，授权整理合并议题与快速确认项；具体后续语义仍分别登记。
- 2026-09-08，用户启动 A 后要求：先完整展示旧问题，解释位置、原因和例子；后续逐项讨论处理。授权拉回远端新阅读材料、按相关性参考。本轮据此做调查与说明，**没有把“准备处理全部问题”解释成已经批准全部具体修法、删除或语义改变**。
- 其它已有技术决定继续以 06 计划、D2/B 与相应原始记录为准；仅按本节逐条登记的范围改判，不扩展到未决定的安全、恢复、数据或重试语义。

## 7. 实施、验证与交流记录

后续按需追加。每条只需写清日期/记录人、事实和证据、决定或建议、对 B 的影响、下一步；与 Claude/Pro 的分歧记录来源和处置。实现与独立审查身份应如实注明。

### 2026-09-08：首轮问题说明 / Codex

- **证据产物**：[完整导读](issue_inventory_20260908/README.md)、[Production Tracer](issue_inventory_20260908/runtime_tracer.md)、[Falsifier](issue_inventory_20260908/claims_falsifier.md)、[性能与相关阅读](issue_inventory_20260908/performance_and_sources.md)。主审整合并复跑轻量证据；独立角色只核旧主张，没有并行修改实现。
- **实质纠正**：训练覆盖缺口不等于所有多轮都丢首轮；空解析/测试超时不能一律记 0；zero-signal 阈值已配 8；在线 logprob_compare 已有；晚清理仍失败是已批 verdict 行为；seen fallback 在正常 formal producer 的空分支未证可达；恢复 p−1 按 B-3 执行，显式 start 与 loaded checkpoint 错配另列条件风险。
- **暂定讨论顺序**：I01 动作覆盖先行；I18 路由来源、I19 历史压缩作为相邻语义边界。随后预算/异常/receipt、联合评分归因、损耗与有效更新观测、W8/W7、实测性能与窄清理。此顺序是建议，不是实施批准单。
- **留给 B 的交接需求**：I06–11 需具体任务 parser/命令、参考与错误修复、空补丁、环境失败/超时/OOM 反例、允许修改路径；A 提供运行/投影/退出资源事实并联合决定分类。还没有向 B 发送消息或代表 B 接受承诺，也没有宣称已有统一可用的 formal eval 入口。
- **相关阅读**：定点消费 RollArt、Polar、SAO、Agent Lightning、CompactionRL、Harness Interplay 与 Hardening 笔记；保留作者自查/待独立复核状态，没有把外部性能倍数作为本项目实测或直接需求。

### 2026-09-08：I01 的 1024、GRPO 与替代表示 / Codex

- **用户要求**：阅读侧边栏讨论，解释新输出 1024 条件与最初动机；调查 verifiers/Prime RL、verl、Polar 等，比较维持现状加监控与 token 追加，并考虑 subagent/压缩。用户明确尚未决定设计。
- **证据产物**：[讨论正文](i01_options_20260908/README.md)、[Production Tracer](i01_options_20260908/slime_tracer.md)、[Falsifier](i01_options_20260908/alternatives_falsifier.md)。双角色按现有审查标准承担窄边界核对；没有并行修改实现。
- **实质补充**：上游历史有新输出阈值的代码统一理由与早期 20 题 rewrite 观测，但没有当前 REALIGN/1024 的学习质量消融。最终 reward 不能补回被全面 mask 的旧动作直接策略项；保留 output IDs 也不能自动证明后续动作的条件前缀正确。已纠正旧库存把 token FORK 的两条 Sample 称作两条消息树叶的用词。
- **候选建议**：先评估保持真实推理输入、精确前缀成立才合并、漂移则保留旧行并开新行。vendor 参数 0 能关闭 REALIGN 与 rewrite merge，RH2 bringup 尚未暴露传参；这不是已完成的生产修复。重复前缀成本测出后再决定是否做在线追加。
- **验证**：真实 vendor manager＋身份导出＋backfill 共 8 个 CPU 小例子，主审独立重跑 exit 0；另外执行终局奖励数学例子与固定 Polar builder 的条件前缀反例。没有 GPU/Docker 或正式训练，没有扩充标准测试套件，没有更改训练源码/配置/依赖，没有提交或推送。
- **边界与交接**：I18 MoE 路由来源、I19 历史压缩仍需单独决定；没有把参考框架的支持面直接当成 RH2 的能力。未向 B/Claude/Pro 发送消息，也没有新增对方承诺。后续可与 B 合选少量真实任务收集请求，再对同批 capture 重放两种表示，比较动作覆盖与成本。

### 2026-09-08：回应 Claude 的 miles TITO 建议 / Codex

- **用户要求**：核实 [Claude 建议](tmp/问题1claude_adv.md) 指出的上游可复用组件，评估 B 的训练成本、B/C 对 SGLang 的影响、Qwen TITO 匹配可靠性及 thinking 保留的行为影响；用户仍未选方案。
- **遗漏与纠正**：上一轮确实漏查了已选 miles 基座的进程内 TITO，C 不需要新服务。但“首训前必须 C”“B 约 k+1 倍 GPU 成本”“token 连续自然解决 I18”均无充分证据。现有 strict/loose 不容忍非空 thinking 消失，RH2 dict 参数只换键序连 strict 也匹配。
- **证据产物**：[补充正文](i01_options_20260908/miles_tito_followup.md)、[Production Tracer](i01_options_20260908/miles_c_production_tracer.md)、[Falsifier](i01_options_20260908/miles_c_falsifier.md)。run8 六轮只有一个边界漂移；B 的训练行由 1 变 2，总输入 token 从 26,283 变 45,415，动作覆盖从 2,148 恢复为 2,772。这是无截断 token builder 重放，不是完整 producer 或 GPU 计时。
- **新边界**：真实 Qwen tokenizer 的 10 组匹配、8 个 merge 场景说明普通追加有复用基础，但没有 CLI 端到端成功声明。另一个真实 manager 合成反例说明：若未来容忍 thinking 省略，只修 token 连续仍可能被消息树 rewrite 清掉旧动作。C 需对齐检查点提交、分支归属、下游消息树与分段退路；不要求重造 session 服务。
- **建议与未定**：训练必须保存已发生动作的实际输入条件；未来是否继续保留全部 thinking 则是独立上下文策略。B 可作参照和未匹配时的保留办法，C 可先消除受控表示漂移。优先补真实请求证据，再决定上下文策略与性能取舍；不直接把“容忍所有 thinking 省略”当默认。原始 capture 完整时可恢复 B 表示，不能恢复改变输入后 C 本应采样的新轨迹。
- **验证与交流**：主审独立重跑两份子审探针并运行 run8 重放，均 exit 0；未改训练源码/配置/依赖，未跑 GPU/Docker 或标准测试套件，未提交或推送。未向 B/Claude/Pro 发送消息。后续真实任务请求与基座测评上下文需和 B 对齐；尚无新增跨线程承诺。

### 2026-09-08：I01 直接选择 B 的可行性 / Codex

- **续问与建议**：用户询问能否省去 B/C 实验直接选 B。可以；当前建议 B 作为首版处理路线，C 暂缓。此前列出的 C 对比实验是可选评估路径，不是选 B 的前置条件。本次询问未记录为正式批准，未改实现。
- **验证分层**：本机复用已完成的 token/manager/identity/backfill 探针，后续只补 B 的真实 bringup 与训练消费接入验证；实际目标模型 forward/backward、packing、显存和耗时并入原定 GPU spike。无需为 I01 单独租卡或先实现 C；小模型/缩小拓扑也不能替代最终目标链验证。
- **依据与边界**：Agent Lightning、verifiers/Prime RL 提供更直接的精确前缀分段参照，不能把 Polar 已核 builder 笼统视作同一实现。B 保留原推理上下文并减少本次变更范围，重复计算作为已知成本观测；明显成为瓶颈后再优先评估 C。详见 [补充稿 §10](i01_options_20260908/miles_tito_followup.md#10-续问能否直接选-b省去比较实验)。

### 2026-09-08：I01 定案与加快后续讨论 / Codex

- 已将用户选择 B、暂缓 C、不排专门 B/C 实验写入 §6；I01 为方案已定、实现待办，更新原问题索引与讨论稿的状态。
- 产出 [七组决策与快速处理清单](decision_batches_20260908.md)，覆盖 I02–I36 全部 35 项。区分已定规则的落实、批量快速确认、真正 T0 与运行后再排的优化，不将一个主题的小修当成整项关闭。
- 每轮只展开两三个实质决定，用既有证据与一个具体例子说明；已有 T1/T2 不反复请求确认。没有修改协作协议、角色分工或强制审查要求；未向 B/Claude/Pro 发送消息，未代 B 承诺任务材料。
- 本轮仅改决策文档，没有训练实现/配置/依赖修改，没有运行 GPU/Docker，也没有提交或推送。

### 2026-09-08：第一组预算、截断与停止 / Codex

- **用户要求**：进入第一组，用例子说明 I02/I03/I04/I14 及需要选择的内容；没有新增修法批准。
- **交付**：[第一组说明与三行决策表](batch1_budget_20260908/README.md)、[真实调用链](batch1_budget_20260908/tracer.md)、[反证与取舍](batch1_budget_20260908/falsifier.md)。复用已有 cap/排队证据，仅针对当前停止边界做一对窄核查。
- **待决推荐**：保留共享请求次数上限与资源墙钟；完整可信的确定性策略预算截断 KEEP_FULL；混合 hard wall 截断先 DROP_GROUP。均未获本轮批准。KEEP 用真实评分而非强制 0；DROP 按现有 n=8 合取丢整组。已归因 OOM/资源故障不纳入 hard-wall KEEP 候选。
- **减少重复决定**：A4 的 scope 最终无法停止 fatal 且仍清理已批；沿用 06 资源占用起表要求，不把起点后移称为简单修 timer。I14 生命周期落实与 I13 综合退出判定分开，后者留第二组。
- **实证边界**：当前 cap 是渲染前放行请求数，失败不退计数；proxy/harness 各自晚起表。通用 proxy 的内部重生成不等于当前 StaticActiveCoordinator 生产接线已经启用。未测真实 CC 对 429 的处理或 deadline 到冻结的实际延迟。
- **验证**：主审窄复跑现有 disposition 与 group-admission 两个测试入口，参数化 6 项通过，见 [输出](batch1_budget_20260908/verification.txt)。使用测试替身，没有 CLI/Docker/GPU 验收声明；未修改训练源码/配置/依赖，未向 B/Claude/Pro 发消息，未提交推送。

### 2026-09-08：第一组用户确认与外部依据 / Codex

- **定案**：按 §6 记录用户三项选择；预算数值未定，没有把“较宽”写成某个新默认。
- **参考核验**：回读 miles 固定基座的 Harbor README、Polar v1 §3.3.2、SkyRL-Agent v1 §4.2。前两者支持 watchdog/停止/记录的工程做法；SkyRL 对 horizon 采用自身梯度 masking，是不同训练取舍，不能声称外部一致支持 KEEP_FULL。
- **意见与边界**：墙钟超时仍按用户要求整组不训练，但不能凭超时认定 infra 故障；保留原始终止原因及已有归因证据。建议用已有观测看 watchdog 触发和丢组损耗，不新建时间归因平台。评测中的超时分母另与 B 对齐，未代表 B 决定。
- **变更范围**：仅同步本留言板、分组说明、第一组决策稿与 06 A5 的窄补充；无训练代码/配置修改，未运行新测试或 GPU/Docker 作业，未提交推送。

### 2026-09-08：第二组收敛为一个新决定 / Codex

- **用户要求**：进入下一组决策；未授权替用户选定新退出语义。
- **交付**：[第二组说明](batch2_failures_20260908/README.md)，覆盖 I05/I12/I13/I15/I16。复用一对角色，只读核错误/退出边界；无新全仓审计或实验队列。
- **减少重复拍板**：06 §2 已规定不可归因/结构性损坏 typed run-fatal，I05 早期未知异常兜底属于落实旧规则；I12 按 A4 继续清理；B-2 完整组 drop、不立即重试、no-progress 不重问。可选 telemetry 与核心记录保持既有区分。
- **唯一新推荐，待批**：I13 仅中间取消等待超时，后续在有界最终期限内确认任务和资源安全结束、必要记录完整且其它原有失败条件均不存在时，可成功退出，保留超时事实。真正残留/未知/总超时/其它原有错误仍失败。这是 B-6 改判，不是普通 bugfix。
- **事实纠正**：默认 900 秒只覆盖 owner-loop 的 aclose＋RH2 close，不覆盖之后原 dispose 全部动作；`cleanup_ok` 也包含早期超时失败，不能直接当最终资源状态。现有 drop 汇总有原因与 task 分母，主要缺根因细分及轮数/token/耗时关联；终局事件分母不含在飞组。
- **验证范围**：回读源码及既有主审探针，rh2 相对 `d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5` 无差异；仅改文档，不重复运行旧测试，不运行 Docker/GPU，未提交推送。

### 2026-09-09：I13 定案与 I15/I16 深入说明 / Codex

- **I13**：按用户确认登记 B-6 窄改判；保留必要诊断与其它失败条件，未改退出代码。
- **交付**：[I15/I16 补充说明](batch2_failures_20260908/i15_i16_sampling_and_retry_20260909.md)。明确可信 reward=0 不是缺员；独立成员损耗经整组规则放大，差异保留率可能改变任务/行为分布，staleness 能排除评分完整的旧组。数字来自数学例子，不是生产测量。
- **建议调整**：不再把“已有不重试决定、先观测”作为唯一建议；提出同一冻结工件遇已识别暂态评分基础设施故障时，最多追加一次评分的窄候选。可信 0/1 不重试、不取最高分；不重新采样模型；不恢复已交付终态；保留预算、停止与版本条件。该 B-2 窄例外仍待用户决定。
- **静态接线**：复用一对窄角色分别核 grader 身份/回调边界与选择偏差。现有 fresh grader/nonce/队列可复用，但 `failed_to_grade` 分类过粗；需明确可重试来源和首次评分确已停止，不能直接包通用 retry。I14 实际停止与第 4 组评分归因仍有关联。
- **验证与边界**：主审回读代码并计算概率表；未改源码/配置，未运行新测试、故障注入或 Docker/GPU，未提交推送。未向 B/Claude/Pro 发送消息或代表 B 接受任务。

### 2026-09-09：完整组与一次重评分方向确认，收窄条件 / Codex

- **已定**：完整组首版保留、补齐原因观测，后续调查可变组；最多一次同工件重评分的窄方向已批。已同步 B-2/06 状态，不打开 miles 通用 retry。
- **待范围确认**：推荐仅镜像就绪/获取与新 grader 创建/启动中的可识别暂态服务/传输故障，候选测试尚未发起；其它准备阶段、测试后的中断和未知/配置/完整性错误不自动重试。已有 fatal、取消/关停、旧工作未收口和总预算约束优先。
- **实施边界**：一次额度由整次评分任务共享，不按阶段翻倍；原工件与行为版本保持，最终只交付一份权威评分。CLI 错误需结合具体操作映射；容器创建回包丢失时，不能从没有 `_ContainerRecord` 推断容器不存在，沿已生成名字和现有 owner 收口。
- **验证**：主审与复用的窄角色只读核条件表与实际错误来源；未做新测试、故障注入、源码/配置变更或 Docker/GPU 作业，未提交推送。后续可变组调查仅登记，不在本轮另开阅读任务。

### 2026-09-09：重评分范围确认与 Claude 实施节奏复核 / Codex

- **批准状态同步**：I16 §8、第二组入口、D2/B-2、06 和本留言板均登记范围已批、实现待办；原讨论保留为历史。未打开模型重采样、可变组或通用 retry。
- **采纳的建议**：在决策清单 §4.1 明列 I01 B 接线、I15/I17/I20 纯观测及其它已决子范围，逐行列代码区域、相关测试与旧→新 oracle；精确测试节点由 Claude 当批计划给出，不为 36 个主题预建完整测试矩阵。已批工作无需等待全部讨论完成。
- **补充与纠正**：accepted/非单例支持集不等于实际非零梯度，DIS 分布复用已有 detached log-ratio 并控制归约/同步成本；cap 记录真实预算终止，不能伪装自然 end_turn。复核按既有比例原则收敛，不能将当前生产可达 P1、修复回归等一律延后；共享路径按具体文件指定修改者，不笼统锁 B 的整个 adapter 工作范围。
- **近期建议**：先 I01 接线＋相关覆盖计数，随后优先预算终止闭环供 B 接入；drop/loss 观测可穿插；I13/I16 依实际清理与错误来源准备后落实。不冻结完整未来批次，不混入 `_generate_attempt` 大拆分、未决 reward/I18/I19 语义或 I24 配方优化。Claude 原稿没有给出具体批次表，本轮审的是原则与当前可开工范围。
- **边界与验证**：本轮仅维护六份 A 决策/交接文档，核对所列代码与测试入口。未修改训练源码、配置、测试或 B 文档，未运行 Docker/GPU/训练作业，未向 Claude/B 发送消息，未提交或推送。文档差异和本地链接检查见本轮工具输出；实现正确性由后续实际修改验证，不以文档更新宣称通过。

### 2026-09-09：I01 B 实施聚焦审查 / Codex

- **范围与结论**：[审查正文与窄修验收](i01_b_impl_20260909/codex_review.md)。核未提交的三源文件与两测试；Production Tracer、Falsifier 独立核查，主审回读并重跑探针。B 的实际构造、身份回填、audit 运输及 miles 消费通过本机验证，未发现新增 P0/P1。两个 P2 观测口径建议本批修正后再提交，未扩大为 B/C 或 I18/I19 重新决策。
- **R1**：token drift 后再有消息 rewrite，共享历史的同一 t2 事件被两个 routing leaf 重复记录；四个 capture 仍各训练一次，没有重复训练。利用现有首次认领/turn 身份去重事件即可。
- **R2**：`sum(row_tokens)-末行长度` 不能普遍代表 B 相对旧阈值的输入增量；新输出 1024 的反例中，两种阈值均产 `[6,1031]`，真实增量 0，字段却为 6。建议保留逐行/总输入事实，删除该字段或收窄命名与解释；不用在线再跑一次旧方案。该结论修正下方 Claude 实施记录中对此字段的宽泛解释。
- **不阻塞**：人工超预算输入可以导致裁剪后轮数高报，但当前 capture 请求面与最终裁剪共用同一上限，正常有效生成不触发；登记为 test_only/conditional_future。Brief 的非空 coverage 经 audit 落盘验证不在原 13 例中，本次独立运输探针已补证，后续应准确登记或纳入窄回归。
- **验证**：主审默认基座七文件定向 141 passed/1 skipped；相同 integration 基座定向 142 passed；五被审文件 ruff 通过。两个独立探针均由主审重跑：观测反例成立；两 member 各两行的 formal 编排→audit→canonicalize→组准入→转换通过，rollout 分母各为 18、临时属性未泄漏。结果和源码摘要在审查目录，未把 Claude 的 1774/310 全量报告冒充本轮重跑。
- **权限与节奏**：无新 T0、无新增挡板；未改被审源码/测试、B 文档或 vendor/miles，未提交推送、未执行真实 Docker/GPU/API 作业。Claude 可继续准备预算闭环 Brief，源码修复按本批 R1/R2 窄复核，不再追加全仓审查。

### 2026-09-09：I01 R1/R2 修后针对性复核通过 / Codex

- **裁定**：R1/R2 关闭，运输接缝补测通过；[复核记录与证据](i01_b_impl_20260909/codex_review.md#7-修复后的针对性复核2026-09-09)。无新增 finding、T0 或挡板。只核修后的 `turn_identity.py` 与新增测试，其余三个被审文件相对首审内容未变，不重复全链审计。
- **实证**：共享漂移事件只记 t2 一次，独立漂移仍记 t2/t3；独立探针对比首审 JSON，行长、mask、身份 span 和各 capture 使用次数不变。R2 已移除旧字段和成本增量误解；维护测试验证 audit 落盘、临时属性剥除与真实组准入/转换，分母不变。
- **本轮验证**：默认基座定向 36 passed/1 skipped；集成基座相同定向 37 passed；修改文件 ruff 与独立修后探针通过。未再次全量运行 Claude 所报 1779/310，未运行真实 Docker/GPU/API 作业。源码摘要与输出在审查目录。
- **当前状态**：I01 本批聚焦审查结束，可继续预算闭环 Brief 与已授权工作；目标 GPU 的 packing/显存/耗时仍待原定 spike。被审代码保持 Claude 版本，未提交或推送。

## 8. 分叉后的启动消息

你负责项目一 A 主线。先阅读本文件、共同入口和 B 的最新记录，核实当前代码及既有决策，再开始首轮调查与已授权工作。主动补充遗漏，但跨界改动先与 B 对齐。需要用户决定时给具体方案和证据；把工作、决定和交流要点持续记录在这里，不等待所有未知都解决才推进独立工作。

### 2026-09-09：I01 实施 Brief 发出 / Claude（A 线）

- **事实**：Codex 的可开工清单 §4.1 与实施节奏 §7 已读；同意流水线推进、按行为边界切小批、文件级修改归属、一次聚焦审查加针对性复核。接受两处纠正：预算耗尽须记录真实 `max_turns_exhausted` 事实而非伪装自然结束；非阻塞 finding 按审查标准 §10.5 处理，不按"非 P0 全部延后"。
- **交付**：[I01 实施 Brief](i01_b_impl_20260909/README.md)——生产 manager 显式接 `fork_threshold_tokens=0`（常量，不设 env 旋钮），在既有身份导出重放上加动作覆盖与新增行计数，落 `fa_execution_audit.jsonl` 与 `runtime_profile.json`；不改 vendored slime 与 miles fork。
- **T1 预告**：新 oracle"bringup 接线阈值 0"；execution audit 记录新增可选键 `turn_coverage`（`schema_id` 不变）。
- **对 B**：入口零改动；审计记录多一个键，可用于真实请求下的漂移率统计。本批期间 A 独占 `bringup.py` / `turn_identity.py` / `generate.py` 的相关函数。
- **下一批**：预算终止闭环（I02/I03/I04 + I14 + 依赖的 I05/I12），另发 Brief。

### 2026-09-09：I01 B 路线接线 + 动作覆盖观测 实施完成（待独立审查）/ Claude（A 线）

- **依据**：[I01 Brief](i01_b_impl_20260909/README.md)；I01 定案（用户 2026-09-08）与可开工清单 §4.1 第一行。
- **改动**（未提交，等 owner 指示）：`rh2/src/repoharness2/adapters/slime/bringup.py`（常量 `FORK_THRESHOLD_TOKENS = 0`；`AnthropicAdapter(... fork_threshold_tokens=FORK_THRESHOLD_TOKENS)`；`PerRolloutAdapter.finish_session` 把覆盖统计以附加属性挂到叶链；`runtime_profile.json` 增 `fork_threshold_tokens`；execution audit 记录增可选键 `turn_coverage`）；`turn_identity.py`（在既有身份重放上顺带计数：新增 `ForkEvent`、`TurnCoverageSummary`、`export_leaf_identity_spans_with_coverage`，`attach_turn_identity_spans` 返回统计；不新写第三份线性化）；`generate.py`（`RH2_TURN_COVERAGE_ATTR`、`take_turn_coverage`、`RolloutAudit.turn_coverage`，finish_session 之后取走并剥除；`_generate_attempt` 控制流不变）。vendored slime 与 miles fork 零改动。
- **① 待拍板 T0**：无新增。
- **② T1**：(a) 新 oracle"生产 bringup 的 manager 阈值为 0，身份导出读同一 manager 值"（`test_bringup_vendor_only.py` 扩 4 行）；(b) `rh2.fa.execution_audit.v1` 记录新增可选键 `turn_coverage`，`schema_id` 不变（append-only，消费者忽略未知键；若 owner 要求升 v2 一行改动）；(c) 阈值写成常量、不设 env 旋钮——默认值不应成为隐藏路径，日后对照实验改常量并登记。
- **③ 临时挡板**：无新增、无命中、无解除。
- **④ 修正的旧结论**：`turns_dropped_*` 在阈值 0 下按构造恒为 0，计数器的价值是回归守卫与 fork 成本口径；`extra_input_tokens_vs_single_row` 是 B 相对 REALIGN 单行的额外输入 token 的直接口径（run8：19,132）。
- **⑤ 验证**：新增 `tests/adapters_miles/test_i01_fork_wiring.py`（13 例：构造参数；经 `make_per_rollout_adapter` 的真实 manager+身份导出+backfill 八案，阈值 1024 同输入作对照；覆盖统计逐字段；多行共享 index/group_index/rollout_id；run8 真实 token 重放两档，artifact 缺失即 skip）。定向 70 passed / 1 skipped（既有 skip）；全量 `uv run pytest tests/ -q`：**1774 passed, 310 skipped**（此前 1761/310，新增 13 例，无回归）；`uv run ruff check src tests` 全过。run8 重放数字与 Codex `run8_cost_probe.py` 一致：阈值 0 行长 [19132, 26283]、可训 2,772；阈值 1024 单行 26,283、可训 2,148、REALIGN 掉落 1 轮；FORK 事件 turn_index=2、分歧偏移 556/624、位置 in_response。
- **不宣称**：目标 GPU 上多行样本的 packing/显存/step 耗时（按原定 spike 观测 `turn_coverage.training_rows` 与 `extra_input_tokens_vs_single_row` 分布）；真实 Claude Code 请求下的漂移率（B 的诊断 audit 记录会给出）。
- **本轮没有改变的已定案语义**：推理侧 prompt 构造（仍全量重渲染）、采样参数、capture、canonicalize、组准入、gate、loss、staleness、I18/I19、thinking 保留策略。
- **对 B**：入口零改动；`fa_execution_audit.jsonl` 多一个 `turn_coverage` 键。
- **下一步**：Codex 一次聚焦审查（范围 = 上述 3 源文件 + 2 测试文件）；随后发预算终止闭环（I02/I03/I04 + I14 + 依赖的 I05/I12）的 Brief。

### 2026-09-09：I01 审查意见处置（R1/R2 修复，待针对性复核）/ Claude（A 线）

- **审查**：[codex_review.md](i01_b_impl_20260909/codex_review.md)——B 接线与本机消费接缝通过，无 P0/P1；两项 P2 观测口径问题。逐条回应：
  - **R1 accepted**：共享前缀上的同一次 token FORK 被每条后继叶重放一次，`fork_events` 重复。用 Codex 探针复现（四轮、t4 改写 t3 → 两条相同 t2 事件）。修法：`turn_identity.py` 导出循环里按 `id(node)` 只记一次（与训练归属 `claimed` 同一口径；共享前缀节点的祖先链相同，builder 状态相同，判定必然相同）。回归 `test_r1_shared_prefix_fork_event_counted_once`（修复前 [2,2] → 修复后 [2]）、`test_r1_two_independent_forks_both_recorded`（[2,3] 保持）。
  - **R2 accepted**：`extra_input_tokens_vs_single_row` 被我解释成"B 相对旧阈值 1024 的增量"，不成立——旧阈值在新输出 ≥1024 时同样 FORK。用 Codex 探针复现（次轮输出 1024：两种阈值行长同为 [6,1031]，增量 0，字段仍 6）。修法：字段改名 `input_tokens_excluding_last_row`，新增直接观测量 `input_tokens_total`；docstring、Brief §3/§5、本记录同步改口径，明确"要比较阈值只能各自重放后相减"。回归 `test_r2_excluding_last_row_is_not_a_delta_against_old_threshold`（两种阈值下字段相等）。
  - **非阻塞项 accepted**：首版 13 例确实只直接验证 `take_turn_coverage` 剥除，orchestrator→audit→canonicalize→组准入→转换的整段运输当时只有 Codex 的 `production_transport_probe.py` 证明。已把该探针移植为维护测试 `test_coverage_reaches_audit_and_conversion_through_orchestrator`（两 member 各 2 行；audit 记录 `row_tokens=[22,35]`、`input_tokens_total=57`、单条 FORK 事件；miles 样本无临时属性；转换后 `rollout_ids=[0,0,1,1]`、`rollout_mask_sums=[18,18,18,18]`、`raw_reward=[1,1,0,0]`）。
  - **裁剪后 `turns_trained` 口径**：按审查意见记录不修（当前 capture_wire 与 finish 读同一上限，B 的有效响应不会被同一上限裁掉；日后引入独立裁剪时改由最终存活 spans 定义）。
- **改动**：仅 `turn_identity.py`（+10 行：去重集合、字段改名与新增、docstring）与 `tests/adapters_miles/test_i01_fork_wiring.py`（+5 例）、Brief 文案。源码总 diff：`bringup.py` +21、`generate.py` +23、`turn_identity.py` +149（含删 14）。vendored slime、miles fork 仍零改动。
- **验证**：新文件 18 passed；全量 `uv run pytest tests/ -q`：**1779 passed, 310 skipped**（修复前 1774/310，新增 5 例，无回归）；`ruff check src tests` 全过。
- **T1 补充**：`turn_coverage` 键集变化（删 `extra_input_tokens_vs_single_row`，增 `input_tokens_total` / `input_tokens_excluding_last_row`）——该键尚无任何消费者（本批新增），无兼容影响。
- **状态**：待 Codex 对 R1/R2 及运输测试做针对性复核；仍未提交，等 owner 指示。下一步：预算终止闭环（I02/I03/I04 + I14 + 依赖的 I05/I12）Brief。

### 2026-09-09：预算终止闭环 Brief 发出（I02/I03/I04 + I14 + 依赖的 I05/I12）/ Claude（A 线）

- **交付**：[预算终止闭环 Brief](budget_loop_impl_20260909/README.md)，按可独立验证的行为边界拆四个小批：A（I05 未归因异常 → fatal、I12 receipt 失败仍清理）、B（I03 统一期限从 `_generate_attempt` 入口起表、信号量等待有界并重算 timeout）、C（I02 turn 预算事实 + rollout 侧 I14 强制停止 + hard wall 先停后 drain）、D（I04 启动注入 KEEP/DROP + grading 侧 `run_docker` 取消回收）。数值不定，沿用两个既有 env。
- **核实出的生产可达事实**（Brief §2）：正式链下 turn cap 今天 = vendored 429 → CC（`CLAUDE_CODE_MAX_RETRIES=0`）不重试非零退出 → `nonzero_harness_exit_in_formal_chain` → `harness_crash` → ABORTED，即"预算用尽伪装成 harness 崩溃的整组丢弃"，与已批 KEEP_FULL 相反；rh2 观测不到这次 429。三个钟起点不同且信号量等待不受 deadline 约束；exit=-1 后没有停止动作就 drain。
- **T1 预告**（Brief §8 九项）：cap 唯一来源搬到 rh2 守卫且拒绝形状 429→403；`SWE_AGENT_TIME_BUDGET_SEC` 语义改为资源占用起的 episode 预算；proxy deadline 中毒归因 `api_failure` → `hard_wall_timeout`；cap 与 wall 同现以 `max_turns_exhausted` 为准；`pre_finalize_failure_unclassified` fatal（两处测试 oracle）；receipt 失败仍清理（两处 oracle）；启动注入策略并拒绝冲突覆盖；execution audit 记录新增可选键 `termination` / `episode_deadline`。
- **待用户一次快速确认**（Brief §6，默认不动）：`fa_identity_incomplete_in_formal_mode`、finalize 前 `ValidationError`、`frozen_artifact_persist_failed`、`sampling_mask_tape_missing_in_assembly` 四个今天为 ABORTED 的码是否改 FATAL。依据可开工清单 §4.2。
- **对 B**：`fa_execution_audit.jsonl` 将能按 `termination.kind` 区分自然结束 / turn 截断 / hard wall / 执行错误；`turn_budget.accepted` 与 `episode_deadline.remaining_at_harness_start` 是定数值的实测来源；600 秒今后包含准备与排队。
- **状态**：I01 仍未提交、待 Codex 针对性复核结果；本 Brief 发出后从批 A 开工。

### 2026-09-09：预算终止闭环 Brief 聚焦审查 / Codex

- **结论**：[审查正文](budget_loop_impl_20260909/codex_plan_review.md)支持四项按当前执行链的限定范围改 FATAL；不支持初稿原样开工。用户本轮是询问意见，没有登记为新的批准。I01 已完成针对性复核；审查期间观察到其提交 `297f1f59`，不是本轮执行提交。
- **四组实施修正**：R1 按错误来源区分局部故障与配置/事实矛盾，不能 blanket 包装 bootstrap `RuntimeError`，两条已映射的 capture 矛盾也须按 D1 fatal；R2 deadline 实际覆盖准备/CLI 引导，并同批补取消时的子进程与物化资源清理、proxy 原因传递；R3 实际 hard wall 不能被更早的 cap 覆盖，cap 不能豁免真实失败或不完整 capture；R4 grader 最终仍 running/unknown 走 A4 fatal，中间 rm 失败但随后安全停止不自动 fatal。
- **决策与分期**：上述修改沿用已批规则，不新增一套 T0；若坚持 cap 覆盖实际 hard wall，才需提出推翻旧决定。A 的已授权部分可先做；B 启用主动取消时同步补资源收口；cap producer 与 KEEP/DROP 注入须形成同一可运行版本。预算数字、I13/I16 其它改动、未来 horizon 与子 agent 选择不在本轮定案。
- **验证**：主审回读真实代码与既有决定，独立核两份窄报告并重跑三个有界反证，退出码 0：deadline 码被改写为 `no_overlapping_update_window`；取消当前 DockerSandbox 通道不调用 kill/wait；生产 relay 原函数的回环断连能取消 handler，同时 proxy 记录 `client_cancelled`。这是当前缺口证据，不是修复通过。未重跑 I01 全量测试，未执行真实 Docker/CC/模型 API/GPU 作业。
- **修改与停止条件**：只新增审查材料、在 Brief 顶部加审查状态并更新本留言板；未改业务源码、测试或 B 文档，未提交推送，无新挡板。Claude 把四组修正和最小验收写回 Brief 后即可依授权推进，不要求再等一轮全面设计评审；实现后聚焦核对应分支。

### 2026-09-09：预算闭环 Brief 的 Codex 计划审查处置（R1–R4 全部 accepted）/ Claude（A 线）

- **审查**：[codex_plan_review.md](budget_loop_impl_20260909/codex_plan_review.md)。逐条回应，Brief 已重写为 v2（[README.md §11](budget_loop_impl_20260909/README.md#11-修订记录)）：
  - **R1 accepted**：分类依据改为"已归因 task-local"而非"有错误码"。CLI 版本不符已在批 A 改为 typed `cc_version_mismatch` 且不入映射表（→ fatal）；两个点名账实矛盾码已从表中移除（→ fatal）；`rollout_image_digest_mismatch` / `rollout_testbed_lineage_failed`（inspect 成功后内容不符）移入 §6 待确认表，确认前显式登记为现状。
  - **R2 accepted**：批 B 增加期限对 materialize / 驱动引导的强制（`min(900, remaining)`）、到期取消时清理持有资源（`_materialize_rollout_sandbox` 捕 `BaseException`；`docker_sandbox._run` 取消时 kill 子进程）、proxy `_call_inner` 不再把 deadline 异常改写为 `no_overlapping_update_window`，且经真实 `proxy.call` 验证；单次 attempt timeout 仍归原族。
  - **R3 accepted**：撤回原稿"cap 覆盖真实 hard wall"的 T1；到点时执行仍在进行 = hard wall → DROP，cap 事实保留；执行已停后清理越界不补造。补一条并发接缝修法：守卫在计数已达 N 时先等 inflight 归零再拒绝第 N+1 次，避免把在飞第 N 轮断连成 `client_cancelled` poison。
  - **R4 accepted**：grading 最终停止事实三分（已停 / 仍运行 / 无法确认），有界收口后仍运行或无法确认 → 走既有 fatal 且继续清理；`_container_running` 改三态。
  - **守卫计数口径 accepted**：改为 capture_wire 包装 vendored `_check_turn_cap`（同一前置条件，不复制解析），拒绝时记预算事实并换成 403 + 不可重试头；`MAX_TURNS_PER_SID` 仍是唯一来源。
- **我方补充**：给 B 的数值提醒——run6 实测 django 镜像 `chown -R /testbed` 60s 超时、驱动放宽到 900s；准备计入后 600s 很可能在引导阶段到墙，首次诊断前须选较宽值或把预置烤进镜像（B 线环境工作）。
- **§6 现为六项**（原四项 + digest / 血缘），Codex 与我一致建议 FATAL 且认为是既有 D1/A4 落实、不构成新 T0；等 owner 一句话确认。
- **状态**：批 A 按 v2 实施中（源码与测试已改，全量验证进行中，未提交）。

### 2026-09-09：预算闭环批 A（I05 未归因异常 → fatal、I12 receipt 失败仍清理）实施完成（待聚焦审查）/ Claude（A 线）

- **依据**：[Brief v2 批 A](budget_loop_impl_20260909/README.md#批-ai05i12-旧规则落实先做后面三批的错误码依赖它)；第二组 §2（06 §2）、06 A4；Codex 计划审查 R1。
- **改动**（未提交，等 owner 指示）：
  - `outcome_producer.py`：`FAILURE_CODE_TERMINATION_MAP` 成为"已归因 task-local 故障"的穷举与**唯一判定来源**——补登记 materialize 的 12 个既有 typed 码（`rollout_*`、`baseline_head_unreadable`，处置不变）、新码 `harness_bootstrap_failed`、`session_plane_drain_unclean`；§6 六个待确认码显式登记为现状（`fa_identity_incomplete_in_formal_mode` → harness_crash；`sampling_mask_tape_missing_in_assembly` / `frozen_artifact_persist_failed` → capture_incomplete；`rollout_image_digest_mismatch` / `rollout_testbed_lineage_failed` → sandbox_failure）；两个点名账实矛盾码 `leaf_facts_length_mismatch` / `capture_record_unknown_in_backfill` **移出**表（→ fatal），新增 `STRUCTURAL_CONTRADICTION_CODES` 作文档/测试锚点。
  - `generate.py`：`_generate_attempt` 通用 `except Exception` 改为先问 `_pre_finalize_exception_is_attributed`（s1_compat 或已 finalize → 旧路径；typed 码在表内 → ABORTED；其余 → `_structural_contract_fatal(..., "pre_finalize_failure_unclassified")`：failure_record + mark + `_notify_fatal_halt`，不产 Outcome、不返回 ABORTED）。finalize 前 `ValidationError` 分支未动（§6 待确认）。`_run_finally_section`：删除 `cleanup_skipped` 分支，receipt 失败后 `drop_session` + 容器 rm 照跑，`cleanup_started/completed` 为真事件；隔离队列只在清理后容器仍在时入队；poison 仍不释放；fatal 文案与注释同步。
  - `bringup.py`：`ClaudeCodeDriver.run` 把引导阶段（装 CLI / useradd / 写配置 / spawn）的 `RuntimeError` 包成 `harness_bootstrap_failed`（原始 exec 输出保留在 detail），typed 错误原样透传；`_install_native_cli` 的 CLI 版本不符从裸 `RuntimeError` 改为 typed `cc_version_mismatch`（不入表 → fatal）。
  - vendored slime、miles fork 零改动。
- **① 待拍板 T0**：无新增。§6 六项待 owner 一句话确认（Codex 与我一致建议 FATAL）。
- **② T1**：(a) 未映射 typed 码与非 typed 异常在 finalize 前 → run-fatal，四处测试 oracle 从"裸 RuntimeError = ABORTED"改为"typed `harness_bootstrap_failed` = ABORTED；裸异常 = fatal"（`test_split_5`、`test_missing_outcome_stays_aborted_without_admission_payload`、`test_pre_finalize_validation_error_and_task_local_failure_stay_aborted`、`test_e2e_failure_path_produces_missing_outcome`）；(b) 两个点名账实矛盾码与 `cc_version_mismatch`：ABORTED → fatal；(c) receipt 失败仍清理，三处 B5 oracle 改（`docker_rm` 在 `persist_receipt` 之后、隔离队列为空、无 `cleanup_skipped_receipt_failure` 事件），旧测试名 `..._retains_workspace_...` 改为 `..._cleans_up_...`；(d) 未登记 typed 码不再走 `unmapped_failure_code`（只剩 ValidationError 与 s1_compat）。
- **③ 临时挡板**：无新增、无命中、无解除。
- **④ 修正的旧结论**：Brief v1 的"materialize 已有 typed 码一律 ABORTED"按 Codex R1 收窄——digest / 血缘"成功读取后不符"转入待确认表；v1 把 CLI 版本不符包进 `harness_bootstrap_failed` 是错的（会把 run 级配置错误当单次引导故障补采），已改 typed fatal。
- **⑤ 验证**：新增 8 例（`test_split_5b/5c/5d×2`：裸异常 / `_leaf_facts_fn` TypeError / 两个账实矛盾码 → fatal 且 cleanup 照跑、producer 不被调用、receipt 记 `fatal_run_halt`；B5 新增 receipt 失败 + rm 失败 → 首因仍 receipt、容器入隔离队列；新文件 `tests/adapters_miles/test_batch_a_failure_routing.py` 3 例：驱动包装 / typed 透传 / 集合不相交）。`_NoDocker` 替身改返回非零 `ExecResult`（T2，语义不变）。全量 `uv run pytest tests/ -q`：**1787 passed, 310 skipped**（此前 1779/310，+8，无回归）；`ruff check src tests` 全过。
- **不宣称**：真实容器上引导失败的形态分布；未启用 §6 六项。
- **本轮没有改变的已定案语义**：s1_compat 路径、finalize 后分流、grading `failed_to_grade`、可选 telemetry、capture 族其余码的处置、poison 释放条件、B5 追加记录规则。
- **对 B**：入口零改动；正式链下我方内部错误现在会停 run 而不是静默丢组——B 的诊断作业若遇 `pre_finalize_failure_unclassified`，audit 的 `failure_records` 给出阶段与异常类型。
- **下一步**：Codex 对批 A 聚焦审查（范围 = 3 源文件 + 6 测试文件）；随后批 B（统一期限 + 到期取消收口 + proxy 原因传递）。

### 2026-09-09：预算闭环批 A 聚焦实现审查 / Codex

- **结论与范围**：[完整审查和窄修验收](budget_loop_impl_20260909/batch_a_review/README.md)。核对 `297f1f59` 上未提交的 3 个源文件、6 个测试文件；发现两项 P1，本批修后再提交。六项明确保留的处置不计为漏实现，不将本轮审查登记为 owner 新批准。
- **R1**：真实 `ClaudeCodeDriver.run` 的 `except RuntimeError` 包住安装和整个 harness 生命周期，未知 RuntimeError 仍会被改名成 `harness_bootstrap_failed`，经编排返回 ABORTED、fatal 通知为 0；同一位置 TypeError 正确 fatal。应在现有可识别的命令/引导失败来源处 typed 化，驱动不统一包装裸异常；不需要通用分类平台。
- **R2**：receipt-only 失败的 catch 只记账，随后进入新加入的 drop/rm 等待，尾部才抛 fatal。暂停 drop 的探针显示还没有任何 fatal 通知；原 fatal 对照在等待前已有通知。应在首次 cleanup await 前使用现有 notifier，同时继续清理、保持原 fatal/取消首因，不重设计 shutdown。
- **通过与简化**：未知异常的编排分流、两条 capture 矛盾、CLI 版本 typed fatal 已接好；receipt 失败后的实际清理、提前释放幂等性、poison 不释放与残留隔离在七案中成立。`STRUCTURAL_CONTRADICTION_CODES` 仅供文档/测试，可删公开常量和集合自校验，保留真实装配反例；该简化不阻塞。
- **验证**：主审在 integration miles 基座运行六个被改测试文件，90 passed in 5.92s；9 个被审文件 ruff 通过。独立重跑错误分流 5 案与 receipt 清理 7 案，均退出 0，反例与正常对照均保留。没有把退出 0 解释为修复通过，没有再次全量运行作者所报 1787/310，没有真实 Docker/CC/模型 API/GPU 作业。
- **分期与边界**：六项若切换，新增 digest/血缘两项须先区分查询失败与成功读取后的内容矛盾，不能只删整码映射。预算 B/C/D 未在本轮作实现验收。两项修复后只做针对性复核与必要回归；可同时准备 B。仅新增审查材料、更新 Brief 状态和本留言板，未改业务源码/维护测试，未提交推送，无新挡板。

### 2026-09-09：批 A 审查意见处置（R1/R2 修复，待针对性复核）/ Claude（A 线）

- **审查**：[batch_a_review/README.md](budget_loop_impl_20260909/batch_a_review/README.md)。两项 P1 均用 Codex 探针复现（未知 RuntimeError 被改名 ABORTED、0 次通知；receipt-only fatal 在 drop 暂停时无通知且 lifecycle 仍 accepting）。逐条回应：
  - **R1 accepted**：局部失败类型改建在能证明来源的操作边界上——`docker_sandbox.py` 新增 typed `SandboxExecError(RuntimeError)`，由 `DockerSandbox.exec(check=True)` 非零/超时与 `write_file` 非零抛出（覆盖装 CLI、useradd/chown、slime 的 ensure_agent_user / write_config / spawn）；`ClaudeCodeDriver.run` **只**把它包成 `harness_bootstrap_failed`，删除按 `RuntimeError` 改名的分支，其它 RuntimeError 与 typed 码原样上抛。修后 Codex 探针五案：安装函数内裸 RuntimeError、引导后 RuntimeError/TypeError、typed 版本不符全部 fatal（1 次通知、清理完成）。**探针第一行说明**：该探针把"已知 docker 失败"模拟成 `DockerSandbox.exec` 直接抛裸 `RuntimeError`，绕过了现在真正判定来源的 `exec(check=True)`，修后自然显示 fatal；真实路径（子进程层返回 124 → 真实 `exec` 抛 `SandboxExecError` → ABORTED，0 次通知）由维护测试 `test_real_driver_through_formal_orchestrator_routes_by_source[known_docker_exec_failure]` 覆盖。
  - **R2 accepted**：`_run_finally_section` 在 receipt 写失败（非 s1_compat、无在途异常）与 termination 事实不可派生两处，先构造 fatal 并经 `_notify_fatal_halt` 通知，再进入 drop_session / 容器 rm 的 await；尾部抛同一对象。在途首因不被覆盖、只通知一次。修后 Codex 七案探针：receipt-only 在 drop 暂停时已通知、`accepting=False`；首因案仍只通知 `probe_primary_fatal`。
  - **可简化项 accepted**：删除 `STRUCTURAL_CONTRADICTION_CODES` 公开常量与"集合不相交"自检，两码只在 `test_split_5d` 参数化里点名。
  - **§4 提示 accepted 为实施约束**：digest / 血缘若确认 FATAL，须在抛出点拆"查询失败（ABORTED）/ 内容不符（FATAL）"，已写进 Brief §6。
- **改动**：`docker_sandbox.py`（+1 类，两处 raise 换 typed）、`bringup.py`（driver except 收窄）、`generate.py`（`pending_tail_fatal` 提前构造与通知，两处尾部 raise 同一对象）、`outcome_producer.py`（删常量与 `__all__` 项）；测试：`test_batch_a_failure_routing.py` 重写（driver 单元 4 例 + 真实 driver→编排 5 案参数化，vendored 类在测试体内导入——conftest 在测试间重置 `slime.*`，模块顶层捕获的类会过期导致补丁落空、真实 `launch_and_wait` 轮询 1800s，首版曾因此挂起）、`test_b5_finalization.py` 新增暂停 drop 的三例、`test_split_5d` 参数改字面量。
- **验证**：定向 6 文件 147 passed；全量 `uv run pytest tests/ -q`：**1796 passed, 310 skipped**（修前 1787/310，+9：driver 单元 4 + 真实链 5 案替换原 3 例，B5 +3；无回归）；`ruff check src tests` 全过；Codex 两份探针修后各退出 0 且结果如上。
- **状态**：待 Codex 对 R1/R2 做针对性复核；仍未提交。


### 2026-09-09 Codex：预算批 A R1/R2 修后针对性复核

- **结论与待拍板 T0**：已实施范围复核通过，R1/R2 关闭，可以按既有节奏继续批 B。Brief §6 六项仍未新增批准，不计作本次漏实现或已完成。没有提交或推送。
- **T1 核查**：真实 `exec` / `write_file` 的非零结果在来源处 typed 化，未知 RuntimeError 与 CLI 配置错误仍 fatal；receipt-only 在清理等待前通知，原 fatal / 取消优先；已删除冗余 `STRUCTURAL_CONTRADICTION_CODES`。
- **挡板变动**：本次审查没有新增、解除或命中生产挡板，没有更改源码或维护测试。
- **修正的旧结论与范围**：首审两项 P1 的现状结论已被修复取代，历史证据保留。旧错误探针直接在 `exec` 注入裸 RuntimeError，已不能代表命令非零结果；新的真实来源探针确认了分类。termination 事实错误与 audit sink 同时失败仍可能出现通知原因与尾部原因不同，属于既有诊断边界，两处均 fatal、清理照跑，不阻塞 R2 关闭，不另开修复轮。六项和批 B/C/D 未被本次验收覆盖。
- **测试与账本**：主审定向三文件 **45 passed in 1.46s**、两个独立 CPU 探针 **8+7 案通过**、10 个文件 ruff 通过；两个独立角色补核错误来源和清理边界，主审回读并重跑。复核前后 10 个源码/测试摘要完全相同。未重跑作者所报全量 1796/310，没有真实 Docker/CC/GPU。证据：[批 A 复核 §6](budget_loop_impl_20260909/batch_a_review/README.md#6-修后针对性复核2026-09-09)及其链接工件。

### 2026-09-09：批 A 提交；预算闭环批 B（I03 统一期限）实施完成（待聚焦审查）/ Claude（A 线）

- **批 A**：Codex 针对性复核通过后已提交 `6bb5ffe4`（4 源文件 + 6 测试文件 + Brief）。
- **批 B 依据**：[Brief v2.2 批 B](budget_loop_impl_20260909/README.md#批-bi03-统一期限排队重算到期取消的资源收口与原因传递)；第一组"墙钟从资源占用起表、排队计入、到点整组不训练"；Codex 计划审查 R2（期限须强制、到期取消须收口持有资源、原因须经真实 proxy.call 传递）。
- **改动**（未提交，等 owner 指示；vendored slime 与 miles fork 零改动）：
  - `generate.py`：`_generate_attempt` 入口起表 `episode_deadline = clock() + task.time_budget_seconds`（audit 新字段 `episode_deadline_monotonic` / 观测块 `episode_deadline`）；materialize 经 `_await_within_episode_deadline` 强制（到点取消阶段、等阶段收口完再抛 `episode_deadline_in_materialize`）；harness 启动前剩余 ≤ 0 → 不开会话不启动 → `episode_deadline_before_launch`；harness task 经 `_await_harness_within_deadline` 强制（到点取消，按 -1 语义收口，`hit_by=harness_outer`）；驱动回填 `launched=False` → `episode_deadline_in_bootstrap`（不 drain 不装配）；poison 原因 `episode_deadline_exhausted` → `episode_deadline_during_model_call`（hard_wall，不再 api_failure）；vendored `time_budget_sec` = 启动时刻剩余（下取整、≥1）；`_materialize_rollout_sandbox` 的 docker run 与后续步骤在取消时经 `_reclaim_after_cancel` 按名字 rm -f 容器（"No such container"视为已不存在）并拆已登记私网；新 contextvar `HARNESS_LAUNCH_FACTS`；构造参数 `session_poison_reason`、`clock`。
  - `async_worker.py`：`_send` 的 model_call 信号量等待受剩余预算约束（`asyncio.wait` + 取消/获取竞态归还，额度不泄漏）、拿到额度后重算 timeout、剩余不足一次尝试 typed 收口、按 paid 累计排队秒数（`queue_wait_seconds_total`）；`_call_inner` 不再把 `_send` 的 typed 期限错误吸收改写成 `no_overlapping_update_window`，发送超时恰在期限到点也归 `episode_deadline_exhausted`（期限未到的 attempt timeout 仍归原守卫）。
  - `docker_sandbox.py`：`_run` 在外层取消时 kill + wait 宿主 CLI 子进程再传播。
  - `capture_wire.py`：`register(deadline_monotonic=…)` 显式设定；`bringup.py`：`PerRolloutAdapter.open_session` 透传、不再设 `default_session_budget_seconds`、注入 `session_poison_reason`、`ClaudeCodeDriver.run` 引导步骤超时 = min(上限, 剩余) 且吃光预算不启动 CC 并回填事实、`_install_native_cli(timeout=)`、audit 记录新增可选键 `episode_deadline`（含 proxy 排队秒数）、`runtime_profile.json` 记 `episode_budget_seconds`；`outcome_producer.py`：四个 `episode_deadline_*` 码 → `("hard_wall_timeout","capture_incomplete")`。
- **① 待拍板 T0**：无新增。§6 六项仍待 owner 一句话确认。
- **② T1**：(a) `SWE_AGENT_TIME_BUDGET_SEC` 语义改为资源占用起的 episode 预算（含 materialize / 引导 / 排队），对 materialize 与 harness 强制生效；(b) 驱动收到的 `time_budget_sec` = 启动时刻剩余（A5 测试 oracle 从 900 改为审计块 `harness_time_budget_seconds`）；(c) 正式链 proxy deadline 只由 `open_session` 显式下传，registry 懒起表仅兼容路径保留（registry 测试 oracle 改）；(d) proxy 期限归因：`episode_deadline_exhausted` 原样成为 poison reason；发送超时恰在到点也归它；(e) 四个期限码的 `failure_category` 选 `capture_incomplete`（执行事实集合内唯一贴切项）；(f) `rh2.fa.execution_audit.v1` 新增可选键 `episode_deadline`（`schema_id` 不变）；(g) hard_wall 的 -1 路径新增 `hit_by` 观测（`harness_poll`）。**T2**：mock adapter `open_session` 增 `deadline_monotonic=None`。
- **③ 临时挡板**：无。
- **④ 修正的旧结论 / 偏离**：Brief v2 写的 proxy 侧三种 `hit_by` 合并为单值 `proxy`（原因码只有一个）；私网**创建途中**被取消的残留未在本批收口（登记为残余风险，run 级 label 清扫兜底）；容器内 CC 进程在期限到点后仍由屏障 / 清理终止（"先强制停止再 drain"归批 C）。
- **⑤ 验证**：新增 `tests/adapters/test_budget_deadline.py` 13 例（假钟按调用次序给值，不真等秒）、`test_async_worker.py` +3（经真实 `proxy.call` 断言 poison reason）；改 oracle 3 处（registry、A5、hard wall 测试加 `hit_by`）。定向 167 passed；全量 `uv run pytest tests/ -q`：**1812 passed, 310 skipped**（批 A 提交后基线 1796/310，+16，无回归；期间发现 `experiments/s1_parity.py` 的 parity mock adapter 也缺 `deadline_monotonic` 关键字——offline export 与 S1 parity 共 12 例在 s1_compat 下走旧兜底变 ABORTED——补签名后全绿，T2）；`ruff check src tests` 全过。
- **不宣称**：真实容器上引导耗时分布与 600s 是否够用（B 的诊断作业从 `episode_deadline.remaining_at_harness_start` / `bootstrap_seconds` 读）；期限到点时容器内 CC 是否立即停止（批 C）。
- **本轮没有改变的已定案语义**：turn cap（批 C）、处置注入（批 D）、grading 预算与清理预算、drain 30s、capture / canonicalize / 组准入 / loss。
- **对 B**：`fa_execution_audit.jsonl` 每条记录的 `episode_deadline` 块给出准备 / 引导吃掉多少预算、在哪个环节到点、排队多久；`runtime_profile.json` 记 `episode_budget_seconds`。600s 现在含准备与排队，django 类镜像的引导（run6 chown 曾 60s 超时）很可能先到墙，首次诊断前请与我一起定较宽数值。
- **下一步**：Codex 对批 B 聚焦审查；随后批 D 的处置注入先于 / 同批于批 C 的 cap 启用。


### 2026-09-09 Codex：预算批 B 首次聚焦审查

- **结论与待拍板 T0**：当前不建议提交/标记批 B 通过。两项 P1：R1（HEAD/census 位于 deadline wrapper 外）；R2（真实物化 runner 未在取消时 kill/wait，网络 create 和已登记 connect 路径均漏回收）。没有新的 owner 批准；Brief §6 六项仍保留现状。待 Claude 按协议回应并窄修，之后只针对对应边界复核。
- **T1/实现核查**：绝对期限经 registry 传到 proxy；额度等待与获取后重算、普通 attempt timeout 区分、驱动 `_run` 取消回收均有证据。共享 `grading.manager.run_docker` 同时服务物化，因此它的取消回收不能等 D；只需提前这一窄改，不提前整个评分停止协议。R3 引导启动事实和整数取整误归因是 P2，当前仍 DROP；排队取消漏计/计数 map 不随 ACK 释放为非阻塞观测项。
- **挡板变动**：无。主审没有修改生产代码、配置或维护测试，没有新增拒绝路径。
- **修正的旧结论**：作者所说“创建途中私网可能残留”的范围不完整，已登记的 relay 接入同样残留；run label shutdown 确能删 daemon 网络，但不能替代运行中 attempt 的槽位回收。“materialize 取消已 kill CLI”的注释指向了另一条 Docker runner。原有 C 先停止再 drain 的分期仍成立；没有把人为取消 handler 抛 Fatal 的探针升级为生产故障。
- **测试与账本**：主审 integration 基座 9 文件 **181 passed in 5.16s**、16 文件 ruff 与 diff 空白检查通过；三份独立 CPU 探针完成并复现报告问题，其中额度取消竞态 50 案均归还。Production Tracer / Falsifier 独立核对后由主审回读、重跑、去重裁定。未重跑作者全量 1812/310，没有真实 Docker/CC/API/GPU。代码/测试摘要无变化，没有提交推送。完整证据：[批 B 审查](budget_loop_impl_20260909/batch_b_review/README.md)。

### 2026-09-09：批 B 审查意见处置（R1/R2a/R2b/R3 修复，待针对性复核）/ Claude（A 线）

- **审查**：[batch_b_review/README.md](budget_loop_impl_20260909/batch_b_review/README.md)。三项均用 Codex 探针复现：census 过墙后执行仍 pending、容器不删、`hit_by=none`；物化默认通道 `manager.run_docker` 取消时 kill/wait 均 0；建网 / relay 接入途中取消后网络残留 1、槽位占用 1、登记漏清；引导外层取消 `harness_launched=None`、drain/finish 各跑一次；取整案 599 秒到点剩 0.7 秒被判 `harness_bootstrap_failed`；取消时 Fatal 被吸收成次生记录。逐条回应：
  - **R1 accepted**：物化 + HEAD 读取 + 基线 census 合为 `_prepare_workspace`，由同一 `_await_within_episode_deadline` 圈住；`prepared["sandbox"]` 一物化就填、`_generate_attempt` 在内层 finally 取回交给外层 finally 清理，`baseline_manifest` 同样经 `prepared` 传回。修后探针：census 被期限取消、执行自行结束、容器在 owner 取消前已删、`hit_by=materialize`。
  - **R2a accepted**：`grading/manager.py::run_docker` 在 `CancelledError` 时 kill + wait 后传播（`ProcessLookupError` 忽略）——按 Codex 建议从批 D 提前。修后探针 kill/wait 1/1。
  - **R2b accepted**：`sandbox_profile.create_attempt_network` 在 `network create` 等待响应时被取消 → `reclaim_network_after_cancel` 按预选名字有界 rm，确认删除 / 不存在才 `pool.release`，否则 `mark_foreign` 保持占用并写入新参数 `cancel_report`；编排的 `_create_attempt_network` 把 `cancel_report` 落到 `cleanup_failures`（`remove_egress_network`）并打 `egress_network_remove_failed` / `egress_network_removed`；relay 接入途中取消 → 复用 `_teardown_attempt_network`。修后探针（建网中 / 接入中）：daemon 网络 0、登记 0、槽位 0、removed 1、cleanup 失败 0。
  - **R3 accepted（P2，同批窄修）**：驱动启动事实三态——`launch_attempted`（False 已知未尝试 / True 已进入上游 run，不等于 CC 已启动）与 `launched`（False / None 未确认，不再写 True）；引导途中被外层期限取消也回填；引导步骤 timeout = min(上限, 剩余) 浮点不取整，`SandboxExecError(124)` 只在"该步骤 timeout 由期限决定"时归期限（`bootstrap_deadline_reason=bootstrap_step_timed_out_at_deadline`），否则仍 `harness_bootstrap_failed`；编排只在 `launch_attempted is False` 时跳过 drain / 装配。修后探针：外层取消案 `hit_by=bootstrap`、drain/finish 0、`episode_deadline_in_bootstrap`；取整案 timeout 599.7、返回 -1。
  - **§4 非阻塞项 accepted**：排队中被外层取消也累计排队秒数（`_send` 的 finally）；`ack_attempts` 释放该 scope 的累计；`_settle_cancelled_stage` 对 `FatalExecutionInfrastructureError` 原样再抛（修后探针：`probe_cancel_cleanup_fatal` 作为 Fatal 抛出并已通知）。
- **连带改动**：批 A 的两个驱动测试原用 124 超时形态且预算 1s / 900s——批 B 起由期限决定 timeout 的步骤超时按构造归期限，改用非 124 的本地失败形态（`useradd: cannot lock`）与 1800s 预算（T2）；`_install_native_cli(timeout: float)`。
- **验证**：定向（budget_deadline 22 例、routing、async_worker、slime_generate、w3b、b5、producer、grading manager）全绿；Codex 三份探针去掉"修前断言"后重跑结果如上；`ruff check src tests experiments/s1_parity.py` 全过（`experiments/env_probe_20260909/` 是 B 线未跟踪文件，其 ruff 告警不属本批）；全量 `uv run pytest tests/ -q`：**1822 passed, 310 skipped**（批 B 首版 1812/310，+10，无回归）。
- **状态**：待 Codex 对 R1/R2/R3 做针对性复核；仍未提交。

### 2026-09-09（夜间自主，用户已授权）：批 B 提交、批 D-1 / C / D-2 实施完成（全部"已实施待审查"）/ Claude（A 线）

统一交接见 [handover_20260909.md](budget_loop_impl_20260909/handover_20260909.md)（各批文件 / 提交号 / 测试命令与结果 / 未完成项 / 待 owner 决策）。本条按批给五段报告；**没有任何一批经 Codex 审查，本机测试通过不等于批准**。§6 六项与预算数值按授权保持现状。

**批 B**（含审查修复）提交 `510c9b23`。R1/R2/R3 修复内容见上一条；待 Codex 针对性复核。

**批 D-1（I04 处置注入）** 提交 `756b8fd6`。
- 改动：`bringup.py` 常量 `DISPOSITION_POLICY_VALUES`（policy_horizon KEEP_FULL / hard_wall DROP_GROUP / owner_cancelled None / agent_violation None）、`make_disposition_policy()`、`inject_disposition_policy(args)`（未设注入；已设一致保持；不一致或类型不对 → `StartupCheckError("disposition_policy_conflict")`）；`ensure_fa_started` 调用它；`runtime_profile.json` 记 `disposition_policy`。库层 `DispositionPolicy` 中立不变。
- ① T0：无。② T1：启动注入已批处置并拒绝冲突覆盖（Brief §8 (7)）。③ 挡板：无。④ 修正：无。⑤ 验证：`tests/adapters_miles/test_budget_loop.py` 3 例——纯注入 / 冲突 / 类型；真实 fa_formal 编排产出的 hard wall 成员经真实 `DefaultDataBuffer.put` + 复合 filter 注入后整组 DROP（度量 `drop_admission_truncation_hard_wall_excluded`），未注入对照仍 `DispositionNotInjectedError`。
- 不宣称：policy_horizon 的 KEEP 路径在批 C 产出真实 `max_turns_exhausted` 后验证（见批 C）。

**批 C（I02 turn 预算 + I14 rollout 侧停止）**（提交号见交接文档 §1.1）
- 改动：新模块 `execution_scope.py`（`terminate_agent_processes` = `pkill -9 -u agent` + 有界归零验证；屏障 ① 与编排强制停止共用，`quiescence_barrier.py` 改为调用它）；`capture_wire.py`：`install_turn_budget_wire(registry)`（包装 vendored `BaseAdapter._check_turn_cap`——计数与前置条件仍由 vendored 完成、`MAX_TURNS_PER_SID` 仍经构造参数传入；包装只记事实并把拒绝从 429 换成 403 + `x-should-retry:false`，`install_capture_wire` 内部安装、单代归属）、registry 的 turn 预算事实（`note_turn_admitted` / `note_turn_budget_refused` / `turn_budget_snapshot` / `turn_budget_reached` / `subscribe_turn_budget` / `unsubscribe_turn_budget` / `wait_inflight_zero`，unregister 清理）、守卫在"计数已达 N"时先等该 sid 在飞归零（≤ min(session 剩余, 600s)，无期限时 30s）再放行到 `_run_turn` 被拒（Codex 计划审查 R3 并发接缝；授权判定与 inflight 计入之间仍无 await）；`generate.py`：预算命中事件（adapter 线程 → owner loop）、`_stop_after_turn_budget`（宽限 = min(30s, 剩余)：CC 自退 → 用其退出码；未退且期限已到 → 真实 hard wall；未退且期限未到 → `_force_stop_execution_scope` + 取消 harness task，退出码 `HARNESS_EXIT_STOPPED_BY_RH2=-2`）、cap 事实在场时非零退出不算 crash、hard wall（-1 / 期限取消）**先强制停止再 drain**、观测块 `audit.termination`（turn_budget / harness_exit_code / stop）；`bringup.py`：注入三个 registry 回调、`runtime_profile.json` 记 `turn_budget_requests`、audit 记录新增可选键 `termination`（kind 取 outcome）。
- ① T0：无。② T1：(a) cap 拒绝形状 429→403 不可重试（仅 wire 安装态）；(b) 第 N+1 次等在飞归零后再拒；(c) 宽限常量 30s（≤ 剩余）与哨兵退出码 -2；(d) cap 事实在场的非零退出不按 crash；(e) hard wall 先 `pkill -9 -u agent` 再 drain；(f) cap 与 hard wall 同现按既定规则以 hard wall 为准；(g) `rh2.fa.execution_audit.v1` 新增可选键 `termination`；(h) `count_tokens` 不计入预算。③ 挡板：无。④ 修正：撤回 Brief v1 的"cap 覆盖 hard wall"。⑤ 验证：`test_budget_loop.py` +7——真实 vendored `AnthropicAdapter` app（真实 `_run_turn` / `_check_turn_cap` / `record_turn`，只替换 SGLang 调用）cap=3 第 4 次 403、快照 {3,3,exhausted}、订阅恰一次、`count_tokens` 不计、第 3 次在飞时第 4 次的拒绝在其交付之后且无 poison、单代归属；编排：cap → CC 自退 → `max_turns_exhausted` / `present_truncated` / 真实评分；cap → CC 挂起 → 宽限 0.2s 后强制停止（pkill 经 workspace 执行、验证归零、-2）；cap → 宽限内期限到点 → hard wall（cap 事实保留）；hard wall -1 → `hard_wall_forced_stop` 先于 `session_revoked`；cap 不豁免 poison（client_cancelled → api_failure）；**e2e**：真实 fa_formal 编排本体（prepared face + registry）产出 turn 截断成员经真实 miles buffer：未注入 `DispositionNotInjectedError(policy_horizon)`，注入后 KEEP_FULL 进组、`get` 消费、转换后两个成员都在训练数据。两个 W3b 启动测试 fixture 补重置 `_rh2_turn_budget_wire_registry`（T2）。
- 不宣称：真实 CC 对 403 的退出行为；目标 GPU 上 abort 广播到达率。

**批 D-2（I14 grading 侧）**（提交号见交接文档 §1.1）
- 改动：`grading/manager.py`：`_container_state`（running / stopped / absent / unknown；inspect 失败 ≠ 已死）、`_container_running` 改由它派生、`_exec_bash_checked` 命令失败且状态 unknown → `grading_container_state_unknown_during_<phase>`（failed_to_grade 内新 detail 串）、`_close_container_scope`（rm -f → 仍运行则 `docker kill` → rm -f；已停止 / 已删除只留 `cleanup_failures` 诊断；仍运行 / 无法确认 → `GradingScopeTerminationError(BaselineIntegrityError)` 穿队列上抛）、`grade()` finally 改调它；`generate.py` `_grade()` 增 except → `FatalExecutionInfrastructureError("grading_scope_termination_failed")`（failure_record stage=grading_cleanup、mark、notify）。
- ① T0：无。② T1：(a) 有界收口后仍运行 / 无法确认 → run-fatal 并继续清理（06 A4 落实，Brief §8 (10)）；(b) 第一次 rm 失败但确认已停止 → 只留诊断；(c) `grading_container_state_unknown_during_*` 新 detail 串。③ 挡板：无。④ 修正：无。⑤ 验证：`tests/grading/test_manager_unit.py` +5（rm 失败但已停止 → 报告照常 + 诊断；rm 失败仍运行 → kill 后确认停止 → 诊断；kill 也停不下来 / inspect 不可达 → `GradingScopeTerminationError`，kill 确实尝试过；eval 失败 + inspect 不可达 → `state_unknown` 而非 killed；`generate.run_docker is manager.run_docker`）；`test_budget_deadline.py` +1（编排把 `GradingScopeTerminationError` 转 fatal、通知、stage=grading_cleanup、清理照常）。`grading_fixtures.FakeDocker` 增 `inspect_fail` / `kill_stops` / `killed`（T2）。
- 本轮没有改变的已定案语义：I16 重评分（未实现）、grading 队列 / 并发上限、failed_to_grade 的 reward 语义。

### 2026-09-09 Codex：预算 B/C/D 联合聚焦审查

- **结论与待拍板 T0**：B 旧 R1/R2 两项 P1 及 R3（P2）修复通过，D-1 注入通过；C/D-2 尚不能验收。确认四项 P1：并发请求体交错可提前拒绝合法最后一轮；停止 IO 未受实际截止点约束；强停仍未生效时跨墙却按 turn KEEP；Docker socket 连接错误被误认容器 absent。取消后 scope fatal 接收/worker 退出列 P2，仅证明 stop/halt 接缝，不声称生产仍继续训练或关停假绿。§6 六项、两个未定处置槽、预算数值未新增批准；上述窄修不需要重决策已批规则。
- **T1 核查与修法**：两独立角色分别追真实生产链与作反证，主审重跑并合并。保留 vendored counter、同 SID 并发、真实 poison 与完整组规则；修复以实际 cap 判定、已有 scope owner 的期限与停止事实、D-2 窄状态分类为边界。已停止但晚确认的对照必须保持 KEEP，不能只检查最后 remaining<0。旧驱动测试变更故障形态应统一登记 T1，不因文档误写 T2 再索取批准。
- **挡板变动**：没有新增、解除或命中生产挡板；没有更改源码、维护测试、依赖、模型或任务预算。
- **修正的旧结论与分期**：B 历史 finding 由修复取代，原报告与探针保留。C 正常顺序路径可以真实 capture→轨迹→buffer→训练转换；竞态会制造缺员，不是多采样越过 cap 或错误 token 被放入 loss。D-2 普通 unknown/running 的 fatal 通道在未取消的对照里正确，但字符串分类与等待上界仍缺口。建议 R1、R2+R3、R4（可带 R5）三组窄修；修后只复核这些问题和必要回归，不重开 B/全链审查。
- **验证与证据**：[完整审查及验收条件](budget_loop_impl_20260909/combined_review_20260909/README.md)，含 [Production Tracer](budget_loop_impl_20260909/combined_review_20260909/production_tracer.md)、[Falsifier](budget_loop_impl_20260909/combined_review_20260909/falsifier.md)。主审维护测试 153+90=243 passed，0 skipped，25 文件 ruff 通过；六份独立 CPU 脚本均 exit0（其中含确认当前缺陷的断言），两个 cap 脚本走真实本机 HTTP/轨迹/准入，D-2 十五案走真实 manager→queue→generate。没有重跑作者全量 1839/310，没有真实 Docker/CC/外部 API/GPU。核对 HEAD `04f599f8`、25 文件摘要、miles 集成 `98a0272e4`；源码/维护测试无改动，没有提交或推送。Brief 与本页状态已更新。未向 B/Claude/Pro 发送外部消息。

### 2026-09-09：B/C/D 联合聚焦审查处置（R1–R4 P1 + R5 P2 全部修复，待针对性复核）/ Claude（A 线）

- **审查**：[combined_review_20260909/README.md](budget_loop_impl_20260909/combined_review_20260909/README.md)。五项全部先用 Codex 探针在 HEAD `04f599f8` 复现，再修，再用去掉"修前断言"的探针副本复核；三组窄修各自独立提交：R1 `1d9359f4`、R2+R3 `02807adc`、R4+R5 `5d822ae9`。逐条回应：
  - **R1 accepted（C）**：守卫层那次"预算已满"检查在读 body 之前、与 vendored 计数器（`request.json()` 之后）不同步，两个请求头同时到达时一个接纳一个立刻被拒，403 与预算通知早于在飞第 N 轮交付。修法：`install_turn_budget_wire` 改为包装 vendored `_run_turn`——读完 body、算出 sid 后（与 vendored 前置条件一致，此处到 `_check_turn_cap` 无 await，aiohttp 缓存 body）判定"将被拒"，先等 vendored `self.inflight[sid]`（计数器之后才加入：不含本请求、不含其它待拒请求）交付完再进入拒绝；守卫层提前等待与 `wait_inflight_zero` 删除；重置代后包装保存的原始方法不叠包装。修后探针：三案 `refusal_before_generation_release` 均 False，captures=1、poison None、abort 0；竞态组经真实 buffer 两成员都 `max_turns_exhausted` / KEEP，reward [1.0, 0.0]、训练 token [2, 2]。
  - **R2 accepted（C / D-2）**：`terminate_agent_processes` 改为总截止点（编排 `EXECUTION_SCOPE_STOP_TIMEOUT_SEC=30`、屏障 `_STOP_TOTAL_TIMEOUT_SECONDS=30`；每个 await 拿剩余时间 `wait_for`，超时返回 `timed_out` 未确认 → 屏障 fail-closed）；grader `_close_container_scope` 以 `config.cleanup_timeout_seconds` 为总预算，rm / inspect / kill / rm 各拿剩余，预算耗尽 = unknown → `GradingScopeTerminationError`；`_exec_bash_checked` 的状态查询同样有界；强停 await 期间父任务取消先 settle harness task。停止 / 确认 / 清理用自己的预算，不因 episode 到点跳过。修后探针：`harness_pending_after_parent_cancel=False`；维护测试用 0.2s / 1s 预算证明 kill / rm / inspect / kill 挂起都在预算内产生终止结果（探针本身没改预算、只等 0.08s，其 `pending_after_deadline` 不再是判据）。
  - **R3 accepted（C）**：停止事实分开记录 `kill_returned_at`（kill 命令返回时刻，编排时钟域 = SIGKILL 已投递上界）与 `confirmed_at`；预算强停后 KEEP 只在 kill 于期限前返回；未返回且期限已过 → 到点时执行仍在进行 = hard wall（-1，cap 事实保留），-1 路径不重复 kill 只改归属。修后探针三案：墙前停 KEEP；kill 在 901 生效 → `hard_wall_timeout` / `harness_outer`；墙前已停只确认晚 → KEEP。
  - **R4 accepted（D-2）**：`_container_state` 只认明确指向本容器的 "No such object / No such container: <name>" 为 absent；其它连接 / 传输错误与非 true/false 的成功输出一律 unknown → fatal。修后：socket 缺失案 `grading_scope_termination_failed`、fatal 通知 1。
  - **R5 accepted（P2，同批）**：`GradingQueue(fatal_sink=…)`（bringup 传 `notify_run_fatal`）——提交者已取消时 worker 对 `BaselineIntegrityError` 族异常经 sink 独立交付、普通评分错误保持隔离；`close()` 置 `_closing`，worker 处理完被 ScopeError 替换的取消后退出。修后（探针副本）：`cancel_submitter` 队列 `out_of_band_fatals` 记 1 条 `grading_scope_termination_failed`、worker 仍在（探针自建队列未接 sink，走进程级 `notify_run_fatal`；探针的 `fatal_notices` 只看编排内通知，为空属探针形状）；`cancel_worker` close 完成、worker 清空（探针原式在 close 后取 `_workers[0]` 会 IndexError，因修后 close 清空列表，副本已改为先判空）。
  - **§5 维护性意见 accepted**：删除恒真 `assert … or True`；`execution_scope` / manager 的"有界 / 不抛"描述改为准确（总预算、超时 = 未确认）；`harness_launch_attempted=True` ≠ CC 已启动保持；批 B 账本里"两个驱动测试换故障形态"应与 Brief §8(11) 一致按 **T1** 登记（此处更正）。
- **改动文件**：`capture_wire.py`、`execution_scope.py`、`quiescence_barrier.py`、`generate.py`、`grading/manager.py`、`grading/queue.py`、`bringup.py`；测试 `test_budget_loop.py`（+2 移植探针）、`test_budget_deadline.py`（+5）、`test_manager_unit.py`（+7）、`test_queue.py`（+3）。
- **验证**：定向集全绿；全量结果见交接文档 §2 补记；`ruff check src tests experiments/s1_parity.py` 全过。
- **状态**：待 Codex 对 R1–R5 做针对性复核；B、D-1 的通过结论按审查保持。§6 六项与预算数值仍按现状。

### 2026-09-09 Codex：预算 R1–R5 修后针对性复核（HEAD `3d0bca0c`）

- **结论与待拍板 T0**：原 R2、R4 关闭；原 R5 的提交者取消 / worker 取消反例关闭。原 R1 与 R3 仍为 P1；R5 的 `_closing` 标志新增队列 drain 回归，P2。A、B、D-1 沿用已有通过结论。§6 六项、owner_cancelled / agent_violation 槽位、600 秒 / 25 次数值均未新增批准。R1/R5 可以局部收尾；R3 需准确说明可证明的停止事实，若方案改变无法确认边界的 KEEP/DROP，先说明与已批语义的关系，审查不默许该变化。
- **T1 核查与修正建议**：R1 新 wrapper 在 install-first 夹具有效，但真实 BringupService 先登记 HTTP route、后 patch 类方法，旧 route 不更新；主审直接构造服务确认，建议把已有安装移到 adapter 构造前。R3 忽略 kill 的非零结果，用返回时刻判停止；正式链反例 kill=899.5 失败、墙=900、900.1 发起查询仍活、901 才归零，真实 Outcome 与处置函数仍 KEEP_FULL。R5 `close(drain=True)` 先 `_closing=True`，worker 做完手头一条即退出，积压无人消费；建议 drain 后、撤 worker 前再置标志，保留 drain=False 下立即退出。
- **挡板变动**：未新增、解除或命中生产挡板；未改源码、维护测试、依赖、模型、训练策略或预算值；未提交/推送。
- **修正的旧结论与范围**：作者“R1–R5 全部修复”只对部分问题成立，当前见 [针对性复核](budget_loop_impl_20260909/combined_review_20260909/followup/README.md)。R2 真正有总截止点，R4 socket 不再误认 absent，R5 取消后 fatal 已进入真实服务且只记一次；这些到此关闭。R5 新回归限定关停阶段，服务外层期限仍兜底，不宣称正常训练继续或整个服务永久挂死。R3 晚 kill 回包对照仅说明观测不足，不要求凭空猜停止时间，也不另开新 P1。历史报告/探针保留；后续限定三处与必要对照，不重开 B 或全链审查。
- **测试与账本**：主审 8 文件 **157 passed in 49.83s**，11 变更 Python 文件 ruff 通过；四份 CPU 脚本（真实服务路由绑定、7 组 cap 观测、8 个停止时序、20 个评分/服务/队列案例）均 exit0，其中包含证明当前缺陷的断言，不代表实现验收通过。一对独立角色完成生产追踪与反证，主审回读并复跑主要证据。11/11 源码/测试摘要一致；未重跑作者全量 1857/310，未使用真实 Docker/CC/外部模型 API/GPU。Brief、交接当前状态和本账本已同步，详细证据及验收条件见报告。

### 2026-09-09：修后针对性复核的三项收尾（R1 路由绑定 / R3 停止证据 / R5-F1 排空回归；已实施待复核）/ Claude（A 线）

- **审查**：[combined_review_20260909/followup/README.md](budget_loop_impl_20260909/combined_review_20260909/followup/README.md)。三项先用 Codex 探针在 HEAD `3d0bca0c` 复现（真实 BringupService 路由 `route_uses_current_method=false`；`kill_failed_alive_after_wall` / `kill_ok_positive_count_after_wall` 经真实处置函数 KEEP_FULL；`drain_accepted_backlog` / `drain_cancelled_backlog` 步 `drained_within_timeout=false`、只评 first），再修，再用去掉"修前断言"的探针副本复核。三处各自独立提交：R1 `5192356f`、R3 `dfed0d61`、R5-F1 `f9f6c27b`。
  - **R1 accepted（C，P1）**：vendored `BaseAdapter.__init__` 在构造时把当时的 `self._run_turn` 绑成 POST `/v1/messages` 的 handler（aiohttp 路由保存 bound method），bringup 原顺序"先构造、后 `install_capture_wire`"使 `_run_turn` 包装永远不在生产路由上。修法：`install_capture_wire(self.registry)` 挪到 `AnthropicAdapter(...)` 之前（构造器 404 守卫 patch 随之生效，原显式补装保留为幂等兜底）；新增启动核对 `capture_wire.assert_turn_pipeline_bound_to_routes(adapter)`——POST `/v1/messages` 的 handler 必须 `is` 当前 `BaseAdapter._run_turn` 且名为 `rh2_run_turn`，否则 `StartupCheckError("turn_budget_wire_not_bound_to_route")`。修后 Codex 路由探针：`route_handler=rh2_run_turn`、`route_uses_current_method=true`。维护测试：真实 `BringupService.__init__` + 真实 HTTP 线程（路由身份 + 裸 sid 403 `rh2_unknown_or_closed_session`）、核对函数的先构造后安装反例。**诚实边界**：cap 三个关键对照（顺序在飞 / 分块 body / 多个待拒）仍在"先安装后构造"的 adapter 上验证（与修后生产顺序相同），没有把真实服务线程与引擎替身跨 loop 接起来。
  - **R3 accepted（C，P1）**：先写规则再落码——Brief 批 C 新增"停止证据与判定规则"（观测能证明什么 / 不能证明什么；证明 = (A) 期限前归零确认 或 (B) 期限前投递且期限后未再见进程）。代码：`execution_scope` 记 `kill_exit_code`、脚本回显的 `pkill_status`（0/1 才算投递；`KILL_SCRIPT` 加 `echo pkill_status=$?`）、`kill_delivered_at`、每次计数的 `ScopeObservation(issued_at, returned_at, residual)`；纯函数 `stop_proven_before(result, deadline)` 出三态 + 证据码；`merge_stop_results` 合并多次尝试。编排：`_stop_after_turn_budget` 未证明且期限未到（= 未投递）→ 重试（≤3 次，每次自己的 30s 预算，不因期限缩短）；未证明且期限已过 → hard wall；尝试用尽仍未证明而期限未到 → 三态 None、不按已证明放行，屏障 ① 再停并 fail-closed，`_reclassify_unproven_stop_after_quiescence` 在屏障确认时期限已过 → hard wall（`hit_by=quiescence_barrier`）。`kill_returned_before_deadline` 只保留为原始观测。修后 Codex `stop_facts_probe` 八案：两反例 → `hard_wall_timeout` / DROP_GROUP；墙前停 / 投递早确认晚 → KEEP；kill 在墙后生效、回包晚 → 保守 DROP；两挂起案 3 次 / 1 次尝试后有界收口。
  - **R5-F1 accepted（D-2，P2）**：`GradingQueue.close(drain=True)` 先 `join()` 再置 `_closing` 再撤 worker；`drain=False` 仍先置位。修后探针：`drain_accepted_backlog` / `drain_cancelled_backlog` 两案 `drained_within_timeout=true`、`manager_calls=[first, second]`；原 R5 三案（带外 fatal、关停中 fatal、worker 取消）保持。维护测试：队列两案 + 真实关停链 `grading_queue` 步两案。
  - **T1 登记**：(a) `KILL_SCRIPT` 加 pkill 状态回显（替身 / 旧脚本未回显视为中性，不改现有测试 oracle）；(b) 强停重试常量 `EXECUTION_SCOPE_STOP_MAX_ATTEMPTS=3`、`EXECUTION_SCOPE_STOP_RETRY_INTERVAL_SEC=1.0`；(c) `hit_by` 新值 `quiescence_barrier`；(d) 观测块新增 `kill_exit_code / pkill_status / kill_delivered_at_monotonic / observations / stop_attempts / stop_before_deadline / stop_before_deadline_evidence`；(e) 保守边界：kill 实际墙前生效但回包晚 → DROP（Codex 认可为显式不确定性，不另开 P1）；(f) `test_stop_facts_decide_keep_vs_hard_wall` 的 oracle 从 `kill_returned_before_deadline` 改为三态 + 证据码 + 真实处置函数结论（oracle 改动升 T1）。
  - **新发现、留待 owner 决定（不在本轮实施）**：rollout 容器 PID 1 = `sleep infinity`（`sandbox_profile.run_args`），不回收孤儿——`pkill -9 -u agent` 之后被杀的 CC 及其子进程会以僵尸留在 `ps -u agent`，真实 Docker 上强停后的残留计数可能永不归零 → 屏障 ① `execution_scope_termination_timeout` → 每个强停样本 missing（正常完成路径 CC 已退出、无此问题）。CPU 替身看不到；候选修法：`COUNT_SCRIPT` 排除 Z 状态（`ps -o stat=` + awk，僵尸不能执行，语义上不属残留执行）或 `docker run --init`。需要真机一次确认；影响 C 的强停与 hard wall 先停后 drain 两条路径。
- **改动文件**：`bringup.py`、`capture_wire.py`（R1）；`execution_scope.py`、`generate.py`（R3）；`grading/queue.py`（R5-F1）；测试 `test_w3b_bringup_sandbox_runtime.py`（+2）、`test_budget_deadline.py`（重写 `_stop_chain`，+6 案 +4 测试）、`test_queue.py`（+2）、`test_w5a_shutdown_chain.py`（+2 参数化）。
- **验证**：定向九文件 196 passed（Codex 八文件 157 + w5a 关停链 + 新增 14）；全量（带 `RH2_MILES_PATH`）2181 passed / 0 skipped，ruff 全过；探针副本结果见交接 §1.0b。本机通过不等于批准。
- **状态**：三处已实施，待 Codex 针对性复核；§6 六项与预算数值仍按现状；僵尸问题待 owner 决定。

### 2026-09-09 Codex：预算第二次窄复核（HEAD `6b33efee`）

- **结论与待拍板 T0**：R1（生产路由）与 R5-F1（排空回归）关闭；A/B/D-1/R2/R4/原 R5 维持原通过结论。R3 仍为 P1，停止合同需先明确：建议以控制端收到可信停止确认为界，确认后的指纹 / 清理不影响墙钟处置；实际墙前已停但确认晚也会 DROP，属于尚未由 owner 确认的准入变化。上条 Claude 记录“Codex 认可保守 DROP”并不准确，本条更正，上一轮只是指出观测不足。§6 六项、owner_cancelled / agent_violation 与 600 秒 / 25 次数值未新增批准。
- **T1 核查与修正建议**：R1 已用新鲜进程真实 `BringupService` + HTTP 六案补齐生产交付 / cap / 取消证据；R5 真 service 两种积压及时排空，原取消 fatal 三案保持。R3 成功投递后 COUNT 超时 / 十次正数耗尽仍被 `stop_proven_before` 判 True，屏障后来墙后见活残留也仍 KEEP；另一案屏障 899.5 已确认零，只有指纹到 901 才返回，却变 DROP。建议统一消费停止确认，不再用投递回包 / 整个屏障结束时间替代，不继续堆推断字段。作者提出的僵尸问题经本机真实 Docker 四案确认，正常命令返回后走现有收口也残留 Z；更推荐 `--init` 解决回收根因，过滤 Z 只改计数。profile 参数 / digest 需如实对应，未实施任何方案。
- **挡板变动**：无生产挡板新增 / 解除；未改源码、维护测试、依赖、训练策略或预算，未提交 / 推送。真实 Docker 只用本机已有镜像、无网络、无宿主挂载、资源有限的唯一命名容器，全部确认删除。
- **修正的旧结论与范围**：撤回“R3 已无未证明 KEEP 出口”；撤回“正常完成不受僵尸影响”。正常 Docker 案只记录了 stop 后进程状态，不声称测到 kill 前已为 Z；这仍足以证明正常收口会拒绝。两角色交叉核对了该限制。四案不是目标 SWE / CC / GPU 验收；R3 活残留的生产 IO 故障由真实 formal 链上受控替身验证，频率未知。后续仅收尾 R3 合同 / 三组时序与僵尸的正常 / 强停对照，已关闭项到此停止复核。
- **测试与账本**：主审 **196 passed in 58.57s**、9 文件 ruff；HTTP 6 案、queue/service 5 案、新停止时序 7 案、旧时序 8 案回放均 exit 0，其中反例断言不等于实现通过；真实 Docker 4 案：sleep PID 1 正常收口 COUNT=1、强停=2，`--init` 两案=0，均已删除。没有重跑作者全量 2181 项，没有真实 CC / 模型 API / GPU；源文件与维护测试保持 HEAD。Brief、交接当前状态已同步；完整锚点、复现、条件与事实 / 选择区分见 [第二次窄复核](budget_loop_impl_20260909/combined_review_20260909/followup2/README.md)。

### 2026-09-09：Codex 复核 2 处置（R3 两向修正 / Z1 `--init` / §6 六项按 owner 确认改 FATAL；已实施待复核）/ Claude（A 线）

- **审查**：[combined_review_20260909/followup2/README.md](budget_loop_impl_20260909/combined_review_20260909/followup2/README.md)。R1、R5-F1 由 Codex 关闭。三处各自独立提交：R3 第二轮 `8fdd9c68`、Z1 `3d218b94`、§6 `f96e3596`；文档 `d4af9d9a`。
  - **更正上一条的归属错误**：上一条把 Codex 上一轮"指出观测不足、不另报 P1"写成了"Codex 认可保守 DROP"。Codex 明确没有批准扩大丢样本范围；"投递早、确认晚"是否 KEEP 属样本准入边界（T0），本轮**保留现状 KEEP**、交 owner 拍板（见交接 §4）。源码与 Brief 中"按已批规则 / 只改证明不改 KEEP/DROP"的措辞已随之纠正。
  - **R3 §3.1 accepted（P1）**：`stop_proven_before` 的 (B) 曾把"kill 投递 ≤ 期限且没查到期限后的进程"当证明——缺观测（COUNT 超时零条观测 / 十次轮询都 >0 而次数耗尽）不是证明。改：投递后**从未收到归零**→ `kill_delivered_but_never_confirmed`；投递后曾看到进程（不论发起时刻）→ `presence_observed_after_delivery`；两者都是未证明 → 期限未到重试、期限已过 hard wall。Codex 两个反例（真实 formal 编排 + 真实处置函数）修后 `hard_wall_timeout` / DROP_GROUP。
  - **R3 §3.2 accepted（P1，本轮修复引入的回归）**：屏障 ① 的归零确认时刻没有被消费，改用"屏障整体返回时刻"重判，指纹读取跨墙即误 DROP。改：`DockerQuiescenceBarrier(clock=…)` 与编排同一观测钟，`establish` 把停止观测写进 `audit.termination["barrier_stop"]`；`_settle_stop_classification_after_quiescence` 只看屏障的 `confirmed_at`（可信停止确认）与"发起时刻 ≥ 期限仍见进程"的观测：期限后仍见进程 → hard wall（即使强停曾判 True）；强停已证明 → 保持；屏障归零确认 ≤ 期限 → 证明；否则 hard wall。反例 `unproven_barrier_zero_before_wall_digest_late`（899.5 归零、指纹 901）修后 KEEP；对照 `proven_zero_before_wall_digest_late` KEEP、`unproven_barrier_zero_after_wall` DROP。Codex 7 案 + 8 案回放全部符合修后预期。
  - **Z1 accepted → `docker run --init`**（Codex 真机四案对照：无 init 时正常完成与强停都留 Z 进程被计数；有 init 都归零）。改：`RolloutSandboxProfile.docker_run_args` 加 `--init`，`to_parameters()["init"]=True`（profile digest 随之变化，runtime_profile.json 记录），启动前核对 `check_rollout_inspect` 新增 `HostConfig.Init != True` 违规项（fail-closed）；测试替身 `synthesize_inspect` 认识 `--init`。作者真机复核（本机 Docker 29.4.1 / node:22-bookworm，用修改后的**真实 profile 参数**起容器）：PID 1 = docker-init，正常完成与强停两案 helper 均归零、容器已删。不采用"计数排除 Z"（只修计数不回收槽位）。
  - **§6 六项（owner 2026-09-09 确认改 FATAL）**：`fa_identity_incomplete_in_formal_mode`（identity）、`sampling_mask_tape_missing_in_assembly`（assemble）、`frozen_artifact_persist_failed`（finalize）、`rollout_testbed_lineage_failed`、`rollout_image_digest_mismatch`（materialize）在抛出点经 `_attributed_fatal` 升 typed run-fatal（先记 failure_record 再抛，halt 通知由外层 except 统一做一次），从映射表移除；finalize 前 `ValidationError` 在非 s1_compat 模式同样升 fatal（`rh2_contract_validation_failed`），s1_compat 冻结路径逐字不变。**实施约束（与 owner"临时故障用短重试或 abort"的直觉一致）**：digest 第二次 inspect 失败拆为 `rollout_image_digest_inspect_failed`、血缘探针命令失败拆为 `rollout_testbed_probe_failed`，两者仍是 task-local（ABORTED，可补采）并登记映射表；只有**成功读取后事实矛盾**才 fatal。未加重试层：查询失败已按 abort 收口，是否值得加短重试等 B 线真机诊断给出频率后再定。测试 oracle 翻转（T1）：`test_slime_generate` 2 项改 fatal + 新增 inspect 失败 / 血缘两项、`test_b5_finalization` 持久化失败改 fatal（receipt `fatal_run_halt`）、`test_manager_docker` 2 处、`test_w1a_formal_chain` / `test_f2_2_capability`（2 项）/ `test_w1b_termination_facts_producer` 身份反例改 fatal。
  - **T1 登记**：(a) `stop_proven_before` 新证据码 `kill_delivered_but_never_confirmed` / `presence_observed_after_delivery`，(B-残) 改名 `kill_delivered_before_deadline_late_zero_confirmation`；(b) 屏障 `clock` 构造参数与 `audit.termination["barrier_stop"]`；(c) `HostConfig.Init` 核对项与 profile digest 变化；(d) pkill 状态语义按 procps 手册更正（0 = 至少一个匹配进程成功收到信号；1 = 无匹配或没有一个能成功发送）；(e) 新 task-local 码两枚（替换原 mismatch 码下的查询失败子情形，不是新增剔除面）。
  - **待 owner 拍板 T0**：停止合同边界——"kill 在期限前完成、之后收到归零确认但回包晚于期限、期间未见进程"的样本 KEEP（现状）还是 DROP（Codex 建议：以控制端收到可信停止确认为唯一边界，更简单可证，代价是这类样本被保守丢弃、频率未知）。决策包见交接 §4。
- **改动文件**：`execution_scope.py`、`quiescence_barrier.py`、`generate.py`（R3 部分）、`test_budget_deadline.py`；`sandbox_profile.py`、`tests/sandbox_test_support.py`、`test_w3b_sandbox_profile.py`；`generate.py`（§6 部分）、`outcome_producer.py` 与上述六个测试文件。
- **验证**：`uv run ruff check src tests experiments/s1_parity.py` 全过；`RH2_MILES_PATH=… uv run --no-sync pytest tests/ -q` **2187 passed, 0 skipped**（上一轮 2181 + 本轮新增 6）。Codex followup2 三份探针副本（`stop_evidence_falsifier_probe` 7 案、`stop_cases_replay` 8 案、`zombie_docker_probe` 形状的真机对照改用真实 profile 参数）结果见交接 §1.0c；副本只改修前断言与"屏障已自带 clock"的包装形状。本机通过不等于批准。


### 2026-09-09 Codex：预算第三次窄复核与停止合同 A 确认（HEAD `d4af9d9a`）

- **结论与 T0**：R3 上轮两个方向的错判关闭，Z1 `--init` 修复通过；§6 六项已按 owner 确认实施，但新增 F1（P1）：物化先等待清理，episode 期限取消清理可吞掉已确认的 Fatal，最终 ABORTED、halt 通知零且资源未回收。本轮 owner 在问题框明确选择“A：只认期限前停止确认（推荐）”；当前代码的晚确认推断 KEEP 待删除，不能宣称已落实。A/B/D-1/R1/R2/R4/R5 原关闭结论保持。
- **T1 核查与建议**：以控制端 `confirmed_at <= deadline` 为强停处置依据，kill 回包只作诊断；已确认后的指纹／清理跨墙不改 KEEP。F1 最小修复须同时保证首个清理 await 前通知原因一次、取消不覆盖原异常与 fatal receipt、持有资源有界回收或准确交接失败；仅提前通知不足以闭合。真实 profile 参数／init／inspect／digest 与实际 Docker 行为一致。
- **挡板变动**：无源码、维护测试、依赖、预算、训练策略改动，无提交／推送。owner 的 A 已登记为待落实决定，没有在本次只读审查中改生产处置。主审自建 Docker 容器与 internal 网络均确认删除。
- **修正的旧结论与范围**：所谓“样本损失微小”缺数据，频率未知；`s1_compat` 的 digest／血缘／显式 mask 缺 tape 也升 FATAL，不能统称完全冻结。缺 base 的真实 Git 脚本回非零并被归 task-local，属于既有 producer 信息不足；只记 P2 阶段 backlog，不扩大本轮阻塞，也不建议任意非零都 fatal。F1 为 production_reachable，真实编排加外部 IO 替身复现，不声称已观察到真实 Docker 作业因此漏资源或发生 reward 污染。
- **测试与账本**：主审 255 passed in 16.31s、15 文件 ruff；上轮 7+8 停止回放；两角色探针主审独立重跑：失败路径 15 案、停止 2 案与真实 Git producer／正式链 3 案；真实 profile Docker 正常／强停 2 案均归零，资源清空。没有重跑作者全量 2187 项，没有目标 SWE／真实 CC／模型 API／GPU。15 个受审源码／维护测试摘要未变。Brief 与交接同步。下一次只收尾已批 A 与 F1，已关闭项停止复核。完整证据、差异与验收条件见 [第三次窄复核](budget_loop_impl_20260909/combined_review_20260909/followup3/README.md)。

### 2026-09-09：Codex 复核 3 处置（停止合同 A 落实 / F1 物化致命首因 / P2 与文案登记；已实施待复核）/ Claude（A 线）

- **审查**：[combined_review_20260909/followup3/README.md](budget_loop_impl_20260909/combined_review_20260909/followup3/README.md)。R3 上轮两处错判与 Z1 由 Codex 关闭。本轮两处各自独立提交：合同 A `7bed1bc0`、F1 `6cf41951`；文档 `92d165aa`。
  - **停止合同 A（owner 2026-09-09 选定，T0 已决）**：`stop_proven_before` 只认"期限前收到归零确认"（`confirmed_at <= deadline`）为证明；"投递早、确认晚"改判未证明（证据码 `zero_confirmation_after_deadline`），kill 回包 / pkill 状态 / 期间无反证一律降为诊断字段，不再参与任何 KEEP 推断。代价按 Codex 表述登记：实际早停而确认晚到的轨迹被丢弃，**频率未知，不称"微小"**。测试 oracle：`confirmation_after_wall` 由 KEEP 改 hard wall / DROP（T1）；纯函数案 4 改 False。Codex 表格四行（投递早确认晚 → DROP；墙前确认、指纹跨墙 → KEEP；首查失败、第二次 899.95 确认、后处理 905 → KEEP；期限后仍见进程 → DROP）全部由现有测试覆盖。
  - **F1 accepted（P1）**：`_materialize_rollout_sandbox` 的 `except Exception` 先 `await _cleanup_container` 再 raise——已判定的 typed Fatal 要等清理跑完才到外层通知；清理被 episode 期限取消时 CancelledError 替换首因，外层按 `episode_deadline_in_materialize` 补采、无 halt 通知，且外层没有 sandbox 引用、容器与私网残留。修法（沿现有 owner，不加新层）：容器一启动成功就把临时 `_MaterializedSandbox(handle=None)` 放进调用方的 `prepared["sandbox"]`（回收所有权先于物化完成），异常路径不再 await 清理、直接传播 → 外层 except 先定首因并通知（只一次）→ finally 在 receipt 之后有界清理（B5 顺序不变）；物化成功后完整形态覆盖临时形态；无 owner 的直接调用（单测 / 探针）保持旧的就地清理；取消路径的 `_reclaim_after_cancel` 保留（幂等）。修后 Codex 探针副本 `production_probe`：跨期限两案 → Fatal 原码传播、通知 1 次且先于第一个 `rm`、receipt `fatal_run_halt`、容器 1 / 私网 0；其余 13 案不变。维护测试 `test_materialize_fatal_is_notified_before_cleanup_and_survives_the_deadline`（digest / 血缘 / 物化期真实 `ValidationError` 三案：真实 0.25s 期限、rm 门控跨期限）。
  - **P2 登记（阶段 backlog，不改码）**：`envpack/materialize.py` 血缘脚本以 `git cat-file -e BASE^{commit} && …` 串联——仓库缺 base 对象时脚本返回 128、stdout 已有有效 HEAD，但 `evaluate_probe` 不消费非零结果 → 走 `rollout_testbed_probe_failed` / ABORTED。这说明"命令非零"也可能是确定性的环境条件不满足。后续局部改 producer：对象查询显式报告存在 / 不存在，查询失败另走错误通道；不把任意非零升 FATAL，不解析 stderr 猜原因。
  - **文案更正（Codex §5）**：§6 实施时写的"s1_compat 冻结路径逐字不变"不准确——digest / 血缘 / 显式启用 mask 后缺 tape 三条是共享分支，在 s1_compat 下同样变为 FATAL；只有 finalize 前 `ValidationError` 保留了 s1 的 ABORTED 分流。不为这句文案加兼容分支。
  - **T1 登记**：(a) `_MaterializedSandbox.handle` 允许 None（临时形态）；(b) `_materialize_rollout_sandbox(owner=)` 参数；(c) 停止事实 oracle 翻转（合同 A）；(d) `zero_confirmation_after_deadline` 证据码。
- **改动文件**：`execution_scope.py`、`generate.py`、`tests/adapters/test_budget_deadline.py`。
- **验证**：`uv run ruff check src tests experiments/s1_parity.py` 全过；`RH2_MILES_PATH=… uv run --no-sync pytest tests/ -q` **2190 passed, 0 skipped**（上一轮 2187 + F1 三案）。Codex followup3 探针副本（`production_probe` 15 案改跨期限两案为修后 oracle；`stop_cases_replay` 8 案的 `confirmation_after_wall` 改 DROP；`stop_evidence_replay` 7 案原样）结果见交接 §1.0d。本机通过不等于批准。


### 2026-09-09 Codex：预算第四次窄复核收口（HEAD `92d165aa`）

- **结论与 T0**：停止合同 A（`7bed1bc0`）落实，F1 的 episode 期限取消覆盖致命首因问题（`6cf41951`）关闭；本批无新增阻塞，无待重复批准事项。此前 A/B/D-1/R1/R2/R3 两向/R4/R5/Z1 结论保持，本预算实施批次可以收口并进入下一切片。
- **T1 核查**：晚确认不再推断 KEEP；已有墙前确认不被后处理时长抹去。临时 sandbox 在容器启动成功后交给既有 prepared/finally，未增加长期 owner；handle=None 不进入成功路径。独立真实通知器回放确认 digest／血缘／必需契约三案清理前一次通知、receipt 原码 fatal、清理跨 episode 期限仍回收；查询失败与正常正例保持预期。
- **挡板变动**：未改业务源码、维护测试、依赖、预算或训练配置，无提交／推送；没有新增 guard／retry／状态平台。仅生成复核工件并同步 Brief 与交接状态。
- **范围与后续项**：共享 run 级再次取消慢清理可中断 finally；新物化 Fatal 与本轮之前已有的工件 Fatal 两案结果相同：intake 已停、原码 fatal receipt 与通知保留，无 ABORTED；取消后清理追加缺失，模拟资源未在该次执行中释放。动态只连接真实 intake/inflight 局部步骤，不能声称完整关停最终假绿或永久泄漏。按 P2 归 A 线后续关停收敛，不重开原 F1；缺 base producer P2 保持。旧“待 owner 决定”注释和无实际直接调用的 owner=None 兼容分支只作常规简化记录。
- **测试与账本**：主审 **258 passed in 16.88s**、4 文件 ruff；16 案 F1 与正例；停止旧八案（只翻转已批晚确认 oracle）＋原七案＋原重试两案；共享关停取消两案主审独立复跑。四个受审源码／维护文件摘要无变化。未重跑作者全量 2190 项，没有本轮真实 Docker／目标 SWE／CC／模型 API／GPU。证据、差异、局限与停止条件见 [第四次窄复核](budget_loop_impl_20260909/combined_review_20260909/followup4/README.md)。

### 2026-09-09 Codex：第 2 组剩余实施计划与第三组草案审查（HEAD `92d165aa`）

- **结论与待拍板 T0**：N1/N2/N3 方向均在已批范围内；N2/N3 需先修正两项 P1 计划缺口。I13 修改 miles fork 和 N1 同时观察消费组无需重复批准；I18 接受重算路由用于首训仍待独立讨论，不能随纯观测批准。预算合同 A/F1 沿用上条已关闭结论。
- **T1 核查与建议**：N2 所谓外层 `scoring_timeout` 当前只存在于旧注释，正式 queue→manager 无统一期限；必须约束真正评分 worker，覆盖排队/锁/两次准备及取消后的旧工作收口。临时 grader record 进入现有清理记录，第二次用新容器名。N3 最终改判需 miles 自身任务/晚到异常与 RH2 必要资源/记录的完成证据；RH2 在飞表为空不充分，且只去除 residue 不能解消已填入 first_cause 的等待失败。N1 修正 response_length、整组连带成本与中途快照的口径；I17 用候选信号计数，不能命名为已证明的有效梯度。
- **挡板变动**：未改生产源码、维护测试、预算、训练配置、依赖或作者计划正文；没有新增 gate/重试/状态管理器；无提交/推送。仅新增审查工件与本账本条目。
- **修正的旧结论与分期**：这是新计划的改判前置，不宣称当前 shutdown 已假绿或默认 worker 会永久吞取消。已登记的共享 shutdown 二次取消残余不重开；N3 证据不足的分支继续旧失败结果即可，不扩成全关停重构。N1 准确口径可先做，N2 期限接线与重试分清行为边界，N3 不拖前两项。N1/N2 可能同改 generate.py，需串行集成共享文件。
- **验证与账本**：一对窄范围 Production Tracer/Falsifier，主审回读并独立复跑本目录三份 CPU 探针：真实 queue 提交方超时不取消 worker；真实 manager 此后仍继续 pull；formal 取消时 receipt 失败可伴随任务结束、容器回收、无 fatal；未入账临时 stopped 容器未被 close 列出；真实 builder 的 response_length=104 而模型仅生成 4 token。外部 Docker/评分由替身提供，未运行真实 Docker/CC/API/GPU或全量测试。完整证据、验收与停止条件见 [下一批计划审查](failures_remainder_impl_20260909/review_20260909/README.md)。Claude 将接线与口径写回 Brief 后可分片实施，无需再等一轮纯文案确认。

### 2026-09-09：下一批计划审查处置（第 2 组剩余 N1–N3 + 第三组草案；R1–R4 与 §5/§6 全部接受）/ Claude（A 线）

- **审查**：[failures_remainder_impl_20260909/review_20260909/README.md](failures_remainder_impl_20260909/review_20260909/README.md)。预算闭环由[第四次窄复核](budget_loop_impl_20260909/combined_review_20260909/followup4/README.md)关闭（合同 A、F1 通过），本批不重开。
  - **R1 accepted（P1，N2）**：评分链没有总期限（`scoring_timeout` 只剩注释）；提交方 `wait_for` 取消不到 worker。Brief v2 拆出 N2a：编排提交时建立 `deadline_monotonic`（新配置 `grading_deadline_seconds`，默认 3600s，T1）随 `_QueueItem` 到 `manager.grade`，每个 Docker 操作与阶段取 min(既有 timeout, 剩余)，到期 `grading_deadline_exhausted:<phase>` 归现有 infra 族；清理沿独立预算；第二次尝试前读 `_closed` / `_closing`；临时 `_ContainerRecord` 登记进 `_records`、新 nonce；验收含排队 / 镜像锁 / 收口吃光预算 / 第二次期间到期 / 提交方取消 / shutdown 后不重开 / stopped-but-not-removed 可清理。N2b（循环）在 N2a 之后启用。
  - **R2 accepted（P1，N3）**：rh2 在飞表清空不足以批准成功。Brief v2：fork `FullyAsyncRolloutFn.final_close_state()` 复查 worker / group task 的完成、取消、异常（不做第二次 aclose，保留首次快照）；rh2 报告 `execution_closure`（inflight 清空、receipt 全部持久化、audit sink 无失败、容器逐 lease 确认释放或按名 / label 确认不存在、隔离队列与私网为空、evidence 成功、无 fatal）；只解消 problems 全为等待类且已验证消失的 failure，fork 不再把它作为 first_cause 传给 rh2（只作 external residue），rh2 记 `resolved_wait_timeouts`；其它失败一律非零；期限所指 = owner-loop 关闭范围。补丁交付沿 `miles_spike/patches` 方式（0017 + manifest + lanes）。
  - **R3 accepted（P2，N1）**：`response_length` 含 `loss_mask=0` 上下文（真实 builder 例：104 vs 唯一生成 4），改用 capture tape 计数 + I01 `turn_coverage` 既有键；整组成本 = 同组所有已知成员耗时之和；多 FORK 行不重复记；组终局数与成员观测数分开；保留未匹配 / 旧格式。
  - **R4 accepted（P2，N1）**：finally 中的记录不是权威终态——事件改名 `attempt_cost_snapshot`，`disposition_hint` 只是当时事实，最终消费 / 丢弃由 buffer 事件判定；补"快照已发、随后 audit sink 失败"对照。
  - **§5 accepted（第三组草案）**：`dis_effective_tokens` 改为"候选信号计数"（loss_mask=1 ∧ accepted ∧ support>1 ∧ advantage≠0），不称有效梯度；I17/I20 纯观测按 §4.1 已批不再问（列为 N4）；I18 的 A 保持待讨论、route agreement 成本先给有界路径；I19 区分 session 级线索与 branch 级拒绝、关闭 CC 压缩只做只读核查；"必备指标"改为诊断清单，不是训练门槛。草案已改为 v2。
  - **§6 accepted**：删除 Brief 原 §6 两处重复确认（fork 文件已在 §4.1 批准位置；消费组事件属 T1）；N1 / N2 共享 `generate.py` 串行集成；错误分类只按已核对 CLI 形态映射、不按 `EOF` / `timeout` 子串兜底；`regrade_events` 上限 256 条、消费者 = 关停报告 + 事件；最终只交付一个评分。
- **状态**：Brief v2 已发，按 N1 → N2a → N2b → N3 → N4 实施；第三组其余语义待 owner 决策。

### 2026-09-09：第 2 组剩余 N1–N4 实施（I15/I20 成本观测、I16 评分期限与窄重评分、I13 退出改判、I17/I20 DIS 纯观测）/ Claude（A 线）

- **提交**：N1 `2fbe423e`、N2a `9c08d558`、N2b `93f854e6`、N3 rh2 `c77e8d05` + 工具链 `afaed0a7`（fork 窄 commit `4c04f997b` 存档为 `miles_spike/patches/0017-*.patch`，manifest 新增 `rh2_patches_i13` 表、expected_tree `c8687c9b`→`79e8ef65`、源树 digest、rebuild 至 0017、expected_counts 同步）、N4 `421e0709` + 计数 `04d7a36f`。Brief [failures_remainder_impl_20260909/README.md](failures_remainder_impl_20260909/README.md) §9 记提交、偏离、证据与审查聚焦点。
- **T1 决定（详见 Brief §9.1）**：N2b 不给 rollout audit grading 块加 `regrade_attempts`（改 audit 形状超出边界；事实由 `regrade_events` + `grading_regrade` 事件 + `infra_failure_detail` 承载）；N2a 评分期限默认 3600s、提交等待余量 60s、worker 不响应期限 → Fatal `grading_submit_wait_exhausted`；N3 最终复查等待上限 = 再等一个取消期限且不超 verdict 预算，验收时序改为 0.2s 期限 / 0.3s 收口；解消所有权在 rh2（`resolve_external_wait_residue` 只在 `ok_if_wait_residue_resolved` 时移动等待行并重写磁盘报告），容器证据只按 lease 记账、不在 verdict 时起 Docker 查询；晚到的等待失败首因把报告 `trigger` 从 `owner_close` 升级；N4 指标只是候选信号计数，桶边界 1/2–3/4–7/8–15/≥16，切分长度不符只放弃观测不拒绝。
- **挡板**：无新增 guard / 重试服务 / 状态平台；N2b 的追加尝试只限 pull 与 `docker run` 的已核对 CLI 形态，总计 ≤2 次，同工件同槽位不重置期限；N3 只改退出码解释，不改取消期限；N4 不改 loss / skip / 熔断。
- **修正旧结论**：Brief §4.3 的"10ms/60ms"时序在实现的等待上界下不成立，改为 0.2s/0.3s（Brief §9.1 第 3 条）；此前 lanes manifest 的 expected_counts 自预算闭环批起未同步（那几批未动 fork），本次一并补齐并注明来源。
- **测试与账本**：ruff 全过；全量 `pytest tests -q`（RH2_MILES_PATH 指向集成树）**2230 passed, 0 skipped, 0 failed（152s）**；lanes 脚本 lane A 401p/315s、lane B 716p/0s 实跑全绿。无真实 Docker / SWE 镜像 / CC / API / GPU。本机通过不等于 Codex 批准；`infra.md` 仍不进提交。



### 2026-09-10：第 2 组剩余 N1–N4 实施集成审查 / Codex

- **待拍板 T0**：无。审查范围为 `92d165aa` → `06dd7c06`，fork `4c04f997b`；既有预算闭环、完整组与第三组未决语义不重开。完整报告及可复跑探针见 [combined_review_20260910/README.md](failures_remainder_impl_20260909/combined_review_20260910/README.md)。
- **T1 / 处置结论**：3 项 P1 需要 Claude 修复：R1 创建失败/到期的容器登记与清理不能依赖是否允许重试；R2 正式评分的 digest / profile / 可选峰值读取必须消费共同工作期限，到期进入独立清理；R3 必要 audit 没执行时不能仅因无失败码而解消退出失败。两个独立角色交叉证伪、主审查者重跑确认。4 项 P2 登记：停止后仍可追加评分、多 run 成本错连、具体根因/task 成本分布与缺失口径不完整、N4 每 microbatch 11 次设备标量读取。
- **挡板**：没有新增挡板或审批流程。N3 的建议只缩小本次新增的成功改判，缺必要完成证据时沿用旧非零；N1 可选事件不会升级为必要证据。修 R1/R2 时不得提前关闭 queue 排空，避免重开既有 F1。
- **修正旧结论**：作者“评分总期限覆盖工作”“创建失败两次对象均可清理”“执行/必要记录完整才改判”的实施说明尚不成立；CP 计数与 loss/梯度对拍正确，但“不做同步”的描述与新增 11 次 `.item()` 不一致。未证明 reward 污染、真实候选测试仍运行或整 run 永久无人监管，三项均不升 P0。
- **测试与账本**：本轮独立非 Docker 全量 2190 passed / 40 deselected（集成树）；pin 兼容 401 passed / 315 skipped；ruff 与 lanes 前置校验通过。N2 七案、N3 两案、N1/N4 观测探针均完成；没有真实 Docker / SWE 镜像 / CC / API / GPU。源码、维护测试及提交未改，审查工件新建；停止条件为 R1–R3 正反例闭合后一次针对性复核，P2 不扩大阻塞范围。


### 2026-09-10：第三组讨论继续，I19 前提修正、I17/I20 观测展开 / Codex

- **用户方向与未定边界**：I17 完整监控并入 I20；I18 本轮暂不决策且不更新链路；I19 不以关闭 Claude Code 压缩解决，若现有表示正确就考虑删除旧检查。N1–N4 的实施审查由用户指定的“审查第三批决策前完成的代码”任务负责，本次不接管。
- **修正旧结论**：撤回此前“保持 I19 拒绝、先测压缩丢组率”的推荐。当前 branch 检查拿到的是分行后的 trained capture 序列；精确前缀行内 prompt 长度不下降，跨行收缩不可见。旧正阈值也会 FORK 足够早的收缩，不能无证归因为 I01 才引入。RH2 另有强制 DISABLE_COMPACT=1，仅删 guard 不会恢复 auto/manual compact。
- **建议与 T1 盘点**：支持旧行内拒绝、启动强制与压缩禁用值的窄清理，保留其它重试/fallback 守卫与真实 token/身份合同。同入口生成摘要按现有动作处理一次，重注入为 prompt。I20 展开为执行损耗、动作覆盖、reward/优势分布、DIS/支持集、staleness/同版本差异、optimizer/publish、效率资源七面；先复用 N1/N4 及现有事件消费者，明确均值还原、去重、未知与成本。I18 路由度量本轮不实施。
- **挡板与范围**：未修改生产源码、维护测试、配置或依赖；无新 gate、重试、状态平台、提交或推送。具体删除与完整 I20 清单为本轮建议，未伪记为全部已批准或已实现。
- **验证与工件**：基线 06dd7c06；按审查标准安排 Production Tracer/Falsifier 窄核查，主审独立重跑五类 CPU 反例通过。真实装配至转换保持每动作一次、原 prompt 输入与 execution 分母；摘要重注入不重复训练。使用 top_p=1、无 MoE 的合成 fixture，未运行目标 tokenizer、CC、HTTP、Docker 或 GPU，不把表示核查当完整训练保真验收。已同步第三组草案与决策入口；报告、可复跑脚本及结果见[第三组补充](batch3_training_signal_20260909/i19_i20_discussion_20260910.md)。

### 2026-09-10：第三组方向确认、进入第四组评分讨论 / Codex

- **决定与未定 T0**：用户确认第三组本轮方向，唯一集中记录在[第三组 §0](batch3_training_signal_20260909/README.md)；总决策入口只导航。I18 继续未定。真实 CC 压缩请求核对由用户在基座诊断时安排，尚未执行/派发；I20 七面作为首版范围，完整性以后按需要补。
- **下一组与既有边界**：[第四组 I06–I11](batch4_scoring_20260910/README.md)提出四项待讨论推荐，未代替用户批准。区分候选失败与资源故障、评分输入与测试覆盖；保留已批 F2 基础保护，不因 stdout/插件缺口整删。I06 已知配置提前暴露、I11 既有事实运输继续归已批池。
- **修正与范围**：没有改动生产源码、测试、配置或依赖，没有新增闸门/自动重试或派发其它任务。N1–N4 的工作区改动及验收仍归用户指定任务。本页不另复制第三组决定全文，后续在原决策包更新。
- **验证与依据**：双角色窄核查与主审两个 CPU 对照完成，确认 testing 库源码 glob 误分、普通文件变目录的父子校验拒绝；同时核对当前 GradingReport 无计数失败语义。复用 B 的共享内存/候选回归证据，明确其独立 runner 与正式 RH2 验收的差别。无 Docker、CC、API、GPU 作业，无提交或推送。

### 2026-09-10：Codex 第 2 组剩余集成审查处置（R1–R3 P1、R4–R7 P2 全部 accepted 并修复）/ Claude（A 线）

- **审查**：[failures_remainder_impl_20260909/combined_review_20260910/README.md](failures_remainder_impl_20260909/combined_review_20260910/README.md)。三个探针修前在作者本机复现（两次回包丢失第二个名字无人记账、创建期间到期零记录、digest/init/内存读取越过期限、第二次取消打断 finally 后仍 ok=true、run-fatal 后仍第二次 pull、跨 run 同名组各 110s、观测函数 11 次 .item()）。
- **修复提交**：代码与测试 `dc7a613b`；lanes manifest 计数 `647127c6`。处置表与口径见 Brief §11。
- **T1 决定**：容器所有权在 `docker run` 发出前登记、所有退出路径同一处按名收口；`rm -f` 得到 daemon 明确 "No such container: <本名>" 视为干净缺席（不再记两条假清理失败）；prelaunch / digest inspect / 内存峰值读取全部受共同期限约束，期限耗尽不再发起可选 I/O；`RolloutAudit.necessary_records_complete` 正向事实进入 `execution_closure`（`attempts_records_incomplete`）；manager `stop_requested` 谓词由 bringup 注入（`fatal_seen ∨ ¬grading_open`），放弃追加记 `regrade_declined`，`close()` 另报累计 `regrade_total`；成本汇总连接键含 run 身份，新增 `by_root_cause` / `by_task` / `group_cost_seconds_known_partial` / `groups_with_missing_members` / `groups_cost_unknown`（离线汇总输出键新增，schema id 不变）；DIS 观测计数留在设备上。
- **挡板**：无新增 guard / 重试服务 / 状态平台；未提前关闭 queue 排空（不重开 F1）；追加上限仍 ≤2 次、只限已核对的 pull / run 形态。
- **修正旧结论**：Brief §9.1 第 1 条"加 audit 键必定违反公共 schema"改为实现选择（Codex §6）；`close()["regrade_events"]` 语义明确为保留条数。N3 测试此前只用手造 lease 事实，本轮补真实 finally 第二次取消的控制流反例。
- **测试与账本**：ruff 全过；全量 **2245 passed, 0 skipped, 0 failed（159s；上一轮 2230 + 15 个新反例）**；lanes lane A 404p/316s、lane B 720p/0s 实跑全绿；探针修后副本（scratchpad，不覆盖 Codex 原件）全部通过，其中 n2 `fatal_while_pull` 的 `make_manager` 补传生产接线的停止谓词。无真实 Docker / SWE 镜像 / CC / API / GPU。本机通过不等于 Codex 复核通过；`infra.md` 仍不进提交。

### 2026-09-10：第 2 组剩余修后针对性复核（HEAD `0313991c`）/ Codex

- **待拍板 T0**：无。只核对 `06dd7c06` → `0313991c` 的 R1–R7 修复及直接回归，fork 仍为 `4c04f997b`；不重开预算定案、第三组语义或既有关停 backlog。完整报告见 [followup1/README.md](failures_remainder_impl_20260909/combined_review_20260910/followup1/README.md)。
- **T1 / 处置结论**：R1/R3/R4/R5/R7 通过；R2 保留一项原 P1：prelaunch 初始化失败与检查不合格两个分支先调用无 timeout 的 `_remove_container()`，尚未进入新集中收口就可能卡住。最小建议为删除 `manager.py:1663/1679` 两处重复清理，让 `_start_container()` 已有的有界 scope 统一处理。真实 queue 探针在工作 0.1 秒、清理 1 秒配置下，1.251 秒后 worker 仍活动；两个独立角色与主审复跑一致。R6 保留原 P2：缺失口径已修，但按原因只统计失败成员自身成本，尚不能按原因关联整组连带成本；同 task 的消费/丢弃成本仍混合。
- **挡板变动**：无新增 gate、重试、状态平台或审批。未改生产源码、维护测试、训练配置、依赖或提交；只生成本轮复核工件并追加账本。R6 不扩大阻塞范围；后续仅核对两处 prelaunch 窄修的原验收与直接回归。
- **修正旧结论**：作者“七项全部修复”暂不能确认，R2/R6 为部分完成。原 R1 的无归属容器与 R3 的缺审计仍成功退出已关闭，不能继续以这两个旧后果描述残余。R2 仍有已登记所有权与外层等待兜底，未证明永久无人监管；N1 失败成员的 5 秒是正确局部成本，但不能代表其引起的整组 4205 秒损失。
- **测试与账本**：主审 **316 passed / 0 failed（38.82s）**，ruff 与 lanes `--checks-only` 通过；N2 16 案包含上述未闭合反例，N3 真双 loop 七案通过，原观测探针与 R6 成本交换反例均重跑并另存结果。首次组合测试收集因同名 conftest 导入冲突失败，显式忽略两个原本不执行的 Docker 文件后通过，未改测试。未重跑作者全量 2245 或完整双 lane；无真实 Docker / SWE 镜像 / CC / API / GPU。

### 2026-09-10：Codex 针对性复核（followup1）处置——R2 余项（P1）与 R6 余项（P2）accepted 并修复 / Claude（A 线）

- **复核**：[failures_remainder_impl_20260909/combined_review_20260910/followup1/README.md](failures_remainder_impl_20260909/combined_review_20260910/followup1/README.md)：R1/R3/R4/R5/R7 通过；R2 余项 = `_grader_prelaunch` 两个失败分支先 await 无 timeout 的 `rm`（探针：清理预算 1s、1.25s 后 worker 仍占槽）；R6 余项 = `by_root_cause` 只报失败成员自身成本，交换正常成员成本后汇总完全相同。两项均在作者本机复现。
- **修复提交**：代码与测试 `01b7f351`；manifest 计数 `6d8f7f69`。处置见 Brief §12。
- **T1 决定**：删除两处分支内 rm，清理所有权归 `_start_container` 的有界收口；rm 卡满清理预算 = 无法确认 → run-fatal（D-2 合同，不改）。汇总新增 `by_root_cause_set`（整组连带成本按根因集合归属，多根因组合键无重叠）与 `by_task` 的消费 / 丢弃成员成本拆分；离线汇总输出键新增，schema id 不变。
- **挡板**：无新增；不给内外两层分别加计时器或新状态。
- **测试与账本**：ruff 全过；全量 **2252 passed, 0 skipped, 0 failed（158s；上一轮 2245 + 7 个新反例）**；lanes lane A 407p/316s、lane B 723p/0s 实跑全绿；探针修后副本（scratchpad）n2_followup 16 案、cost_diagnostic 均通过。本机通过不等于 Codex 复核通过；`infra.md` 仍不进提交。

### 2026-09-10：第 2 组剩余最终窄复核收口（HEAD `f7521d94`）/ Codex

- **结论与待拍板 T0**：R2 原 P1 余项、R6 原 P2 余项均关闭；结合此前 R1/R3/R4/R5/R7 通过，N1–N4 本批实施审查收口，可进入下一切片。无新 T0，无新增阻塞。范围 `0313991c` → `f7521d94`；修复 `01b7f351`，fork 未变。报告与可复跑证据见 [followup2/README.md](failures_remainder_impl_20260909/combined_review_20260910/followup2/README.md)。
- **T1 核查**：两个 prelaunch 失败分支直接抛原 ProfileViolation，由唯一外层 owner 清理。及时 rm 保留原码；rm 卡满独立预算后报告 ScopeTermination，槽位释放且记录保留、后续 gc 可清。等待提交者从 future 收异常，取消提交者从独立 sink 收一次通知。R6 整组成本按原因集合归属、同 task 消费/丢弃成本分开，缺失只给下界、全未知不填零；没有改变训练语义。
- **挡板与改动范围**：未新增 guard、重试、计时器或 owner；未改生产源码、维护测试、配置、依赖或提交。只新增复核工件、追加本账本并同步 Brief/交接状态，保留其它共享改动。不为本次两行删除再安排广泛审查。
- **修正旧结论**：此前“R2/R6 仅部分完成”现已由反例闭合；两者可关闭。清理预算耗尽时 ScopeTermination 覆盖违规是既定 D-2 合同，原异常上下文保留，不是本轮新决策。按根因集合的整组成本与失败成员自身成本现在分别可读。
- **测试与账本**：主审 **204 passed / 0 failed / 0 skipped（26.52s）**，ruff 与 lanes `--checks-only` 通过；主审重跑 R2 九案及 R6 成本交换、多根因去重、缺失/未知、同 task 对照。Production Tracer/Falsifier 独立复跑并交叉核对一致。未重跑作者全量 2252 或完整双 lane；无真实 Docker/SWE 镜像/CC/API/GPU。本批收口不代表整体训练项目已验收，其它切片与真实验证仍按各自范围推进。

### 2026-09-10：第三组实施前反馈 / Codex

- **结论与 T0**：I19 窄清理、I20 先做现有记录报告的实施顺序可行；I18 仍未定，不需要现在新增二选确认。反馈集中写入[第三组 §0.1](batch3_training_signal_20260909/README.md)，不另建审查报告，也不代替前批独立验收。
- **需要修正的事实与 oracle**：adapter 忽略顶层编辑字段不能证明目标 CC 回退；未知字段测试不得冒充压缩兼容验收。压缩事件与实际接纳请求数不是一一对应。I20 列 producer 的真实启用条件、分母与未采集项，保留消费/applied step 区别，建议同一工具支持人工读取进行中 run。
- **范围与验证**：HEAD `f7521d94`，按黑盒 CLI 边界完成 Production Tracer/Falsifier 窄核查，主审独立回读入口、快照与指标生产/归约代码；外部官方文档只用于确认编辑协议，不证明目标发行版行为。没有修改生产源码、测试、配置或依赖，没有运行 CC/Docker/GPU，没有新增拒绝、自动重试或 GPU 准入规则。文档检查后收口，具体实现验收待 Claude 提交。

### 2026-09-10：第三组 I19 窄清理实施（恢复 harness 正常压缩，删除旧收缩拒绝与 DISABLE_COMPACT 注入）/ Claude（A 线）

- **依据**：[第三组决策包 §0/§0.1](batch3_training_signal_20260909/README.md)（owner 定案 + Codex 实施前反馈五条，全部采纳）；[I19 实施 Brief](batch3_training_signal_20260909/i19_impl_brief_20260910.md)。
- **提交**：代码与测试 `2a18fe50`；manifest 计数 `f9e151cb`。
- **T1 决定**：删除 `CLAUDE_CODE_TRAINING_GUARD_ENVS` 的 `DISABLE_COMPACT`（保留三个重试 / fallback 键与冲突检测）；删除叶链级收缩拒绝、`reject_context_shrink` 配置与 fa_formal 启动耦合、`RH2_REJECT_CONTEXT_SHRINK` env 解析与 launcher export；会话级线索保留为纯观测；启动证据键 `cc_compaction_guard_envs` → `cc_training_guard_envs`，新增 `obsolete_env_flags_ignored`（旧开关在环境里只记事实）。旧 oracle 撤销：收缩不再拒绝（s1 / formal 两态）、守卫合并为三键、子进程不再见 `DISABLE_COMPACT`。新增真实接缝两案（逐字沿用 Codex 探针装配）。
- **挡板**：无新增；不加压缩管理器、不改适配器、不加"未知字段永远忽略"合同。
- **修正旧结论**：我此前"未知字段被忽略 → CC 回退客户端压缩"与"每次压缩多一次请求"两条推断按 Codex 反馈撤回；请求预算按实际接纳请求计。
- **测试与账本**：ruff 全过；全量 **2254 passed, 0 skipped, 0 failed（158s）**；lanes lane A 407p/318s、lane B 725p/0s 实跑全绿。本机通过不等于 Codex 复核通过；`infra.md` 仍不进提交。

### 2026-09-10：第三组 I20 首版实施（离线 run 报告工具，只消费已有记录）/ Claude（A 线）

- **依据**：[第三组决策包 §0/§0.1 第 4 条](batch3_training_signal_20260909/README.md)；[I20 首版 Brief](batch3_training_signal_20260909/i20_run_report_brief_20260910.md)（七面→现有 producer 映射、启用条件、关联键、分母、缺口）。
- **提交**：`a467d885`；manifest 计数 `a8e49e0d`。
- **T1 决定**：纯消费者（`repoharness2.adapters.miles.run_report`，CLI 可对进行中 run 快照运行），复用 `drop_events` 两个汇总器；七面各自 collected / partial / not_collected 并写原因（无事件目录 ≠ 无损耗）；`train_step.metrics` 按 均值 × num_rollouts 还原总量、跨 step 比例用总量之和、同 (rollout_id, step_id) 多 rank 副本只取一份；缺失 / 未知 / 未匹配 / 进行中单列不填 0；会话级长度下降只叫线索；同版本与跨版本 logprob 差异分列；优势符号只给标注的近似。无新增 producer、阈值、告警或常驻服务。
- **挡板**：无新增。
- **测试与账本**：ruff 全过；全量 **2261 passed, 0 skipped, 0 failed（157s）**；lanes lane A 414p/318s、lane B 732p/0s 实跑全绿。本机通过不等于 Codex 复核通过；`infra.md` 仍不进提交。


### 2026-09-11：第三组 I19 / I20 实施聚焦复核 / Codex

- **结论与待拍板 T0**：无新 T0。范围 `f7521d94` → `76ede7f4`；I19 窄清理通过，I20 已实现但四项 P2 统计缺口需修正后收口。完整报告与可复跑证据统一在 [batch3_training_signal_20260909/review_20260911/README.md](batch3_training_signal_20260909/review_20260911/README.md)。I18 未定、基座诊断核对目标 CC 请求面的安排均不变。
- **T1 / 处置建议**：R1 读错 lifecycle 字段且把队列深度当秒；R2 真实 audit 不含 grading，已评分被报未评分；R3 FORK 多行重复计入成员 reward / 优势符号；R4 多 run step 碰撞且指定 run 仍混入其它 audit。均应限制在现有消费者 / 测试内修正，真实缺口如实标未知；R5 TP>1 副本重复为条件性 P2，默认 TP=1 不触发，单列登记。I19 少量旧注释非阻塞。
- **挡板与范围**：没有新增拒绝、阈值、重试、监控平台或 GPU 验收；未改生产源码、维护测试、配置、依赖、既有提交，也未 stash / checkout / git apply。只新增审查工件、追加共享账本并为两个 Brief 补复核入口。
- **修正旧结论**：作者“真实 producer 已映射、FORK 成员去重、跨 run 不混连”的 I20 完成说明尚不成立。实际训练 reward / loss 不受这个纯消费者影响，不放大为训练 P1。当前 consumed tuple join 成立，I19 两案也没有冒称目标 CC 压缩验真，不列为问题。
- **测试与停止条件**：主审 171 passed / 0 failed（23.29 秒），相关 ruff、launcher 语法与 lanes `--checks-only` 通过；真实 writer / emitter 到 loader / report 的四类反例与条件性 TP 基数模拟独立复跑。未复跑作者全量 2261 / 完整双 lane，无真实 CC / Docker / API / GPU。I20 修正 R1–R4 并补对应接缝测试后只做一次针对性复核，不扩展到其它未决算法或第四组评分。

### 2026-09-11：Codex I19/I20 聚焦复核处置——I19 通过；I20 R1–R4（P2）与 R5（条件性 P2）accepted 并修复 / Claude（A 线）

- **复核**：[batch3_training_signal_20260909/review_20260911/README.md](batch3_training_signal_20260909/review_20260911/README.md)。四项均在作者本机用 Codex consumer 探针复现：生命周期读错字段把队列深度当秒数；评分从不存在的 audit 字段读、已评分记成未评分；FORK 行当成员算 reward 与优势符号；step 去重与 audit 归属缺 run 身份。
- **修复提交**：`c8bf6bd4`；manifest 计数 `1bc2dfb7`。处置见 I20 Brief §7。
- **T1 决定**：新增 `bringup_events.jsonl` 为报告输入并按 session_id 关联 audit；无 bringup 文件时评分是"无法知道"；多 run 输入默认逐 run 出子报告（不混连），audit / bringup 行按 bundle 内唯一 run_id 归属、否则只计数；成员先归并再统计、矛盾计数不静默；`logprob_compare` 精确去副本，`sample_dis_accounting` 标 TP>1 不支持（事件无 rollout_id）；压缩时代注释与 Brief 措辞收窄。
- **挡板**：无新增；不新增 producer、平台或训练拒绝路径。
- **修正旧结论**：I20 首版报告的"评分 / 生命周期 / 成员 / 跨 run"四处口径此前不可靠（Codex 正确），已修；旧 `attempts_without_grading`、`audit_grading` 键撤销。
- **测试与账本**：ruff 全过；全量 **2264 passed, 0 skipped, 0 failed（162s）**；lanes lane A 415p/320s、lane B 735p/0s 实跑全绿；夹具改用真实 rh2 writer 与 fork 原函数。本机通过不等于 Codex 复核通过；`infra.md` 仍不进提交。


### 2026-09-11：第三组 I20 修后针对性复核 / Codex

- **结论与 T0**：范围 `76ede7f4` → `bc2cfa71`，只核对 R1–R5 与直接回归；R1 / R2 / R3 通过，R5 按 TP 支持范围收口，R4 留一项原 P2，另有本次修复新引入的 P2 回归 R6。无新 T0。完整报告见 [review_20260911/followup1/README.md](batch3_training_signal_20260909/review_20260911/followup1/README.md)。
- **T1 / 最小建议**：R4 取消“其它 bundle 没有事件就归给唯一可见 run”的两处兜底，保留未知归属，audit-only 单目录仍可读；R6 成员级版本统计应汇集所有叶，或保留明确标为逐行的旧统计。两者只影响消费者，不能描述为训练 reward / loss / staleness 判定被改坏。
- **挡板与范围**：未新增 producer、阈值、拒绝、重试或状态平台；未改生产代码、维护测试、配置、依赖或提交，无 stash / checkout / git apply。本轮纯消费者 / schema 窄复核，不重复安排上一轮双角色；只新增复核工件、追加本账本及 Brief。
- **修正旧结论**：作者“R1–R5 全部修复”中，R4 只在两个 run 都有事件时成立；无事件目录仍会串入。R5 的 logprob 去副本已实现，逐叶 DIS 仍是原始事件累计值，TP>1 明示不支持，不能概括为全指标已去重。I19 文字余项已清理，原实现通过结论保持。
- **测试与停止条件**：主审 71 passed / 0 failed（5.92 秒），相关 ruff 与 lanes `--checks-only` 通过；原 writer / emitter 反例重跑，R4 两 bundle 缺事件、R6 跨版本分行及顺序交换反例复现。没有作者 2264 全量 / 完整双 lane 的独立重跑，无真实 CC / Docker / API / GPU。后续只复核 R4 / R6 两处小修，不扩展到 I18 或第四组。

### 2026-09-15：B 线 SWE 真实评分接线计划审查 / Codex（A 线）

- **结论与 T0**：方向认可；审查集中追加到 [swe_grading_wiring_20260915.md §8](swe_grading_wiring_20260915.md#8-a-线计划审查--codex--2026-09-15)，不另建决策主文档。D3 是实际 conda 写权限扩张，需用户批准范围；D4 诊断派生镜像与正式环境替换分开，D1–D4 均未因本次审查被自动批准。第四组未决语义保持，不复审第三组代码。
- **T1 / 最小修改**：拟议 driver 补已有结构分类、候选容器有界生命周期及冻结后释放；D4 明选 RepoDigest 或仅诊断用显式 local-build 身份。安装顺序改为待对账，不拿段末 RC 证明全部构建成功；投影验收不用普通 Git diff 替代含未跟踪文件的冻结视图。补 gold 输入、shm 记录、评分版本和 parser/report 口径。S1-a、S1-f 及 parser 回归材料可先推进。
- **挡板与范围**：没有新生产拒绝、重试、hash 校验器或反作弊平台；未改生产代码、维护测试、配置、依赖或 Git 提交。仅追加本页、原计划审查节及一个窄探针与结果；两个独立 reviewer 只读。写入记录不等于已通知 B 或 Claude。
- **修正旧结论**：九仓安装顺序无影响、整 conda 属主交付不增加能力、Git diff 能列出完整候选，以及缺席参考 ID 属于 silent success，这些说法均不准确。安装非零后的官方分数可保留诊断，但不能因此宣称安装作用于候选已验收；也不统一改成 0/None。
- **证据与停止条件**：Production Tracer / Falsifier 交叉核对；主审四类 CPU 对照（结构分类三案、report 四案、复合 shell 退出码、临时仓库新增文件）完成，结果见计划 §8.5。未运行 Docker/SSH/CC/API/GPU 或新评分批次。修订接缝、事实与验收说明并落实权限/镜像范围后进入小切片，不要求先完成第四组全部决策或全量环境流水线。

### 2026-09-15：Codex I20 针对性复核（followup1）余项处置——R4 余项与 R6 accepted 并修（用户审查通过后提交 `35fce017` / `0d3bccd3`）/ Claude（A 线）

- **复核**：[batch3_training_signal_20260909/review_20260911/followup1/README.md](batch3_training_signal_20260909/review_20260911/followup1/README.md)。两项均可达且在作者本机复现：无事件 bundle 的 audit / bringup 被唯一可见 run 认领（指定 r1 时 r1 报 2 条 audit、陌生 task 混入）；成员级版本统计只取首叶（`[['5'],['6']]` 报单版本、叶顺序交换改变结果）。
- **处置**：`run_report.py` 删除"只见一个 run 就认领"的两处兜底，归属只看本 bundle 事件；成员版本取全部叶并集并记部分事实。`test_run_report.py` +2 例；manifest 计数 415/320/735 → 417/320/737。用户审查通过后提交（代码 `35fce017`、manifest `0d3bccd3`）；涉及文件：`rh2/src/repoharness2/adapters/miles/run_report.py`、`rh2/tests/adapters_miles/test_run_report.py`、`docs/.../miles_spike/integration_base_manifest.json`、I20 Brief §8。
- **挡板**：无新增；不新增 producer、平台或拒绝路径。
- **修正旧结论**：我此前"跨 run 不混连已修"在无事件 bundle 场景不成立，Codex 正确；R3 修复引入的成员级版本统计有回归，已修。
- **测试与账本**：ruff 全过；全量 **2266 passed, 0 skipped, 0 failed**；lanes lane A 417p/320s、lane B 737p/0s 实跑全绿；Codex followup 探针修后副本（scratchpad，改 `fixed` 断言）全部通过。本机通过不等于 Codex 复核通过；`infra.md` 仍不进提交。

### 2026-09-15：第三组 I20 R4 / R6 修后窄复核收口 / Codex

- **结论与 T0**：R4 余项与 R6 均通过，I20 离线报告首版的本轮实施审查收口，无新 T0。被审对象为 HEAD `4529ebd7` 上 Claude 未提交的工作区修复；报告与源码快照见 [followup2/README.md](batch3_training_signal_20260909/review_20260911/followup2/README.md)，I20 Brief §9 已同步。
- **T1 / 验收**：无事件 bundle 的 audit / bringup 在指定 run 与默认输出中均只计未知归属，不再混入 r1；全无事件时本地摘要仍可用。成员版本汇集全部叶，叶顺序不影响结果；有叶缺版本单列部分事实，`single_version` 只表示已知集合大小为 1。R3 成员计权、多 run step 和 R5 logprob 去副本正控通过。
- **挡板与范围**：未新增 producer、阈值、训练拒绝或 GPU 验收，未改 Claude 的生产代码、维护测试和 manifest，也未提交、stash、checkout 或 apply。仅新增本轮审查工件、追加原 Brief 与账本；历史证据保留。
- **修正旧结论与限制**：上一轮 R4 / R6 未收口状态由本轮证据更新为通过；R5 的 `sample_dis_accounting` TP>1 不支持限制保留，不概括为所有指标支持多 TP。I19 通过、I18 未定及目标 CC 请求面待基座诊断核对的状态不变。
- **测试与停止条件**：主审相关测试 **73 passed / 0 failed（5.51 秒）**，ruff、lanes `--checks-only` 通过，原反例与缺失数据正控独立执行。未复跑作者全量 2266 / 完整双 lane，无真实 run 文件、CC、Docker、API 或 GPU。不要求再加一轮广泛审查；本批保持未提交，后续按用户安排处理提交与既定诊断。

### 2026-09-15：第四组 A/C/D 定案与 B 文件边界、筛查顺序讨论 / Codex

- **用户决定 / T0**：A 批准将可信归因于候选的错误作为失败信号，当前可给 0，真实逐测试结果保留，未来细粒度配方另定；C 仅排除确认可再生且非答案的 Python SWE 缓存，未知保留；D 支持普通文件变目录。决定集中写入[第四组 §0](batch4_scoring_20260910/README.md#0-当前已确认的决定2026-09-15)。D1–D4=A 已在 B 接线计划登记，不重问；B 具体规则、细粒度公式与自动作弊惩罚仍未批准。
- **B 方案 / 实施建议**：见同页 §6。推荐仓库/版本共用规则加逐题例外，agent 在准备阶段分析职责，程序执行固定规则，用合法替代解与篡改反例验证。普通源码不按测试名称删除，混合职责不一刀切；D3 已接受的运行器可写风险仍按原决定观察。建议当前 B Claude 单一实施，A 负责通用语义与独立复核；尚未派发任务或代双方承诺排期。
- **范围 / 挡板**：只更新第四组、决策导航和本账本；未修改 B 当前代码、公共契约、奖励函数、评分输入或工作区其它改动。没有新 hash 闸门、自动拒题、重试或反作弊平台。
- **修正旧口径**：第四组不再是“四项均未批准”；A 不是所有非零/空解析都记 0，更不能伪造未运行测试的逐项失败。评分已知缺口应在规模筛查前修正，但不能要求先证明评分器没有任何问题才允许小批校准。当前严格二值契约不等于永久禁止细粒度奖励；与 R2E 已选最小表达方案协调实施。
- **证据与停止条件**：核对当前源码、B 接线及筛查清单，按既有精读导航复查 FrogNano、Hardening Agent Benchmarks、SWE-1.7、Anthropic reward-seeker 原文；没有新 Docker/SSH/模型/GPU 作业或实现测试。已批工作可准备，B 原则确认后以少量真实 RH2 对照校准首批规则，再扩量；新问题按影响范围修复和重验，不重复全仓审计。

### 2026-09-15：按用户后续意见收窄第四组 B / Codex

- **方向**：用户提出先移除 I08，再在流水线中按题分析是否需要额外排除、说明理由，无需额外项则不加。Codex 推荐采用这个窄方案，具体边界集中到[第四组 §6.5](batch4_scoring_20260910/README.md#65-b-首版收窄现在移除-i08-默认通配额外排除留给流水线2026-09-15-后续讨论)；早前 §6.2 的完整流程不作为当前实施前置，后续机制尚未定案。
- **具体范围**：实际 SWE 构造入口取消 `DEFAULT_SWE_TEST_GLOBS` 默认注入，`test_globs=()`；官方测试恢复/注入、精确清单和运行期保护保持。现有 `test_patch` 混合源码的潜在冲突另由流水线检查，不宣称删除 glob 就消除所有误伤。
- **挡板与实施**：本轮未改生产代码或测试，未新增白名单、规则平台、自动作弊处罚或排题条件，未向 B 发消息；仅修订第四组、导航与本账本。
- **修正旧建议**：不要求先完成逐仓规则生成流程才可修 I08；额外清单允许为空，未发现具体依据不等于已经证明不存在 hacking，也不需证明绝对安全才能使用空清单。
- **验证与停止条件**：真实分类函数的五路径 CPU 对照确认两种 testing 源码不再被 glob 拦截，精确 official、保留名及普通源码分类不变。正式入口接线、实际重放和现有 official 恢复的窄回归留给实现者；无 Docker/模型/GPU 作业，不延伸为全链复审。

### 2026-09-15：第四组实施计划独立审查 / Codex

- **结论与 T0**：P-B 可先实施；P-A/P-C/P-D 按[原实施计划新增 §5](batch4_scoring_20260910/impl_plan_20260915.md#5-codex-实施前审查2026-09-15)修订后实施对应部分，e1 原版本继续。没有新的用户决策前置，A–D、SWE 接线 D1–D4=A、R2E-A 均不重开；缓存可先做更窄范围或暂缓，不挡小批校准。
- **具体反馈**：R1 评分负样本不能加入执行缺失集合；R2 零解析不能覆盖真实 collection 失败，路径相交也不等于归因；R3 新默认字段及缓存计数会改变旧身份/重建判据；R4 名字过滤丢失软链等类型事实，未经确认的全树 pyc 超出窄缓存依据；R5 文件变目录必须保留投影后的必要删除。另补 R2E 无结果/额外键、已批编译失败、P-B 纯观察与历史预检记录口径。
- **范围与挡板**：HEAD `acb0e4bf` 加当前 B 的 S1 未提交代码；只新增审查证据与文档记录，未改生产源码、维护测试、配置、提交，未触碰 e1、未向 B 派发消息。不新增异常分类平台、哈希闸门、自动作弊处罚或自动回滚。
- **修正旧结论**：所谓 gate 负样本白名单不存在；当前 frozen 路径的 ignored 控制面条目不自动变 hygiene 拒绝；默认字段不保证旧哈希兼容；已确认候选编译失败已有用户授权，只有未归因安装异常仍需证据。pytest 反例并不否定 SWE 官方缺席计不通过或当前 binary 0，否定的是“解析一项等于实际执行了一个 case”和拟议分支覆盖。
- **证据与停止条件**：Production Tracer/Falsifier/Training Semantics Reviewer 有界核查，主审独立回读并复跑四个 CPU 探针（真实 pytest、当前投影/应用、拟议缓存过滤、当前 digest 函数）；结果见[证据目录](batch4_scoring_20260910/impl_plan_review_20260915/README.md)。无 Docker/SSH/模型/GPU 作业，无全量测试通过声明。实现后只验相关契约、运输及 fresh Docker 往返；损耗频率仍由 e1/e2 测，不再扩成全仓审计。

### 2026-09-15：第四组实施计划 Codex §5 的 A 线补充核查 / Claude（A 线）

- **结论**：R1–R5 全部 accepted（R5 为 P2）；Codex 四个 CPU 探针在会话临时目录独立复跑，结果与其保存的 stdout / JSON 逐项一致。R3 的"仅缓存数量不同就 baseline_digest_mismatch"限定为原则性风险（rollout 基线 census 与 grader 重建 census 都在新鲜镜像状态、任何 Python 执行前），修法不变；同时补充旧 v1 manifest JSON 在加载时因 `policy_digest` 校验器会直接读不进来。
- **新增 S1（P1）**：候选把文件变目录 / 目录变文件，今天在 fa_formal 正式链是 `rh2_contract_validation_failed` run-fatal（exporter 不捕 `FrozenPatchArtifactV1` 的 ValidationError，编排 `assemble` 段升 fatal）；e1 驱动器同样未包住（脚本带回溯退出、无账本行）。正式链 CPU 探针三例（file→dir、dir→file、对照）见 [impl_plan_a_line_probes_20260915/](batch4_scoring_20260910/impl_plan_a_line_probes_20260915/README.md)。建议并入 P-D：exporter 转 typed `PatchExportError("unsupported_delta_shape")`，编排复用 unsafe 通道，驱动器映射 `ReplayStageError`；通道选择请用户知情。
- **P-A 建议**：producer 挂点改为"解析成功但参考集合全部缺席"路径（候选语法错误今天落 `tests_failed` 且 `num_parsed_tests=1`，零解析分支不可达）；首版正向规则 = pytest rc 族 + 全部参考缺席 + collection 中断文本 + `py_compile` 复证；资格用记录（镜像 / 配方 digest）不用布尔；资源终止事实列 `RH2_TEST_RC ≥ 128`、`memory.events oom_kill`、`State.OOMKilled`。`GradingReport` 无内容 digest，加默认字段不破锚。
- **更正自己**：README §7.3 的"触碰 `*tests/*` 即 hygiene 拒绝"只对 S1 diff 路径成立，frozen 路径是静默不重放；已在 README 原处追加更正。
- **记录与边界**：结论写入 [impl_plan §6](batch4_scoring_20260910/impl_plan_20260915.md#6-a-线-claude-补充核查2026-09-15)。未改生产代码、未运行 Docker、未触碰 e1、未提交；本条与上述文档不进提交，待用户安排。

### 2026-09-16：第四组作者修订计划聚焦复核 / Codex

- **结论与 T0**：最新意见写入[原计划 §8](batch4_scoring_20260910/impl_plan_20260915.md#8-codex-对-7-的聚焦复核2026-09-16)。P-B 可继续，P-C/P-D 按已批范围补明确验收；S1 复用旧 unsafe/整组 DROP 已获既有授权，不需要新通道决定。不同意“所有后续都等新决策”；本任务没有代为启动 e2。
- **P-A 余项**：F1 有/无 pytest 摘要的同类语法失败覆盖仍不一致，可分片但不能核销原负样本遗漏；F2 资源否决不能只禁新类别后回落旧 reward 0；F3 py_compile 的 I/O 非零和仓库模块遮蔽不构成语法证明，改用不落盘、明确 SyntaxError 的复证；F4 构建切片不能以安装串最后一条命令的 RC 非零为必要条件。F2/F3 在 producer 启用前修，F1/F4 明确后续切片；无新 reward 配方或平台决定。
- **接受与补充**：消费者枚举、P-B 纯观察、P-C 按类型剪目录及计数出身份、R2E 矩阵均认可。P-C 旧身份测试须覆盖嵌套 policy 的整份 manifest；只用于确认范围，并记录版本。P-D 承接 B 已登记的宽 catch 与拒绝详情两条 P2，不另立 e1 阻塞；S1 completed 不代表已评分或可训练。
- **证据与边界**：HEAD `bac7659e` 加本机工作区改动；按既有标准有界子审、主审独立运行新 P-A 真实 pytest/编译 CPU 探针与 P-C 嵌套字段模拟，见[本轮证据](batch4_scoring_20260910/impl_plan_followup_20260916/)。资源回落为输入组合模拟，没有真实 OOM 实验。承接 B 的 e1/S1 与 metacopy 导层风险报告，未复跑远端、改机器或旧工件，未改生产代码/维护测试/配置/提交。
- **停止条件**：实现者按 §8 的明确条件修订和分片，后续只验对应失败分流、正式报告运输、旧身份与冻结/评分往返；不扩成全仓审计，不因普通 e2 校准仍有旧归因就要求全部停工。


### 2026-09-16：SWE 评分接线与第四组夜间实施完整审查 / Codex A 线

- **结论与 T0**：本轮未整体验收通过。统一报告在 [implementation_review_20260916/README.md](batch4_scoring_20260910/implementation_review_20260916/README.md)；原计划 §10、接线页 §16 仅做导航。已有 A–D 与 D1–D4 不重问；stdout/hook 污染仍需用户定首版应对范围，root 插件或 XML 不能直接称根治。参考 ID 全缺席的扩大处置需对齐明确授权。
- **T1 / 修正建议**：R1 无关坏语法不能证明本次失败；R2 compile 复证不得导入候选 json.py；R3 必要终止事实未知不能当作正常。资格正式注入与构建切片仍未完成；R6 缓存反向形状、R7 冲突证据作窄修；接线 §14.2 三项旧余项沿原分期。建议仍由当前 B 实施者统一改共享 manager，A 后续只复核对应正反例。
- **范围与挡板**：三路独立子审后主审去重、复跑关键探针并核真机证据；未新增生产 gate、retry、阈值、状态机或权限规则。未修改生产代码、维护测试、配置、旧 evidence 或提交；只追加审查文档、证据和本条。没有向其它用户任务发送消息。
- **修正的结论**：1392 项测试通过真实，但不足以证明 P-A 归因正确；当前 driver 可达的误判在 formal 尚需资格接入，不能说训练已经污染。78 行 e2 用较旧代码，25 行回归才覆盖最终代码；15/15 是可比项，不能写成全部 24 题一致。P-A 构建/正式资格缺口不应只因未实现就再变成 reward T0。
- **验证与停止条件**：本机 1392 passed / 1 skipped，ruff 通过；Linux 3 个新增 Docker 往返通过且无残留、metacopy=Y；77 个涉及文件与远端最终树一致；103 行账本中 92 份评分日志全部摘要匹配。真实本机 pytest/compile/JUnit 反例、6 个 P-B/C/D CPU 反证和实际 miles buffer→训练数据转换均由主审复跑。无 GPU/API/全题库重跑或真实 OOM。修对应三项归因、对齐 R4、按正式使用时间接资格及既有余项后收口，不再扩成全仓审计。


### 2026-09-19：后续复核与第五组分叉准备 / Codex A 线

- **已读与当前分工**：读过 `tmp/prompt给claude.md`、216 题真实 RH2 结果和 279 条零分审查。按用户安排，B Claude 修通用链路，B Codex 修环境/数据；本任务在 Claude 交付后复核相关修复。此次没有重跑实验或核销其尚未完成的修复。
- **用户补充约束**：反作弊措施结合流水线/真实模型探针按证据决定，不能自动把全部合成攻击面视为首版训练前置；环境资格记录已定，真实记录待环境处理产出，不重复问是否使用。评分归因正确性及既有保护边界继续遵循已批决定。
- **分叉建议与入口**：准备 [第五组讨论入口](batch5_launch_eval_20260919/README.md)，新 A Codex/Claude 从 I21/I22/I36 继续，后续第六/七组；I18 仍单独待议。讨论可现在并行，正式集成验证使用 B 稳定快照与小批已校准任务。当前只是准备，未自动创建或派发新任务。
- **修改归属与边界**：当前 B 实施者继续负责评分、工件、资格相关文件；新 A 的 eval/恢复如需改 `bringup.py` / `generate.py` / `prepared_task_face.py` / 公共 fixture，先在已有 Brief 约定单一写入者。不新增审批平台，不提交他人工作。
- **验证范围**：仅阅读资料、窄核 generate_fn 的 formal 身份路径、恢复 override 和旧 s1_compat launcher；新增一份第五组入口并追加导航/本账本。未改源码、测试、配置、旧 evidence；无 SSH/GPU/API 作业、提交或其他任务消息。


### 2026-09-19：Claude 链路修复聚焦复核 / Codex A 线

- **结论与 T0**：主审统合三条独立检查，报告在 [chainfix_review_20260919/README.md](batch4_scoring_20260910/chainfix_review_20260919/README.md)，原计划新增 §11。大部分修复可核销；P-A 原 R1/R4 各有一个 P1 余项，cache normalizer 新增一个 P2 范围错误，均沿既定语义窄修，无新用户决策。
- **关键事实**：任意参数路径提及仍可误关联坏语法，将缺依赖故障变成可训 0；单测试捕获 traceback 仍可把正常完成的失败测试变成 None/整组 DROP；清缓存未 prune `.git/` / `.harness/`。主审复现了真实日志、真实 Git/Bash 后果和实际 miles 组运输，未把 CPU 替身当作已发生的真实训练污染。
- **已闭合与后置**：R2/R3、R6 原例、R7 持久诊断、全文释放、两处取消、派生资格常规 ID 失效及 --init 接线可核销。正式资格仍缺加载来源，缓存计数仍缺 audit 序列化；F4 与反作弊/环境决定按用户既定分期，不重新扩成前置。完整冲突详情在 audit，不要求再扩 receipt。
- **验证与边界**：1402 passed / 1 skipped、ruff；本机 batch4 Docker 4 passed；三个真实 SWE 解释器（3.8/3.9/3.12）的实际复证脚本通过；8 条作者真机产物摘要对账，77 文件与作者真机树一致。未跑 GPU/API/全题库，未改生产源码/维护测试/配置/旧证据或 Git，未操作 B Codex 的远端实验。远端缺 fixture 镜像即停止该测试，改在本机已有镜像验证，未安装依赖。
- **停止条件**：Claude 窄修 CR1/CR2 并补 CR3 排除剪枝，保留本轮正控，再聚焦复验即可。新 A 决策任务继续，B 环境/数据工作继续；本条只是登记，不等于已经通知其它任务。

### 2026-09-19：第五组方向与分期确认 / 分叉 A Codex

- **用户决定**：集中写入[第五组 §6](batch5_launch_eval_20260919/README.md#6-2026-09-19用户后续决定与实施分期当前口径)。A/B 评测方式可共存，B 按复用成本安排，复杂则不阻塞首训；启动命令随八卡方案确定；恢复暂以明确 checkpoint 且不手填起始编号避开错配，可做窄修。环境流水线基座诊断与后续完整八卡验收分开，具体 GPU 作业后定。
- **源码依据**：miles shared-engine eval 阻塞训练驱动继续执行，`FullyAsyncRolloutFn._call_eval` 暂停新组提交并在 finally 恢复，但不等待已有 active groups 全部结束。RH2 formal 身份/prepared assignment 与 eval 的共同接线仍需补齐；不能把现成组件等同于当前真实入口已验证。
- **修正旧建议**：不再把 A/B 写成二选一；不以“小规模闭环”代替用户要求的完整八卡验收与参数探索；条件性恢复错配允许先用操作约束规避，不单独阻塞当前修复。I18 保持独立未决。
- **范围与验证**：仅静态读码并更新第五组、导航与本条；未改生产代码、测试、配置或他人审查结论，未运行 CPU 测试、Docker、GPU 或远端作业。本条没有派发任务，也未批准具体 GPU 预算。


### 2026-09-19：CR1–CR3 窄修复核 / Codex A 线

- **结论 / T0**：报告见 [chainfix_followup_20260919/README.md](batch4_scoring_20260910/chainfix_followup_20260919/README.md)，原计划 §12。CR1、CR3、formal 缓存计数持久化通过，CR2 原例通过但剩自然内层 pytest 标题穿透 Captured 的同边界 P1，无新增用户决策。
- **具体余项**：父 pytest 正常 1 fail + 1 pass，Captured stdout 中子 pytest 的 session/ERROR 分节被当成父层，来源 0→None；主审用实际 dvc 镜像 pytest 6.2.3 日志进入当前 manager/miles 运输，得到 `[1,None]`、整组 DROP。固定测试不变，无资格或伪造日志前提；真实题库频率未知。推荐正向识别外层完成事实，不继续逐标题打补丁。
- **已核销**：无关参数路径不再触发 compile，10 个真实 collection/conftest 语法正例仍给 0；原捕获 Python 子进程例恢复来源 0；真实 Git 排除区和 manifest 摘要保持、缓存类型重放正常；非空缓存计数经 fsync 审计落盘。已有资源/清理/资格分期不重开。
- **验证 / 边界**：1407 passed / 1 skipped、ruff，本机 Docker 4 passed；独立五种 traceback 日志矩阵及主审关键重放；新真机两行摘要核对，stale 不计入；78 文件与作者远端树一致。仅新增审查证据及本条/原计划导航，未改生产源码、维护测试、配置、旧工件或 Git；一个隔离临时容器已回收，未干扰 B。
- **停止条件**：Claude 只收齐外层正常完成判据，嵌套例回来源 0/组可消费，并保持本轮已通过的正反控，即结束 CR1/CR2 扩审。本条为登记，未向其他用户任务发送消息。

### 2026-09-19：A 线 Claude 分叉开工——I21 评测公共入口 Brief / Claude（A 线分叉）

- **状态**：分叉线程已开工，先交 [I21 窄实施 Brief](batch5_launch_eval_20260919/i21_eval_brief_20260919.md)（含 I22 窄修），待 Codex 聚焦检查；未改生产代码、测试、配置或 fork，未运行 Docker / GPU / 远端作业，未提交。
- **核对到的事实**：miles 共享引擎 eval 现成（发布后 `await dispatch`、`_call_eval` 暂停新组提交并在 finally 恢复、不排空在飞组、异常原样上抛停训练驱动；只有快照分支才降级成 skip）；eval 样本没有 `group_index`、数据集名与 eval rollout_id。RH2 在 fa_formal 下对 eval 样本于 `mint_attempt_identity` fail-closed；eval 交付面 `float(grading_reward or 0.0)` 与 `_abort_result` 的 `reward = 0.0` 把评不了分 / 没跑成记成 0 分；prepared 链没有 eval 题的加载点与 train/eval 互斥检查；execution audit 与 run_report 不区分训练与评测 attempt。
- **方案要点**：eval 命名空间的六字段身份（宿主事实由 fork patch 0018 盖章）；第二个 prepared 产物目录 + 按平面绑定 + 启动期校验；出口 typed 载荷三类分开（graded / reward_unavailable / execution_missing），不可得记 `None + aborted`；`eval_report` 聚合与 `eval_point` 事件；audit 行加 `evaluation` 块、run_report 分出。共享引擎形态不改 miles 生命周期，首版不排空、用 `eval_window` 事件量化重叠；作业内专用 eval 引擎组后置（RH2 网关启动时绑定训练 router）。I22：显式 `start_rollout_id > 0` 与加载点不符即拒（patch 0019）。
- **待用户确认**：eval 不可得不记 0 分；fork patch 0018；eval 题单用第二个 prepared 目录；`generate.py` / `bringup.py` 小改与 B Claude 的落地顺序。
- **文件归属**：A 线自有 = `adapters/miles/{identity,generate_fn,attempt_assignment,eval_report,run_report}.py`、`adapters/slime/eval_result.py`（新）、fork patch；共享 = `generate.py` 三处、`bringup.py` 四处（Brief §6 列了函数）；不碰 `grading/`、`prepared_task_face.py`、`contracts/`、`envpack/`。


### 2026-09-19：CR2' 收尾判据聚焦复核 / Codex A 线

- **结论 / T0**：报告 [chainfix_footer_review_20260919/README.md](batch4_scoring_20260910/chainfix_footer_review_20260919/README.md)，原计划 §13。默认格式原反例已回来源 0、组 `[1,0]` 可消费；仍留一项同根因 P1，无新增用户决策。
- **具体余项 / 修正口径**：最后一个匹配到的 pytest 摘要不一定属于外层。真实 quiet 父日志的裸收尾被漏掉，子失败可使来源 0→None 丢组，子成功可使未确定 None→0 进入训练；普通 `-rA` 的 conftest 启动失败没有父摘要，也可能借用子成功摘要。§10.5 的“子摘要都在外层摘要之前”缺少外层摘要确实存在且被识别的前提。
- **建议 / 止损**：局部补齐 bare footer 和外层结束事实相容性，不按任意非零 rc 给候选 0 分，不扩展反作弊。28 案进程内设计对照通过，只是修法可行性证据，未实施。维持前轮 CR1/CR3 核销；下一轮只验三个剩余边界与已通过正控。
- **验证**：主审 58 passed、ruff；真实 pytest 9.1.1 输出和旧真机 pytest 6.2.3 日志重放、实际 manager/miles 组运输；59 条旧真机日志 hash 全匹配，本次短路未改变其形状判定；78 文件与作者远端独立树一致。题库发生频率未知。未新跑 Docker/GPU/题库，未修改生产代码、维护测试、历史证据或提交。
- **协作**：只登记本条和原计划导航；没有向其他用户任务发送消息，没有改变 B 工作分工或已有资源/资格/反作弊决定。

### 2026-09-19：I21 / I22 实施 Brief 聚焦审查 / 分叉 A Codex

- **结论 / T0**：报告 [i21_eval_review_20260919/README.md](batch5_launch_eval_20260919/i21_eval_review_20260919/README.md)，Brief §10 已登记。复用方向可保留，R1–R3 先修计划；R4 完成 A 前补入口证据，R5 做 I22 前明确零编号语义，也可按用户决定暂缓。四个待确认点多数是已有授权下的 T1；全局题目互斥属于新增范围，推荐删除，不打包重新问用户。
- **关键证据**：真实指标函数体在带 samples 的 `[1,None]` 上抛 TypeError；真实训练驱动函数体在 before/after 均可派发 eval(0)；debug-rollout-only 一轮仍调用 training generate。固定元数据之外的唯一评测调用与目标模型绑定需补齐；显式 start=0 不自动重置已加载的训练状态。
- **分期与范围**：B 共享引擎的不排空策略可按已定范围做观测，真实竞争代价留八卡；A 的只评测控制流/模型来源可先 CPU 验证，完整命令仍后置。I18、评分修复、B 数据划分与 GPU 数值不重开。
- **验证 / 边界**：8 个窄观测场景，使用原函数 AST 节点，Ray/模型/日志依赖为替身；源码摘要和结果保存在审查目录。未运行全套 pytest、完整 CLI、模型加载、Docker、GPU 或远端作业，未改生产代码/维护测试/fork/配置，未提交或发送其它任务消息。
- **停止条件**：作者按 R1–R3 修订并明确 R4/R5 后开始窄实施；后续只验这些反例、真实入口与必要回归，不扩成全仓审计。


### 2026-09-19：CR2 收尾判据修复通过 / Codex A 线

- **结论 / T0**：报告 [chainfix_footer_followup_20260919/README.md](batch4_scoring_20260910/chainfix_footer_followup_20260919/README.md)，原计划 §14。CR2 核销，无新增阻塞项或用户决策；CR1、CR3 维持核销，结束该边界扩审。
- **证据**：41 个当前 manager 对照、6 个实际组运输对照全部符合预期。quiet 正常嵌套与原 pytest 6.2.3 日志回来源 0、组可消费；无资格的真实全局失败保留 None；新真实 pytest-pretty passed/failed/error 以及外层 rc=0、rc=1+error 的对照通过。
- **非阻塞修正**：“其它未识别格式一律未确定”应改为“退回既有形状/三路判定”；复合命令仅未覆盖，不是已实现自动拒绝。既有 e2 已有 pretty failed 样本，本轮补齐真实 error 验证。无新增生产规则或临时挡板。
- **验证 / 边界**：63 passed，被审两文件 ruff 通过；59 条旧真机日志 hash 全匹配，52 条正常完成、7 条非正常；7 个评分相关文件与作者远端树一致。并行 A 线正修改 generate/bringup，本轮不代替其集成审查。未新跑 Docker/GPU/远端评分，未改生产代码、维护测试、配置、历史工件或提交。
- **协作**：资源配方、参考键分层修复、反作弊与资格记录按用户已决定的流水线分期处理；本条仅登记，未向其他用户任务发消息。

### 2026-09-19：I21 评测公共入口与共享引擎形态——已实施、本机验证 / Claude（A 线分叉）

- **依据与决定**：Codex [I21 Brief 审查](batch5_launch_eval_20260919/i21_eval_review_20260919/README.md) R1–R5 全部 accepted（其探针本机原样重跑，8 个场景与保存结果一致）；用户回复四点——评不了分 / 没跑成不记 0 分（同意，并区分修复失败与 infra 失败、失败题目会安排 agent 逐题检查）、fork patch 允许、评测题包独立配置但**代码不设 train/eval 互斥**、现在实现。修订与实施记录在 [Brief §10–§11](batch5_launch_eval_20260919/i21_eval_brief_20260919.md#10-修订2026-09-19回应-codex-审查与用户决定)。
- **实现要点**：评测身份 `eval-{eval_point_id}-d{di}-p{pi}_m{slot}`（宿主每次调用生成 eval_point_id；rollout_id 只作标签）；第二个 prepared 题包 + 按平面核对 / 解析；出口与 audit sink 共用一个纯函数派生三类结果（graded / reward_unavailable / execution_missing，不可得 = `None + aborted`）；钩子接管 eval 日志（分母分开、唯一成员集合核对、`binding` 单列）；成本汇总与 run 报告把评测 attempt 单列；启动期预检 14 个拒绝条件；`RH2_EVAL_ONLY` 独立评测作业。fork patch 0018（本地提交 `e13f00086`，未 push）：宿主派发事实与模块标记、`eval_window` 事件、共享分支目标版本。
- **修正自己 Brief 初稿的三处**：钩子返回 False 保留默认日志 → 会对 `None` 求和而崩，改为接管；用 rollout_id 拼评测点身份 → 训练前与第 0 步后都是 r0，改用宿主 eval_point_id；train∩eval 非空即拒 → 删除（用户决定不设互斥，交集只进启动证据）。I22 窄修按 R5 整项暂缓：只按 `start=0` 判断新实验会留豁免，正确修法要看 finetune / bridge 等实际加载方式，随恢复入口一起做。
- **实施中发现**：独立评测作业在 sandbox profile 核对处因训练任务表为空而 `StopIteration`（真实 bringup 用例暴露，已改为回落评测题包镜像）；CPU 测试环境导入不了 miles eval 模块（缺 pybase64），宿主盖章能力探测改为"已加载取标记、否则静态读源码"。
- **共享文件**：`generate.py` 四处、`bringup.py` 若干处（函数清单见 Brief §11.1），未碰 `grading/`、`prepared_task_face.py`、`contracts/`、`envpack/`，未覆盖 B 的未提交改动。
- **验证**：双 lane 脚本清净环境 lane A 454 passed / 326 skipped、lane B 780 passed / 0 skipped（树哈希、工作树干净、17 个语义 patch digest、pin 全过）；contracts / adapters / governance / grading / envpack 非 Docker 1433 passed / 1 skipped；ruff 通过；源码 digest 算法在 HEAD~1 归档上复算得到 manifest 旧值。未跑 Docker 套件与任何 GPU / 远端作业。新增测试 63 例。
- **未完成 / 后置**：A 形态驱动层"只发生 eval、无训练派发"的本地证据与固定 HF 导出如何进入引擎（待接线）；真实引擎端到端、`eval_window` 重叠代价、目标版本与引擎回报版本的真实对照（GPU 方案）；作业内专用 eval 引擎组、快照 skip 事件、多评测数据集（启动期明确拒绝）。主仓库未提交，待 Codex 聚焦复核。

### 2026-09-20：I21 实施聚焦复核 / Codex A 分叉

- **结论 / T0**：报告 [i21_implementation_review_20260920/README.md](batch5_launch_eval_20260919/i21_implementation_review_20260920/README.md)，Brief §12 与第五组入口已登记。原设计审查 R1–R5 的修正/分期接受；实现需 IR1、IR2 两项 P1 窄修，另有 IR3/P2 统计遗漏。无新增用户决策或临时挡板。
- **确定性反例**：train top-p=.95 / eval top-p=1 的 unsafe 评测结果已应为 None+aborted，却因保留 vendor 叶而撞训练 mask 检查；两题包先过滤长题，再以存活一题为计划，报告 complete=True；两题全被过滤时钩子不接管，默认日志 ZeroDivisionError。仅评测发生一次重评分，训练 facet 仍计为一次。
- **建议 / 止损**：评测结果载体与训练 mask 要求分开，训练本身的缺 mask 仍拒绝；保留调用级计划/身份，空结果也有结构化未完成事实；用已有 trajectory_id/audit 分流重评分。下一轮只验这三个边界与正控，不扩到评分、恢复或数据总审计。A 的独立作业驱动/固定模型加载、I22、GPU 竞争成本仍后置；I18 未决不受影响。
- **验证**：独立跑新增 63 例；双 lane A 454 passed/326 skipped、B 780 passed/0 skipped，相关 ruff 与 fork/pin/patch 前置通过。7 个窄探针结果与生产源文件 hash 已保存。另在临时副本保留此前未提交改动并去掉 I21，仍复现六项 dp_schedule 导入失败，确认非本批回归；干净 HEAD 的全 CPU 对照为 1906p/320s，故不笼统称它为 HEAD 旧失败。
- **范围 / 协作**：只写审查报告、探针与导航，未改生产源码、维护测试、配置、fork 或历史工件；未提交、push、Docker/GPU/远端作业，未向其它用户任务发消息。共享工作区的 B 线修改维持原样。

### 2026-09-20：I21 实施复核 IR1–IR3 已修复 / Claude（A 线分叉）

- **判定**：Codex [I21 实施复核](batch5_launch_eval_20260919/i21_implementation_review_20260920/README.md) 的 IR1（P1）、IR2（P1）、IR3（P2）全部 accepted；其探针在未修复的树上原样重跑，7 个场景与保存结果一致。无新增用户决定。修复记录在 [Brief §13](batch5_launch_eval_20260919/i21_eval_brief_20260919.md#13-对-codex-实施复核-ir1ir3-的修复2026-09-20claude已实施本机验证)。
- **IR1**：评测结果载体统一为输入样本（不进训练），unsafe artifact 路径的 vendor 叶不再充当载体——训练 `top_p=0.95`、评测 `top_p=1.0` 时"评不了分"不再变成 `sampling_mask_required` 异常去停训练驱动；训练面缺 mask 仍 fail-closed，未给评测补伪造 mask。
- **IR2**：既定题目集合由评测题包的 prompts.jsonl 给出（成员键 `(task_id, slot)`），被 miles 加载器按长度过滤掉的题逐条列为缺失、`prompts_not_loaded` 单列，读不到题包不声称完整；fork patch 0019 把调用级事实挂到数据集结果，零样本时仍有唯一评测点，钩子接管而不回落默认日志（后者对空列表除零）。未新增"禁止长度过滤"的闸门，只在启动证据记 `eval_max_prompt_len`。
- **IR3**：`grading_regrade` 按 `trajectory_id` 与 audit 连接分成训练 / 评测 / 归属未知；训练 facet 只数训练的。
- **验证**：Codex 原探针（临时副本补 0019 常量）三个反例全部改判；双 lane 清净环境 lane A 461 passed / 329 skipped、lane B 790 passed / 0 skipped；contracts / adapters / governance / grading / envpack 非 Docker 1433 passed / 1 skipped；ruff 通过。fork 本地提交 `227806cfb`（未 push），patch 0019、manifest、patches README 已同步；主仓库未提交；未跑 Docker / GPU。
- **边界**：只动 A 线自有文件与 `generate.py` 出口一处（评测结果落定提到 termination 事实盖章之前）、`bringup.py` 启动证据一个字段；未碰 B 的评分文件。后置项不变：A 形态驱动层证据与固定模型加载、I22、真实引擎验证。

### 2026-09-20：I21 IR1–IR3 修复复核通过 / Codex A 分叉

- **结论 / T0**：[修复复核报告](batch5_launch_eval_20260919/i21_fix_followup_20260920/README.md)，Brief §14 与第五组入口已登记。IR1、IR2、IR3 均核销，无新增阻塞项、用户决定或临时挡板。
- **确定性证据**：不同 train/eval top-p 的 unsafe 评测正常交付 None+aborted；训练真缺 mask 仍拒绝。带题包的部分过滤保留原计划与缺失成员，全过滤仍有独立评测点、不崩溃；第一题被过滤/每题两样本的索引重排对照通过。训练、评测、归属未知的重评分分别计数，跨 run 同名 trajectory 不串账。
- **验证**：73 个 I21 用例通过；完整双 lane A 461 passed/329 skipped、B 790 passed/0 skipped；相关 ruff 与 fork/pin/18 个语义 patch 前置通过。11 组独立探针及结果已落盘，13 个相关源文件在验证结束后无摘要漂移。未重跑全 CPU；既有 dp_schedule 导入问题维持上一轮对照结论。
- **口径与分期**：全过滤时无样本 reward、模型评分为 None，但计划解决比例下界为 0，不能将后者当模型准确率。A 独立作业驱动/固定模型加载、I22、GPU 竞争与真实引擎证据仍后置，I18 未决不受影响。本轮停止三项聚焦问题的扩审。
- **协作边界**：只写新审查工件和导航，未改生产代码、维护测试、配置、fork 或上一轮历史工件；未提交、push、运行 Docker/GPU/远端作业，未向其它用户任务发消息，B 线工作树保持原样。

### 2026-09-20：第五组剩余本机部分收口 + 真实八卡核验清单 / Claude（A 线分叉）

- **依据**：Codex 对 IR1–IR3 的修复已核销；用户指示完成第五组剩余本机部分，必须留到 GPU 的记录下来供真实八卡核验。记录在 [Brief §15](batch5_launch_eval_20260919/i21_eval_brief_20260919.md#15-第五组剩余本机部分2026-09-20claude已实施本机验证)，清单在 [gpu_verification_checklist_20260920.md](batch5_launch_eval_20260919/gpu_verification_checklist_20260920.md)。
- **A 形态（独立固定 checkpoint 评测）**：驱动形态 = `--debug-rollout-only --num-rollout 0 --eval-interval N --hf-checkpoint <被评 HF 导出>`；lane B 新增 6 例执行 `train_async.train` 原函数体（零轮只发生一次 eval、无训练派发；只加 rollout-only 仍派发训练 rollout；禁用训练前 eval 则什么都不评；rollout-only 下引擎服务 hf_checkpoint 的三处源码事实）；RH2 预检对 `RH2_EVAL_ONLY=1` 要求零轮 + rollout-only + 零起点；评测记录、汇总与 run 报告带 `engine_model_path`（此形态 `binding=unverified` 是预期，模型身份以该路径为准）。
- **I22 窄修（T1，fork patch 0020，本地 `275e31eb2` 未 push）**：显式 `--start-rollout-id N>0` 必须满足 `N-1 ==` trainer 实际加载迭代，否则 `RecoveryStartMismatch`（任何 publish 之前）；`0`（全新 run 的框架置值）与加载点未知保持原语义，未新增"0 = 新实验"的 oracle（Codex R5 的约束）。oracle 翻转：`(5,2)→4` 改为拒绝。不支持手工重编号，已批 B-3 不变；操作约束（指定 checkpoint、不手填编号）继续有效。
- **留真实八卡**：共享引擎评测 E1–E11（模型绑定、评测期间无发布、重叠代价、单题 infra 失败、题单一致、统计分流等）、独立评测作业 A1–A6（真实 CLI 是否接受零轮、引擎实际加载路径、HF 导出与 checkpoint 对应）、冷恢复 R1–R4（真实恢复、错配拒绝的多 rank 路径、目标加载方式下 `loaded_rollout_id` 取值、保存 / 恢复耗时），以及此前各批已登记真机核验项的指针。
- **验证**：双 lane 清净环境 lane A 461 passed / 340 skipped、lane B 801 passed / 0 skipped（19 个语义 patch digest、树哈希、pin 全过）；contracts / adapters / governance / grading / envpack 非 Docker 1436 passed / 1 skipped；ruff 通过。未跑 Docker / GPU / 远端 / miles 真实 CLI 参数解析。主仓库未提交；共享文件本轮只动 `generate.py` 两处（audit 字段与入口赋值），未碰 B 的评分文件。
- **第五组状态**：本机部分收口；后置仍为作业内专用 eval 引擎组、快照 skip 事件、多评测数据集（启动期明确拒绝）与八卡启动命令（随作业方案）。可以开始第六 / 七组讨论；I18 仍单独未决。

### 2026-09-20：第五组剩余本机部分审查 / Codex A 分叉

- **结论 / T0**：[审查报告](batch5_launch_eval_20260919/i21_i22_local_completion_review_20260920/README.md)，Brief §16 与第五组入口已登记。I22 正编号配对窄修接受；A 独立评测仍需 LR1/P1、LR2/P2 两项修正，无新增用户决定。IR1–IR3 维持核销。
- **LR1 证据**：真实 CLI 选项默认 fully_async=False、rollout_global_dataset=True；零轮非 fully-async 驱动仍预取一次训练；没有 prompt_data 的真实默认数据源 TypeError，而显式关闭它的正控成功。现有预检均未处理这两个前提，测试固定 fully_async 并绕过数据源。建议明确首版启动形态与统一 CPU 配置，不新建评测调度系统。
- **LR2 与清单**：引擎有效参数可为同模型路径+dummy，或被 group override 改路径；args.hf_checkpoint 只证明配置来源，需补有效参数与加载判据。另建议 E7 明确故障命中 eval attempt，E10 只核评测自身资源，合法在飞训练不算残留。
- **验证**：120 passed；完整双 lane A 461p/340s、B 801p/0s，fork/pin/19 个语义 patch 前置与相关 ruff 通过；17 个独立 CPU 场景及参数注册默认值已记录；13 个源文件在验证结束后无摘要漂移。I22 四个错配均在读取状态前拒绝，匹配、自动编号、零值与未知加载点的正控符合窄修范围。
- **边界 / 止损**：下一轮只验 LR1、LR2 与清单口径；真实 CLI/模型加载、多 rank、GPU 重叠代价留部署环境，不阻塞第六/七组。只写审查工件与导航，未改生产代码、维护测试、配置、fork 或历史证据；未提交、push、Docker/GPU/远端作业，未向其它用户任务发送消息。

### 2026-09-20：第五组本机收尾审查 LR1 / LR2 已修复 / Claude（A 线分叉）

- **判定**：Codex [本机收尾审查](batch5_launch_eval_20260919/i21_i22_local_completion_review_20260920/README.md) 的 LR1（P1）、LR2（P2）均 accepted，无新增用户决定；I22 正编号配对窄修已被接受，不动。修复记录在 [Brief §17](batch5_launch_eval_20260919/i21_eval_brief_20260919.md#17-对-codex-本机收尾审查-lr1--lr2-的修复2026-09-20claude已实施本机验证)。
- **LR1**：独立评测形态补齐为 `--fully-async --debug-rollout-only --num-rollout 0 --disable-rollout-global-dataset --eval-interval N --hf-checkpoint …`（非 fully-async 分支在零轮循环前就预取一次训练 rollout；默认全局训练数据源在 RolloutManager 构造时读 `prompt_data=None` 即 TypeError）。预检新增三条；**明确预检在首条样本时才运行**——"更早崩溃"与"不派发任何评测"两类配置在真实作业里到不了预检，由启动命令核对清单约束，launcher 直接调用同一函数时才生效。我上一轮的驱动用例有两处绕过：夹具固定了 `fully_async=True`、remote 替身只在 await 时记录（吞掉了未 await 的预取）；现改为一份形态同时过真实 `RolloutDataSourceWithBuffer` 构造、调用即提交的 `train` 原函数体与预检，三个反例各有对照。
- **LR2**：`engine_model_path` 改名 `configured_hf_checkpoint(s)`（配置来源，不是权重已加载的证明，`binding=unverified` 保留）；预检把 dummy 权重加载排除在独立评测形态之外；engine group 的 `model_path` 覆盖首版不支持、由清单 A3 逐引擎核对；配置证据改用真实 `_compute_server_args` 的有效参数四案。
- **清单**：§0 形态与预检运行时点、A3（有效 load_format / model_path、加载日志、`/get_model_info`、无 publish、greedy 抽样；路径相等不足以验收）、E7（确认故障命中评测 attempt——注入只按 task_id 匹配、不分平面）、E10（只核评测 attempt 自己的资源，合法在飞训练容器不算残留）。
- **验证**：双 lane 清净环境 lane A 461 passed / 342 skipped、lane B 803 passed / 0 skipped；contracts / adapters / governance / grading / envpack 非 Docker 1442 passed / 1 skipped；ruff 通过。不动 fork，只更新 manifest 计数；未跑 Docker / GPU / 真实 CLI；主仓库未提交。

### 2026-09-20：第五组 LR1 / LR2 修复复核通过 / Codex（A 线分叉）

- **结论**：[复核报告与探针](batch5_launch_eval_20260919/i21_local_fix_followup_20260920/README.md)，Brief §18。LR1/P1、LR2/P2 均核销，无新增代码阻塞项。本次本机实施与修复审查可收口；I22 与 IR1–IR3 维持接受，第六/七组可继续。
- **LR1**：同一配置连过真实 DataSource、调用即提交的驱动原函数体和预检，一次 eval、零训练提交。非 fully-async、默认数据源无训练文件、跳过首次 eval 三个反例均保留且有排除条件；明确真实预检依赖首条样本，不冒充已接前置 launcher。
- **LR2**：真实有效参数四案成立，env / CLI dummy 均被独立评测形态拒绝，训练中 eval 正控通过。配置来源字段完整进入真实 audit、交付、评测聚合和 run 报告，完整评测点也仍为 binding=unverified。group 覆盖不在首版支持范围，预检不拦，仍须逐引擎核对。
- **文档澄清**：直接修正 GPU 清单 §0（无样本时惰性预检不会执行，包括非零起点或全部过滤）、A3（与基座输出不同不能证明目标权重；greedy 对拍只是辅助证据）。不新增代码工作、挡板或 T0，不回写历史审查证据。
- **独立验证 / 边界**：90 个 I21 用例通过；完整双 lane A 461p/342s、B 803p/0s；相关 ruff 与前置存档核对通过；14 个相关文件至收尾无摘要漂移。未跑完整 CLI、Docker、GPU、远端或全 CPU 套件；未改生产代码、维护测试、配置、fork，未提交、push 或发送跨任务消息。


### 2026-09-20：跨 manager 启动误清理的修复分工建议 / Codex（A 线分叉）

- **范围与状态**：用户拟在第六组前安排 Claude A 修 manager、Claude B 修 driver；本条核对方向与分工，尚未实施或验收。依据 B Codex [19:00 运行发现](env_recipe_repair_20260919/runtime_findings_1900.md)及 `runs/env_recipe_repair_20260919/namespace_probe_1909.json`。已读当前源码和既有探针，没有重跑远端实验。
- **事实**：`SWEGradingManager.startup()` 用共享 label 查其它 manager 容器，超过 3600 秒即 `rm -f`，非法时间戳也按无限年龄删除。年龄不能证明 owner 已结束；B 的隔离探针记录活跃旧时间戳容器同命名空间被删、异命名空间存活。`close()` 则只处理本实例 `_records`，两条路径可以独立修改。
- **A 修复建议**：删除启动时跨 manager 的年龄清扫，保留评分 finally、实例 close/gc 与整 run 已结束后的精确 run-label 清理。无需新增心跳/租约存活探测或抬高年龄阈值。既有 startup 调用可暂留无副作用入口以避免与 B 的 driver 同时改接线；年龄配置及旧测试 oracle 的移除需核对实验脚本消费者。尤其 `replay_with_install_recipe.py` 仍读该配置字段，删除时由 B 同步适配，历史运行证据不回写。owner/trajectory/run 标签继续有诊断和精确清理用途，不随年龄清扫一起删除。
- **代价与边界**：进程异常消失留下的容器，不再由新 manager 猜测后自动回收；在确认所属 run 已结束后按其 run_id/容器名清理。缺 run 标签时不能退回共享 label 全扫。单个 manager 结束也不能触发仍有其它活跃 worker 的整个 run 清扫。
- **B 修复建议**：只改重放 CLI 及其测试，不与 A 同改 manager.py。现 `scripts/replay_grade.py` 打印 manager_close 后只看 halted 决定退出码；未清容器、close 异常/无法确认收口必须非零并保留摘要。`cleanup_failures` 是累计历史，不能仅因曾经失败但最终已清理就一概判失败；沿已批晚清理口径保留诊断。模型未解出/reward=0 与 CLI 运行失败分别处理。
- **不要遗漏**：原报告还有中断日志被标 `log_partial=false`。A 在同一 manager 文件里核对 `_exec_bash_checked → _run_eval` 的实际返回码/中断事实运输；不能将删除清扫等同于该观测问题已修。先用既有故障输出或窄探针定位，保持 infra reward=None，不凭缺日志改判模型负样本。
- **窄验收**：同命名空间两个 manager，外来活跃容器无论年龄/时间戳如何均不被 startup 或本实例 close 删除；自身评分成功/异常/取消仍清理；driver 正常收口返回 0、未清/未知收口返回非零、晚清成功留诊断。必要时只重放短 sleep 容器 Docker 探针，无需重跑 216 题或 GPU。按用户现有方向推进，不另开训练语义决策；代码完成后分别聚焦复核。

### 2026-09-20：R2E 接线计划复核 / Codex（A 线）

- **结论与交接**：[复核报告、CPU 探针与结果](r2e_grading_wiring_review_20260920/README.md)；[实施计划 §11](r2e_grading_wiring_20260920.md) 已追加指针。方向可行，原稿须修 2 项 P1 / 3 项 P2 后推进对应切片；不是实施验收或用户批准。
- **关键勘误**：DR2 复用了 09-09 已撤回的“Prime 正则漏 ESC”误读。固定上游源码 AST 函数重放 336 份旧日志，与本地 runner 的 reward 全部一致；含 ANSI 的 pillow 六题共 24 次 gold 均为 1。建议撤回当前 DR2 二选一，不实现虚构的 `prime_v1` 及双结果通道，固定真实代码版本；历史日志不回写。
- **接缝**：R2E 空 F2P/P2P 桶使现有 manager 把“部分缺键”也当“全部缺席”；提前 infra/P-A 候选归因等分支会丢失来源语义并回落 SWE。须补实际 producer 测试。混来源验收应是同批不同题组，不改 GRPO 同题分组。原稿输入文件仅 24 行，应改用已核对的 M3 48 行合并快照。单镜像 build-time chown 不能推出两侧初始化成本消失：rollout/grader 默认 UID 分别 54321/54322。
- **决定与分期建议**：DR1/DR3 推荐 A，DR4 沿既定来源口径与后续筛题分期，DR2 撤回。正式 actor 的派生环境执行仍未验；多来源 loader 保持现有默认题单，R2E 显式选入。driver 收口修复按已登记 B 分工在真机批前完成；manager.py 与 run_report.py 不和其它 A 任务同时修改。
- **验证 / 边界**：336 份既有日志离线重放、48/24 输入核对、真实 P-A 判定与五条 manager 报告分支、profile 渲染 UID/chown 核对通过；探针 ruff E9/F 通过。manager 探针替代尚未实现的 R2E 字段 producer，候选案另替代归因结果，不宣称正式 R2E 接线完成。只写审查工件和导航，未改生产代码/维护测试/配置，未跑 Docker/GPU/远端、未提交或派发消息。

### 2026-09-20：跨 manager 启动误清理——manager 侧已修复、本机验证 / Claude（A 线分叉）

- **范围**：按上面 Codex 的分工建议与用户安排，A 只改 `rh2/src/repoharness2/grading/manager.py`、其测试与三处过时注释（`grading/__init__.py`、`shutdown/run_residue.py`）。B 的重放 CLI 与实验脚本未动；无新增用户决定；reward 语义与 P-A 判定不变。
- **清扫**：`startup()` 改为无副作用入口（恒返回 `[]`，保留给既有调用方），删除 `GradingManagerConfig.orphan_min_age_seconds`。评分 `finally`、本实例 `close()/gc()`（只认自己的 `_records`）、run 确认结束后按 `rh2.run_id` 的精确清理不变；owner / trajectory / created_at_epoch 标签照盖。**代价**：进程异常消失留下的评分容器不再被后来的 manager 自动回收，须在确认所属 run 结束后按 run_id / 容器名清理，缺 run 标签时不退回共享 label 全扫。不新增心跳或孤儿回收服务。
- **`log_partial=false` 的定位（用既有故障输出）**：`runs/env_recipe_repair_20260919/numeric_v1e/tasks/Project-MONAI__MONAI-763/gold/ledger.jsonl` 该行 `markers_seen` 止于 `RH2_TS_TEST_START`、`test_rc=null`、日志尾停在测试中途，却记 `log_partial=false`；同目录 `driver.log` 的收口记录显示随后的 `rm -f` 报 "removal … already in progress"、状态 stopped。运输路径：exec 以 137 返回 → `_exec_bash_checked` 的 inspect 此刻仍看到 running（大进程拆除期间删除未完成）→ 结果原样返回 → profile 路径"exec 返回即 `log_partial=False`" → 截断日志交给 parser，报告成了 `official_bad_codes_after_successful_replay`。删除清扫只消除了这次的触发源，不修这条运输，所以一并修了两支：
  1. **竞态支**：候选段是否跑到收口看日志事实（`RH2_TEST_RC` / `RH2_TS_TEST_END` 任一在场；脚本完全不打标记 = 未知）加 exec 真实退出码。exit ≥ 128 且未到收口 → `grading_candidate_exec_killed:signal=N:candidate_phase=…`（infra、reward=None、不追加评分）。测试进程被杀但脚本自己收尾（`RH2_TEST_RC=137` 在场）仍走既有解析路径。
  2. **容器已死支**（真实容器实测发现的相邻缺口）：既有 `grading_container_killed_during_test` 丢弃了 exec 已交付的输出与退出码，容器不在后 tee 文件读不回，sidecar 只剩 setup 日志、`candidate_phase=unknown`。现由 `GradingInfraError.exec_result` 携带，实测同一场景得到 `candidate_phase=test`、`candidate_exec_exit_code=137`、`candidate_segment_completed=false`、候选输出保留。
  - 新增事实键 `candidate_exec_exit_code`（None = exec 未返回，即超时 / 取消）、`candidate_segment_completed`（True / False / None）；`log_partial` 的含义扩为"候选段未到收口，或 exec 被信号终止，或超时 / 取消后的部分读取"。收口行在候选测试输出之后打印、候选可伪造，但伪造只会把"被打断"变回"按截断日志评分"，换不到 reward。
- **oracle 变化**：年龄清扫的单测与真实 Docker 用例翻转为"外来活跃容器（旧时间戳 / 非法时间戳）经 startup + 本实例 close 后存活、自身容器照常回收、配置字段不存在"；`test_replay_grade` 的 R3 用例夹具原是手写缩略日志（缺真实脚本必打的收口行），补齐后断言 `partial is False` 不变，并加缺收口行的反例；profile 单测的精确事实字典加两个新键。新增：竞态支单测、容器已死支单测、收口事实参数化（含 fixture 只打 `RH2_TEST_RC` 的形态）、真实容器"候选测试中被外部 `rm -f`"用例。
- **验证**：contracts / adapters / governance / grading / envpack 非 Docker **1449 passed / 1 skipped**；`tests/grading` + `tests/adapters` 真实 Docker **49 passed**（本机 Docker，含上述新用例，结束后无残留容器）；`tests/adapters_miles` 集成树 803 passed（lane 计数不变，未动 fork / manifest）；相关 ruff 通过。未跑 216 题、GPU、远端；主仓库未提交。
- **B 侧待办（owner = B，A 未改）**：① `rh2/experiments/env_recipe_repair_20260919/replay_with_install_recipe.py:129` 仍读 `after.orphan_min_age_seconds`，只在传 `--grading-label-prefix` 时执行，届时 AttributeError；该处的 scope 文案"production orphan detection remains unfixed"也已过时。② 同目录 `probe_grading_namespace.py` 钉的是修复前行为（同命名空间旧容器被删）并读同一字段，修复后必然失败——建议作为历史反例保留并注明对应的 manager 源摘要，维护中的等价用例是 `tests/grading/test_manager_docker.py::test_foreign_live_containers_survive_another_manager_startup_and_close_real`。③ CLI 退出码所需事实 manager 已具备、无需再改 manager：`close()["containers_open"]` 是最终状态（本实例记账中未确认删除的容器），`cleanup_failures` 是累计历史（含之后已清理成功的）。④ `scripts/screening_facts.py:520` 对 `log_partial` 的注释"超时后的部分读取"可按上面的新含义更新。B 线会话在本机会话列表里无法按名称识别，未发跨会话消息，由用户转达。


### 2026-09-20：跨 manager 清扫修复聚焦复核通过、诊断残余分期 / Codex（A 线分叉）

- **结论 / T0**：[审查报告与独立探针](manager_cleanup_review_20260920/README.md)。删除跨 manager 年龄清扫接受，无新增阻塞或用户决定。startup 无副作用、外来活跃容器不被清理、自身 finally/close/gc 保留。exec=137 时 inspect 仍 running 或已 stopped 的两条运输路径已修，正常正负 reward 与资源清理对照通过。
- **CR1 / P2，非阻塞诊断余项**：exec 已交付 stdout/137 后，在 inspect 或异常分支读 tee 的 await 上被取消，仍会丢尾部和退出码；完整旧 manager 与当前实现对照均复现。另有 tee 非空但比 stdout 短时丢后半段并误记阶段。取消仍传播、容器仍回收，没有额外错误 reward；建议由 A 后续维护，先保存已交付结果再补 tee，不新增恢复机制。验收条件与 owner 建议已写报告，作者处置待回填，不阻塞本轮或下一组。
- **修正说明**：上条 Claude 记录及源码注释的“伪造收口行换不到 reward”过强；合成官方 End/PASSED 输出时旧新代码均可给 1，收口行不构成可信评分证据。已知 stdout 信任边界继续归 B，不作为本轮新回归。`candidate_exec_exit_code=None` 只能表示未记录到退出码，不能保证 exec 未返回。历史记录不回写，以本条澄清。
- **独立验证**：152 个相关非 Docker 维护测试通过；5 个真实 Docker 对照通过；8 案主探针、6 案取消/运输差分、4 案生产渲染器真实 Bash 正控通过；相关 ruff 通过，8 个受审文件验证期间摘要不变。MONAI 用既有日志核对摘要并注入 rc/state 重放，没有重跑题目。未将作者的 1449/49/803 数字冒充独立验证；未跑 216 题、GPU 或远端。
- **B 交接 / 边界**：`replay_with_install_recipe.py:129` 的已删除年龄字段仍须在下次使用 `--grading-label-prefix` 前适配；旧 namespace probe 属历史反例；CLI 最终退出码由 B 独立修验，不按累计 cleanup_failures 一概判失败。未向不明会话发消息。只新增审查工件和本条，未改生产代码、维护测试、配置、fork、历史运行证据；未提交或 push。核心反例/正控已齐，本轮停止扩审。

### 2026-09-20：R2E 计划修订与 R-0 driver 聚焦复核 / Codex（A 线）

- **结论 / T0**：[复核报告与证据](r2e_grading_wiring_review_20260920/followup_20260920.md)，[计划 §11.2](r2e_grading_wiring_20260920.md) 已登记。计划修订通过，旧五项及 B 线补充已落实，无新 P0/P1 或用户决定；可以推进 R-a / R-b，正式 R2E 接线尚未实施。
- **R-0**：真实 driver → replay_one → manager 的 CPU 控制流确认：正常及晚清成功为 0、最终残留为 3、typed 停批为 2，停批后清理成功仍为 2；exec=137 的事实进入账本且 reward 保持 None。使用固定 profile 配置与 Docker I/O 替身，没有将手工状态函数测试当成整链验收。B 两份实验脚本已适配删除的年龄字段/注明历史用途，上一条交接中的这两项现已核对落实。
- **非阻塞 P2**：CR1 未捕获异常或取消时，进程继续失败，但新 `final_status` 可能误报 0/ok；CR2 scope 异常覆盖报告返回时，已经落盘的日志/sidecar 没挂入停批账本，取消分支 `test` 块仍未填。建议 owner = B driver 实现者，随下一次 driver 窄改、在 R-f 异常对账/摘要消费者启用前补齐；不阻塞材料/parser，不改变 reward/停批，不新增恢复机制。作者处置待回填。
- **验证 / 边界**：21 个维护测试通过，8 案 CPU 探针与 1 个未 mock 的真实 CLI 缺补丁子进程；代码 ruff、探针 E9/F 通过，测试文件尾多一空行属 T2。未重新跑 336 日志或全库/Docker/GPU/远端；没有把 Claude 的全量数当独立结果。按 §10.4 双角色复核并由主审独立复现，核心证据齐全，本轮停止扩审。
- **改动范围**：只写本次审查文档、探针、结果与两处导航；未改生产代码、维护测试、数据、配置、fork，未提交/push 或发送跨任务消息。

### 2026-09-21：第六组评分容器与依赖供应的设计讨论 / Codex（A 线分叉）

- **状态**：[讨论记录](batch6_efficiency_20260921/grading_environment_options.md)，仅建议，未改变用户已批 D2 的 fresh 评分与网络策略，未启动实施。应分别决定交付物（可重建仓库修改或最终环境）、容器复用方式和分阶段的包供应能力，避免把验收对象变化当成单纯性能优化。
- **外部与本地事实**：回查 MAI 官方报告，确实在原任务容器评分，必要联网经缓存代理/域名允许列表；不应再称 fresh grader 为该报告要求。当前 RH2 只重放 workdir 文件增量，工作区外安装状态不会继承。B 的新依赖 canary 验证了声明加预置 wheel，尚未证明任意新依赖；216 题 noop/gold 也不能估算真实 CC 因环境状态遗失的失败率。
- **建议**：当前 SWE 若仍以可重建仓库修改为成果，保留 fresh 首版、单独改进依赖供应及扫描/初始化；若认可活环境本身是成果，同容器更契合，避免为了 fresh 建完整环境录制重放系统。两者均可复用来源评分、环境修复及训练接线。原容器需重新明确停止 agent、容器持有交接、执行身份及私有测试注入，不能只搬当前 root trusted setup。
- **证据与边界**：只重汇总旧 432 条账本，431 次实际评分的 grader 启动/基线重建中位数约 1.0/4.6 秒；脚本、原始账本摘要和结果在同目录。不是新实验或预期提速；未测全链三次扫描总成本，不能把重编译全部视作换容器开销。仅新增讨论工件与本条，未改生产代码、既有测试、配置、历史 evidence；未跑 Docker/GPU/远端、未提交或推送。

### 2026-09-21：第六组四项决定确认、依赖供应准备设计 / Codex（A 线分叉）

- **用户决定**：四项原建议全部同意，集中在 [第六组 README](batch6_efficiency_20260921/README.md)：I25/I26/I29 等价窄优化；I23 无损紧凑表示（I18 来源仍不定）；I24 诊断/效率配置、首次完整 GPU 诊断保留额外 forward；I27/I28/I30 按既定八卡实测分期。已回写分组导航与 06 的补充指针，不重复请用户确认。
- **实施建议**：E1 权限初始化、E2 批量 census 可先由 A Claude 写窄 Brief；E3 tape 表示、E4 完成历史各自独立；E5 配置/测量准备。给出了真实消费者与最小验收要求，不把删除检查、丢弃路由轮次、累计统计缩水或大规模拓扑改造夹进窄优化。共享文件按 B 当前 owner 顺序修改。
- **评分/网络方向**：继续独立评分；准备共用受控 Python 包源/下载缓存与两侧安装能力，具体组件、来源和阶段切换待短设计。当前 grader 已先注入私有测试再安装，必须一起处理可见时点和真实出口，不能只改网络参数。已有可解题环境的基座诊断不等完整网络能力，不先建两套评分系统。原容器作为后续优化候选，触发调查后看评分可比性与总成本，不仅看一次启动时间。
- **修正旧表述**：采纳 B，补丁目标不必然要求 fresh，同容器也可以是补丁任务的执行优化；它的单次通过不独立证明可重建性。已在上一轮讨论追加澄清，未回写历史证据。
- **核对与边界**：核查当前 census、权限链、网络 profile、grader 阶段及 miles actor forward 条件，在线核对 MAI、pip 与 devpi 官方资料。本轮仅文档与设计，无生产代码/配置/测试/fork 修改，无 Docker/GPU/远端作业或提交/push；未向 Claude/B 任务发送消息，实施尚未开始。

### 2026-09-22：跨 manager 修复已提交；第六组方向检查 / Claude（A 线分叉）

- **提交**：用户要求后提交 `24456d08`（manager 修复，8 个文件；`tests/adapters/test_replay_grade.py` 只含本修复的 hunk，B 线 R-0 改动仍在工作区未提交）与 `cee933b4`（仅注释：按 Codex 澄清，收口行不是可信评分证据、`candidate_exec_exit_code=None` 不保证 exec 未返回）。提交前在干净 worktree 复验 152 passed。未 push；infra.md 不进提交。
- **对 Codex CR1 / P2 的处置**：accepted，deferred_with_owner_and_gate——owner = A，随第六组 E4（同在 `manager.py`）一起修：exec 结果一交付就先记到 record，再去 inspect / 读 tee；tee 比已交付 stdout 短时以较长者为准。gate = 八卡作业前。不改变 reward 与取消传播。
- **第六组方向检查**：[检查意见](batch6_efficiency_20260921/claude_a_direction_review_20260922.md)。四项决定与"继续独立评分"无异议；E1–E5 方案成立。补充：① 优先级建议 E3 先（事件循环阻塞的条件估算在 64 并发下可饱和，须先实测每轮关键路径）；② 本机探针显示 `chown -R` 在 overlay 上整树 copy-up——scikit-learn 镜像 rollout 侧约 0.25 GB、评分侧（含 conda 前缀）约 1.2 GB 写入，E1 原范围只消除便宜的重复遍历，提出需 B 配合的候选 E1+（派生镜像预置属主、两侧 uid 对齐），先测后定；③ E2 用 coreutils 批量，不用容器内 Python。
- **依赖供应的两点不同意见**：① 需要按题目 `created_at` 截止的索引视图，同时堵"装被测项目后续版本读修复"的泄漏与版本漂移，过滤必须在服务端；② 首版不调换评分阶段顺序，保持 root 可信 setup 先于任何候选代码，只把候选段拆成"安装段联网 / 断网 / 测试段离线"两次 exec——调换后 root 需在候选可写的 `.git` 与 conda 激活钩子之上再跑 git / 激活环境，会破坏 F2 前提。rollout 侧复用既有 `InternalService` relay，不需要新拓扑。
- **待用户决定**：时间截止视图是否采用；评分阶段保持顺序还是调换；是否测量后把 E1+ 交 B 评估。方向确认前不起 Brief、不改生产代码。本轮只读源码与资料，另做一次用完即删的本机 Docker 探针；未跑 GPU / 远端。

### 2026-09-22：第六组方向复核与依赖供应取舍 / Codex（A 线分叉）

- **结论**：[方向复核](batch6_efficiency_20260921/codex_direction_review_20260922.md)。四项效率决定与 fresh 评分继续有效；采纳 E3 可先做、E2 批量 coreutils 候选，E1+ 的既定目标机测量与方案评估无需重复授权。效率 Brief 不等网络选择；未批准新的权限边界或网络实现。
- **两项用户取舍**：包源历史限制范围（建议默认限制被测项目远端发行包、保留 B 验证兼容依赖，不一律以题目年份限制第三方包）；私有测试可见时联网安装（首版可保持现顺序，但明确接受受控取包时已可读私有测试）。两者尚未定案。MONAI-763 的 2020 年题目与已验证配方中的 2022 年 NiBabel 是历史截止政策的实际权衡；仅过滤远端不会立即禁掉预置 wheel。
- **必须补齐的设计**：共享 relay 同时含模型代理及其他服务端口，包源侧又只看到 relay 来源，不能直接宣称仅通包源/天然按 attempt 记账；安装与测试拆 exec 必须保留支持的 shell 状态、期限、日志和资格事实；下载不等于安装，事后健康探针不足以单独确定失败原因。
- **修正与验证**：600 秒是预算上限，不能作吞吐收益分母；本机全量 copy-up 不能推广到启用 metacopy 的目标机，也不重新建议全局启用 metacopy。按审查标准两路复核，主审核查源码/真实配方/官方组件，运行当前阶段渲染器的 CPU/Bash 反例：同 shell 测试 rc=0，直接拆 shell rc=1。证据在本批目录；没有测试实际网络部署或重跑既有 manager 测试。
- **边界**：仅文档、审查探针和结果；未改生产代码、维护测试、配置、fork 或历史运行证据；未运行 Docker/GPU/远端，未提交/push，未向 Claude/B 发送跨任务消息。本轮设计复核结束，具体网络实现留短 Brief 检查。

### 2026-09-22：第六组方向收口（用户倾向）与 E3 窄 Brief / Claude（A 线分叉）

- **对 Codex 方向复核的处置**：[复核](batch6_efficiency_20260921/codex_direction_review_20260922.md)的修正全部 accepted，回应写在[方向检查 §7](batch6_efficiency_20260921/claude_a_direction_review_20260922.md)。核对属实的证据：MONAI-763 `created_at` 2020-07-15 而已验证配方离线安装 2022 年的 `nibabel==4.0.2`，且配方开头 `export OMP_NUM_THREADS=…` 依赖同一 shell；本项目自己的 metacopy 记录（chown 180 s → 11 s，后因与 `docker commit` 组合产生全 0 文件撤回通用开关）；`relay_listen_map()` 恒含模型代理端口。我原先的四处过强表述（E1/E2/E4 不影响吞吐、overlay 改属主必全量复制、下载出口无信息外发、健康检查可定归因）以 §7 为准。
- **用户倾向（2026-09-22，选择一为"暂时倾向"，未记为最终决定）**：选择一取 Codex 的 1A——默认不提供被测项目自身的远端发行包，第三方依赖不按题目日期截断；选择二取 2A——保持现有评分阶段顺序。**我撤回"时间截止视图是必需的"**：我们验证过的环境本来就不是题目当年的依赖世界，套历史视图会挡住兼容版本。1A 落地需要仓库→发行包名对应表（含 `hydra-core`、`monai-weekly` 这类异名/同源包）、宿主按 attempt 绑定且候选改不了的索引入口、索引页与文件下载同受约束；不声称可复现，记录实际安装版本。2A 的机制由"拆两次 exec"改为**同一 shell 内的可信闸门**（安装段结束 → manager 断网并确认 → root 放行 → 测试段），grader 用只通包服务的窄接法，不复用 rollout relay；明确接受私有测试可读时仍可向包服务发请求。
- **E3 窄 Brief**：[e3_routing_tape_brief_20260922.md](batch6_efficiency_20260921/e3_routing_tape_brief_20260922.md)，待 Codex 聚焦检查，未实施。用真实函数跑的本机微基准（`rh2/experiments/batch6_e3_20260922/baseline_bench.py`）：逐轮 hook 8K/16K/32K = 76/157/374 ms，与清单历史探针吻合；新增两点——每叶的投影层再展开是最大单项（32K 时 1,081 ms），`raw_meta_info_digest` 占逐轮约三分之一且大头是 `json.dumps` 而非哈希（三段式流式计算 144 → 35 ms、摘要逐位相同，列为可选子片 E3b）。方案：全程只留一份小端 int32 字节，工件字节/摘要/契约不变；`TurnTape.routed_experts_flat` 改名为 bytes 字段以免漏改处悄悄算错；不满足 dtype/维数/字节序即回落现状路径。
- **提醒**：第五组 I21/I22 的主仓库改动仍未提交，E3 会叠加在同一个 `generate.py` 上；是否先提交第五组由用户定。本轮只写文档与一个未跟踪的基准脚本，未改生产代码，未跑 Docker/GPU/远端。

### 2026-09-22：第五组 I21/I22 已提交；E3 Brief 补齐循环拓扑与冻结面说明 / Claude（A 线分叉）

- **提交（用户同意后）**：`0b5a5189` 代码、测试与 fork patch 存档（26 个文件：adapters/miles 五个既有文件与 `eval_report.py`、adapters/slime 的 `bringup.py` / `generate.py` / `eval_result.py` / `eval_wiring.py`、九份 I21 用例、两处 oracle 同步、patches 0018–0020、manifest、patches README）；`110bbd91` 第五组 README、I21/I22 Brief、GPU 核验清单。逐文件核对过 hunk 归属：工作区里 B 线的 R2E 在制品（envpack、`prepared_task_face.py`、`replay_grade.py`、`manager.py` 新改动等）与 `decision_package_D2_B.md` 的既有改动都没有进提交；Codex 审查目录按惯例不进提交；infra.md 不进提交。未 push。
- **提交后复验（干净 worktree，导入的是提交内源码）**：集成树形态 `tests/adapters_miles` + 两份 I21 adapters 用例 832 passed；原始 pin 形态 461 passed / 342 skipped，与 manifest 计数一致。
- **E3 Brief 补充**：① 读代码确认逐轮捕获成本落在**单个** adapter aiohttp 线程的循环上、每叶成本落在 miles 共享后台 owner 循环上，全 run 的会话各共用一个，不被多进程分摊（占用率仍要真实作业才有，归 E5）；② `adapters/slime/projection.py` 按既有约定是 slime 冻结面，E3 主方案要动它的三个内部 helper（输出逐位不变、以既有测试面为对照），已在 Brief §3.1 单列为需要 Codex 表态的偏离，并给出零触碰的备选与折中。Brief 现可交 Codex 聚焦检查。

### 2026-09-22：E3 Brief 聚焦复核 / Codex（A 线分叉）

- **结论 / T 级**：[复核及证据](batch6_efficiency_20260921/e3_plan_review_20260922/README.md)。采用主方案，按已批 I23 接受对 RH2 自有 `adapters/slime/projection.py` 的窄等价优化；原“冻结面零触碰”文案确实更强，本轮作为 T1 强报告偏离，不宣称从来只冻结语义，不全面解冻。`TurnTape` 改名同意，E3b 可在主体后独立提交/验收；无需新 owner 决策。
- **实施前修订**：ER1，旧解码器先 `.tolist()`，memoryview 不能直接走原字节分支；ER2，值域内 int64 旧链可通过，非 int32 是回退条件而非统一拒绝，快路径仍须对照配置形状；capture 超界旧抛 `struct.error`、projection 才包装 typed 码，按入口保留。ER3，“每轮 tape/store 共用 bytes”不等于全生命周期一个 buffer，逐叶 tensor、分支工件和 canonicalize ndarray 各有存量。正式 JSON/base64 路径无 memoryview，不把该兼容反例说成已发生训练污染。
- **验收补充**：真实 sampling-support wrapper→projection→canonicalize；两叶修改隔离且 capture 工件不变；记录对拍固定时钟；E3b 按 JSON 结构定位已验证的 routing 字符串，不搜索占位文本。`frombuffer(bytearray)` 经局部引用释放/GC 仍有效，无需额外 clone。
- **生产与性能证据**：当前单 RolloutManager 拓扑下逐轮 hook 在 adapter 循环、逐叶消费在 owner 循环；model-call=32 不限制全部 tape 存量。原微基准重跑：32K hook 358.5 ms、张量化 343.0 ms、投影 1047.0 ms；累计微基准 RSS 1872.8 MiB 不能叫生产单轮峰值。E3b 的作者 144→35 ms 未在本脚本复现，实施后需含判定成本计时。
- **验证 / 边界**：依 §10.4 两路审查，主审独立核对关键源码并跑小反例/正控；相关基线 36 passed，审查探针 ruff 通过。只写审查工件、导航和本条；未改生产代码、维护测试、配置、fork 或作者方案正文；未跑 Docker/GPU/远端，未提交/push 或发跨任务消息。修订并入后可开工；不扩大到 I18、第五组重审或网络供应。

### 2026-09-22：第六组 E3 主体已实施、差分逐字节相同、已提交 / Claude（A 线分叉）

- **对 Codex 计划复核的处置**：ER1–ER3 与 §3 验收补充全部 accepted，并入 [Brief §7](batch6_efficiency_20260921/e3_routing_tape_brief_20260922.md)；实施记录 §8。冻结面窄偏离按 Codex 依用户第六组决定的表态执行（T1 强报告，不解冻）。
- **实施**：`projection.py` 新增直通解码 / 字节引用 / 3 维 int32 数组快路径（保留 layers/topk 对照与引擎行数公式），`_build_routing` 不适用时原封不动走旧路径含旧错误顺序；`generate.py` 的 `TurnTape` 路由字段改名为 bytes，hook 对非 wire 形态沿用旧路径（超界仍是原生 `struct.error`），backfill 按字节裁剪，`torch.frombuffer(bytearray)` 给每叶自己的可写缓冲区。提交 `45c67de3`（含 4 处测试改名、新增 12 + 1 例、manifest 计数、第六组 README / 两份讨论稿 / 成本汇总 / 方向检查 / Brief；Codex 的两份审查工件按惯例不进提交）。
- **差分证据**：旧树 `110bbd91` 与新树各自独立进程跑同一探针（只调生产入口，固定 `_now_utc`），输出 JSON 除 `tree` 字段外逐字节相同：捕获记录全字段、逐轮与分支工件摘要、精确 / 裁剪两种叶的张量与 metadata、canonicalize ndarray、无配置保底、13 项错误矩阵的异常类别与 reason_code。探针与结果在未跟踪的 `rh2/experiments/batch6_e3_20260922/`。
- **本机测量（旧 → 新，25 轮增长到 32K 行 × 48 × 8、两叶，独立进程）**：捕获合计 69.2 → 2.6 s；最后一轮 5,074 → 194 ms；捕获期心跳最大延迟 7,521 → 296 ms；tracemalloc 常驻 6,867 → 627 MiB；每叶投影 5,866 → 17 ms；进程 maxrss 9,827 → 2,644 MiB。单轮微基准看不出的事实：旧表示的逐轮成本随 session 存量恶化（同规模单轮 0.54 s，第 25 轮 5.1 s）。均为本机 Apple Silicon 数字，不外推到多并发与 GPU 作业。
- **验证**：既有 `test_project_from_slime.py` + `test_slime_generate.py` 91 例不改断言通过；五目录非 Docker 1555 passed / 1 skipped；双 lane 脚本全绿（A 461p/343s、B 804p/0s，manifest 已同步）；ruff 通过。
- **接下来**：E3b（meta 摘要流式等价）按 Codex 意见排在主体之后、独立提交与验收，实施中。

### 2026-09-22：第六组 E3b（meta 摘要流式等价）已实施、已提交 / Claude（A 线分叉）

- **实施**：`generate.py` 的 `_canonical_meta_digest`，只对已严格 base64 解码成功的顶层 `routed_experts` 串按键序结构定位、五段 `sha256.update`；`contracts/_base.py` 原函数不动、作 oracle；未设大小阈值（一条路径，全尺寸等价测试覆盖，比 Brief §3.3 原写法少一个分支）。记录见 [Brief §9](batch6_efficiency_20260921/e3_routing_tape_brief_20260922.md)。提交 `d4a11940`（E3b 单独可回退）。
- **等价与测量**：11 例全尺寸 / 键位 / 同值干扰 / Unicode / 回落 / TypeError / hook 记录对拍通过；摘要 28 / 52 / 107 ms → 5 / 10 / 21 ms（8K / 16K / 32K 行），逐位相同；单轮 hook 合计 旧 182 / 294 / 544 → E3b 22 / 42 / 85 ms（本机，独立进程）。
- **验证**：五目录非 Docker 1566 passed / 1 skipped；双 lane 脚本全绿（A 461p/343s、B 804p/0s，计数不变）；ruff 通过。未跑 GPU / 远端；旧树 worktree 已删除，差分与基准结果留在未跟踪的 `rh2/experiments/batch6_e3_20260922/results/`。
- **交 Codex 聚焦复核**：E3 主体（`45c67de3`）与 E3b 各一次；建议复核重点：快 / 旧路径的分流条件（`_routing_int32_array_payload` / `_routing_fast_payload`）、hook 里 `routing_verbatim` 的前提是否只在严格解码成功后成立、`frombuffer(bytearray)` 的生命周期、E3b 的键序结构定位。可用 `results/differential_*.json` 与两份基准脚本直接重跑。
