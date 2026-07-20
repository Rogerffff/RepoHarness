# 05 — FA 独立工作流执行计划：version-aware fully async 训练链

日期：2026-07-12（状态更新 2026-07-20）。状态：**执行中**——FA-0 完成；FA-1 本机实现完成（含 codex 轮次 6~14 九轮审查修复，closure 批次落地）；FA-3 离线/FA-4 对拍完成（接线未做）；FA-2 下一步（先 2A 身份与持久性基座，见 FA-2 节分批重排）；闸门 `rh2_fully_async_training_path_verified` 仍 false。

输入：P3 收口结论（`preflight/preflight_report.md`：wait_time_ratio=0.82、尾闲 26~28% > 25% 阈值）、FA 设计讨论稿（`fully_async_rollout_pipeline_design_discussion.md`，codex，2026-07-12——**机制分析与对象模型的权威出处，本计划不复述其论证**）、fully_async 升级设计（`preflight/slime_fully_async_upgrade_design.md`：四缺口 + slime 机制知识）、原 S2-0b 硬化规格（问题 A~E，自 `04-s2-execution-plan.md` 迁入并废止原节）、算法分析（`../training_design/repoharness_sao_dis_grpo_ppo_analysis.md`：GRPO 保持首训、faithful DIS 为正确性组件）、orchestrator 审查（2026-07-12：proxy 边界、eval 路径、契约测试先行、reward 广播语义核实）。

退出闸门：**`rh2_fully_async_training_path_verified = true`**。与 S2 的关系：**独立工作流、独立 acceptance、并行推进**；`rh2_formal_training_allowed` 需要 FA ∧ S2 两个闸门同时为真，任何一方不是另一方的子任务。唯一的物理耦合点是 FA-5 与 S2 G10 **合并为同一次短租**。

---

## 0. 已定案决策（用户拍板记录，实现不得偏离；改判需回写本节）

