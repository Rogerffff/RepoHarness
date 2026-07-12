# 05 — FA 独立工作流执行计划：version-aware fully async 训练链

日期：2026-07-12。状态：**已定案，待开工**（设计依据与本计划的分工见下"输入"）。

输入：P3 收口结论（`preflight/preflight_report.md`：wait_time_ratio=0.82、尾闲 26~28% > 25% 阈值）、FA 设计讨论稿（`fully_async_rollout_pipeline_design_discussion.md`，codex，2026-07-12——**机制分析与对象模型的权威出处，本计划不复述其论证**）、fully_async 升级设计（`preflight/slime_fully_async_upgrade_design.md`：四缺口 + slime 机制知识）、原 S2-0b 硬化规格（问题 A~E，自 `04-s2-execution-plan.md` 迁入并废止原节）、算法分析（`../training_design/repoharness_sao_dis_grpo_ppo_analysis.md`：GRPO 保持首训、faithful DIS 为正确性组件）、orchestrator 审查（2026-07-12：proxy 边界、eval 路径、契约测试先行、reward 广播语义核实）。

退出闸门：**`rh2_fully_async_training_path_verified = true`**。与 S2 的关系：**独立工作流、独立 acceptance、并行推进**；`rh2_formal_training_allowed` 需要 FA ∧ S2 两个闸门同时为真，任何一方不是另一方的子任务。唯一的物理耦合点是 FA-5 与 S2 G10 **合并为同一次短租**。

---

## 0. 已定案决策（用户拍板记录，实现不得偏离；改判需回写本节）

| # | 决策 | 定案 |
| --- | --- | --- |
| D-FA-1 | 正式训练链形态 | **version-aware fully async + faithful DIS**（用户 2026-07-12）。session-pinned policy、bounded async/update barrier、TIS/IcePop 近似均不是候选主案；IcePop-style 只作小规模实现对照。bring-up 与正式预算走同一代码路径，只缩模型/任务数/并发/步数 |
| D-FA-2 | 成员补采 | **首版不做**。缺员组过期/拒绝，worker 持续创建新 PromptGroup；可信残组轨迹保留为审计/离线资产（`group_not_admitted` 标注，不自动进 SFT 池） |
| D-FA-3 | **权重更新 abort 的处置 = proxy 级 turn 重生成**（用户 2026-07-12 采纳 orchestrator 方案） | 模型调用重试语义的唯一执行点是 **model proxy 边界**（黑盒 harness 下我们唯一可控的点）。区分两类中断：(a) **我方权重更新引发的 abort**——允许该 turn 在 `continue_generation` 后重生成：半截输出可证从未交付 agent（逐 token 捕获），记为 non-delivered、不进任何 mask/loss；重试轮 provenance 干净落在新 weight_version 上，faithful DIS 覆盖跨版本；execution **不终止**。(b) **不可归因的连接损坏**——终止当前 attempt，组缺员（讨论稿 §4 重试表原规则）。理由：CC 对 API 错误有原生自动重试，"终止"反而需要 proxy 主动杀会话；且一律终止会带来每步杀伤在途 execution 的浪费与长度偏置回归 |
| D-FA-4 | eval 路径首版 | **训中不评，只做 before/after**（用户 2026-07-12）。stock fully_async 的 eval 模式 raise；before/after 评测走标准（非 FA）路径，在训练开始前/结束后执行，与 FA worker 生命周期不重叠 |
| D-FA-5 | 首训算法 | GRPO n=8 保持；faithful DIS 是**正确性组件**而非可选增量；正式链不提供无 DIS/静态 policy version 旁路。PPO/SAO/CompactionRL 是后续算法工作流（算法分析文档 §10），不进本计划 |
| D-FA-6 | compaction | 首训强制关闭且必须成为**运行时硬事实**：`SLIME_AGENT_CC_EXTRA_ENVS='{"DISABLE_COMPACT":"1"}'` + inspector 验证子进程真实收到；发现明确 compaction 或无法解释的上下文收缩 → 该轨迹退出 GRPO 基线。P3 脚本未设此变量，不能引用 P3 作为"已关闭"证据 |
| D-FA-7 | fan-out reward 语义（权威口径修正） | 我方 adapter 实际行为 = **整 reward 广播给每个 branch**（`generate.py:1727`）+ rollout 级 loss 分母——与问题 E 不变量一致，作为权威契约固化。slime README 的 "reward/K 分摊" 与源码不符（`TrajectoryManager.get_trajectory` 写整 reward）；本项目旧文档中的 "reward/K" 表述一律废止 |

