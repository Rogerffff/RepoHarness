# FA-2A 决策包（v4：已批准版——含 codex 五审修订）

```text
status: approved
owner_decision:
  D1 = A（带修订批准，非原样批准 v3.2）：
    ① 批准 D1a 事实表达能力（termination fact 与 disposition 分离 /
       quiescence 后才冻结评分 / 三 disposition 正交 / 两 mask 分离 /
       固定 n 不静默 n-1 / continuation mode 与 profile 分离）；
    ② FA-2A 只实现 Observability V0（只记录，不用新计时改变 termination
       /reward/admission/gradient；不定义 chargeable_policy_seconds；
       不导出 trajectory.jsonl，不声称工具级精确计时）；
    ③ audit_only 不关闭 security/identity/capture/provenance 守卫，
       且不产出正式在线训练 batch；
    ④ hard_wall_timeout 仅为 termination trigger，completion 由事实
       推导（present_truncated 处置留 D1b/FA-4）；
    ⑤ D1b 显式延后（profile 选择 / watchdog 数值 / 截断处置 /
       chargeable policy time 是否存在 / masked member 的
       GRPO·DIS·分母·GBS 语义）。
  D2 = A（同节点首版 / 单一 checkpoint owner / pending-before-cursor /
       四层身份 / recovery_epoch+fencing；不承诺 optimizer exactly-once，
       跨节点延后）。
  D3 = A（adapter 线程单 owner；有界命令/快照接口；owner 死亡
       fail-closed；生产路径禁绕过）。
  D4 = A（穷举映射 / FaultDomainMonitor ownership / 安全三档 / worker
       recovery 与 staleness 控制动作；正式阈值数值延后 pre-RL/FA-5
       校准后单独 T0 预注册）。
approved_at: 2026-08-07
errata_4: |
  勘误 4（2026-08-16，用户经 codex 七/八轮讨论批准——capture wire 单代
  启动 + D2 范围澄清）：
  ① 每个 RolloutManager 进程只允许一代 capture wire / registry /
    BringupService 启动事务；启动状态 NEW→STARTING→RUNNING|FAILED，
    FAILED sticky（记录首个根因、尽力清理、原样上抛、后续 get() 重抛
    同一错误、绝不创建第二代）。实现形态（类级状态或薄闩锁）属 T1，
    不要求大型 CaptureWireRuntime，不做反向 monkeypatch。
  ② 启动不做通用指数退避；仅白名单内幂等 readiness 瞬时子操作（如
    SGLang 就绪探测）允许有限重试；配置/digest/renderer/权限/磁盘
    错误立即失败。当前恢复语义如实为**终止训练 run**：WorkerHalted
    不自动杀死/替换 Ray Actor；Actor replacement、checkpoint replay
    与 fencing 属 F2-4。
  ③ 生命周期 × 故障性质正交判定：STARTING 白名单瞬时故障→子操作内
    有限重试；STARTING 其他→sticky FAILED 终止 run（不进 F2-4）；
    RUNNING 确定性故障（配置/契约/安全/血缘/digest/权限/持久存储）→
    run_halt 不自动恢复；RUNNING 明确可恢复的 state-owner/瞬时基建
    故障→F2-4 后受控恢复；RUNNING 未分类→run_halt（不得猜成瞬时）。
  ④ D2 未批准且 F2-2/F2-4 v1 不得顺手实现：同进程 BringupService
    reset、WorkerHalted 自动杀 Actor、ActorHandle 自动替换、训练循环
    无感续跑、mid-episode resume、optimizer exactly-once、跨节点恢复、
    联合分布式 checkpoint、未分类故障自动恢复。F2-4 v1 = 安全停止后
    从持久 checkpoint 受控重启同一逻辑 run 并 replay 未完成工作
    （首版只支持 RolloutManager-only recovery；whole-run 恢复须先对账
    trainer checkpoint identity 与 policy version，不兼容整组重建）。
  ⑤ registry 生命周期 = 进程级单代绑定；capture 可变状态 mutation
    owner 仍按已批 D3 于 F2-3 收敛为 adapter event loop 单 owner。
    不同 registry 重绑 = typed fatal（暴露所有权错误）；同 registry
    重复安装幂等。
errata_3: |
  勘误 3（2026-08-15，用户批准 codex F2-2 复核二轮 T0 建议）：
  RuntimeFailureCategory pre-formal 原地修订新增 runtime_quiescence_failure
  ——仅当 Runtime 静止屏障（F2-2b）**已真实执行但失败**时使用；reason_code
  细分 execution_scope_termination_timeout / active_writer_detected /
  late_model_request_detected / snapshot_freeze_failed /
  snapshot_integrity_mismatch。"屏障尚未实现"由启动闸门表达，不产本值、
  不进每 rollout 故障统计。修订依据：v2 尚无正式外部资产（producer 未上
  GPU），旧严格消费者拒新枚举值的兼容问题不存在；若 v2 已冻结则须升
  schema 版本（本次不适用）。同步：三分封闭集合（归执行事实集）、D4 表 1
  新行、集合等式测试、旧 artifact 读取测试。
authoritative_plan_ref: 05-fully-async-execution-plan.md FA-2A 节（已回写为引用本文 approved 语义）
```