| # | 决策 | 定案 |
| --- | --- | --- |
| D-FA-1 | 正式训练链形态 | **version-aware fully async + faithful DIS**（用户 2026-07-12）。session-pinned policy、bounded async/update barrier、TIS/IcePop 近似均不是候选主案；IcePop-style 只作小规模实现对照。bring-up 与正式预算走同一代码路径，只缩模型/任务数/并发/步数 |
| D-FA-2 | 成员补采 | **首版不做**。缺员组过期/拒绝，worker 持续创建新 PromptGroup；可信残组轨迹保留为审计/离线资产（`group_not_admitted` 标注，不自动进 SFT 池） |
| D-FA-3 | **权重更新 abort 的处置 = proxy 级 turn 重生成**（用户 2026-07-12 采纳；2026-07-12 codex 审查修正为 **proxy 内部重生成**，不依赖 CC 自身重试） | 模型调用重试语义的唯一执行点是 **model proxy 边界**。**在同一个 CC HTTP 请求内部完成**：attempt_1 被更新窗口 abort → proxy 丢弃未交付 attempt（记 non-delivered artifact）→ 等引擎恢复 ACTIVE 且版本前进 → proxy 内部发起 attempt_2 → **只把最终成功响应交付 CC**。non-delivered 保证的物理依据 = adapter 完整缓冲语义（`common.py:346` 先 await 全量 `/generate` 结果、`anthropic.py::_render_stream` 才从完成 blocks 渲染 SSE）——CC 全程无感知，不消耗 turn cap（turn 计数在生成前递增），不依赖黑盒 SDK 的重试行为（CC 原生重试只是最后兜底的现实背景，不是机制）。**守卫条件**（三者同时成立才允许内部重生成）：失败与已知更新窗口重叠 ∧ 响应未交付 ∧ 恢复后版本符合预期；否则按**不可归因故障**终止 attempt、组缺员。abort 识别必须覆盖 SGLang 以正常 JSON 返回 `finish_reason=abort` 的情形，不只是网络异常 |
| D-FA-4 | eval 路径首版 | **训中不评，只做 before/after**（用户 2026-07-12）。stock fully_async 的 eval 模式 raise；before/after 评测走标准（非 FA）路径，在训练开始前/结束后执行，与 FA worker 生命周期不重叠。**训后补充（codex #10）**：除 final checkpoint 外，对训练期间保留的周期 checkpoint **依次评测**（判断中途能力峰值与后期退化；eval 只需模型权重 ~60GB/份，不必保优化器状态，存储按此规划） |
| D-FA-5 | 首训算法 | GRPO n=8 保持；faithful DIS 是**正确性组件**而非可选增量；正式链不提供无 DIS/静态 policy version 旁路。PPO/SAO/CompactionRL 是后续算法工作流（算法分析文档 §10），不进本计划 |
| D-FA-6 | compaction | 首训强制关闭且必须成为**运行时硬事实**：`SLIME_AGENT_CC_EXTRA_ENVS='{"DISABLE_COMPACT":"1"}'` + inspector 验证子进程真实收到；发现明确 compaction 或无法解释的上下文收缩 → 该轨迹退出 GRPO 基线。P3 脚本未设此变量，不能引用 P3 作为"已关闭"证据。**警示（codex #11，CC 压缩文档证实）**：`DISABLE_COMPACT` 只覆盖 auto/manual compact；CC 另有 Microcompact / Context Collapse 等机会主义压缩层走独立路径（`reference/claude-code-docs/claude-doc/16-autocompact-detail.md`）——**"上下文收缩即拒绝"的兜底是硬要求，不能只凭环境变量宣布 compaction 已关闭** |
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
2. **`RolloutAttemptOutcome`**（升级或替换 `RolloutFailureRecord`，`generate.py:958-964`）：字段按讨论稿 §5.1，**含两处 codex 审查修正**——(a) completion_class 用 `present`（不叫 present_trainable：Outcome 只记录在场事实 + `eligibility_report_id` 引用，**在线训练资格仍只由 EligibilityReport 决定**，不复制权威结论）；(b) `behavior_policy_version` **不是单值**——一次 execution 可跨多个版本，保存逐 turn 版本引用/序列，并派生 `intra_execution_version_span` / `current_version_at_finalize` / `current_version_at_consume` / `worst_token_lag`。可信 `reward=0` 负样本 = `present + unresolved`，**绝不是缺员**。
3. **真实 weight_version 管道**：每次模型调用把 SGLang `meta_info.weight_version` 写入 turn tape、Sample、TrajectoryProjection、BackendHandshake；静态 `policy_version="step_0"`（`generate.py:930`）与 `staleness_steps=0`（`:1601`）只允许测试路径，正式链启动断言禁止。**schema 升级**：`BackendHandshake.policy_version` 当前是单值（`handshake.py:96`），多版本事实以 `weight_versions_seen` 序列为权威 + 上条派生字段，单值字段语义收窄为"finalize 时刻的 current version"并改名或注释写死，不得把多版本事实压回单值。
3b. **TrainingRuntimeCoordinator 跨进程协议**（codex #2：权重更新、RolloutManager、proxy、trainer 在不同 Ray actor/线程，不能依赖普通内存事件）：显式协议字段——`update_epoch`、`phase ∈ {ACTIVE, PAUSING, UPDATING, RESUMING}`、`old_version / target_version / active_version`、`window_started_at / window_completed_at`、`fencing_token`。proxy 判定"更新窗口 abort"只信该协议（D-FA-3 守卫条件的数据来源）；fencing_token 防陈旧窗口误判。
3c. **proxy 调用账目字段**：`logical_turn_id` / `model_call_attempt_id` / `delivery_status`（delivered / non_delivered_aborted / non_delivered_failed）——D-FA-3 的 attempt 语义与 non-delivered 留痕靠它记账，capture 记录逐 attempt 关联。
4. **provenance loss mask 与 algorithmic mask 分离**：DIS/staleness 的 step-local `dis_mask`/`importance_weight` 不得改写 `LossMaskSpan`（算法分析文档 §6.3 的两对象定义照抄进契约注释）。
5. **D-FA-6 落地**：`DISABLE_COMPACT=1` 注入 + inspector 探针（验证 CC 子进程环境）+ "检测到 compaction/上下文收缩 → 轨迹退出基线"的 gate 维度。
6. **D-FA-7 落地**：reward 广播 + rollout 分母写进 RewardFacts/契约注释；全仓 "reward/K" 表述清理（本计划落地时已完成文档面清理，代码契约随本任务）。
7. **fully_async 表面契约测试**（F6 纪律扩展，orchestrator 审查补充）：对我们依赖的 slime 面钉契约测试——worker 生命周期/done_cb 行为/output_queue 语义/`add_samples` 组长度断言/`pause_generation`+`continue_generation` 端点行为。上游已领先 8+ commit，升级前先跑契约测试。
8. **`RoutingTensorRef.routed_experts_start_len` 扩展位**（2026-07-12 自 S2-0 迁入，用户确认）：字段默认 0 + 校验器兼容中段拼接语义的注释（上游 680824dd 已改 tape 契约）。它是 §6 第 7 条真续跑递延路径的契约前置，随本任务的 tape 契约批次一并落。

