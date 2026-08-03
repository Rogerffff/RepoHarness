# FA-2A 决策包（v3.1：自包含版——只读本文即可完成四项决策）

```text
status: draft（v3.1——codex 三审 13 条 + true_resume/K3 语义澄清全部采纳）
owner_decision: （待拍板：D1=A/B，D2=A/B/C，D3=A/B，D4=A/备选）
approved_at: （待定）
authoritative_plan_ref: （拍板后回写 05 计划；05 计划只引用本文，不复制正文）
```

> 外部证据入口：`docs/harness_improve/external_paper_references/
> agentic_rl_training_recipe_evidence_matrix.md`。审查历史与计时调查
> 归档：`s2/codex_reviews.md`。本版验收条件（codex 三审）：不依赖
> v2/git 历史可完成决策；"7 条正常 + 1 条 horizon-masked"可由 member
> 级契约表达；provenance mask / 算法 mask / batch 计数不混用；全部
> termination/failure/security 类别有唯一动作；D2 状态无含义重叠；
> 05 计划不再维护第二份决策事实。

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
     ——首版恒按非策略结果处理（missing），任何 profile 不得把它评分
   控制面族：owner_cancelled
     ——控制面取消，默认不产生 reward（不属"正常完成"）
   基础设施族（missing，reward=None，进对应 fault domain 计数）：
     inference_timeout / sandbox_rpc_timeout / update_wait_timeout /
     grading_infra_timeout / harness_crash / api_failure /
     sandbox_failure / model_proxy_failure
     ——model_proxy_failure 显式承接 max_regenerations_exceeded
     （D-FA-3 重生成耗尽；重生成本身不是终止事件）
   正常族：completed
   ```

   **推导不是线性链**，disposition 由多个事实共同决定：

   ```text
   termination fact + capture/quiescence/grading facts
     → completion_class + （可选）failure_category
     → 选定 profile（组/run 级配置）
     → member disposition（member 级结果）
   ```

2. **评分超时拆两类**（不并入一个"grading timeout"）：

   ```text
   grading_infra_timeout      → reward=None，missing（基建族）
   test_execution_timeout     → 仅当 clean grader 已正常启动、测试预算
                                确定性、且超时可归因于 agent patch（如
                                patch 引入死循环）时 reward=0（模型真实
                                失败）；无法归因 → 仍按 infra，reward=None
   ```

3. **双时钟 = 区间并集口径**。保存原始事实而非派生数：

   ```text
   wall_start / wall_end
   non_chargeable_intervals: [{start, end, reason, measurement_source}]
   chargeable_execution_seconds = 同一 owner 对区间做并集后派生
   （重叠暂停不得重复扣除）
   ```

   首版只把**权重更新暂停**与**系统反压等待**列为 non-chargeable，其他
   阶段先观测不扣除。预算判定用 chargeable 时钟（否则基建等待被训练成
   策略失败）。

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

7. **三态区分**（staleness 是消费时刻的准入决定，不倒写成"rollout 没
   产生"）：

   ```text
   missing                    execution 事实未完整产生
   present_but_not_admissible 事实完整，但 staleness 等使其不能进当前 batch
   permanent_rejection        事实完整，但安全/契约禁止训练
   ```

8. **profile 是穷举映射，audit_only 是 enforcement mode**：

   ```text
   profile ∈ { strict_missing_v1, scored_horizon_masked_v1 }
     ——每个 profile 必须对全部 termination_kind 给出唯一 disposition
       （含 horizon 族/看门狗/控制面/各类 infra/无法静止），缺项 = 配置
       非法拒绝启动
   enforcement_mode ∈ { audit_only, enforce }
     ——FA 开发/诊断期 = audit_only（只记 disposition 不执行剔除）；
       正式训练 = enforce + profile 与配置 digest 预注册
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

11. **真缺员清单**（任何 profile 下整组不进在线更新；固定 n，不做静默
    n-1）：半截模型响应；capture/logprob/version 账目不完整；workspace
    无法静止；基建失败重试耗尽；安全泄漏/身份矛盾/artifact 污染。

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

诊断后决定：32K/50-turn 是否合适；watchdog 取成功轨迹 P90/P95 或分
难度桶；是否启用 scored_horizon_masked_v1（参考：单员 5% 缺失率下
0.95^8=66.34% 完整组存活）；FA-4 算法五项（上文第 10 条）。

**拍板选项**：
- **A（推荐）**：D1a 契约按上文采纳；D1b 显式延后。
- **B**：跳过诊断直接 strict_missing_v1——最快，但确定性长度/难度偏置。

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

**方案（推荐）——穷举映射**（映射表逐字覆盖全部 `RuntimeFailureCategory`
枚举值并加**集合相等测试**；未知/未来类别默认 run_halt）：

| 类别 | 动作 |
|---|---|
| contract_violation / 审计持久化失败 | run_halt |
| **worker_crash** | **fence 旧 owner → `recovery_in_progress`（暂停消费）→ 走 D2 恢复；恢复检查失败才 terminal run_halt**（不是一步 halt） |
| token_alignment_failure | 单发：该 execution missing + capture 域计数；频发超窗：run_halt |
| proxy / inference_service / sandbox / harness 基建故障 | 组件级熔断（circuit open 停止派发），持续超窗升级 run_halt；不隔离任务 |
| grading_infra_failure（含 grading_infra_timeout） | 组件级熔断（评分域）；不隔离任务 |
| capture_incomplete | 该 execution missing + capture 域计数 |
| identity_conflict（环境血缘） | task_quarantine |
| 环境包确定性损坏 | task_quarantine |
| cleanup_failure | 容器进隔离队列 + reconciler；持续超窗升级组件熔断 |
| **staleness_exceeded** | **单条：BatchAdmission 判 present_but_not_admissible 排除本 batch**；短窗比例升高：由 `TrainingRuntimeCoordinator` 执行反压/暂停更新（**Monitor 不直接操作 trainer**）；不隔离任务 |
| test_execution_timeout（可归因 agent patch） | reward=0 正常样本，不进熔断 |
| 模型真实失败（reward=0） | 正常样本，不进熔断 |
| security（三档，凭结构化 `security_impact` 字段确定性分档） | `attempted_blocked` 无泄漏/副作用 → present，只进安全指标；task-local `executed`（如 test tampering）→ permanent_rejection 整组；**边界击穿**（hidden verifier/secret 泄漏、sandbox escape、拦截器被绕过）→ 立即 run_halt + artifact quarantine |
| 未知/未来类别 | run_halt |

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
