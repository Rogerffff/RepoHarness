# FA-2A 决策包（四项 T0，用户拍板后才开工）

```text
status: draft（v2——codex 决策包审查 7 findings + 9 补充全部采纳后的修订版）
owner_decision: （待拍板）
approved_at: （待定）
authoritative_plan_ref: （拍板后回写 05 计划对应小节）
```

> 按 `collaboration-protocol.md` §2 决策包格式起草；v2 修订依据
> `s2/codex_reviews.md` 归档的决策包审查（5 阻塞 + 2 一般 + T0 完整性
> 扫描）。流程：本文 → 用户逐项拍板 → Claude 只改 05 计划 → codex
> 复审计划 → 按 F2-0/F2-1/F2-2/F2-3 小批实施。显式不在本包内：DIS
> 分母档位（FA-4 前另出决策包）；overlap 挡板（已定案，闸门跟踪）；
> 正式熔断阈值数值（FA-5 校准后预注册，另出清单）。

---

## 决策 1：episode 超时轨迹的终止分类与训练语义

**要决定什么**：CC 因 episode 时间预算耗尽被终止的轨迹，是"作废缺员"
还是"截断但有效、按真实评分拿 reward"？

**现有代码事实**（v2 补充加粗项）：slime 超时返回
`EXIT_TIME_BUDGET_EXCEEDED = -1`（sandbox.py:63），但**只是停止轮询——
没有 kill/wait，经 setsid 分离的 CC 进程组可能仍在运行**；而 rh2 在容器
清理**之前**执行 drain/capture/评分/Gate（generate.py 主链）。即：不加
硬条件的"截断评分"会在 CC 还在改文件/发请求时评分（竞态 patch、评分
污染、账目漂移）。当前 `reject_on_nonzero_harness_exit=True` 把超时全拒。
P3 实测时长方差大，超时不是罕见事件。

**方案**：

- **A（推荐）分类处理 + 静止三硬条件**：
  1. 新增独立 **`termination_kind`** 枚举（"为什么停止"）：completed /
     episode_time_limit / owner_cancelled / harness_crash / api_failure /
     sandbox_failure。**单向映射**到既有分类，不并入也不复用：
     `termination_kind → completion_class → RuntimeFailureCategory →
     reward/eligibility 语义`（映射集中一处，加类别只改枚举+映射）。
     **`policy_update_abort` 不是终止类别**——它是 ModelCallAttempt 内部
     被透明重生成的事件（D-FA-3），只有重生成耗尽
     （max_regenerations_exceeded）才升格为 episode 失败。
  2. `episode_time_limit` 按**截断但有效**处理（进评分、拿真实 reward），
     前提是**静止序列完成**：
     ```text
     主动终止整个 harness process group
     → 等待并确认 quiescence（无新文件写入、无新模型请求）
     → 冻结 workspace/patch snapshot
     → 只对冻结快照评分
     ```
     quiescence 无法确认 → 仍作废缺员。另两条既有守卫不变：capture
     交付账完整闭合、无半截模型响应。
  3. 验收探针（experiment-required，FA-5）：超时后子进程持续写文件的
     对抗场景——终止确认后文件 digest 不再变化、无新增模型请求、评分
     只读冻结快照。
- **B 维持全拒**：所有非 completed 一律缺员——零实现，但长任务被系统性
  剔除（确定性长度偏置）。
- **C 全收**：无条件进评分——CC 未静止时评分被污染，不可取（v2 注：
  没有静止序列的 A 实际上就是 C 的隐藏版）。

**外部证据（K3 技术报告）**：frontier 实践不把"没跑完"当废样本——K3
partial rollout 把未完轨迹暂停下一迭代**续跑**；Reasoning Effort RL 里
超 token 预算的轨迹拿 **reward=-1**（超限是训练信号）。true-resume 路径
（05 计划 §6 递延项 7）确认为成熟方向，但依赖可恢复沙箱基建，维持递延。