## 1. 任务分解

| # | 任务 | 位置 | 依赖 |
| --- | --- | --- | --- |
| FA-0 | 身份/版本/执行结果契约 + fully_async 表面契约测试 | 本机 | — |
| FA-1 | 持续 RolloutExecution worker + 有界队列 + proxy 边界语义 | 本机 | FA-0 |
| FA-2 | PromptGroupAssembler + QualifiedPromptGroupQueue | 本机 | FA-0/1 |
| FA-3 | SlimeBatchAssembler + build_dp_schedule 差分预检（原 S2-0b 迁入） | 本机（离线部分可先行） | FA-0（离线部分）；FA-2（接线） |
| FA-4 | faithful DIS + 真实版本管道 + staleness 准入 | 本机（对拍可先行） | FA-0 |
| FA-5 | 本地故障注入 + 短租 GPU 集成验收（与 S2 G10 合并） | 本机 + 一次短租 | FA-1~4 |

### FA-0 身份、版本与执行结果契约（先行，兼益同步路径）

1. **三层身份固化为契约字段**（不是约定俗成）：PromptGroup（`group_index`/`parent_rollout_id`，GRPO 归一化单位）/ RolloutExecution（`rollout_execution_id`，`build_dp_schedule` 计数单位）/ Branch（`branch_id`，共享 rollout_id，loss 按 rollout 聚合）。P3 反例（group_index=5 一次执行 8 branch）作为 schema 文档内的固定示例。
2. **`RolloutAttemptOutcome`**（升级或替换 `RolloutFailureRecord`，`generate.py:958-964`）：字段按讨论稿 §5.1（completion_class：present_trainable / missing_after_local_retry / permanent_rejection；task_outcome；failure_category/failed_component；recovery_scope；behavior_policy_version；evidence_refs）。可信 `reward=0` 负样本 = `present_trainable + unresolved`，**绝不是缺员**。
3. **真实 weight_version 管道**：每次模型调用把 SGLang `meta_info.weight_version` 写入 turn tape、Sample、TrajectoryProjection、BackendHandshake；静态 `policy_version="step_0"`（`generate.py:930`）与 `staleness_steps=0`（`:1601`）只允许测试路径，正式链启动断言禁止。
4. **provenance loss mask 与 algorithmic mask 分离**：DIS/staleness 的 step-local `dis_mask`/`importance_weight` 不得改写 `LossMaskSpan`（算法分析文档 §6.3 的两对象定义照抄进契约注释）。
5. **D-FA-6 落地**：`DISABLE_COMPACT=1` 注入 + inspector 探针（验证 CC 子进程环境）+ "检测到 compaction/上下文收缩 → 轨迹退出基线"的 gate 维度。
6. **D-FA-7 落地**：reward 广播 + rollout 分母写进 RewardFacts/契约注释；全仓 "reward/K" 表述清理（本计划落地时已完成文档面清理，代码契约随本任务）。
7. **fully_async 表面契约测试**（F6 纪律扩展，orchestrator 审查补充）：对我们依赖的 slime 面钉契约测试——worker 生命周期/done_cb 行为/output_queue 语义/`add_samples` 组长度断言/`pause_generation`+`continue_generation` 端点行为。上游已领先 8+ commit，升级前先跑契约测试。

**验收**：契约测试全绿；假 `step_0` 进正式链被启动断言拒绝的负测试；DISABLE_COMPACT inspector 探针在本地 harness 冒烟中验真；三层身份在一条真实 P3 元数据夹具轨迹上可完整往返。

### FA-1 持续 worker、有界队列与 proxy 边界