> 外部证据入口：`docs/harness_improve/external_paper_references/
> agentic_rl_training_recipe_evidence_matrix.md`。审查历史与计时调查
> 归档：`s2/codex_reviews.md`。本版验收条件（codex 三审）：不依赖
> v2/git 历史可完成决策；"7 条正常 + 1 条 horizon-masked"可由 member
> 级契约表达；provenance mask / 算法 mask / batch 计数不混用；全部
> termination/failure/security 类别有唯一动作；D2 状态无含义重叠。
> 已知残留：05 计划 FA-3 节仍有旧 `SUBMITTED→TRAINED→ACKED` 状态机与
> "全 execution 计入 GBS"表述——**拍板后的 05 计划回写时一并修**（四审
> 确认不阻塞本包决策，但计划审查必须修）。

---

## 决策 1：超时/预算终止——架构契约（D1a 现在拍）与训练处置（D1b 延后拍）

### 为什么拆两阶段

公开系统对超时处置互相冲突（SA-SWE 保组统计屏蔽梯度 / Nemotron 屏蔽
loss / Composer 2 未见 overlong masking 收益 / K3 同步框架暂停续跑 +
token 预算罚分 / Endless Terminals 对 wall 与 turn 耗尽分流程），无
"最佳做法"可抄；我们自己的计时现状（P3：97% 中位墙钟在 harness_run
混合大桶、四个时钟起点错位、5 条 exit=-1 轨迹超预算 181~480s）也不足以
区分"策略慢"与"基建慢"。所以：现在拍**架构契约**（让各种语义都能表达、
都有事实可查），pre-RL 诊断后拍**训练处置**（选 profile 与数值）。

### D1a（现在拍板）：终止事实、双时钟、静止屏障、member 级处置

