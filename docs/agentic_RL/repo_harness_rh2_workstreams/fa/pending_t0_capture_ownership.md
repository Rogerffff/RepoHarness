# 窄 T0 决策包：CaptureRegistry 所有权模型定案（F2-3 批 2c 复核后）

> **status: approved（方案 A，用户拍板，2026-08-24；实施 commit
> fa8e796a + 联合终核修正）**——本文件是所有权模型的现行权威，后续
> 实现者不得重新实现已撤回的批 2c 命令桥。

## 要决定什么

D3 已批文本要求 CaptureRegistry **完整** single-owner（hooks/pending/
versions/poison 全量、有界命令面、禁绕过）。批 2c 实现的命令桥被复核
证明未达标且自带三个生产可达 P1。现在必须二选一：**修改 D3 口径采用
混合所有权模型（撤回命令桥）**，或**投入补全完整 single-owner**。

## 代码事实（复核证据）

- 批 2a/2b 成果与桥无关且稳固：drain/inflight/revoke 已 adapter-loop
  独占（顺序 = 先证不写再冻结）；request 级归属已消灭串账与误杀。
- 命令桥三 P1：①超时不取消——命令在 owner 恢复后**迟到生效**（探针：
  register 超时后 late_sid 仍被注册），异常还被收成缺员而非
  WorkerHalted；②D3 覆盖面未达——poison 仍双线程共锁、探针 stage 绕过
  owner、single_pending_turn 返回可变别名、stats 跨线程直读写、
  `.result(timeout)` 只是等待有界而非队列有界（可同时排入 32 命令）——
  旧锁仍是正确性必要条件；③drain 桥无 bridge 层 deadline，owner loop
  停转时 execution 永久 in-flight。
- 对照证据：批 2c 之前的锁模型经 5000 轮竞态压力测试零异常/零悬挂/
  零复活。

## 方案

**A（codex 推荐）混合模型**：保留批 2a（adapter loop 独占 revoke/
inflight/drain）+ 批 2b（request 级归属）；**撤回命令桥**（register/
unregister/boundary/快照回到显式锁直调）；SessionPoisonRegistry 保持
独立线程安全对象。D3 文本按此修订（"完整 single-owner"收窄为"生命
周期临界段 owner 独占 + 其余短态锁保护"）。
优点：每个状态域恰一个所有权机制；压力测试实证；删码不加码；三 P1
中 ①② 随桥消失。缺点：D3 字面目标放弃，需本 T0 背书。

**B 补全完整 single-owner**：桥加取消/世代 fencing（迟到命令丢弃）、
有界命令队列、poison/stats 收编 owner、绕过断言、owner 死亡 watchdog、
I/O 移出 owner。
优点：D3 字面达成，锁可物理移除。缺点：新增 fencing/队列/watchdog 三
套机制——正是历史上触发修复循环熔断的"叠状态机"形态；复杂度与新故障
面显著增加，而它要防的实际竞态已被 2a/2b 靶向修复覆盖。

**共同必修项（无论 A/B，T0 批后立即实施）**：drain 桥有界超时 → typed
fatal；owner 停转后不得有迟到状态修改；owner 故障 → WorkerHalted 而非
缺员；慢 abandon/artifact I/O 不在 adapter loop 执行（P2）。

## 推荐及理由

**推荐 A**。判据即用户既定授权三条：B 属过度设计（为字面目标建三套新
机制去防已被靶向修复的竞态）；A 删除双所有权模型使故障语义可审计；
5000 轮压力证据站在锁模型一边。D3 当初的动机（torn snapshot/串账/
误杀）已由 2a/2b 根修——"完整 single-owner"是手段不是目的。

## 长期代价与可回改性

- A 的代价：若 F2-4 恢复重放或未来并发扩张需要全量串行化，届时带证据
  重新提案（可回改；2a/2b 的 owner 面是良好基座）。
- 锁模型的维护约束写入 capture_wire 模块头（新增状态必须声明所属域：
  owner 独占域 or 锁域，禁跨域混用）。
- 批 2c 撤回 = revert 命令桥相关 diff（bind_owner_loop/_run_on_owner/
  包装方法），保留其测试中仍适用的部分（drain owner 测试不受影响）。

## 以后还能改什么

所有权模型本身（A→B 需新 T0 带证据）；共同必修项的实现细节（T1）；
poison 收编与 stats 域归属（T1，A 下默认维持现状）。