**验收**：契约测试全绿；假 `step_0` 进正式链被启动断言拒绝的负测试；DISABLE_COMPACT inspector 探针在本地 harness 冒烟中验真；三层身份在一条真实 P3 元数据夹具轨迹上可完整往返。

### FA-1 持续 worker、有界队列与 proxy 边界

1. 基于 slime fully_async 骨架实现 **RH2 自己的 rollout-function-path**（不给 slime dynamic_filter/`_key`/data buffer 各处打零散补丁）；执行资源按全局并发池调度，不为每组独占 worker。
2. 修复 stock 三缺陷：task 异常静默泄漏（`fully_async_rollout.py:173-175`——异常样本必须进失败账目或 pending/quarantine）；阻塞式 output queue 反压（有界 + 计数 + backpressure，不得在 put 阻塞中停摆 reap/top-up）；**不依赖 stock ABORTED 整组回队**（`add_samples` 断言 `len==n_samples_per_prompt`，对 fan-out 形状也会炸——我们的 abort 处置在 proxy 层，见下条）。
3. **proxy 边界语义（D-FA-3 的实现主体，proxy 内部重生成）**：
   ```text
   同一个 CC HTTP 请求内：
     proxy 发起 model_call_attempt_1
     → 识别更新窗口 abort（判据含 SGLang 正常 JSON 的
       finish_reason=abort，不只网络异常；窗口事实来自
       TrainingRuntimeCoordinator 协议，FA-0 3b）
     → 丢弃未交付 attempt：capture 记 non-delivered artifact
       （mask 无关物，不进 loss、不进 tape 行数核算，留审计；
       delivery_status=non_delivered_aborted）
     → 等 phase=ACTIVE 且 active_version 前进（fencing_token 校验）
     → proxy 内部发起 model_call_attempt_2（同 logical_turn_id）
     → 只把最终成功响应交付 CC —— CC 全程无感知，
       不消耗 turn cap，不依赖黑盒 SDK 重试
   守卫三条件（缺一按不可归因故障）：
     失败与已知更新窗口重叠 ∧ 响应未交付 ∧ 恢复后版本符合预期
   不可归因中断：
     终止 attempt → RolloutAttemptOutcome(missing_after_local_retry)
     → 组缺员，worker 继续新组
   ```
6. **资源分类限额（codex #9）**：active sandbox、并发模型调用、评分容器、pending groups、ready groups **各自独立限额**，不共用一个全局并发池——任何一类资源打满都只反压自己的上游，不饿死其他类。
4. 交付边界 fan-out aware（三视图，讨论稿 §6.1/原 S2-0b 问题 C）：内部权威三层结构；rollout/filter 视图保留 PromptGroup 外层 + 身份 sidecar；train converter 视图平铺 + 无损回链。
5. 局部幂等重试按讨论稿 §4 白名单表（max_attempts=3、指数退避 full jitter、评分阶段只允许一次完整重试）；重试记录进 `RolloutAudit` 时间线，不新增公共 schema。

**验收**：故障注入单测覆盖——task 异常不泄漏、queue 满反压不停摆、更新窗口 abort → turn 重生成且 non-delivered 留痕、不可归因中断 → 正确缺员；fan-out 形状对 dynamic_filter 与 `_key` 的直接单测（slime 真函数 + 我方交付形状，不打补丁）；**旧 token 悬挂负测试**（升级设计缺口①的最坏组合"带旧 token 但 agent 重开沙箱"——我方从不回队 ABORTED 样本，断言任何进入组装器的 execution 不携带上一 attempt 的残留 tokens）。