1. **termination_kind 三族 + 推导关系**。分类：

   ```text
   策略 horizon 族（可复现，截断有效的候选）：
     task_token_budget_exhausted / max_turns_exhausted（slime 429 turn
     cap）/ context_limit_reached
   看门狗族：hard_wall_timeout
     ——**仅为 termination trigger**（五审 4.2 撤回"恒 missing"预决：
       触发者身份不决定事实完整性）。completion 由事实推导：capture
       closure + Runtime quiescence + 冻结 snapshot 全部成立 →
       completion 候选 = **present_truncated**（不得仅因 hard wall 触发
       改写为 missing）；任一不成立 → missing。评分是否成功不参与
       completion（勘误 2）。
       present_truncated 的 group/reward/gradient/GBS 处置留 D1b/FA-4
   控制面族：owner_cancelled
     ——控制面取消，默认不产生 reward（不属"正常完成"）
   基础设施族（missing，reward=None，进对应 fault domain 计数）：
     inference_timeout / sandbox_rpc_timeout / update_wait_timeout /
     harness_crash / api_failure / sandbox_failure /
     model_call_regeneration_exhausted
     ——三层分离（停止事实 / 故障域 / 具体原因）：
       termination_kind = model_call_regeneration_exhausted
       failure_category = model_proxy_failure
       reason_code      = max_regenerations_exceeded
     （D-FA-3 重生成本身不是终止事件，耗尽才是）
   注：grading 阶段的超时不是 rollout 终止类别（评分发生在终止之后），
   其契约载体是 GradingFailureCategory（见第 2 条）
   正常族：completed
   ```

   **推导不是线性链**，disposition 由多个事实共同决定：

   ```text
   termination fact + capture/quiescence/snapshot facts
     ——**批准后勘误 2（2026-08-07，六审后聚焦复核）：completion 只由
       runtime/capture/quiescence/snapshot 完整性决定；grading facts
       只进入 reward 与 admission，评分基建故障不倒写执行事实**
     → completion_class ∈ { present_complete, present_truncated, missing }
       （事实层；与消费侧三态 missing/present_but_not_admissible/
        permanent_rejection 的关系：completion 是事实，后者是准入判定）
       + （可选）failure_category
     → 选定 profile（组/run 级配置）
     → member disposition（member 级结果）
   ```

2. **评分超时拆两类，契约载体 = GradingFailureCategory**（现值：
   `infra_failure / test_log_parse_failed / patch_apply_failed /
   tests_failed`，本包新增一值）：

   ```text
   基建性评分超时 → failure_category=infra_failure，
                    outcome=failed_to_grade，reward=None
                    （reward unavailable + admission 不通过；
                     **不倒写 execution completion**——勘误 2）
   GradingFailureCategory 新增 test_execution_timeout：
                    outcome=unresolved，reward=0（模型真实失败）
                    ——仅当三条件全真才允许构造：clean grader 已正常
                    启动 ∧ 测试预算确定性 ∧ 超时可归因于 agent patch
                    （如 patch 引入死循环）；任一不成立 → 按 infra 构造
   ```

3. **双时钟 = 区间并集口径**。保存原始事实而非派生数：

   ```text
   wall_start / wall_end
   non_chargeable_intervals: [{start, end, reason, measurement_source}]
   chargeable_execution_seconds = 同一 owner 对区间做并集后派生
   （重叠暂停不得重复扣除）
   ```

   **FA-2A 只记录，不切换预算判定时钟**（五审 2.1 消除 v3.2 冲突）：
   候选 non_chargeable_intervals（权重更新暂停、系统反压等待）如实
   记录，但 D1b 前**不得**扣除成带训练含义的派生值；首版不定义
   `chargeable_policy_seconds`（含评分/投影/清理的全程派生值不是
   "策略时间"，五审 2.2——该量是否最终需要存在也留 D1b）。首版只保留
   workflow_wall_seconds / agent_episode_wall_seconds /
   per_stage_durations 三个如实命名的量。

