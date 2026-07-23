# 学习台账（面试复习材料，按主题积累）

> 用途见 `collaboration-protocol.md` §6：每轮报告的"⑥ 学习摘要"与 codex
> 的组件讲解按主题归档于此。每条目固定形状：**场景（真实代码/真实 bug）→
> 机制解释 → 不变量 → 失败场景 → 延伸阅读指针**。抽象概念必须配具体
> 数值、路径或反例。

## 0. 面试必答清单（每完成一个阶段补充可回答的新问题）

起点八条（codex 2026-07-20 列出，能不看文档回答才算过）：

1. 一个 task 如何变成 rollout，再进入 optimizer step？
2. PromptGroup / RolloutExecution / Branch 为什么是三层身份？
3. worker、adapter、proxy、SGLang、trainer 分别在哪个线程或进程？
4. 为什么不能把 infra failure 当成 reward=0？
5. 为什么 fully async 需要 policy version 和 DIS？
6. 为什么缺员组不能静默采用可变 n？
7. 为什么 fail-closed 仍可能造成训练数据偏置？
8. 项目真实跑过哪些 GPU 实验，发现了什么，哪些结论还没有验证？

## 1. async/await、event loop 与 task cancellation

（待积累）

## 2. 线程与 event loop：为什么需要 call_soon_threadsafe

### 条目 2.1：跨线程取消 harness 的三次演进（FA-1 轮次 9→10 真实 bug）

**场景**：poison（判定会话作废）发生在 aiohttp adapter 线程，要取消的
harness task 活在 Ray actor 的 AsyncLoopThread。轮次 9 的实现是订阅回调
里直接 `harness_task.cancel()`。

**机制**：`asyncio.Task.cancel()` 不是线程安全 API——它假定调用方与
task 在同一个 event loop 线程。从别的线程调用时不会报错，但取消信号
不会被正确投递（codex 双线程探针：`task_cancelled=false`，而账面显示
subscriber 已处理）。正确写法是让 owner 线程先记下自己的 loop：

```python
owner_loop = asyncio.get_running_loop()          # 在 owner 线程内取
def cancel_from_any_thread(_sid, _reason):
    owner_loop.call_soon_threadsafe(harness_task.cancel)   # 跨线程投递
```

`call_soon_threadsafe` 把回调塞进目标 loop 的就绪队列并唤醒它——这是
asyncio 里**唯一**保证跨线程安全的入口。

**不变量**：任何 asyncio 对象（Task/Future/Queue）只能在它所属的 loop
线程里操作；跨线程只许经 `call_soon_threadsafe` / `run_coroutine_threadsafe`。

**失败场景**：单事件循环的测试永远发现不了这个 bug——poison 和 task 在
同一个 pytest loop 里时直接 cancel 恰好是合法的。修复后的回归测试必须
从真 `threading.Thread` 发 poison（`test_poison_from_real_thread_cancels_
harness_in_owner_loop`，修复前该测试永久挂起）。

**延伸阅读**：`rh2/src/repoharness2/adapters/slime/generate.py` 的
`_cancel_from_any_thread`；`async_worker.py` 的 `SessionPoisonRegistry.
subscribe`（回调复制后锁外调用的原因）。

## 3. producer/consumer、有界队列与 backpressure

（待积累）

## 4. identity、idempotency、lease/ACK、at-least-once

（待积累；FA-2A 的 F2-1/F2-4 会产出本节主要内容）

## 5. 状态机、事务式持久化与崩溃恢复

### 条目 5.1：审计落盘为什么必须 snapshot→写→ack（FA-1 轮次 14 真实 bug）

**场景**：execution 终态审计先 `drain_attempts()`（从内存摘走 attempt
记录）再写 JSONL。磁盘满时写失败——rollout 被拒绝，而 attempt 证据也
已经从内存里消失了。

**机制**：这是经典的"先删后写"事务顺序错误。正确顺序是先复制（snapshot，
不删）、持久化成功（含 fsync）、再确认删除（ack）：

```text
snapshot_attempts(sid)   # 锁内复制，不移除
-> 写 JSONL + fsync      # 失败则抛异常，内存原样
-> ack_attempts(sid)     # 只有写成功才移除
```

**不变量**：任何"内存 → 磁盘"的移交，删除内存副本必须发生在持久化
确认**之后**；两步之间进程崩溃的后果只能是重复（可去重），不能是丢失。

**失败场景**：写失败测试必须断言 ledger 完好（`test_write_execution_
audit_failure_keeps_ledger`）。

**延伸阅读**：`glue.py` 的 `write_execution_audit_record`；同批的
`FatalExecutionInfrastructureError`（审计存储不可用为什么必须停机而
不是当普通失败）。

## 6. policy version、staleness、off-policy 修正与 DIS

（待积累；FA-4 接线时产出本节主要内容）

## 7. fail-closed 的数据偏置与 fail-loud

### 条目 7.1：非零 exit 全拒 = 确定性的长度偏置（轮次 9→14 的推翻）

**场景**：轮次 9 定案"正式链一切非零 harness exit 都拒绝"（理由：任务
失败的负样本是 exit 0 + reward 0）。轮次 14 推翻：slime 的 episode 时间
预算耗尽返回 `EXIT_TIME_BUDGET_EXCEEDED = -1`（sandbox.py:60）——超时是
**主路径的正常终止**，全拒等于把长任务系统性剔出训练分布。

**机制**：fail-closed 把 bug 转化为"缺员"（样本作废），缺员不报警、只让
数据变少变偏。当某个拒绝条件与轨迹的某个属性（这里是时长）相关时，拒绝
就变成了对该属性的隐性过滤器——模型会"学会不做长任务"。

**不变量**：每新增一条拒绝路径，必须回答"它系统性剔除哪类轨迹"，并有
分类计数 + 熔断阈值（fail-loud），否则偏置不可见。

**失败场景**：episode 超时截断的轨迹若 capture 完整闭合、workspace 可
评分，正确处理是"截断但有效、拿真实低 reward"，而不是作废。

**延伸阅读**：05 计划 FA-2A 节"结构化终止枚举"；协作协议 §2 的 T0
升级规则 4（新增剔除轨迹的拒绝路径必须 owner 拍板的原因）。