### FA-2 PromptGroupAssembler 与合格组队列

> **分批重排（codex 轮次 13 完整审计定序，轮次 14 修订，2026-07-20）**：
> FA-2 分两批。第一批 **FA-2A：Runtime Identity & Durability Foundation**
> （不只"身份"——含持久性与 collector 契约），第二批 FA-2B 才是本节原有的
> assembler 状态机。FA-1 closure（未知 SID fail-closed / drain 先行 /
> capture 事务化 / open rollback / limiter 真接线 / audit sink + 事务化
> 落盘 + FatalExecutionInfrastructureError 停机）已随轮次 13/14 落地。
>
> **FA-2A 执行顺序（codex 轮次 14 定序——F2-4 语义必须先于 F2-1 编码，
> 因为 crash replay 是否复用公开 execution id 直接决定身份格式）**：
>
> 1. **F2-4 定案（先设计后编码）**：崩溃恢复与 replay 身份语义。首版方案
>    （codex 轮次 14 建议，采纳）：slime data-source checkpoint + 与
>    rollout_id 绑定的 RH2 pending-state checkpoint + **replay-stable 公开
>    execution id** + 每次真实会话重新生成私有 capability + 下游按
>    execution_id/batch_id 幂等去重。**不做**完整 data source lease/ACK
>    改造（首版过重）；也**不允许**裸 at-least-once + dedup（无 cursor
>    回退则已预取但丢失的组永远取不回来）。
> 2. **F2-0 代码提升**：正式运行时代码从 `experiments/s1_7a_bringup/`
>    提升进 `src/repoharness2/`（capture_wire 的 registry/事务/守卫、glue
>    的装配工厂——正式链承重墙不住在 experiments 目录）。
> 3. **F2-1/F2-2 身份与凭证**：ExecutionIdentity 贯穿 worker→orchestrator
>    →session→proxy→capture→grading→artifact→Outcome；公开
>    `rollout_execution_id`（可审计、replay-stable）与
>    `session_auth_capability`（128-bit 随机、仅当前会话、不落公开
>    artifact、会话关闭即失效）分离。**poison 只绑定实际 session/attempt，
>    不绑任务槽位**（轮次 14 设计规则 1：当前稳定 SID + 归档毒 = 非确定性
>    任务拉黑，一次 infra 抖动可能整 run 排除一个题——身份拆分后此病根治）。
> 4. **F2-3 request 级 capture 归属 + 单 owner 状态变更**：
>    `(execution_id, request_id)` 键替代 SID+fail-closed；同时把
>    CaptureRegistry 从"散锁"收敛到单 owner 串行化状态变更（连续多轮竞态
>    问题的共同根源是共享可变状态跨三个执行域传播——停止叠锁，收敛所有权）。
>    落地后解除 overlap fail-fast（并行 subagent 误杀解除）。
> 5. **F2-4 实现**：按第 1 步定案落地恢复语义。
> 6. **F2-5/F2-6**：collector 组不变量（组长度 == n、slot 0..n-1 无重复、
>    重复投递拒绝、混合 branch 策略显式、dropped 有界）；attempt→Outcome
>    durable manifest（snapshot/ack 事务接口已在，接 per-execution
>    manifest 与双向引用）。
>
> **FA-2A 附带定义项（编码前定案）**：
>
> - **结构化终止结果枚举**（轮次 14 设计规则 2）：`completed /
>   episode_time_limit / owner_cancelled / policy_update_abort /
>   harness_crash / api_failure / sandbox_failure`。事实依据：slime episode
>   时间预算耗尽返回 `EXIT_TIME_BUDGET_EXCEEDED = -1`（sandbox.py:60），
>   rh2 Docker RPC 超时返回 124——"所有非零 exit 一律拒绝"会确定性剔除
>   长任务（长度偏置）。`episode_time_limit` 在 capture 完整闭合、无半截
>   响应、workspace 可评分时按**截断但有效**的 rollout 评分，不自动判
>   infra failure。require_real_weight_versions 与非零 exit 拒绝的启动
>   断言硬耦合已解除（轮次 14 代码已落，推翻轮次 9）；FA-5 负责实测映射，
>   不承担首次定义语义。
> - **按 fault domain 分类的熔断**（轮次 14 设计规则 3，实现挂 FA-2B 与
>   assembler 同批）：contract_violation/审计持久化失败/身份矛盾 → 立即
>   run_halt；模型服务/sandbox/capture 基建故障 → 组件级暂停或 run_halt
>   （**不隔离任务**）；环境包确定性损坏 → task_quarantine；模型真实失败
>   reward=0 → 正常样本不进熔断；安全策略触发 → 拒绝 execution/group 但
>   默认不隔离任务；staleness 偏高 → 反压/暂停权重更新协调，不隔离任务。
>   载体：现有 `RolloutAttemptOutcome` + 纯函数 `RecoveryPolicy` + 最终写
>   `PromptGroupAdmissionReport`——**不新增报告层**。
> - **正式训练闸门补充**：`rh2_formal_training_allowed` 的前置检查显式
>   包含"overlap fail-fast 挡板已由 request 级归属替代"与"分类拒绝率
>   熔断在位"两条——临时挡板不解除不得开正式训练（防训练分布被隐性裁剪）。