4. **Runtime 级静止屏障**（"杀进程组"不充分——CC/工具可再起新 session
   或后台进程）：

   ```text
   撤销 adapter session（HTTP 层拒新请求）
   → 终止 sandbox execution scope（容器/cgroup 级）
   → owner 侧确认在飞模型调用与文件写入归零
   → 冻结不可变 workspace snapshot
   → 只对冻结副本评分
   ```

   digest 稳定只是探针；无法确认静止 → missing，禁止配置开关强行评分。

   **watchdog 三层与 ownership**（五审 4.1/4.3）：组件局部 timeout
   （Docker RPC/模型请求/评分测试/工具命令）防局部卡死；agent episode
   watchdog 看 `cc_process_spawned → quiescence` 段；workflow watchdog
   看 `execution_received → cleanup_completed` 全程。全局 watchdog 由
   **RolloutExecution 的 Runtime owner** 拥有（trainer/assembler/proxy
   都不单独决定训练处置），触发序列 = 撤销 session → proxy drain/abort
   → 终止 execution scope → capture 关账 → 确认 quiescence → 冻结 →
   按完整性事实分类 → profile 后置导出处置。实施上预留 quiescence/
   cleanup reserve（先停开新 turn，absolute hard kill 只作最后上限）
   ——把 wall cutoff 尽量收口在已提交 turn 边界以减少 missing；但
   **不得为保固定 n 把不完整 execution 重标 present**。CC 内部的 Bash
   timeout 不可作为安全边界（后台命令可越过单工具调用存活）。

5. **member 级处置契约**（不新增账本，单一事实来源 + 派生视图）：

   ```text
   PromptGroupAdmissionReport:
     termination_policy_profile        # 组/run 级配置
     member_dispositions:              # member 级结果
       - rollout_execution_id / outcome_id
         group_membership / reward_disposition / gradient_disposition
         reason_codes
   派生视图（不独立维护事实）：
     GroupOutcomeView      固定 n 个成员及 reward → advantage 计算
     TrainableBranchView   只含可构造训练张量的 branches → trainer

   三个 disposition 的精确枚举：
     group_membership     ∈ included | excluded_by_profile | unavailable
     reward_disposition   ∈ included_in_advantage | excluded_from_advantage
                            | unavailable
     gradient_disposition ∈ train | masked | excluded
   ```

6. **两种 mask 严格分离（纠正 v3——不放宽零 token 守卫）**：

   ```text
   provenance_loss_mask   不可变历史事实（该 execution 真实生成的
                          可归因 token；horizon member 有真实非零 token）
   horizon_gradient_mask  本次训练的算法决定（step-local，=0 表示该
                          member 梯度屏蔽）
   ```

   没有任何可归因采样 token 的 execution 仍是**真缺员**——不伪造零
   token branch，不放宽 `zero_trainable_tokens_execution` 守卫。

7. **三态区分与精确归类**（completion fact 不被训练策略改写；staleness
   是消费时刻的准入决定，不倒写成"rollout 没产生"）：

   ```text
   missing（事实未完整产生）：
     半截模型响应 / capture·logprob·version 账目不完整 /
     workspace 无法静止 / 基建失败重试耗尽
   present_but_not_admissible（事实完整，本次不可准入）：
     staleness 超限 / 被严格 profile 排除的完整 horizon 轨迹
   permanent_rejection（事实完整，禁止训练）：
     executed 级安全事件 / 身份·契约矛盾 / artifact 污染
   ```

8. **profile 是穷举映射，audit_only 是 enforcement mode**：

   ```text
   profile ∈ { strict_horizon_excluded_v1, scored_horizon_masked_v1 }
     ——更名（四审）：严格档下完整可评分的 horizon 轨迹是
       excluded_by_profile，不是 missing——"strict_missing"名字会把
       profile 决定伪装成 completion fact
     ——每个 profile 必须对全部 termination_kind 给出唯一 disposition
       （含 horizon 族/看门狗/控制面/各类 infra/无法静止），缺项 = 配置
       非法拒绝启动。**批准后勘误（2026-08-07，六审 3——与 owner 批准
       范围第 ④⑤ 点对齐）**：D1b 前 candidate profile 只对**已定案**
       类别计算 disposition；`hard_wall_timeout`（present_truncated）
       标 `decision_deferred`；含 decision_deferred 的映射下 `enforce`
       模式禁止启动——"必须穷举"自 D1b 发布完整映射的正式 profile
       版本起生效
   enforcement_mode ∈ { audit_only, enforce }
     ——audit_only（FA 开发/诊断期）：不执行 profile 剔除，且**同时计算
       两个候选 profile 的 disposition** 记入
       candidate_dispositions_by_profile（pre-RL 比较组存活率与分布）。
       **audit_only 不放宽任何守卫**（五审 2.3）：security / identity /
       token provenance / capture 完整性 / hidden verifier 隔离照常
       fail-closed；audit_only 模式**不产出可进正式在线训练的 batch**。
       enforce（正式训练）：单一 profile + 配置 digest 预注册
   ```

   **true_resume 从 profile 中移除**（v3 错误；见下"续跑维度"）。

