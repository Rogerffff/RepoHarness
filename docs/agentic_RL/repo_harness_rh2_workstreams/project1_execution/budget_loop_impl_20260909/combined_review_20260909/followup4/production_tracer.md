# 第四次窄复核：Production Tracer

日期：2026-09-09。角色范围：只追临时 sandbox 提前交给 `prepared` 后的真实调用、异常、取消和清理；不审停止规则 A，不重开已关闭项。

审查基线：`d4af9d9a449555580e27126425391de2cf87fbf5`。被审 HEAD：`92d165aa1dae5a660557f5f07cc702c3dee62ea3`。本角色聚焦修复：`6cf41951`。已读当前状态简报、协作协议、审查标准 §10、作者最新交接和 followup3 总报告。

**结论：本次改动消除了 F1 的直接根因；临时 `handle=None` 没有进入成功路径的解引用点。未发现需要本轮新增阻塞的生产接缝。** episode 期限不再圈住已确认 Fatal 的清理，首因先到外层通知及 receipt，资源引用也已交到该外层。仍须区分既有的 run 级关停取消：它可以中断正在进行的清理，但不会把本案变成普通 ABORTED 补采。此共享限制只登记，不据此重开本批。

本角色没有重跑主审负责的旧 15 案或维护测试。独立动态证据仅为 [production_probe.py](production_probe.py) 的两个局部对照，执行结果见 [production_probe.json](production_probe.json)，退出码 0。原 F1 跨 episode 期限反例的最终关闭由主审的独立重放裁定；这里给出独立生产追踪和范围反证。

## 1. 生产调用与所有权证据

**标签：`production_reachable`。** 代码中的实际链为：

```text
Rh2MilesGenerateFn.__call__
→ rh2_custom_generate
→ RolloutOrchestrator.generate / _generate_attempt
→ BringupService._resolve_task：登记当前在飞 task、安装 LifecycleState 通知器
→ _await_within_episode_deadline 创建准备子 task
→ _prepare_workspace
→ _materialize_rollout_sandbox(owner=prepared)
```

- miles 入口在 `rh2/src/repoharness2/adapters/miles/generate_fn.py:106,169-177`；薄转发在 `rh2/src/repoharness2/adapters/slime/generate.py:5721-5743`。
- 当前 task 的登记与通知器安装在 `bringup.py:1744-1755`、`shutdown/chain.py:204-218,243-261`；准备子 task 由 `generate.py:3757` 创建，与父 task 同在 miles 的 owner event loop，继承 task context。Bringup 的 owner loop 说明及绑定在 `bringup.py:1015-1027`。本次没有新增线程、跨 loop owner 或服务级表。
- 每次 `_generate_attempt` 各建一个局部 `prepared`（`generate.py:2753-2759`），一个准备子 task，只持有该 attempt 的 sandbox。`owner` 不是服务级共享字典；同时在飞的不同 attempt 不共用它。
- 容器成功启动之后，`generate.py:4543-4551` 同步创建 workspace 并写入 `owner["sandbox"]`，随后才到首次 digest 校验 await（4557）。这段没有 await，不存在“本事件循环已经切到外层取消、但临时引用尚未交出”的窗口。容器启动尚未返回、或建网中的取消仍走原先的按名字回收路径，不依赖临时引用。
- 外层 `generate.py:2760-2764` 的内层 `finally` 在成功、异常、期限取消时都会取回 `prepared.get("sandbox")`。因此 `_materialize_rollout_sandbox` 尚未返回完整对象，外层也已经能够拿到其 `lease`、`container_name` 和 workspace。

## 2. `handle=None` 的窄安全条件

`_MaterializedSandbox` 是内部 dataclass（`generate.py:2274-2288`），本次允许其 `handle` 暂为空。临时引用供清理读取的是 lease 和容器名；receipt 构造及清理失败追加也不解引用 `handle`（`4197-4231,4290-4305,4339-4356`）。