1. 每条执行完成评分/投影/Gate 后才提交 `RolloutAttemptOutcome` 给 assembler；`PromptGroupState` 为进程内轻量状态机（定期 checkpoint，不注册公共 schema）；组终结时唯一落盘 `PromptGroupAdmissionReport`（admitted/rejected/quarantined + 讨论稿 §5.3 字段）。
2. 状态机照讨论稿 §9（NEW→RUNNING→PRESENT/LOCAL_RETRY/MISSING/PERMANENT_REJECTED；组 OPEN→READY/EXPIRED/QUARANTINED；READY→BatchAdmission）。`WAITING_FOR_BATCH_ALIGNMENT` 不倒写 eligibility、不重跑 harness。
3. 只有固定 n 完整、eligibility 合格、policy span 达标的组进 `QualifiedPromptGroupQueue`（保存 raw group facts + token 长度 + 身份；不固化任何 step-local 算法张量）；组进队后**消费时重算 staleness**。
4. 过采样供给：`initial_groups = B + reserve_groups`（预注册值见 §5）；残组不占 GPU、到 deadline/TTL 过期。
5. 组终结六条件照讨论稿 §6.4；executed 级安全事件整组拒绝（不能"重采到不作弊为止"）；熔断（同故障短窗超阈值 → task_quarantine / run_halt）。
6. **长度偏置监测**（讨论稿 §4）：每个被放弃 attempt 留 `elapsed_seconds_before_failure / captured_turn_count / captured_token_count / failure_phase`；失败率随长度显著上升 → 修 runtime，不许靠重采掩盖。

**验收**：状态机属性测试（非法迁移不可达）；讨论稿 §11 场景 1/4/5/6/7/9/10/13 的本地夹具复现。

### FA-3 SlimeBatchAssembler 与 batch 准入（原 S2-0b 迁入；**离线部分可先行开发**）

原 S2-0b 的问题 A~E 定义、五条归一化不变量、`BatchAdmissionReport` 归属（批次级报告 + `BackendHandshake.backend_rejection_reason` 引用，**不碰 eligibility**；枚举扩 `insufficient_rollout_count / microbatch_alignment_failed / prompt_group_incomplete / capacity_backpressure`）全部继承，此处不重复（历史文本见 04 计划 git 历史与 `s2/codex_reviews.md` 轮次 2）。FA 架构下的增量语义：

1. 输入只来自 ready queue 的完整组；事务式选取，**带 lease 与 trainer 确认**（codex #4：裸 peek→consume 无法处理 trainer 崩溃——提交前删丢 batch，训完删又可能重启后重复训练）：
   ```text
   READY → RESERVED(batch_lease_id, expires_at)
         → SUBMITTED(optimizer_step_id) → TRAINED → ACKED / RELEASED
   恢复语义 = at-least-once 提交 + batch_id+optimizer_step_id 去重；
   lease 到期未 ACK → RELEASED 重新可选。不承诺 exactly-once
   （队列账本与 trainer checkpoint 无法原子提交）。
   ```