9. **续跑是另一个维度，不是终止处置**（K3 语义澄清，用户抓的混淆）：

   ```text
   rollout_continuation_mode:
     continuous_live_v1                     当前正式方向：live execution
                                            跨训练步继续 + D-FA-3 当前
                                            turn 重生成（权重更新 abort 时）
     checkpoint_resume_across_iterations_v1 K3 的 partial rollout——同步
                                            框架里"本轮收够 λ 比例即暂停
                                            长尾、下轮恢复"；触发条件是
                                            迭代级完成度，不是单条轨迹到限
     token_level_response_resume_v1         从已生成 token 续 decode
                                            （custom_generate 当前不支持）
   ```

   我们 = continuous_live_v1。K3 的机制是同步迭代框架的长尾解法，不是
   "达到 episode 限制后恢复"；若未来做"超时后延续"，那是
   `execution_state=deferred + continuation_mode=checkpoint_resume`，
   且各限制不能统一 resume（max_turns 恢复违反上限；context_limit 需要
   compaction/分段；hard_wall 续跑应改叫 timeslice_expired）——留未来
   能力闸门，当前不可被正式配置启用。

10. **FA-4 算法边界（D1a 不预决）**：D1a 只保证 reward-only member
    **可表达**。以下全部留 D1b/FA-4 决策包：GRPO mean 还是
    leave-one-out；是否做 std 归一化；masked member 是否进 loss 的
    execution 平均分母；是否占 optimizer global_batch_size；
    BatchAssembler 是否需补充 gradient-bearing execution。正式闸门在
    这些语义预注册前保持关闭。

11. **组完整性**：固定 n，不做静默 n-1。missing 与 permanent_rejection
    成员（按第 7 条精确归类）使整组不进在线更新；present_but_not_
    admissible 的处置由 profile 与 admission 决定（如 scored_horizon_
    masked 下 horizon 成员保持 included）。

### D1b（pre-RL 诊断后拍板）：profile 选择与数值

诊断设计：50~100 题 × n=8，记录原始 monotonic 区间（materialize /
sandbox_start / harness_install / model_queue / model_generation /
tool_execution / sandbox_idle_while_model / quiescence_and_snapshot /
grading_* / group_wait / admission_wait）+ turn_count /
generated_tokens / termination_kind / group_survival /
trainer_wait_ratio / policy_version_lag。

**成本（修正单位，初步估计，D1b 时批真实预算）**：400~800 条 rollout，
按 P3 中位 633s、并发 8~16 → 约 **4.4~17.6 实例墙钟小时**（8 GPU 实例
≈ **35~141 GPU-hours**）；建议与 FA-5 短租合并成一次租期。

诊断后决定（D1b 完整延后清单，与 owner 批准范围第 ⑤ 点一致）：
timeout/horizon profile 选择（参考：单员 5% 缺失率下 0.95^8=66.34%
完整组存活）；watchdog 数值（**必须用拆桶后的 cc_process_spawned→
quiescence 段校准**，不能用混合桶）；hard-wall 截断（present_truncated）
的训练处置；chargeable policy time 是否存在（可能最终不需要）；
reward-only/masked member 的 GRPO/DIS/分母/GBS 语义（FA-4 决策包）；
32K/50-turn 校准。