1. 基于 slime fully_async 骨架实现 **RH2 自己的 rollout-function-path**（不给 slime dynamic_filter/`_key`/data buffer 各处打零散补丁）；执行资源按全局并发池调度，不为每组独占 worker。
2. 修复 stock 三缺陷：task 异常静默泄漏（`fully_async_rollout.py:173-175`——异常样本必须进失败账目或 pending/quarantine）；阻塞式 output queue 反压（有界 + 计数 + backpressure，不得在 put 阻塞中停摆 reap/top-up）；**不依赖 stock ABORTED 整组回队**（`add_samples` 断言 `len==n_samples_per_prompt`，对 fan-out 形状也会炸——我们的 abort 处置在 proxy 层，见下条）。
3. **proxy 边界语义（D-FA-3 的实现主体）**：
   ```text
   权重更新窗口（我方触发，时间窗已知）内被 abort 的模型调用：
     proxy 返回可重试错误（或 hold 至 continue_generation）
     → CC 原生重试 → 新 turn 在新 weight_version 上生成
     → 半截输出由 capture 记为 non-delivered artifact（mask 无关物，
       不进 loss、不进 tape 行数核算、留审计）
     → execution 继续，不终止、不记缺员
   不可归因中断（非更新窗口内、或无法证明非交付）：
     终止 attempt → RolloutAttemptOutcome(missing_after_local_retry)
     → 组缺员，worker 继续新组
   ```
   proxy 必须能区分两类中断：与 TrainingRuntimeCoordinator 共享"更新窗口开始/结束"事件即可判定。
4. 交付边界 fan-out aware（三视图，讨论稿 §6.1/原 S2-0b 问题 C）：内部权威三层结构；rollout/filter 视图保留 PromptGroup 外层 + 身份 sidecar；train converter 视图平铺 + 无损回链。
5. 局部幂等重试按讨论稿 §4 白名单表（max_attempts=3、指数退避 full jitter、评分阶段只允许一次完整重试）；重试记录进 `RolloutAudit` 时间线，不新增公共 schema。

**验收**：故障注入单测覆盖——task 异常不泄漏、queue 满反压不停摆、更新窗口 abort → turn 重生成且 non-delivered 留痕、不可归因中断 → 正确缺员；fan-out 形状对 dynamic_filter 与 `_key` 的直接单测（slime 真函数 + 我方交付形状，不打补丁）；**旧 token 悬挂负测试**（升级设计缺口①的最坏组合"带旧 token 但 agent 重开沙箱"——我方从不回队 ABORTED 样本，断言任何进入组装器的 execution 不携带上一 attempt 的残留 tokens）。

### FA-2 PromptGroupAssembler 与合格组队列

1. 每条执行完成评分/投影/Gate 后才提交 `RolloutAttemptOutcome` 给 assembler；`PromptGroupState` 为进程内轻量状态机（定期 checkpoint，不注册公共 schema）；组终结时唯一落盘 `PromptGroupAdmissionReport`（admitted/rejected/quarantined + 讨论稿 §5.3 字段）。
2. 状态机照讨论稿 §9（NEW→RUNNING→PRESENT/LOCAL_RETRY/MISSING/PERMANENT_REJECTED；组 OPEN→READY/EXPIRED/QUARANTINED；READY→BatchAdmission）。`WAITING_FOR_BATCH_ALIGNMENT` 不倒写 eligibility、不重跑 harness。
3. 只有固定 n 完整、eligibility 合格、policy span 达标的组进 `QualifiedPromptGroupQueue`（保存 raw group facts + token 长度 + 身份；不固化任何 step-local 算法张量）；组进队后**消费时重算 staleness**。
4. 过采样供给：`initial_groups = B + reserve_groups`（预注册值见 §5）；残组不占 GPU、到 deadline/TTL 过期。
5. 组终结六条件照讨论稿 §6.4；executed 级安全事件整组拒绝（不能"重采到不作弊为止"）；熔断（同故障短窗超阈值 → task_quarantine / run_halt）。
6. **长度偏置监测**（讨论稿 §4）：每个被放弃 attempt 留 `elapsed_seconds_before_failure / captured_turn_count / captured_token_count / failure_phase`；失败率随长度显著上升 → 修 runtime，不许靠重采掩盖。

**验收**：状态机属性测试（非法迁移不可达）；讨论稿 §11 场景 1/4/5/6/7/9/10/13 的本地夹具复现。

### FA-3 SlimeBatchAssembler 与 batch 准入（原 S2-0b 迁入；**离线部分可先行开发**）

原 S2-0b 的问题 A~E 定义、五条归一化不变量、`BatchAdmissionReport` 归属（批次级报告 + `BackendHandshake.backend_rejection_reason` 引用，**不碰 eligibility**；枚举扩 `insufficient_rollout_count / microbatch_alignment_failed / prompt_group_incomplete / capacity_backpressure`）全部继承，此处不重复（历史文本见 04 计划 git 历史与 `s2/codex_reviews.md` 轮次 2）。FA 架构下的增量语义：