1b. **训练进度权威（codex #8）**：完全异步后 slime 名义 epoch / `train_iters`（按名义 rollout 数推导）与 lr 调度会漂移——数据源为 reserve/rejected 组持续推进。进度权威 = **已确认 optimizer step / 已消费 RolloutExecution / 有效 token**；attempted 与 trained 的 prompt coverage 分开记账（与 FA-5 第 7 项覆盖率对账共用计数）。
2. **按唯一 `rollout_execution_id` 计数** global batch；branch 不计数。GRPO 归一化按 `group_index` 键控（原型：`reference/slime/slime/rollout/_fanout_test_helpers.py::grpo_normalize_by_group_index`），advantage 广播给 branches，rollout 级分母。
3. 修复动作只有：**换组（按 token 长度分桶 + 有界搜索）→ 等待更多 ready 组 → 预注册 fallback**（首版 fallback 只登记不启用，见 §5）。禁止：拆组、复制成员、branch 充数、改 eligibility、重跑 harness、人工碰运气改 gbs。
4. **差分验证**：同一输入喂我方预检器与 slime 真 `build_dp_schedule`（纯 Python import），成功/失败类别、step 数、microbatch 数三项一致。

**离线验收（继承原 S2-0b 六项，不需要 GPU，可在 FA-1/2 之前完成）**：J4 事件元数据夹具复现 A 类（44→31→19<32）与 B 类（23 mbs≠24）；差分验证；D 不变量属性测试；E 五不变量属性测试 + group5×8branch 定向回归；展平 round-trip + dynamic_filter/`_key` 直接单测；强验证挂 FA-5 短租。

### FA-4 faithful DIS 与 off-policy 正确性（**对拍部分可先行开发**）

1. faithful DIS 自定义 loss（`--custom-loss-function-path`）：实现论文语义 `f(current/rollout ratio) × advantage × log π_current`，区间内 ratio 加权、区间外置零；**denominator 语义预注册**（被拒 token 是否留在分母——slime stock TIS 的"留分母、零梯度"语义与"仅按接受 token 归一化"不同，必须显式选择并写死）。
2. **逐 token 手算对拍**（codex #7 扩充——不能只对拍 forward loss，以下每项都要固定并测试）：loss 正负号；importance ratio 是否 `detach`；越界 token 的**梯度精确为零**（不只是 loss 项为零）；denominator 是否包含被拒 token（与第 1 条预注册一致）；top-p replay 是否参与 current logprob 计算；DP/CP/VPP 下归约一致性；逐 token 梯度与手算逐位一致。先合成张量，后接真实 rollout dump。
3. IcePop-style 近似（`--use-tis` + custom TIS hard mask）只作实现对照档，结果**不得标注为 GRPO+DIS**。
4. **准入分层（codex #3 修正：DIS ratio 需要 current 模型 logprob，只在 trainer forward 时产生，ready queue 阶段物理不可得）**：
   ```text
   ready queue 准入：provenance 完整、组完整、版本跨度、
                     current-version staleness（§5 预注册值）
   trainer forward：计算 current logprob → faithful DIS ratio → token mask
   训练决定：正常反传；全局有效 token=0 时跳过整个 optimizer step
             （计数并告警，连续跳过触发熔断）
   ```
   DIS 有效 token 比例（90%）首版是**监控黄灯阈值**，不是 queue 硬门；若未来要按它换 batch，需另立"两阶段 logprob 预检"或"forward 后取消重取"的 trainer 协议（明确不在首版）。
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
7. 【N6 worker 崩溃恢复】注入 worker 死亡 → 验证 **halt → 整个 rollout
   actor 退出并重启**（与 §6.1 P1-3 定案一致；单例 + monkeypatch 拓扑不
   支持进程内线程重建，不得验证"线程重建"这种不存在的语义）+ in-flight
   丢失被 prompt 覆盖率对账捕获（每个 prompt 的 dispatched/finalized/
   consumed 计数对账，缺口即告警）。
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

