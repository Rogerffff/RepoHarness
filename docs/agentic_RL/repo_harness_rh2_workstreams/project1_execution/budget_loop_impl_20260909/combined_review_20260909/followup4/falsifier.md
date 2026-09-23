# 预算终止闭环：第四次窄复核 · Falsifier / Simplifier

日期：2026-09-09。基线 `d4af9d9a449555580e27126425391de2cf87fbf5`，被审 HEAD `92d165aa1dae5a660557f5f07cc702c3dee62ea3`。主责停止合同 A（`7bed1bc0`），并反查 F1 物化资源交接（`6cf41951`）的最小性与直接接缝。已读 CURRENT-STATE-BRIEF、review-standards §10、[上轮结论](../followup3/README.md)及作者最新交接；旧 A/B/D-1/R1/R2/R4/R5、Z1 与缺 base 的 P2 不重开。

**结论：支持停止合同 A 的本轮收口。F1 原来的“物化异常先等待清理、被 episode 期限取消覆盖”已从生产调用路径中移除；临时 sandbox 没有新增长期 owner 或状态机，也没有发现 `handle=None` 被生产成功路径读取的接缝。另发现的关停宽限取消问题属于既有共享 finally 限制，建议记 P2 阶段 backlog，不能把它描述成原 F1 仍会降级 ABORTED 或继续补采。** 原反例的动态回放由主审负责，本子审没有重复运行旧七案、八案及两案停止重试。

## 1. 停止合同 A：没有绕过期限前确认的生产 KEEP 路径

生产可达性为 `production_reachable`：正式入口 `Rh2MilesGenerateFn → rh2_custom_generate → RolloutOrchestrator.generate → _generate_attempt`，turn 预算触发 `_stop_after_turn_budget`。编排和 `DockerQuiescenceBarrier` 使用同一 `time.monotonic` 时钟域；测试才显式注入同一假钟。

| 边界 | 已核代码与反证结果 |
|---|---|
| 原始确认 | `execution_scope.py:212–223` 只在一次 COUNT 返回可读零计数时写 `confirmed_at=returned_at`，该字段不是 kill 回包时刻。 |
| 唯一证明 | `execution_scope.py:148–149` 的 `confirmed_at <= deadline` 是唯一返回 True 的分支；其余 kill 状态、没有反证、晚确认分支均返回 False。改动删除的是原末尾推断 True，不是提前停查或缩短回收预算。 |
| 强停重试 | `generate.py:3796–3808` 合并真实停止尝试，`3941–3945` 再用同一纯函数裁定；未确认且还未到墙才重试。`merge_stop_results` 保留第一次归零确认，前一次失败不会覆盖后一次墙前确认。 |
| 首次确认晚于墙 | 例如 deadline=900、kill=899.5、首次归零=901：纯函数返回 False，`generate.py:3958–3964` 返回 `HARNESS_EXIT_TIME_BUDGET_EXCEEDED`。`2921/2944` 把 trigger 与请求归属写为 hard wall；屏障归类 `3851–3854` 不会把这条路径翻回 turn KEEP。 |
| 已确认后处理跨墙 | `generate.py:3874–3882` 先查屏障是否有墙后见活的反证，再保留已有确认，或接受屏障自己的墙前 `confirmed_at`。`quiescence_barrier.py:110–118` 在两个指纹 await 前存入停止观测，因此指纹返回到 901 不会把 899.5 已确认的停止改成超时。 |
| Outcome、receipt 与准入 | `generate.py:5606–5607` 将停止 hint 写进 Outcome；`build_finalization_receipt:301–304` 内嵌同一个 typed Outcome。交付面派生 AdmissionPayload 后，`admission.py:635–647` 根据 termination 选择槽位；`bringup.py:240–244` 仍明确注入 turn=KEEP_FULL、hard wall=DROP_GROUP。miles 组准入再次核对 payload 与 termination facts。 |

没有发现本次 diff 新增另一套停止时刻、资格开关或定时器。kill 返回/投递/pkill 状态仍可影响诊断码，但不再影响是否 KEEP；保留这些诊断字段不等于保留旧推断。