1. 输入只来自 ready queue 的完整组；事务式 peek→预检→consume（失败候选不得误标 consumed）。
2. **按唯一 `rollout_execution_id` 计数** global batch；branch 不计数。GRPO 归一化按 `group_index` 键控（原型：`reference/slime/slime/rollout/_fanout_test_helpers.py::grpo_normalize_by_group_index`），advantage 广播给 branches，rollout 级分母。
3. 修复动作只有：**换组（按 token 长度分桶 + 有界搜索）→ 等待更多 ready 组 → 预注册 fallback**（首版 fallback 只登记不启用，见 §5）。禁止：拆组、复制成员、branch 充数、改 eligibility、重跑 harness、人工碰运气改 gbs。
4. **差分验证**：同一输入喂我方预检器与 slime 真 `build_dp_schedule`（纯 Python import），成功/失败类别、step 数、microbatch 数三项一致。

**离线验收（继承原 S2-0b 六项，不需要 GPU，可在 FA-1/2 之前完成）**：J4 事件元数据夹具复现 A 类（44→31→19<32）与 B 类（23 mbs≠24）；差分验证；D 不变量属性测试；E 五不变量属性测试 + group5×8branch 定向回归；展平 round-trip + dynamic_filter/`_key` 直接单测；强验证挂 FA-5 短租。

### FA-4 faithful DIS 与 off-policy 正确性（**对拍部分可先行开发**）

1. faithful DIS 自定义 loss（`--custom-loss-function-path`）：实现论文语义 `f(current/rollout ratio) × advantage × log π_current`，区间内 ratio 加权、区间外置零；**denominator 语义预注册**（被拒 token 是否留在分母——slime stock TIS 的"留分母、零梯度"语义与"仅按接受 token 归一化"不同，必须显式选择并写死）。
2. **逐 token 手算对拍**：固定小张量（token/logprob/version/advantage）+ 手算结果逐位比对 ratio、裁剪、拒绝原因、最终 advantage/loss；先合成张量，后接真实 rollout dump。
3. IcePop-style 近似（`--use-tis` + custom TIS hard mask）只作实现对照档，结果**不得标注为 GRPO+DIS**。
4. 准入链：单 rollout 与 PromptGroup 的 policy-version span、最大 staleness、DIS 有效 token 比例三重上限（§5 预注册值）；超限不进 ready queue / TrainBatch；消费时重算。
5. **current policy version 取数机制**（升级设计缺口④：buffer_filter 调用时 `rollout_id=None` 且拿不到 engine 句柄，current version 无现成管道）：采用其推荐方案 (i)——worker top-up / TrainingRuntimeCoordinator 缓存 `engine.get_weight_version`（~20 行碰 worker），consumer 侧重算 staleness 用该值；方案 (ii)（buffer 内最大版本近似）只作降级对照。`buffer_filter` 可作 slime 侧第二道防线，但不是版本与拒绝事实的唯一权威。
6. **`--release-train`（上游 c7487788）默认禁用**：每步 update_weights 会急剧扩大跨版本盲区——只有真实 weight version 管道 + faithful DIS 对拍 + staleness 验收（本任务 + FA-5）全部通过后才允许评估启用；TIS 近似不能作为其正确性兜底。
7. 记录指标：staleness 分布、**跨版本 token 比例**（升级设计缺口②的前置验证项）、DIS reject ratio（按轨迹长度分桶——监测长度相关拒绝偏差）、有效 token 数、全零梯度 rollout/microbatch 计数、M1 多步版本跨度分布（P3 递延项）。

**验收**：对拍逐位通过；跨版本双 turn 合成轨迹（场景 18）端到端正确；无 DIS 旁路的负测试（正式链配置下禁用 DIS 必须启动失败）。

### FA-5 本地故障注入收口 + 短租 GPU 集成验收

本地全量覆盖 §3 场景后，**与 S2 G10 合并为同一次短租**（一次租卡、两份验收账目、两个闸门独立记账）。FA 侧短租清单：

