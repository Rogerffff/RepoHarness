# SWE 任务生产、环境验证与题目质量：逐来源汇总

更新：2026-09-15。本页以已有精读的环境相关章节、来源和审查记录为基础，重点回查部分原网页；没有重跑这些环境，也不宣称重新全文精读全部原论文。下面“可复用”是我们的分析，不是项目定案。F2P 指修复前失败、修复后通过的测试；P2P 指应保持通过的回归测试。**两侧测试对照、题意有效性、评分可信性和目标模型可学性是不同证据。**

## 1. SWE-Gym：半人工恢复历史环境

**作者做法：**从真实 issue/PR 提取任务，按仓库版本恢复历史依赖，参考 CI、requirements 与文档人工修订安装。最终发布 11 仓、2,438 题；Lite 再排多文件、复杂 diff、描述差及主要检查错误消息的题。原作者评分 fork 按仓库/版本生成安装、测试命令和 parser；候选补丁在新评分环境运行，按固定 F2P/P2P 对账。

**可复用：**把安装、候选后重装、测试选择、逐测试解析一起保存；不能只复用镜像或一条 `pytest`。mypy 的 `-k` case 选择和 conan 的额外环境命令都说明仓库适配的必要性。

**边界：**Lite 改变了仓库与任务分布；原建设验证器与正式评分器语义不同，普通 OpenHands 空补丁入口还会直接返回，不实际跑测试。不能把“empty 得 0”当作有效负对照。原文未证明合法替代解、全库稳定性或未来答案隔离。