`generate.py:3885–3889` 的“非 Docker 注入屏障、无停止观测”回退不是正式 Bringup 路径；正式构造在 `bringup.py:1428` 注入 `DockerQuiescenceBarrier`，后者总会先写 `barrier_stop`。不能把手工注入仅回 `QuiescenceConfirmed` 的替身当作正式入口绕过 A 的证据。

训练分布变化与 owner 已批内容一致：实际可能早停、但控制端首次零确认晚于墙的轨迹被丢弃；损失频率未知。未改变 turn 的真实评分、已有墙前确认正例、自然结束分期或 600 秒／25 turn 数值。

## 2. 测试 oracle 与实际接线

本次 `test_budget_deadline.py` 的维护测试变更准确翻转了 `confirmation_after_wall`：`max_turns_exhausted/-2/KEEP_FULL` 改为 `hard_wall_timeout/-1/DROP_GROUP`，没有降低屏障或完整性断言。测试仍调用真实编排、真实 `DockerQuiescenceBarrier` 和 `decide_member_disposition`，外部 IO 与时钟为替身；不能称为真实 Docker/CC 作业实测。

停止 helper 测试还保留了 `confirmed_at=900.5, deadline=900.5 → True` 的等号对照。此前的失败重试、屏障 899.5 确认而 901 指纹返回、首次强停已确认而晚指纹等维护测试均未被删除或放宽。`test_f2_2b_barrier.py` 仅让 wrapper 透传新增 `owner=`，避免测试包装截断真实回收交接。

新增 F1 三案从真实 digest/血缘校验点或 `WorkspaceHandle` 构造点产生异常，不直接把 Fatal 塞进终态函数；0.25 秒是真 episode 期限，rm 门控使清理跨到 0.4 秒以后。它们验证通知先于 rm、receipt 原码、容器/私网/租约回收。其 notifier 被替换成记录回调，所以只证明 episode 期限场景；不证明完整 Bringup 的后续关停取消，见 §4。

## 3. F1 修法的反证与最小性

实际交接链是 `generate.py:2754–2764` 的 attempt 局部 `prepared` 字典 → `_prepare_workspace:3697` 显式传 `owner=prepared` → docker run 成功后 `4543–4551` 同步放入临时 sandbox。此时尚未进入后续 digest、血缘等 await。

异常发生后，`4687–4693` 的有 owner 分支直接抛出；外层取回 `prepared["sandbox"]`，`3623–3630` 同步通知原 Fatal，`3674–3688` 带在途异常进入原有 finally。receipt 仍先于 cleanup，`5488–5489` 仍按租约的 cleanup timeout 限制 rm。准备子 task 已结束，episode 的等待也已经退出，清理不再悬挂在原 episode 期限所取消的子 task 里。

按修复五问裁定：

1. **旧代码确实在正式入口失败。** 上轮复现不是只测 helper；缺的是物化异常传播期间的资源归属，不能用“最终会抛 Fatal”反驳清理 await 被取消的情况。
2. **当前修复移除了根因。** 它把已有资源引用提前交给既有 finally，删除 owner 路径内的清理 await；没有把错误变为 missing/rejected，也不只提前发通知后继续丢首因。
3. **没有新增长期 owner 或状态机。** 新增 1 种 attempt 内临时表示（`handle=None`）和 1 个内部可选参数 `owner`，未增加重试或运行时降级策略。`prepared` 原本就在单 attempt 内；仅提前填入已有键。临时对象成功后由完整对象替换，不持久化、不挂服务级字典。无 owner 直接调用仍沿旧就地清理；仓库内唯一生产调用点已经传 owner。
4. **无需另建 fail-stop 或恢复系统。** 当前就使用既有 typed run-fatal 和 finally；单独停 run 不能代替将容器名字/lease 交给回收者。新增 supervisor、ledger 或不可取消的通用清理 task 都超出本次修复所需。
5. **成功路径事实未变。** `handle` 唯一生产读取在 `2786`，只有 `_prepare_workspace` 正常完成后才能到达；完整返回对象在 `4695–4696` 构造。异常路径只把临时对象交给清理，清理只取 lease/name，不读 handle。普通 deadline 取消仍执行原按名回收，`audit.lease_released` 防止外层重复删除。