```text
1. 讨论稿 §10.6 六项（worker 跨 step 保温 / ready queue 无重复消费 /
   trainer 不等指定慢组 / 两次 optimizer step 后版本-staleness-DIS 账目
   可解释 / 无泄漏无死循环无全零 step / fan-out 语义正确）。
2. strict J4 等价复验：FA-3 准入 + fan-out + 真实 optimizer step
   （= 协议 J4 判据第 0 项最终落地；preflight_report §6 对应项改判）。
3. 【abort 行为实证——P3 gap ① 的收窄版，D-FA-3 的经验基础】
   实测 pause_generation 对在途请求是 abort 还是 hold（J4c 0.6B 未能区分）；
   实测 CC 原生重试在 abort 下的行为（重试次数/退避/放弃条件）；
   据此校准 proxy 更新窗口逻辑。若实测与 D-FA-3 假设相悖
   （如 pause 实为 hold、无 abort 发生），按实测简化 proxy 分支并回写本节。
4. M1 staleness 多步分布采集（P3 单步跨度=0，多步分布一直缺数）。
5. before/after eval 路径冒烟（D-FA-4：标准路径，FA worker 停止后执行）。
6. 【升级设计 §5"必须实验验证"补齐】current policy version 传播延迟、
   engine.get_weight_version 调用开销、跨版本 token 比例实测、
   N1 泄漏实际发生率（应为 0，兜底代码在位的前提下验证计数器）。
7. 【N6 worker 崩溃恢复】注入 worker 线程死亡 → 验证线程重建 + in-flight
   丢失被 prompt 覆盖率对账捕获（长训练必备审计：每个 prompt 的
   dispatched/finalized/consumed 计数对账，缺口即告警）。
```

**验收**：短租清单全绿 → `rh2_fully_async_training_path_verified = true`；黄灯条款——场景 3 实测推翻假设但 proxy 简化后其余全绿，闸门仍可翻，偏离记 implementation-notes。

## 2. 执行顺序、并行性与工作量

```text
FA-0（2~3 人日，先行——契约面同时解锁 S2 协调）
  ├─ FA-3 离线部分（3~4 人日：预检器/差分/归一化/夹具——纯 Python，可立即开工）
  ├─ FA-4 对拍部分（2~3 人日：DIS loss + 合成张量对拍——trainer 侧，无运行时依赖）
  ↓
FA-1（3~5 人日）→ FA-2（2~3 人日）→ FA-3/FA-4 接线（各 1~2 人日）
  ↓
FA-5 本地（2~3 人日）→ 短租（数小时，与 S2 G10 合并）
合计 ≈ 16~24 人日本地 + 1 次短租。
约六成工作（FA-0 契约、FA-3 归一化/准入、真实版本管道）与路线无关
（同步路线也必须做）；纯 fully-async 增量约四成。
吞吐回收上限 = 实测尾闲 26~28%；主要回报在正式长预算训练 + DIS 正确性。
S2（安全/数据 ingestion）与本工作流并行，互不阻塞；S2-1 可由并行线程执行。
```

## 3. 验收场景

讨论稿 §11 的 18 条全部继承（1~18，此处不重复），新增三条：

```text
19. 权重更新窗口内 abort 一个在途 turn
    -> proxy 允许 CC 重试；turn 在新 weight_version 重生成；半截输出
       记 non-delivered、不进 mask/tape 核算；execution 继续不缺员；
       DIS 覆盖该 execution 的跨版本 turn。
20. 非更新窗口的连接损坏（不可归因）
    -> 终止 attempt，组缺员，不透明重试被拒绝（负测试：proxy 不得
       对该类中断返回可重试语义）。
21. eval 请求进入 FA 路径
    -> 显式拒绝（fail-fast），错误信息指向 before/after 标准路径；
       before/after 评测在 worker 停止后可正常执行。
```

## 4. 闸门与账本

```text
rh2_fully_async_training_path_verified = false   （本计划退出闸门）
rh2_formal_training_allowed 依赖 = FA 闸门 ∧ rh2_s2_signal_trusted
账本：fa/fa_acceptance_summary.json + inspect-rh2-fa（照抄 S1 四步范式：
  digest 锁 evidence+代码、字段白名单、结构化对照、场景清单命中）。
evidence 目录：docs/agentic_RL/repo_harness_rh2_workstreams/fa/
（implementation-notes 三节制 + 各任务报告 + 短租证据 + acceptance）。
协作纪律沿用：每任务一 commit、inspect-rh2-s1 照跑（S1 面不回归）、
独立复核、检查点在 FA-5 短租前。
```

## 5. 预注册参数（初始值；FA-5 校准后定案，改动必须回写）