成功物化在 `4642-4657` 构造真实 `WorkspaceHandle`，经启动前校验后在 `4694-4697` 返回完整 sandbox；`_prepare_workspace` 在 3698 用它替换临时形态，后续准备完成才恢复主链。当前唯一的 `sandbox.handle` 解引用是 `2786` 的 `workspace_id`，只有 `_await_within_episode_deadline` 正常返回才会到达。物化异常、取消和准备阶段超时都跳过该处，直接进入收口。因此不能仅凭字段现在可空就判定生产空引用。

调用库存检索 `rh2` 和本工作流探针中的 `_materialize_rollout_sandbox`：唯一实际生产调用在 `3697`，明确传 `owner=prepared`。维护测试 `test_f2_2b_barrier.py:216-224` 只包裹并透传参数；`test_w1b_delivery_face.py:382` 是替换整个方法的故障桩。**没有发现当前代码直接以 `owner=None` 调真实方法的生产调用，当前维护测试也没有这种实际调用。** 作者称“单测／探针保留旧清理”是保留兼容能力的意图，不能当作已存在调用的证据；该 fallback 不用于判断本轮生产 F1。

## 3. 异常、通知、receipt 与清理顺序

原先物化的 `except Exception` 先 await 清理，清理仍处在准备子 task 的 episode 期限内；被取消后外层只收到 `CancelledError`，也拿不到尚未返回的 sandbox。本次 `generate.py:4687-4693` 在有 owner 时直接重新抛出，去除了这个 await。

当前顺序为：

```text
真实 digest／血缘矛盾，或 WorkspaceHandle 构造失败
→ 准备子 task 结束；其异常由父 task.result() 取出
→ 内层 finally 取回临时 sandbox
→ Fatal 分支同步通知；ValidationError 由结构契约分支转换并通知
→ 外层 finally 读取在途首因
→ receipt 记 fatal_run_halt 与原 reason_code
→ 以 cleanup_timeout_seconds 执行清理，再追加清理结果
```

证据位置：`generate.py:3767-3768,3623-3630,3645-3653,4074-4094,3684-3688,4202-4214`。receipt 对 Fatal 的判定及原码保留在 `265-283`。digest／血缘 Fatal 的通知只由外层 Fatal catch 调一次；契约错误在自己的 except 分支中转换、通知后抛出，不会再次进入同级 Fatal catch。准备子 task 结束以后，`_await_within_episode_deadline` 已退出；外层 `_run_finally_section` 没有再套 episode timer。因此“剩余 episode 时间短于清理耗时”不会再触发原来的洗因和补采路径。

这里的“清理不再覆盖首因”限定于 episode 期限和普通清理异常，不包括外部后来再次取消根 task 的所有情况，见第 5 节。

## 4. 普通取消、成功及清理失败的变化边界

| 路径 | 当前行为与本次差异 |
|---|---|
| 正常成功 | 校验、bundle 写入、handle 构造、基线 census、harness 与评分顺序不变；只提前建立 workspace 和临时资源引用。成功对象仍完整。 |
| digest／血缘查询自身失败 | 仍由原 `SlimeBindingError` 进入 task-local 分流（`4567-4570` 及既有 digest helper）；此次只把清理移到外层 receipt 后，不改错误码或准入分流。 |
| `docker run` 尚未成功返回就取消 | 原 `4525-4532` 按名字回收保留；此时没有临时 sandbox，行为未改。 |
| 容器启动后，校验 IO 被普通 episode 期限取消 | `4682-4686` 仍先 `_reclaim_after_cancel`，成功后 `lease_released=True`；父任务仍收到 `episode_deadline_in_materialize`。外层如今拿到临时引用，但 `_cleanup_container` 在 5485-5486 幂等跳过，不多删一次。 |
| 上述取消的首次回收失败 | `_reclaim_after_cancel` 先落失败／隔离事实（`4704-4731`），临时引用使外层 finally 还能再调用一次既有 `_cleanup_container`。这是本次所有权提前后带来的局部后备尝试；没有改两次调用各自的超时或引入重试状态机。历史失败与隔离记录不因后备尝试成功而自动抹去。 |
| Fatal 后 `rm` 非零／超时 | `_cleanup_container` 的原行为不变（`5488-5508`）：落 `remove_container` 失败并保持 `lease_released=False`；外层追加清理记录，原 Fatal receipt 不重写。不能据“清理步骤已结束”声称容器已回收。 |
| Fatal 后 Docker 通道抛普通异常 | 外层 `4293-4305` 记录 `container_cleanup_exception` 并隔离该容器，之后追加结果；这次物化错误也能进入该统一边界，不再由本地清理异常替换原首因。 |

