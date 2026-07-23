# FA-2A 决策包（四项 T0，用户拍板后才开工）

> 按 `collaboration-protocol.md` §2 决策包格式起草。流程：本文 → codex
> 设计审查 → 用户逐项拍板 → Claude 只改 05 计划 → codex 复审计划 →
> 按 F2-0/F2-1/F2-2/F2-3 小批实施。显式不在本包内：DIS 分母档位（FA-4
> 接线前另出决策包）；overlap 挡板（已定案，闸门跟踪，非选择题）。

---

## 决策 1：episode 超时轨迹的终止分类与训练语义

**要决定什么**：CC 因 episode 时间预算耗尽被终止的轨迹，是"作废缺员"
还是"截断但有效、按真实评分拿 reward"？

**现有代码事实**：slime 超时返回 `EXIT_TIME_BUDGET_EXCEEDED = -1`
（`reference/slime/slime/agent/sandbox.py:60`），是主路径正常终止；当前
`reject_on_nonzero_harness_exit=True`（glue 默认随正式链联动）会把它们
全拒。P3 实测 coding agent 时长方差大，超时不会是罕见事件。

**方案**：

- **A（推荐）分类处理**：定义结构化终止枚举（completed /
  episode_time_limit / owner_cancelled / policy_update_abort /
  harness_crash / api_failure / sandbox_failure）。`episode_time_limit`
  在三个条件同时满足时按**截断但有效**处理（进评分、拿真实 reward）：
  capture 交付账完整闭合、无半截模型响应、workspace 可评分；任一不满足
  仍作废。其余类别照旧缺员。
- **B 维持全拒**：所有非 completed 一律缺员——实现最简单，但长任务被
  系统性剔除，模型会"学会不做长任务"（确定性长度偏置）。
- **C 全收**：超时轨迹无条件进评分——会把 capture 不完整的坏轨迹放进
  训练（正确性风险），不可取。

**推荐理由**：A 是 codex 与 Claude 一致推荐——超时拿低 reward 是真实的
学习信号（"没做完 = 差"），作废则是删除信号；三条件守卫保住正确性底线。

**长期代价**：A 需要终止枚举贯穿 outcome/审计/熔断分类（FA-2A 实现量
+1~2 天）；B 零实现但训练分布有确定性偏置，且 FA-5 实测后大概率要返工。

**以后还能改吗**：枚举本身加类别便宜；但"超时算不算有效样本"改判会
使前后训练数据不可比——正式训练开跑前必须定死。

---

## 决策 2：F2-4 崩溃恢复与 replay identity 语义

**要决定什么**：rollout actor 崩溃重启后，已从 data source 取出但未训练
的组怎么恢复？公开 execution id 在 replay 时复用还是新生成？

**现有代码事实**：worker 预取（codex 探针：batch=1 时预取 7 组）；slime
`RolloutDataSource.save()` 只存已前进的 cursor，RH2 队列/在途/结余不
持久化——当前崩溃 = 预取组永久跳题。恢复语义已定案 halt→整 actor 重启。

**方案**：

- **A（推荐，codex 轮次 14 首版方案）**：slime data-source checkpoint +
  与 rollout_id 绑定的 RH2 pending-state checkpoint + **replay-stable
  公开 execution id**（重启后同一逻辑执行复用同一公开 id）+ 每次真实
  会话重新生成私有 capability + 下游按 execution_id/batch_id 幂等去重。
  语义 = at-least-once + 可去重：极端时序下同一组可能被执行两次，靠
  去重保证不被训练两次。
- **B 完整 lease/ACK 改造 data source**：只有确认训练后才推进 durable
  cursor——语义最强（exactly-once 近似），但要改造 slime data source，
  首版过重（codex 明确不建议）。
- **C 裸 at-least-once + 去重、无 cursor 回退**：实现最省，但已预取而
  丢失的组**永远取不回来**（不是重复而是缺失），训练分布静默丢题——
  codex 明确否决。

**推荐理由**：A 用两个 checkpoint 的并集覆盖了 C 的丢失缺口，又不动
slime 内部；replay-stable 公开 id 让审计与去重有稳定键。

