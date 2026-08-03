# FA-2A 决策包（v3：D1 拆两阶段；D1a/D2/D3/D4 现在拍，D1b 显式延后）

```text
status: draft（v3——codex 决策包二审 4 缺口 + 计时调查 + 外部配方证据矩阵）
owner_decision: （待拍板）
approved_at: （待定）
authoritative_plan_ref: （拍板后回写 05 计划；05 计划已去重，只引用本文）
```

> 外部证据统一入口：`docs/harness_improve/external_paper_references/
> agentic_rl_training_recipe_evidence_matrix.md`（codex 调查 19 份报告 +
> SA-SWE/DeepSWE/K3/Endless Terminals 等）。计时调查（P3 实测 97% 中位
> 墙钟在 harness_run 大桶、四个时钟起点错位、5 条 exit=-1 轨迹超预算
> 181~480 秒）见 `s2/codex_reviews.md` 归档。关键结论：**没有公开工作
> 给出可照抄的完整配方，rh2 是有证据支持的组合设计**；超时语义必须拆成
> group_membership / reward_disposition / gradient_disposition 三个
> 正交决定（SA-SWE 实证：horizon 轨迹可"保留组统计、只屏蔽自身梯度"，
> 不是缺员）。

---

## 决策 1：超时/预算终止的架构契约（D1a 现在拍）与训练处置（D1b 延后拍）

### 为什么拆两阶段

v2 把"episode 超时"当一种统一结果、在"全拒"与"截断评分"里二选一——
外部证据表明这个问题拆得不够细：公开系统的处置互相冲突（SA-SWE 保组
统计屏蔽梯度 / Nemotron 屏蔽 loss / Composer 2 未见 overlong masking
收益 / K3 暂停续跑 + token 预算罚分 / Endless Terminals 对 wall timeout
与 turn 耗尽用不同评分流程），**不存在可抄的"最佳做法"**；而我们自己的
计时现状（97% 墙钟在混合大桶、预算时钟与墙钟错位、基础设施等待计入
deadline）还不足以区分"策略慢"和"基建慢"。所以：**现在拍架构契约
（D1a，让两种语义都能表达、都有事实可查），pre-RL 诊断后拍训练处置
（D1b，选 profile 和数值）**。

### D1a（现在拍板）：终止分类、双时钟、静止屏障、三正交处置

1. **termination_kind 分三族**（单向映射 termination_kind →
   completion_class → RuntimeFailureCategory → disposition；未列类别
   fail-closed）：

   ```text
   策略 horizon 族（可复现、可作为截断有效候选）：
     task_token_budget_exhausted   （策略 token 预算耗尽）
     max_turns_exhausted           （slime 429 turn cap——v2 枚举漏项）
     context_limit_reached
   看门狗族（宽松安全网，首训不作为 reward 信号）：
     hard_wall_timeout
   基础设施族（缺员，reward=None，进对应 fault domain 计数）：
     inference_timeout / sandbox_rpc_timeout / update_wait_timeout /
     grading_timeout / harness_crash / api_failure / sandbox_failure
   正常族：completed / owner_cancelled
   ```

   `policy_update_abort` 不是终止类别（attempt 内透明重生成事件，仅
   max_regenerations_exceeded 升格为基础设施族失败）。

2. **双时钟**：每 execution 记录 `wall_clock_seconds` 与
   `chargeable_execution_seconds`（至少扣除权重更新窗口等待与系统反压
   等待）；预算判定用 chargeable 时钟。理由（P3 实测）：proxy 等待、
   推理阻塞都在耗墙钟——用墙钟判"策略超时"会把基建故障训练成策略失败。

3. **Runtime 级静止屏障**（v2 的"终止进程组"不充分——CC/工具可再起新
   session 或后台进程）：

   ```text
   撤销 adapter session（HTTP 层拒绝新模型请求）
   → 终止 sandbox execution scope（容器/cgroup 级，不只进程组）
   → 等待模型调用与文件写入的 owner 侧确认归零
   → 冻结不可变 workspace snapshot
   → 只对冻结副本评分
   ```

   digest 连续不变只是探针不是证明；Runtime 无法确认静止 → 缺员，
   **不允许配置开关强行评分**。

4. **三正交处置进现有契约**（不新增报告对象）：
   - `RolloutAttemptOutcome` 增：termination_kind / termination_phase /
     quiescence_status / frozen_snapshot_ref / capture_completeness；
   - `PromptGroupAdmissionReport` 增：group_membership /
     reward_disposition / gradient_disposition /
     termination_policy_profile；
   - 环境层只记事实，训练策略 = 纯映射（profile）产出三 disposition。
   - **FA-3/FA-4 契约影响（注记，随 D1a 一并确认）**：
     `scored_horizon_masked` 需要"reward-only member"形态（组统计含它、
     loss 无它的 token）——当前 `normalize_rewards_by_group` 零 token
     fail-closed 需按 profile 放行该形态；与 DIS 分母决策耦合，FA-4 前
     决策包一并处理。