## 4. 与 Production Tracer 交叉反证：后续 run 级取消只登记

Tracer 识别的来源确实为 `production_reachable`，不是任意 `task.cancel()`：`BringupService._resolve_task:1750` 登记当前执行；`LifecycleState` 的 ContextVar 通知器调用 `_on_run_fatal:2455–2456` 调度关停；`close_inflight_executions:288–295` 在宽限后取消未完成 task。缺省 `inflight_grace=30s`，而 rollout cleanup timeout=120s。

因此当 rm 用时超过关停宽限，已在 finally 的 root task 可能被取消，跳过 cleanup 追加记录和 audit sink；`CancelledError` 不被 `generate.py:4293` 的 `except Exception` 捕获。这里应如实保留资源未完成回收的限制，不能声称所有取消都能保留函数返回异常或完成本次清理。

**不据此把原 F1 重新判为 P1，建议进入共享关停的 P2 阶段 backlog：**

- 原 Fatal 已在首次 rm 前通知；intake 已停，receipt 已是 `fatal_run_halt` 与原码。`LifecycleState.fatal_seen` 和完整 service 的 shutdown `first_cause` 独立保留原因。这不是原先“无 halt、receipt=aborted、继续补采”的失效。
- 同一 `_run_finally_section` 与关停取消策略在本批前已存在，既有 `frozen_artifact_persist_failed` 等已通知 Fatal 也进入它。Tracer 的[局部两案对照脚本](production_probe.py)专门比较这两类来源；本子审已静态核对脚本并独立读取[两案输出](production_probe.json)，未重复执行。两案均为 `fatal → intake_stop → rm_enter → rm_cancelled`，各自通知和 receipt 原码保留，`Outcome=None`、`episode_hit_by=none`，本次 cleanup 追加记录为零。
- 该脚本只运行真实 intake/inflight 关停步骤，不能用 `finished_after_cancel=true` 推断整个关停报告假绿。完整 service 保留首因；egress/network 拆除失败也可落关停报告，另有 run 级残留处理。不能把“本次 attempt 未追加 cleanup 结果”扩大称为“永久资源泄漏”或“全部丢账”。
- 后续局部验收应看：已进入 finally 的执行被 run 级取消时，原 receipt/首因不改写，未完成回收有明确归属或失败记录；正常关停仍有界。不得为这一登记反向重构已关闭 A/B，也不要求这轮增加长期状态机。

本项生产频率未知。是否在阶段后续切片处理由主审/owner 排期，本报告不冒充 owner 已接受剩余风险。

## 5. 本子审实际验证与停止条件

在 `rh2/` 目录、离线使用 integration miles，独立执行以下三个维护测试：

```text
tests/adapters/test_budget_deadline.py::test_terminate_records_delivery_and_observations_separately
tests/adapters/test_budget_deadline.py::test_merge_stop_results_keeps_first_delivery_and_all_observations
tests/adapters/test_f2_2b_barrier.py::test_e2e_real_barrier_class_confirms_and_grades_frozen
```

命令使用 `uv run --offline pytest … -q`，结果 **3 passed in 0.19s**。同时核过基线至 HEAD 的两处业务源码及两个维护测试 diff、生产调用点和消费者。没有运行外部服务、Docker、Claude Code、GPU，也没有改动业务源码或维护测试；本子审仅写本报告。

非阻塞文案残留：`generate.py:3925` 仍写“投递早、确认晚的边界待 owner 决定”，与已经落实的 A 过时。建议后续直接同步注释，不为此追加兼容分支或阻塞本批。

本子审重点覆盖 A/B/D/E/F/G/H/K/L/M；C 未见新增生产挡板；J 仅记录上述旧注释；N 未改依赖或外部接口。主审完成 A 与 F1 原反例及必要正例回放后，已有证据足以进入下一切片；共享 shutdown 限制按阶段登记，不以还可构造取消组合为由继续扩展本轮。