| 参数 | 初始值 | 备注 |
| --- | --- | --- |
| reserve_groups | 目标完整组数的 10%~20%，按 `qualified_group_rate` 自调 | 另受沙箱并发与 host RAM 上限约束 |
| 最大 policy lag | 1 个 optimizer step | 不继承 S1 默认 4 |
| PromptGroup 版本跨度上限 | 1 | 组内成员版本差 ≤1；DIS 修 token 梯度，不修 reward baseline 的跨版本可交换性 |
| DIS 有效 token 比例下限 | 90%（观察值） | 低于即拒组；FA-5 校准 |
| DIS ratio 信任区间 | 论文默认，对拍时定死 | denominator 语义随 FA-4 预注册 |
| 组 deadline | 任务 time budget + 评分预算，×1.5 p95 安全系数 | 动态推导 |
| ready queue TTL | 按版本数计（staleness 上限），不按秒 | 消费时重算 |
| batch fallback | 首版禁用（只换组 + 等待） | 启用需与 lr/梯度累积/optimizer-step 语义一起定案 |
| `--release-train` | **禁用** | FA-4 第 6 条门槛通过后才允许评估 |
| 局部重试 | max_attempts=3，base 0.5s，max 8s，full jitter；评分阶段整段重试 ≤1 次 | 讨论稿 §4 |

## 6. 风险与未知

```text
1. pause_generation 的 abort/hold 语义未实证（FA-5 场景 3 关闭；D-FA-3 的
   proxy 分支设计已按两种结果都可收敛的方式编写）。
2. CC 原生重试的细节（次数/退避/放弃阈值）是黑盒观测值，proxy 必须按
   "CC 可能放弃"设计兜底（放弃 = 不可归因中断，走缺员分支）。
3. 上游 slime 移动（pin e848052a 落后 8+ commit）：FA-0 契约测试先行；
   若需 cherry-pick（如 680824dd start_len），走独立 commit + 契约回归。
4. faithful DIS 数值风险：对拍是硬门，denominator 语义错误会静默改变
   有效学习率——预注册 + 手算逐位。
5. 持续 worker 的 host 资源：评分容器池与 worker 并发共享 CPU/RAM，
   FA-1 有界队列 + 评分并发上限沿用 S1 P11 反压；长训练的
   RolloutAttemptOutcome/audit 落盘量需容量估算（FA-2 checkpoint 轻量化）。
6. 残组浪费率未知：qualified_group_rate 实测后才知道 reserve_groups 是否
   够用；若 group_not_admitted 浪费显著且残组稳定为 n-1 可信成员，
   另立工作流评估成员补采（明确不在 FA-0~5 内）。
7. 【递延登记：token 级真续跑】首版对更新窗口 abort 用 proxy turn 重生成
   （D-FA-3），不做 token 级续跑。若 FA-5/首训实测发现长轨迹被非更新窗口
   中断终止的比例显著（长度偏置监测报警），升级路径已有设计存档：
   custom_generate 入口 resume 分支（判 ABORTED ∧ tokens ∧
   start_rollout_id，30-80 行 + agent 沙箱中间态序列化）+ done_cb 补
   start_rollout_id（~5 行碰 core）+ cherry-pick 上游 680824dd
   （routed_experts_start_len，tape 中段拼接基建）——见升级设计文档
   缺口①"正式接线"段。S2-0 的 start_len 留位是它的契约前置。
8. 【递延登记：worker poll 粒度】stock worker 1s poll 对 SWE 分钟级任务
   可忽略（升级设计 N3 已定性）；只有未来混入秒级短任务才需要降到
   50-100ms 或事件驱动——记录在此防止重复调查，FA-1 不做。
```

## 7. 关联文档回填清单（FA 推进过程中完成，不阻塞开工）

```text
[ ] 实验设计文档：§9.1 compaction 运行时硬事实措辞（D-FA-6）；
    附录 A "reward/K 分摊" 勘误（D-FA-7）——随 FA-0 落地一并回填
[ ] 实验设计文档：GRPO+DIS 对照矩阵（算法分析文档 §9.3 的 A/B 两行进
    首轮矩阵；C/D/E 留算法工作流）——随 FA-4 完成回填
[ ] preflight_report §6：batch admission 回填项在 FA-5 短租后改判
[ ] 升级设计文档：FA-5 abort 实证结论回填缺口①（终止其"empirical test
    deferred"状态）
[ ] AGENTS.md / 00-project-status.md：FA 阶段状态随各任务 commit 同步
```