5. **命名 profile（禁布尔开关自由组合）**：

   ```text
   strict_missing_v1          所有超限一律缺员（整组不进在线更新）
   scored_horizon_masked_v1   可评分策略 horizon：组统计保留、自身梯度屏蔽
   true_resume_v1             暂停续跑到完成（未来；依赖可恢复沙箱）
   ```

   FA 开发/诊断期 = `audit_only`（只记事实不做处置）；正式训练必须显式
   选 profile 并记录配置 digest，`rh2_formal_training_allowed` 在
   profile/阈值/组语义预注册前保持关闭。

6. **真缺员清单不变**（任何 profile 下都整组不进在线更新）：半截模型
   响应、capture/logprob/version 账目不完整、workspace 无法静止、基建
   失败重试耗尽、安全泄漏/身份矛盾/artifact 污染、staleness 超限。
   固定 n 不变——**不做静默 n-1**（公开实现均固定 n/K，无可靠反例）。

### D1b（pre-RL 诊断后拍板）：profile 选择与数值

诊断设计：50~100 题 × n=8，记录原始 monotonic 区间（environment_
materialize / sandbox_start / harness_install / model_queue /
model_generation / tool_execution / sandbox_idle_while_model /
quiescence_and_snapshot / grading_* / group_wait / admission_wait）+
turn_count / generated_tokens / termination_kind / group_survival /
trainer_wait_ratio / policy_version_lag。**成本注记（T0 面）**：400~800
条 rollout，按 P3 中位 633s、并发 8~16 估 **7~18 GPU 小时**——建议与
FA-5 短租合并成一次租期（合并后总租时上调），拍 D1b 时一并确认预算。

诊断后决定：32K/50-turn 是否合适；watchdog 取成功轨迹 P90/P95 还是分
难度桶；是否启用 scored_horizon_masked_v1；超时对组存活率（参考：单员
5% 缺失率下 0.95^8=66.34% 完整组存活）与难度分布的影响；reserve 与
队列水位。

**本项拍板选项**：
- **A（推荐）**：D1a 契约按上文全部采纳；D1b 显式延后到 pre-RL 诊断后。
- **B**：不拆阶段，现在直接选 strict_missing_v1 跳过诊断——最快，但
  确定性长度/难度偏置且浪费（66% 组存活）。

---

## 决策 2：F2-4 崩溃恢复与 replay identity 语义

**要决定什么**：RolloutManager state-owner 进程重启后，已取出未训练的
组怎么恢复；replay 身份与提交权怎么定；恢复承诺到什么强度。

**范围与事实**（v2 已定部分不重复）：崩溃 = RolloutManager state-owner
重启；首版同节点；pending checkpoint 是新增持久化面；slime cursor 先推
后存（data_source.py:90/127）。

**方案 A（推荐，v3 收紧版）**——在 v2 五条（顺序不变量 / 状态集 /
四层身份 / 恢复承诺 / crash-point 探针）之上补四条：

1. **单一 checkpoint owner**：pending reservation 与 slime cursor 发布
   由**同一个 owner** 控制（cursor save 只许经它走）——否则任何旁路
   保存路径都能越过"pending 先 durable"的顺序不变量。
2. **ACK 语义如实**：`ACKED` = 训练后端已接受 submission（handoff
   acknowledged），**不是** optimizer 已执行；slime 当前若无 durable
   submission ACK，账面就写 handoff，不暗示 batch 不会丢。
3. **replay 胜出规则**：`recovery_epoch` + fencing_token——只有当前
   physical attempt 能提交 canonical outcome；旧 attempt 的迟到结果只进
   审计，不进训练面。
4. **generation 方向修正 + manifest 绑定**：`pending_generation >
   cursor_generation` 是**安全的可重放状态**（pending 新于 cursor，
   重放即可）；**反向**（cursor 已跳过而 pending 缺失）才是不可恢复
   矛盾 fail-closed。manifest 绑定 dataset revision / task & bundle
   digest / cursor & epoch / sampling 配置——防同一 cursor 在漂移数据
   上指向另一任务。

**方案 B/C**：同 v2（lease/ACK 改造过重；裸 at-least-once 否决）。

**长期代价/可逆性**：同 v2；单 owner 约束把 D2 与 D3 的架构方向绑定
（同一 state-owner 思想），实施在 F2-4 批。

---

## 决策 3：CaptureRegistry 终局——单 owner 消息传递 vs 长期共享锁