**长期代价**：A 需要 termination_kind 贯穿 + 静止序列实现（FA-2A +2~3
天，比 v1 估计多 1 天——静止确认是新增面）；B 零实现但 FA-5 后大概率
返工。

**以后还能改吗**：加终止类别便宜（枚举+映射一处）；"超时算不算有效
样本"改判使前后训练数据不可比——正式训练前必须定死。

---

## 决策 2：F2-4 崩溃恢复与 replay identity 语义

**要决定什么**：rollout actor 崩溃重启后，已取出未训练的组怎么恢复？
公开 execution id 在 replay 时复用还是新生成？恢复承诺到什么强度？

**范围定义（v2 明确）**："崩溃"= **RolloutManager state-owner 进程重启**。
CC / sandbox / adapter 线程 / SGLang 单独故障属各自 fault domain（决策
4），只有升级为整个 RolloutManager 重启才进入本决策。**首版保障范围 =
同节点 actor 重启**（pending store 在本地磁盘；当前部署为单机 8 卡）；
跨节点恢复需要共享持久存储，列为后续升级项不在首版承诺。

**现有代码事实**（v2 补充加粗项）：slime `get_samples()` **立即推进**
`sample_offset`（data_source.py:90），cursor 之后才由独立 `save()`
持久化（data_source.py:127）；RH2 队列/在途/结余不持久化——当前崩溃 =
预取组永久跳题（codex 探针：batch=1 时预取 7 组全丢）。**RH2 pending
checkpoint 是 FA-2A 将新增的持久化面，目前不存在**（既有 model-call
audit 的 snapshot/写/ack 只是审计事务，不是恢复 checkpoint）。

**方案**：

- **A（推荐，v2 收紧版）双 checkpoint + 顺序不变量 + 四层身份**：
  1. **提交顺序不变量**（v1 "两个 checkpoint 的并集"没有回答"cursor 已
     写、pending 未写、此刻崩溃"——预取组照样丢；v2 定死）：
     ```text
     pending manifest 先 durable
     → 才允许发布会跳过这些 execution 的 cursor checkpoint
     → 两者携带同一 checkpoint_generation
     → 恢复时交叉校验；pending 落后于 cursor = 不可恢复矛盾，fail-closed
     ```
     存储格式（JSON/SQLite/WAL）= T1，本包只定语义。
  2. **pending 状态集**：RESERVED / DISPATCHED / RUNNING /
     OUTCOME_DURABLE / GROUP_READY / HANDED_OFF / ACKED。首版对
     DISPATCHED/RUNNING 的恢复 = **从干净环境 replay**，不承诺
     mid-episode resume（那需要沙箱快照基建，见 K3/AgentEnv 笔记）。
  3. **四层身份**（v1 只有 replay-stable 公开 id 一层——旧 attempt 的
     partial artifact/审计会与新 replay 共享事实键，v2 拆开）：
     ```text
     rollout_execution_id   跨 replay 稳定（逻辑执行身份，去重键）
     physical_attempt_id    每次实际重放都不同（artifact/审计的事实键）
     model_call_attempt_id  同一 physical attempt 内的模型调用重生成序号
     session_auth_capability 每次 physical attempt 新生成，旧的撤销
     ```
  4. **恢复承诺（v2 如实降级——v1 "去重保证不被训练两次"表述过强）**：
     ```text
     rollout execution     = at-least-once
     artifact/admission/submission = 幂等可去重
     optimizer step exactly-once   = 首版不承诺
     （trainer 在 optimizer step 后、ACK 前崩溃的窗口无法端到端排除）
     ```
  5. 验收探针（experiment-required）：在 pending 写前/写后、cursor 写前/
     写后逐点注入 crash，重启后每个逻辑 execution 要么恢复要么明确去重，
     零静默丢失。