**拍板选项**：
- **A（推荐）**：D1a 契约按上文采纳；D1b 显式延后。
- **B**：跳过诊断直接 strict_horizon_excluded_v1——最快，但确定性长度/难度偏置。

---

## 决策 2：F2-4 崩溃恢复与 replay identity（自包含完整版）

**要决定什么**：RolloutManager state-owner 进程重启后，已取出未训练的
组怎么恢复；replay 身份与提交权；恢复承诺强度。

**范围**：崩溃 = RolloutManager state-owner 进程重启（CC/sandbox/
adapter 线程/SGLang 单独故障属决策 4 的 fault domain，只有升级为整个
state-owner 重启才进本决策）。首版保障 = 同节点重启（pending store 本地
磁盘；当前单机 8 卡）；跨节点需共享持久存储，递延。

**现有代码事实**：slime `get_samples()` 立即推进 `sample_offset`
（data_source.py:90），cursor 由独立 `save()` 持久化（:127）；RH2 队列/
在途/结余不持久化——当前崩溃 = 预取组永久跳题（codex 探针：batch=1 时
预取 7 组全丢）。RH2 pending checkpoint 是**新增持久化面**（既有
model-call audit 的 snapshot/写/ack 只是审计事务，不是恢复 checkpoint）。

**方案 A（推荐）**：

1. **单一 checkpoint owner**：pending reservation 与 slime cursor 发布
   由同一 owner 控制（cursor save 只许经它走）——否则旁路保存可越过
   顺序不变量。
2. **提交顺序不变量**：

   ```text
   pending manifest 先 durable
   → 才允许发布会跳过这些 execution 的 cursor checkpoint
   → 两者携带同一 checkpoint_generation
   → 恢复时交叉校验：
       pending_generation > cursor_generation  安全（可重放）
       cursor 已跳过而 pending 缺失            不可恢复矛盾，fail-closed
   ```

   manifest 绑定 dataset revision / task & bundle digest / cursor &
   epoch / sampling 配置（防同一 cursor 在漂移数据上指向另一任务）。
   存储格式（JSON/SQLite/WAL）= T1。
3. **pending 状态集（三个交接状态语义互斥）**：

   ```text
   RESERVED / DISPATCHED / RUNNING / OUTCOME_DURABLE / GROUP_READY /
   HANDED_OFF          已交给训练侧（无后端确认）
   SUBMISSION_ACKED    训练后端 durable 确认收到 submission
                       ——slime 当前无 durable ACK 时**不得**记此状态，
                       账面止于 HANDED_OFF，不暗示 batch 不会丢
   TRAINED             optimizer step 已消费（如可从 trainer 侧证据推断）
   ```

   DISPATCHED/RUNNING 的恢复 = 从干净环境 replay，不承诺 mid-episode
   resume（那属 continuation_mode 未来能力）。
4. **四层身份**：

   ```text
   rollout_execution_id     跨 replay 稳定（逻辑执行，去重键）
   physical_attempt_id      每次实际重放不同（artifact/审计事实键）
   model_call_attempt_id    同一 physical attempt 内模型调用重生成序号
   session_auth_capability  每次 physical attempt 新生成，旧的撤销
   ```

5. **replay 胜出规则**：`recovery_epoch` + fencing_token——只有当前
   physical attempt 能提交 canonical outcome；旧 attempt 迟到结果只进
   审计，不进训练面。
6. **恢复承诺（如实）**：

   ```text
   rollout execution                 = at-least-once
   artifact/admission/submission     = 幂等可去重
   optimizer step exactly-once       = 首版不承诺
   （trainer 在 step 后、ACK 前崩溃的窗口无法端到端排除）
   ```

7. **crash-point 验收探针**：在 pending 写前/写后、cursor 写前/写后
   逐点注入 crash；重启后每个逻辑 execution 要么恢复要么明确去重，零
   静默丢失。