**要决定什么**：capture 状态（hooks/pending/versions/poison）的最终
所有权模型。

**现有代码事实**：轮次 13/14 已加短临界区锁并事务化 commit，当前正确；
但锁是九轮审查逐步叠出来的，每次新增字段都要重新推理锁覆盖，连续多轮
竞态问题的共同根源就是共享可变状态跨三个执行域传播。

**方案**：
- **A（推荐）F2-3 时收敛单 owner**：capture 状态归 adapter 线程独占，
  AsyncLoopThread 经线程安全命令/快照接口访问；与 request 级归属同批做
  （反正要重写 stage/commit 键结构）。单 owner 之下用命令队列还是
  请求/响应 = T1。
- **B 长期保留锁**：省 2~3 天，但"锁覆盖完整吗"成为每轮审查的永久税，
  且状态面随 FA-2B/FA-3 继续膨胀。

**推荐理由**：F2-3 是唯一顺路收敛时机，错过成本翻倍。

**长期代价**：A 一次性 +2~3 天、重写部分双线程测试；B 是持续成本
（本项目已为锁竞态修了四轮）。

**可逆性**：A→B 无意义；B→A 越晚越贵。

**验收三项**（拍板后进 05 计划）：命令队列有界 + 反压传导；owner 死亡
fail-closed（挂起命令显式失败）；生产路径禁止绕过 owner 直改
CaptureRegistry（架构断言 + 测试钉住）。

---

## 决策 4：拒绝率熔断按 fault domain 分流（v3：穷举映射 + 安全三档）

**要决定什么**：全部失败类别到动作的**穷举**映射、安全事件分档、熔断
状态的运行期 owner 与重启语义。

**现有代码事实**：同 v2（散落计数器无汇总；attempted_blocked 冻结契约；
identity_conflict 契约注释归 task_quarantine）。

**方案（推荐）——穷举映射表**（未列/未来类别默认 **run_halt**，禁止
编码时临时决定）：

| 类别 | 动作 |
|---|---|
| contract_violation / 审计持久化失败 / runtime 身份·账目矛盾 / token_alignment_failure 频发超窗 | run_halt |
| worker_crash | run_halt（= state-owner 域，走 D2 恢复） |
| proxy / inference_service / sandbox / harness 基建故障 | 组件级熔断（circuit open 停止派发），持续超窗升级 run_halt；不隔离任务 |
| grading_infra_failure | 组件级熔断（评分域）；不隔离任务 |
| capture_incomplete / token_alignment_failure 单发 | 该 execution 缺员 + capture 域计数 |
| identity_conflict（镜像/commit/bundle 血缘） | task_quarantine |
| 环境包确定性损坏 | task_quarantine |
| cleanup_failure | 容器进隔离队列 + 计数（reconciler 处理）；持续超窗升级组件熔断 |
| staleness_exceeded | 反压/暂停权重更新协调；不隔离任务 |
| 模型真实失败（reward=0） | 正常样本，不进熔断 |
| **安全三档（v3 细分）** | `attempted_blocked` 无泄漏/副作用 → present 继续评分，只进安全指标；task-local `executed`（如 test tampering）→ permanent_rejection 整组不训练；**边界击穿**（hidden verifier/secret 泄漏、sandbox escape、拦截器被绕过）→ **立即 run_halt + artifact quarantine**（否则 hidden verifier 已泄漏时系统只丢一组数据继续跑） |
| 未知/未来类别 | run_halt（默认收紧） |

**运行期 owner（v3 补重启语义）**：`FaultDomainMonitor` 由 RolloutManager
state owner 持有，独占滚动计数与 breaker 状态；**重启后从 durable
audit/outcome 重建；无法重建 → 保持 circuit open**（不清零计数继续
训练）。`RecoveryPolicy` 纯函数只做单事件分类；`AdmissionReport` 只记
最终动作。

**备选（不推荐）**：统一单阈值（误伤混类）；或映射留到编码期（每处
临时决定 = 无数隐式 T0）。

**长期代价**：穷举表 + Monitor 持久化重建是真实实现量（FA-2B 与
assembler 同批）；换来的是"任何失败都有预定动作"的确定性。

**可逆性**：加类别便宜；改"某类是否隔离任务"= 训练分布变化，T0 重议。

**待定参数**：正式阈值数值 = T0（FA-5/pre-RL 校准后预注册清单另批）；
统计口径与黄线 = T1。

---

## 拍板方式

回复四项：`D1=A/B`（A = D1a 契约现在批 + D1b 延后）、`D2=A/B/C`、
`D3=A/B`、`D4=A/备选`（或"X 但改 Y"）。拍板后：05 计划更新（引用式，
不再复制正文）→ codex 复审计划 → F2-0 起批。