全局顺序（用户 2026-07-12 确认）：
① FA-0 →（FA-3 离线 ∥ FA-4 对拍 ∥ 并行线程跑 S2-1 ingestion+四门）
② FA-1 → FA-2 → FA-3/FA-4 接线 → FA-5 本地故障注入（短租项除外）
③ S2 其余按序（S2-0 剩余两项 → S2-2 → S2-3/4 → S2-5 → S2-6 →
   S2-7/8 本机段）。开工前置：用户批复 G 系列（尤其 G2/G7 网络方案
   决定 S2-2 写法）。若需压日历时间，S2-2~6 可由第二线程在 ② 期间
   并行（与 FA 无依赖），默认单线程串行。
④ 一次合并短租收尾：FA-5 GPU 清单 + S2 G10（拦截链证据要求
   S2-2 事件日志 + S2-4 CommandFilter 已实现；轨迹留存兼供 G8 复验）。
```

## 3. 验收场景

讨论稿 §11 的 18 条全部继承（1~18，此处不重复），新增三条：

```text
19. 权重更新窗口内 abort 一个在途 turn（含 finish_reason=abort 正常 JSON）
    -> proxy 在同一 CC HTTP 请求内丢弃 attempt_1（non_delivered_aborted
       留痕）、等 phase=ACTIVE 且版本前进、内部发起 attempt_2、只交付
       最终成功响应；CC 无感知、turn cap 不重复消耗；execution 继续
       不缺员；DIS 覆盖该 execution 的跨版本 turn。
20. 非更新窗口的连接损坏（不可归因；或守卫三条件任一不成立）
    -> 终止 attempt，组缺员；负测试：proxy 不得对该类中断做内部重生成。
21. eval 请求进入 FA 路径
    -> 显式拒绝（fail-fast），错误信息指向 before/after 标准路径；
       before/after 评测在 worker 停止后可正常执行。
22. trainer 在 SUBMITTED 之后、ACK 之前崩溃
    -> batch lease 到期 → RELEASED 重新可选；重启后凭
       batch_id+optimizer_step_id 去重，同一 batch 不被重复计入
       optimizer step（at-least-once 语义的两侧都要测）。
23. trainer 长时间停滞（权重不更新）
    -> ready 组的 wall_clock_ttl 正确过期（版本 TTL 此时永不触发）；
       各资源分类限额分别反压，sandbox/评分容器不被 ready 积压饿死。
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
| DIS 有效 token 比例 | 90%（**监控黄灯阈值，非 queue 硬门**——ratio 只在 trainer forward 可得，codex #3） | 持续低于 → 排查 staleness/对齐，FA-5 校准 |
| DIS ratio 信任区间 | **(1−ε_low, 1+ε_high) = (0.2, 4.0) 开区间**（论文式 3 原文裁决 2026-07-12：ε_low=0.8/ε_high=3.0 是式 3 参数不是直接 ratio 边界；此前闭区间 [0.8,3.0] 读法作废——codex FA-3/4 审查 #1。论文正文闭括号与式 3 严格不等号矛盾，以式 3 为准） | denominator 语义随 FA-4 预注册（v1=provenance_tokens 已落 faithful_dis.py） |
| 组 deadline | 任务 time budget + 评分预算，×1.5 p95 安全系数 | 动态推导 |
| ready queue TTL | **双限**：policy_version_ttl（staleness 上限）**∧** wall_clock_ttl（codex #9：trainer 停滞时版本 TTL 永不过期） | 消费时重算 |
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
   缺口①"正式接线"段。FA-0 第 8 条的 start_len 留位是它的契约前置
   （2026-07-12 自 S2-0 迁入）。
8. 【递延登记：worker poll 粒度】stock worker 1s poll 对 SWE 分钟级任务
   可忽略（升级设计 N3 已定性）；只有未来混入秒级短任务才需要降到
   50-100ms 或事件驱动——记录在此防止重复调查，FA-1 不做。