**方案 B**：完整 lease/ACK 改造 slime data source——语义最强（近似
exactly-once），但改外部仓库、首版过重。
**方案 C**：裸 at-least-once + 去重、无 cursor 回退——预取丢失组永远
取不回（缺失而非重复），否决。

**长期代价/可逆性**：A 的 pending checkpoint 是新持久化面（写入时机与
原子性要设计）；A→B 可平滑升级；**身份格式一旦定下很贵改**（决定 F2-1
编码，必须先拍）。

---

## 决策 3：CaptureRegistry 终局——单 owner 消息传递 vs 长期共享锁

> **修订（2026-08-24 窄 T0，用户拍板方案 A，见
> fa/pending_t0_capture_ownership.md）**：终局改为**混合模型**——
> 生命周期临界段（revoke/inflight/drain）adapter loop 独占（F2-3 批
> 2a）+ request 级归属（批 2b）；其余短态操作长期由显式锁保护；
> SessionPoisonRegistry 保持独立线程安全对象。批 2c 命令桥撤回（其
> 三 P1 与双所有权模型复杂度为撤回依据；5000 轮竞态压测为锁模型
> 实证）。"完整单 owner"若未来需要（F2-4 重放/并发扩张）须带证据
> 重新提案。

**要决定什么**：capture 状态（hooks/pending/versions/poison）的最终
所有权模型。

**现有代码事实**：轮次 13/14 已加短临界区锁并事务化 commit，当前正确；
但锁是九轮审查逐步叠出，每次新增字段都要重新推理锁覆盖；连续多轮竞态
的共同根源是共享可变状态跨三个执行域传播。

**方案**：
- **A（推荐）**：F2-3 时收敛单 owner——capture 状态归 adapter 线程
  独占，AsyncLoopThread 经线程安全命令/快照接口访问；与 request 级归属
  同批（反正要重写 stage/commit 键结构）。命令队列 vs 请求/响应 = T1。
- **B**：长期保留锁——省 2~3 天，但"锁覆盖完整吗"成为每轮审查永久税。

**推荐理由**：F2-3 是唯一顺路时机，错过成本翻倍。

**长期代价**：A 一次性 +2~3 天并重写部分双线程测试；B 是持续成本（已为
锁竞态修了四轮）。**可逆性**：B→A 越晚越贵。

**验收三项**（拍板后进 05 计划）：命令队列有界 + 反压传导；owner 死亡
fail-closed（挂起命令显式失败）；生产路径禁止绕过 owner 直改
CaptureRegistry（架构断言 + 测试）。

---

## 决策 4：拒绝率熔断按 fault domain 分流（穷举映射 + 安全三档）

**要决定什么**：全部失败类别到动作的穷举映射；安全事件分档；熔断状态
的运行期 owner、动作边界与重启语义。

**现有代码事实**：散落计数器无汇总；冻结契约：`attempted_blocked`
（拦截成功）是合法训练信号不扣分；`identity_conflict` 契约注释 = 镜像/
commit/bundle 血缘矛盾 → task_quarantine 归因；`contract_violation` =
run_halt 归因。

**方案（推荐）——三张精确映射表**（四审：表键必须是**枚举字面值**而非
描述性合并词，否则承诺的集合相等测试无法执行。实现时对每张表加
"表键集合 == 枚举集合"断言；未知/未来类别默认 run_halt）：

**表 1：RuntimeFailureCategory（勘误 3 后 14 值逐字）→ RecoveryAction**