上表清理分支为独立源码检查，未把其它测试的作者绿灯当作本角色实测。全量清理策略、重试计数和隔离队列状态不在本轮扩大审查范围。

## 5. 既有 run 级取消限制：两案对照，仅登记

实际通知器会调度 Bringup 的关停（`bringup.py:1027,2427-2457`），关停先停止 intake，再通过 `close_inflight_executions` 等待当前执行；默认 30 秒宽限后取消尚未完成的 task（`shutdown/chain.py:288-295,333-334`），而容器 cleanup 默认允许 120 秒。这个共享调用者可能在 Fatal 已通知、receipt 已写后取消慢清理。`generate.py:4293` 捕获普通 Exception，`CancelledError` 不在其中，故此时不能承诺该次执行把清理追加与 audit sink 全部跑完。

唯一 CPU 探针做两个同配置局部对照：① 本次物化 digest Fatal；② 本轮前已有的 `frozen_artifact_persist_failed`（真实持久化 IO 失败点 `3374-3396`）。两者都使用真实编排、真实 LifecycleState 通知器和真实 `close_inflight_executions`；只注入慢 Docker rm（0.2 秒）及把宽限缩短到 0.05 秒。没有注入 helper 判断结果，没有强塞 Fatal 到终态函数。

两个结果相同：

- 事件均为 `fatal → intake_stop → rm_enter → rm_cancelled`。
- 第一个清理 await 前：通知恰好一次，receipt 已为 `fatal_run_halt`，原码各自保留；物化案的 `audit.workspace_handle` 仍为空，已有 Fatal 对照则为完整 handle。
- 根 task 返回 `CancelledError`；`episode_hit_by=none`，`outcome_v2=null`，没有返回普通 ABORTED 样本；intake 已停。
- 该次执行的容器删除数为 0、私网登记仍为 1、租约未释放，cleanup 追加尚未发生。不能称这些资源已经全部回收。

**处置建议：共享 run 级取消的 P2／阶段 backlog，不新增本轮阻塞。** 生产调用者原先就能取消其它 Fatal 的同一 finally，非物化对照证明这不是临时 handle 独有缺陷。原 F1 的关键后果——没有通知、receipt 被改成 ordinary abort、继续补采——没有发生。触发频率未知；局部探针没有执行完整 Bringup 关停、run label 清扫或 launch trap，不能从 `finished_after_cancel=True` 推断整个 shutdown 假绿，也不能推断永久资源泄漏。

真实 `_run_close` 在执行各关停步骤前已把传入首因并入报告（`bringup.py:2118-2134`），随后 egress 步还会尝试处理 run 级残留并登记失败（`2022-2054,2155-2160`）；这是静态所有权证据，不是假称探针已经验证全链回收。下一阶段若处理这个共享限制，应在关停工作包里单独限定验收，不扩展本批 F1 修复。

## 6. 停止条件与最终范围

本角色所需边界已追完：唯一 owner 调用、临时对象可见时刻、完整 handle 读取前提、首因通知、receipt 和既有清理失败／取消收口均有明确生产位置。支持以主审原反例重放及维护测试结果关闭 F1，**不要求任何新增本轮阻塞**。

没有修改业务源码或维护测试，没有提交；只新增本目录的报告、探针和结果。没有运行 Docker、Claude Code、模型 API、GPU 或完整服务关停。停止规则 A 由另一角色负责；已关闭的 R3 旧两处／Z1／A／B／D-1／R1／R2／R4／R5 与缺 base 的既有 P2 均未重审。