**长期代价**：A 的 pending-state checkpoint 是新持久化面（写入时机、
原子性都要设计）；若未来发现 at-least-once 去重不够（如部分训练的组），
可再升级到 B——A 是 B 的子集，不是死路。

**以后还能改吗**：A→B 可平滑升级；id 语义（replay 复用公开 id）一旦
定下**很贵改**——它决定 F2-1 的身份格式，这正是本项必须先于 F2-1 编码
定案的原因。

---

## 决策 3：CaptureRegistry 终局——单 owner 消息传递 vs 长期共享锁

**要决定什么**：capture 状态（hooks/pending/versions/poison）最终收敛为
"单线程 owner + 消息传递"，还是长期保留当前的跨线程共享 + 短临界区锁？

**现有代码事实**：轮次 13/14 已给全部共享容器加短临界区锁并事务化
commit，911 测试全绿——**当前是正确的**。但锁是逐轮叠出来的（codex：
"连续几轮竞态问题的共同根源是共享可变状态跨三个执行域传播……停止叠锁，
开始收敛所有权"）；每次新增字段都要重新推理锁覆盖。

**方案**：

- **A（推荐）F2-3 时收敛单 owner**：capture 状态全部归 adapter 线程
  own；AsyncLoopThread 经线程安全命令/快照接口访问（请求-响应或队列）。
  与 F2-3 的 request 级归属同批做（反正要重写 stage/commit 键结构）。
- **B 长期保留锁**：不再重构，接受"每次改动重新推理锁覆盖"的持续成本
  与竞态风险——短期省 2~3 天，长期每轮审查都要付"锁覆盖完整吗"的税。

**推荐理由**：F2-3 本来就要动 capture 的键结构与生命周期，是收敛所有权
的唯一顺路时机；错过后单独重构的成本翻倍。

**长期代价**：A 一次性 +2~3 天且要重写部分双线程测试；B 的成本是持续
性的（本项目已为锁竞态修了四轮）。

**以后还能改吗**：能，但只会更贵——状态面还会随 FA-2B/FA-3 继续长大。

---

## 决策 4：拒绝率熔断按 fault domain 分流

**要决定什么**：按什么分类统计拒绝率、各类阈值触发什么动作（run_halt /
组件暂停 / task_quarantine / 不熔断）。

**现有代码事实**：各防线只有散落计数器，无汇总无告警——fail-closed 的
系统性问题目前会伪装成损耗（缺员率升高但训练继续）。

**方案（codex 轮次 14 六分类，推荐原样采纳）**：

| fault domain | 动作 |
|---|---|
| contract_violation / 审计持久化失败 / 身份矛盾 | 立即 run_halt |
| 模型服务 / sandbox / capture 基建故障 | 组件级暂停或 run_halt，**不隔离任务** |
| 环境包确定性损坏 | task_quarantine |
| 模型真实失败（reward=0） | 正常样本，不进熔断 |
| 模型触发安全策略 | 拒绝 execution/group，默认不隔离任务 |
| staleness 偏高 | 反压/暂停权重更新协调，不隔离任务 |

载体：现有 `RolloutAttemptOutcome` + 纯函数 `RecoveryPolicy` + 写入
`PromptGroupAdmissionReport`——不新增报告层。备选（不推荐）：只做统一
拒绝率单阈值——实现最简，但"任务性失败"与"基建故障"混在一个数里，
熔断会误伤（如把 infra 抖动当坏任务隔离）。

**待定参数**：各类阈值数值本身不在本包（预注册值 FA-5 校准，属 T1 强
报告）；本项只定**分类框架与动作映射**。

**长期代价**：六分类要求终止枚举（决策 1）先在——两项耦合；若决策 1
选 B（全拒），本项的"任务性失败不进熔断"将失去意义。

**以后还能改吗**：加类别便宜；改"某类是否隔离任务"的动作映射会改变
训练分布，升 T0 重议。

---

## 拍板方式

四项各自回复 A/B/…（或"A 但改 X"）。全部定案后：Claude 更新 05 计划
→ codex 复审计划 → F2-0（代码提升）起批实施。