| 枚举值 | 动作 |
|---|---|
| `model_proxy_failure` | 组件级熔断（model-call 域，circuit open 停止派发），持续超窗升级 run_halt；不隔离任务 |
| `inference_service_failure` | 组件级熔断（推理域），同上 |
| `sandbox_crash` | 组件级熔断（sandbox 域），同上 |
| `harness_crash` | 组件级熔断（harness 域），同上 |
| `worker_crash` | **前提（勘误 4）：仅限 RUNNING 后、已分类可恢复、且 F2-4 能力闸门已通过**——fence 旧 owner → `recovery_in_progress` → 走 D2 恢复；STARTING 失败与确定性故障仍 run_halt；恢复检查失败 terminal run_halt |
| `grading_infra_failure` | 组件级熔断（评分域）；不隔离任务 |
| `capture_incomplete` | 该 execution missing + capture 域计数；频发超窗升级组件熔断 |
| `token_alignment_failure` | 单发：该 execution missing + capture 域计数；频发超窗：run_halt |
| `staleness_exceeded` | 单条：BatchAdmission 判 present_but_not_admissible 排除本 batch；短窗比例升高：由 `TrainingRuntimeCoordinator` 反压/暂停更新（Monitor 不直接操作 trainer）；不隔离任务 |
| `security_violation` | 按表 3（security_impact 分档） |
| `identity_conflict` | task_quarantine（环境血缘矛盾：镜像/commit/bundle） |
| `contract_violation` | run_halt（含审计持久化失败、runtime 账目矛盾） |
| `cleanup_failure` | 容器进隔离队列 + reconciler；持续超窗升级组件熔断 |
| `runtime_quiescence_failure` | 该 execution missing + runtime 域计数；频发超窗升级组件熔断（勘误 3 新增值；屏障**未实现**不产本值——由启动闸门表达） |
| （未知/未来值） | run_halt |

**表 2：GradingFailureCategory（含本包新增值）→ reward/动作**

| 枚举值 | outcome / reward / 动作 |
|---|---|
| `infra_failure` | failed_to_grade / None / reward unavailable + admission 不通过 + 评分域计数（不倒写 completion——勘误 2） |
| `test_log_parse_failed` | failed_to_grade / None / 同上 |
| `patch_apply_failed` | unresolved / 0 / 模型负样本，不进熔断 |
| `tests_failed` | unresolved / 0 / 模型负样本，不进熔断 |
| `test_execution_timeout`（新增） | unresolved / 0 / 模型负样本——仅三条件全真可构造（D1a 第 2 条），否则按 `infra_failure` |

**表 3：SecurityImpact（载体 = `AntiCheatFinding` 新增结构化字段）→ SecurityAction**

| 枚举值 | 动作 |
|---|---|
| `attempted_blocked_no_effect` | present，继续评分；只进安全指标，不触发拒绝熔断 |
| `task_local_executed`（如 test tampering） | permanent_rejection，整组不训练 |
| `boundary_breach`（hidden verifier/secret 泄漏、sandbox escape、拦截器被绕过） | 立即 run_halt + artifact quarantine |

（模型真实失败 reward=0 不在三表内——它不是 failure category，是正常
样本，永不进熔断。）

**运行期 owner**：`FaultDomainMonitor` 由 RolloutManager state owner
持有，独占滚动计数与 breaker 状态；**重启后从 durable audit/outcome
重建；无法重建 → 保持 circuit open**（不清零续跑）。`RecoveryPolicy`
纯函数只做单事件分类；`AdmissionReport` 只记最终动作。

**备选（不推荐）**：统一单阈值（混类误伤）；映射留编码期（无数隐式 T0）。

**长期代价**：穷举表 + Monitor 持久化重建是真实实现量（FA-2B 批）。
**可逆性**：加类别便宜；改"某类是否隔离任务"= 训练分布变化，T0 重议。
**待定参数**：正式阈值数值 = T0（pre-RL/FA-5 校准后预注册）；统计口径
与黄线 = T1。

---

## 拍板方式

回复：`D1=A/B`（A = D1a 现在批 + D1b 延后）、`D2=A/B/C`、`D3=A/B`、
`D4=A/备选`（或"X 但改 Y"）。拍板后：05 计划按本文回写（引用式）→
codex 复审计划 → F2-0 起批。