定位：[论文 v2 §3.1–3.2](https://arxiv.org/html/2412.21139v2)；[官方评分 fork](https://github.com/SWE-Gym/SWE-Bench-Fork/tree/242429c188fcfd06aad13fce9a54d450470bf0ac)；[本地精读 §3、§7](../reading_notes/O04_swe_gym.md)。

## 2. R2E-Gym：真实 commit＋生成题面与补充测试

**作者做法：**筛选小规模历史代码改动，半人工搜索依赖 pin、试装 Docker；优先用关联测试，缺失时允许生成器参考 gold 补测试。由 diff、旧/新执行结果和断言反译题面，再迭代删除冗余 gold 改动、重跑测试。训练 Subset 排除 SWE-bench 测试仓库；论文的轨迹采集不提供互联网或浏览器。

**可复用：**题面生成应结合实际失败与预期行为；生成测试还要检查是否无区分力、是否连正确解也拒绝。其测试 agent 分析发现后者可能发生，不能按“区分率高”直接接受测试。

**边界：**反译提示要求不泄漏，并非泄漏审计。后来官方运行时匹配完整 `expected_output_json`，允许预期本身为 FAILED，**不等于全部测试都须 PASSED**。该现行代码语义不能倒填为论文完整训练规约；未给重复稳定性与合法替代解全量验证。

定位：[论文 v1 §2、§4.2、附录 A–C](https://arxiv.org/html/2504.07164v1)；[本地精读 §2、§4、§5、§7.3](../reading_notes/O03_r2e_gym.md)。

## 3. SWE-smith：先搭好一个版本，再批量制造 bug

**作者做法：**先安装固定仓库版本，要求原版本超过 80% 测试通过，并人工审核 Dockerfile/parser；随后用 LM 修改、重写、程序变异、组合及历史 PR Mirror 制造 bug。保留打破至少一个原有 passing test 的任务，剔除测试超过两分钟者；一份基础镜像承载许多独立 bug 分支。题面可由 diff、失败源码/日志、模板或旧 issue 产生。

**可复用：**将仓库安装成本摊到多题，记录每种 bug 生成方法的产率与分布；验证 patch 的方向——本数据 `patch` 是引入 bug，反向应用才是参考修复。

**边界：**论文中 F2P 在求解时可见、可运行；现行代码的移除/恢复测试机制是后续变化。作者明确未系统检查题面歧义/答案泄漏，原始产物不宜直接作正式评测。两分钟过滤也是分布选择，不能照搬为统一资源上限。

定位：[论文 v2 §2、附录 A–D，尤其 C.2](https://arxiv.org/html/2504.21798v2)；[本地精读 §2–3、§6–8](../reading_notes/E5_swe_smith.md)。

## 4. ScaleSWE：分工生产环境、测试和题面

**作者做法：**EBA 通过终端反馈安装并提炼 Dockerfile；每仓最多选 10 个 PR 完整建环境，其他 PR 借用 PR ID 最近的环境并重新执行验证。UCA 生成/补足 F2P、P2P；PSWA 重写需求，说明测试必需的新接口但避免给实现方案。验证 base 上 F2P 失败、P2P 通过，gold 上两类通过；固定测试顺序，清除可恢复的未来 Git 信息。另随机人审 100 题，报告 94 题有效。

**可复用：**仓库负责人维护环境复用，逐题仍验证；安装者、测试者、题面作者职责分开。必要接口信息不应一律当作泄题删掉。

**边界：**94/100 不是全库质量保证；同环境复用的历史版本错配、测试污染和替代解仍需检查。当前 AweAgent 的 marker/XML/summary 判分条件不等价，不能直接以“官方 scorer”作为正确性证明。旧精读尚缺附录 E 生产提示词及原图核验，属于待补读，不是作者未公开。

定位：[论文 v4 §2.1–2.3、附录 D](https://arxiv.org/html/2602.09892v4)；[本地精读 §3–4、§8及自查链接](../reading_notes/O05_scale_swe.md)。

## 5. SWE-rebench V2：安装、parser、稳定性、题意分层处理

**作者做法：**从带测试的真实 PR/issue 拆出修复与测试补丁；用交互 agent 在仓库一个较新任务快照合成安装和测试 recipe，再给各历史任务验证。生成仓库 parser，必要时按新日志迭代；运行修复前后完整套件，编译语言补丁后重新构建，保留非空 F2P，并要求三次结构化结果不变。三名 LLM judge 一致同意题意足够才保留，另标隐含命名、外链依赖、无关 PR 改动等问题。PR 派生扩容集单独标为较低置信来源。

**可复用：**检查安装是否恢复预期 F2P，而不仅是命令成功；共享 recipe 不免除逐题验证。把诊断标签与过滤决定分开，合法 P2P 回归不应因“耦合”被删除。

**边界：**三次稳定不保证跨机器稳定；judge 阈值有 precision/recall 取舍，Python rubric 的多语言校准不全。补接口或重写题面会改变解题信息条件；网络/浏览工具和按标签设计课程是建议，并非本文已验证训练配方。

定位：[论文 v2 §3–4、附录 A.3](https://arxiv.org/html/2602.23866v2)；[本地精读 §3–6、§10](../reading_notes/O11_swe_rebench_v2.md)。

## 6. DeepSWE：消费现有环境时暴露的运行需求

**作者做法：**直接复用约 4.5K R2E-Gym 任务及镜像，并声明排除评测仓库。发布配方使用测试二元结果，训练评分限时与最终评测限时不同。运行经历包括容器数量增大、dockerd 过载、迁移 Kubernetes 和镜像预热；环境 CPU/磁盘池与训练 GPU 是分别建设的资源。

**可复用：**即便采用成熟数据，也要检查真实 scorer、任务可见字段、评分耗时和环境供给。评分超时会改变奖励，不能直接复制 300 秒作为所有来源上限；先用 gold 与合法候选量出分布。

**边界：**没有公开 DeepSWE 专属的完整 gold/no-op、合法替代解和 flakiness 账本；公开加载器支持多个数据源不等于逐一验证过。仓库去重也不证明镜像、Git 历史或网络中无解答。这里主要是消费环境的经验，不是新环境生成流水线。

定位：[发布文 Environment/Scaling](https://www.together.ai/blog/deepswe)、[模型卡 Data/Environment](https://huggingface.co/agentica-org/DeepSWE-Preview)；[本地精读 §3、§6.3](../reading_notes/O02_deepswe_training_recipe.md)。

## 7. Prime SWE tasksets：三个 Verified 产物，三种保留证据

这是一篇专题笔记覆盖的三个独立数据卡与现行接入代码，不能合并为一个认证标准：

- **[R2E-Gym-Subset-Verified](https://huggingface.co/datasets/PrimeIntellect/R2E-Gym-Subset-Verified)：**4,578→4,522。先全量 gold，失败项再做 10 次 fresh sandbox 重试；仅 0/10 的剔除，至少一次通过的 flaky 项仍留。保持原字段和预期状态，不能称作“每题十次稳定通过”。
- **[SWE-rebench-V2-Filtered-Verified](https://huggingface.co/datasets/PrimeIntellect/SWE-rebench-V2-Filtered-Verified)：**32,079→6,272。按上游质量标签、题面引用/外链、语言与镜像可用性筛选；要求出现 gold 正验证记录，再排 flaky、no-edit-pass 等项。另将模型 0/16 用作触发线索，靠 gold 复查确认问题。平台失败、任务质量和来源偏好都改变最终分布。
- **[Scale-SWE-Verified](https://huggingface.co/datasets/PrimeIntellect/Scale-SWE-Verified)：**20,181→17,202，按镜像、gold failure、no-op pass、稳定 infra failure 名单排除。公开过滤脚本采用排除集合的补集，没有据此展示每个保留项的完整正验证账本；这也不能反推作者从未验证保留项。

**代码层可复用与边界：**三条路径分别隐藏部分评分材料、保留来源判分，并记录运行结果；它们仍在 agent 用过的 runtime 评分，不能继承别处 `deep_swe` 的干净容器性质。固定 `verifiers@27bbd216` 的 `--only-setup` 不执行评分，**不是 no-op**。九月的联网变更与七月清洗条件分开；fair-use prompt 不等于网络过滤。直接复用时应保留逐次结果与条件，不能只拿最终 Verified 名单。

定位：三卡 Changes/Generation；[固定 SWE 接入代码](https://github.com/PrimeIntellect-ai/prime-envs/tree/c4d04dfe212c153a587ea4ce072ae6753e74d6e9/environments/swe)；[本地精读 §3–6](../reading_notes/prime_swe_tasksets_validation.md)。数据卡数字按该精读快照；2026-09-15 本轮另回查了 R2E 卡的重试规则。

## 8. OpenAI Verified 审计：参考解能过，仍可能没有公允题目

**作者做法：**对 o3 多次运行仍不能稳定解决的 138 题深入审核，每题至少六名工程师，问题标记再经团队复核。发现测试强制未说明的 helper 名称、PR 同时修多问题而题面只抽出一个等。另用模型做任务专有信息的污染探测，并人工检查展示案例。

**可复用：**比对题面、可见仓库约定、gold 和测试的要求范围；不仅验证参考解，还要问合理的另一种实现是否会误判。公开 PR 真实性本身不能保证孤立任务契约完整。

**边界：**138 题是难例导向样本，59.4% 不能推广为全部 Verified 坏题率。污染与题目错配分别诊断。该文当时建议改用 Pro，后来已撤回，不能单独引用旧建议决定评测集。

定位：[2026-02-23 原文 Background / Too narrow and too wide tests / Contamination](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)；[本地精读 §3–6](../reading_notes/N13a_swe_verified_audit.md)。

## 9. OpenAI Pro 审计：agent 调查与独立人工分支

**作者做法：**731 道公开题先自动筛出 286 道疑点；随后分别走人类监督 investigator 和人工标注两条深入路径。调查 agent 可读仓库、运行测试、检查补丁/轨迹并独立重复；人工每题五人先形成判断，再看辅助材料，分歧升级。分类包括误导题面、未说明要求、过严测试、低覆盖测试。

**可复用：**让 agent 提交可运行反例和具体证据，仓库上下文参与判断；成功样本也查覆盖不足，避免只审失败题。金标和测试可交审查者，但不因此进入 solver 输入。

**边界：**200 与 249 是同一初筛集合两条审查分支的结果，不能相加。未深入审查的 445 题漏检率未知，也没有公布整个可复现审计器。现有证据支持 agent 辅助调查，不能支持自动判题无需人工裁决。

定位：[2026-07-08 原文 Methodology / 两类 review / Failure modes](https://openai.com/index/separating-signal-from-noise-coding-evaluations/)；[本地精读 §3–6](../reading_notes/N13b_coding_eval_signal_noise.md)。

## 10. FrogNano / TaskPilot：先验证任务，再按当前策略校准

**作者做法：**在 SWE-rebench 仓库快照上生成题面、gold 和隐藏 F2P，保留原 P2P；验证修复前后状态，隔离 gold/新增评分测试。再让当前 Leaf solver 多次求解，根据通过率 refine 题面、重新验证或排除，分轮生产任务。固定代码与测试、只改规格信息的案例表明：欠明确可以被修复，过度定位也可能把答案送得太近。轨迹另经 regex 筛疑点、多 LLM 审查作弊行为。

**可复用：**将任务有效性与策略相对难度分开；题面修改保留前后版本并重新验证。可疑行为只做线索，改测试、用 Git、与 gold 不同均不自动等于作弊。

**边界：**校准采样 N、完整任务血缘与隔离实现未公开；不能据 50% 目标认定最优课程。精读发现正文“零有效作弊”与附录明确有效案例冲突，不复述为已证的安全保证；恢复测试也不能撤销已读取的上游答案。

定位：[官方报告 §3、§5.2、附录 F–G](https://microsoft.github.io/debug-gym/static/papers/frognano_technical_report.pdf)；[本地精读 §4、§9](../reading_notes/frognano_technical_report.md)。

## 11. LinkedIn Real-World Code Repair：依赖漂移与环境简化的反例

**作者做法：**针对企业 PR 构建失败，缓存仓库、构建状态、日志和检索方案，每 rollout 单独目录；固定浮动依赖、关闭自动更新，去掉无需修改便可构建的历史问题。为吞吐另保留初始 build 少于 100 秒的训练 case，并把完整多错误/回滚流程简化为固定错误起点的工具交互，训练时关闭完整流程的 LLM 质量 judge。

**可复用：**历史成功不保证现在可重放；依赖、检索、自动更新同样属于环境状态。记录哪些优化改变了起始问题、可见信息、评分条件及任务分布，而不只统计启动加速。

**边界：**简化流程内 RL 提升未相应迁回完整流程，多个条件同时变化，不能归因给某一项。更长训练出现删除验证代码；反复 build 也可能利用噪声。没有公开环境包；旧精读原图核验仍有缺口。

定位：[论文 v1 §3–4、§6.1](https://arxiv.org/html/2510.22075v1)；[本地精读 §3–4、§7](../reading_notes/agentic_rl_real_world_code_repair_2510.22075.md)。

## 12. SWE-rebench 运维文：可执行数据与独立评分生命周期

**作者做法：**采集、处理、执行验证后发布镜像；agent 在工作容器交付补丁，再建测试容器评分。规模化运行管理 Pod 归属、状态超时、清理、整题重试、资源与监控；以 tmpfs、构建存储策略、制品镜像和批量后端处理大量任务。

**可复用：**区分任务镜像、runner 镜像和候选工件；环境服务不仅负责“启动成功”，还要留下可解释的结束、错误与评分产物。纯评分吞吐和含求解全流程成本分别计量。

**边界：**文章的四核/16GB 示例和 500 补丁约 18 分钟都依赖具体集群，不能变为通用规格。后来代码存在“目录已在就跳过”等条件性恢复风险；新容器、rootless 或平台重试都不是完整可信性证明。现行代码不等同于 2025 性能实验版本。

定位：[2025-11-07 原文 Mining / Kubernetes / Evaluation / Sharing](https://nebius.com/blog/posts/infrastructure-behind-swe-rebench)；[本地精读 §2–4](../reading_notes/O28a_swe_rebench_infrastructure.md)。

## 13. SWE-rebench 原演讲：网络、时间和重复可靠性

**讲者实践：**逐月更新真实任务，以简单 harness 控制比较条件；人工检查题面、环境和测试，举出严格字符串、外部依赖、时间异常。清理未来 Git 历史，并分析轨迹中的网页/curl 答案获取；区分无效模型运行、重新求解与评分重试。五次重复同时看平均成功、至少一次成功和全部成功。

**可复用：**网络依赖、时钟和未来代码都要落实到具体阶段/可见资产；重试不能只保留最好结果。求解重复可靠性与 gold 环境稳定性是不同实验；通过测试也不保证提交没有残留文件等质量问题。

**边界：**这是运维经验与案例，未给总体故障率、统一网络规则或完整重试协议。时间切分不自动排除污染；本地已有的是官方转录全文精读，视频和原幻灯片未核，不能把听写近似值当精确实验数据。

定位：[官方转录 04:12–07:58、09:09–14:14](https://ai.engineer/talks/swe-rebench-lessons-from-evaluating-coding-agents-on-real-software-engineering-tasks-ibragim-bad)、[官方方法页](https://swe-rebench.com/about)；[本地精读 §2–4](../reading_notes/O28b_swe_rebench_evaluation_lessons.md)。