```

### 6.1 codex 轮次 13 完整审计的 P1/P2 递延登记（FA-5 前必须逐项销案或改判）

| # | 事项 | 归属 |
|---|------|------|
| P1-1 | `retry_local_operation` 零生产调用点——逐操作（image/container/artifact/grading/发前请求）定幂等键+错误分类后接入，不做整段装饰器 | FA-2/FA-3 接线时 |
| P1-2 | 生产 shutdown 链缺失：actor teardown 时 worker/GradingQueue/adapter 线程/在途 sandbox/artifact writer 的统一关闭 + 退出校验（账平、in-flight=0、无 open session、隔离区移交） | FA-5 前 |
| P1-3 | 单例 + monkeypatch 不支持进程内恢复——当前恢复语义显式定为 **halt→整 actor 重启**；可重绑 registry holder 前不得声称进程内 recovery | 文档已定，FA-5 验收 |
| P1-4 | 长运行内存无界残余：`audits`/`failure_records`/`dropped_groups`/`cleanup_quarantine`/`GradingQueue.events`（后者还有 O(N²) 扫描）——durable sink + 有界窗口（attempts_ledger 已 drain 化） | FA-2 audit 面 |
| P1-5 | episode deadline 起点晚（首次模型调用起表，未含 CLI 安装/workspace/CC 启动）——orchestrator 在 execution 启动时生成绝对 deadline 并注册 | FA-2 身份批 |
| P1-7 | cleanup_quarantine 只有内存 list——最小 reconciler（持久化 + 重试 + run-halt 阈值） | FA-5 前 |
| P1-8 | StaticActiveCoordinator 永远 ACTIVE：正式链**不会**透明重生成（只保守缺员）；version provider 同步 requests 在 TTL miss 时阻塞 adapter loop ≤5s——trainer 发布、全引擎 ACK 的异步 consensus 快照替换 | FA-4 |
| P1-9 | `/abort_request` 失败无事实记录——计数 + 引擎健康告警；FA-5 四方对账（HTTP req id / RID / abort ACK / attempt status） | FA-5 |
| P2-1 | FA `rollout_id` 未使用——写进 batch request/身份/audit manifest | FA-3 |
| P2-2 | `record_event.weight_versions_engine` 在 unregister 后恒空——cleanup 前冻结 execution snapshot | FA-2 audit 面 |
| P2-3 | fsync 在 adapter 热线程同步执行——专用 writer/WAL 或 to_thread + fsync p95 实测 | FA-5 前 |
| P2-4 | `os.replace` 缺父目录 fsync——crash recovery 若入 FA-5 验收则补齐，否则文档声明进程级原子性 | FA-5 定案 |

**FA-5 验收增项（轮次 13 §11，并入 FA-5 清单）**：未知/伪造 SID 不达
SGLang；并发 subagent 按 request id 归属；commit 故障无 pending draft
残留；`rh2_fa_limit_model_call=1` 实测峰值 =1；actor kill/restart 预取组
不丢不重；≥1h 热状态 cardinality 有上限；shutdown 全归零；update abort
的 RID/ACK/ledger/capture/sample 五方一致；CC 取消终止真实 SGLang 请求
与 sandbox CLI；audit artifact 可重建四态守恒式。

**闸门重申**：本节 P0（已闭）+ F2-1~6 完成前，`rh2_fully_async_training_
path_verified` 保持 **false**；`StaticActiveCoordinator` 在位期间不得声称
"权重更新 abort 已在生产链透明重生成"（只有保守缺员）。

## 7. 关联文档回填清单（FA 推进过程中完成，不阻塞开工）

```text
[x] 附录 A "reward/K 分摊" 勘误（D-FA-7）——2026-07-12 已回填
[ ] 实验设计文档：§9.1 compaction 运行时硬事实措辞（D-FA-6）——随 FA-0 回填
[ ] 实验设计文档：GRPO+DIS 对照矩阵（算法分析文档 §9.3 的 A/B 两行进
    首轮矩阵；C/D/E 留算法工作流）——随 FA-4 完成回填
[ ] preflight_report §6：batch admission 回填项在 FA-5 短租后改判
[ ] 升级设计文档：FA-5 abort 实证结论回填缺口①（终止其"empirical test
    deferred"状态）
[ ] AGENTS.md / 00-project-status.md：FA 阶段状态随各任务 commit 同步
```