- **B 完整 lease/ACK 改造 data source**：语义最强，首版过重（不建议）。
- **C 裸 at-least-once + 去重、无 cursor 回退**：预取丢失组永远取不回，
  否决。

**长期代价**：A 的 pending checkpoint 是新持久化面（写入时机与原子性
要设计，探针成本真实）；A→B 可平滑升级。**身份格式（第 3 条）一旦定下
很贵改**——它决定 F2-1 的编码，本项必须先拍。

---

## 决策 3：CaptureRegistry 终局——单 owner 消息传递 vs 长期共享锁

（v1 内容不变：现状锁正确但逐轮叠出、每次改动重推锁覆盖；**A（推荐）**
F2-3 时收敛单 owner（与 request 级归属同批），**B** 长期保留锁。codex
审查确认可直接选 A，不新增 T0——单 owner 之下用命令队列还是请求/响应
属 **T1**。）

**v2 新增三条验收项**（05 计划 FA-2A 落地时带上）：

```text
命令队列有界 + 反压传导（不许无界堆积命令）
owner 线程死亡 → fail-closed（挂起的命令显式失败，不静默等死）
生产路径禁止绕过 owner 直接修改 CaptureRegistry（架构断言/测试钉住）
```

---

## 决策 4：拒绝率熔断按 fault domain 分流

**要决定什么**：按什么分类统计拒绝率、各类触发什么动作、谁拥有熔断
状态。

**现有代码事实**：各防线只有散落计数器，无汇总无告警。**既有冻结契约**
（v2 修正的依据）：eligibility 维度 5 与 gate 明确 `attempted_blocked`
（拦截成功）**不扣分、是合法训练信号**；`executed` 级才失败。
fa_runtime 注释：`identity_conflict` = 镜像/base commit/bundle 血缘矛盾
（**task_quarantine 归因**）；`contract_violation` = 账目矛盾（run_halt
归因）。

**方案（v2 修正版六分类，推荐采纳）**：

| fault domain | 动作 |
|---|---|
| contract_violation / 审计持久化失败 / **runtime 身份·账目矛盾** | 立即 run_halt |
| 模型服务 / sandbox / capture 基建故障 | **组件级熔断**：停止向该组件派发（circuit open），持续超窗升级 run_halt——不隔离任务 |
| **environment_lineage_conflict**（镜像/commit/bundle 血缘矛盾） | task_quarantine（v1 误并入 run_halt，v2 按契约注释拆分） |
| 环境包确定性损坏 | task_quarantine |
| 模型真实失败（reward=0） | 正常样本，不进熔断 |
| **安全事件（v1 表述错误，v2 按冻结契约修正）**：`attempted_blocked` 且无泄漏/副作用 → **present，继续评分，不触发拒绝熔断**（"尝试→被拦→恢复"是要保留的安全行为分布）；`executed`/泄漏/篡改 → permanent_rejection，整组不得训练 | 分档处理 |
| staleness 偏高 | 反压/暂停权重更新协调，不隔离任务 |

**运行期 owner（v2 新增——纯函数无法维护滑动窗口）**：

```text
RecoveryPolicy（纯函数）      单事件分类：Outcome → fault domain + 动作建议
FaultDomainMonitor（actor 级） 独占滚动计数、窗口统计、breaker 状态机
PromptGroupAdmissionReport    只记录最终动作，不拥有跨组状态
```

**外部证据（K3）**："staleness 偏高→反压"与 K3 的 KV 压力感知
auto-throttling 同构。

**待定参数**：正式阈值 = T0（FA-5 校准后预注册清单另批）；统计方式与
黄线 = T1。**耦合**：本项依赖决策 1 的 termination_kind 先在。

---

## 拍板方式

四项各自回复 A/B/…（或"A 但改 X"）。全部定案后：Claude 更新 05 计划
（含把当前标记为 proposal_pending 的段落转正）→ codex 复审计划 →
F2-0（代码提升）起批实施。
