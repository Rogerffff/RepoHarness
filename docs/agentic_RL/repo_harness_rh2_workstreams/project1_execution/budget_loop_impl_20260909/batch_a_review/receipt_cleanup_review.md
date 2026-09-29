# 批 A I12：receipt 失败仍清理的独立窄复核

日期：2026-09-09。基线：HEAD `297f1f59` 及当前未提交批 A diff。角色：Falsifier / Simplifier。范围：`generate.py::_run_finally_section`、现有容器清理与会话 drop 消费路径、`test_b5_finalization.py`。不重审 B/C/D、I13/I16 或整条 shutdown 链。

## 结论

清理与首因保留的主要改动成立；**有一项本批应补的 P1：receipt 单独失败时，新增异步 cleanup 之前没有发出已有 run-fatal 通知。** 本次去掉 skip 后，原先接近同步抛出的 fatal 被推迟到 drop/rm 之后；生产生命周期在等待期间仍可接收工作。沿用 `_notify_fatal_halt` 即可修，不需要新状态、重试或服务。

其余核查没有发现本批阻塞问题：drop 抛普通异常不妨碍 rm；rm 非零或通道异常会隔离未确认清除的容器；原 fatal 在途时仍保留原异常；receipt/audit 次生错误没有顶替首因；receipt 失败不释放 poison、不追加缺少主 receipt 的 cleanup 记录；已经提前释放的容器不重复 rm。

## P1：receipt-only fatal 在清理等待期间没有通知运行 owner

**当前行为**：`generate.py:3653-3673` 捕获 receipt 构造/持久化失败后仅写 failure/audit；`:3705` 开始等待 `drop_session`，`:3716` 继续等待容器清理；直到 `:3823-3833` 才抛 `finalization_receipt_write_failed`。该异常来自 `_generate_attempt` 的 finally，不会回到 `:3434-3441` 的 `except FatalExecutionInfrastructureError`，因而本段没有调用 `_notify_fatal_halt`。

**违反的不变量**：已确认的 run-fatal 要在异步清理前通知运行 owner，同时照常完成资源清理。项目现有 `_notify_fatal_halt` 的说明就在 `generate.py:4832-4840`；工作正常的对照是原 fatal 已在途分支 `:3434-3441`，先通知再执行 finally。

**生产可达性：`production_reachable`。** 条件是正式链、receipt store 写入/构造失败、此前没有已经传播的 fatal，并且 cleanup 存在实际等待。可用已经允许的 `harness_bootstrap_failed` 构造：此时 session 已 open、rollout 容器尚未冻结释放，该局部故障原本返回 ABORTED；receipt 失败才使它升级为 run-fatal。真实入口 `Rh2MilesGenerateFn → rh2_custom_generate → RolloutOrchestrator.generate`；`BringupService._resolve_task`（`bringup.py:1573-1579`）经 `LifecycleState.enter_execution` 安装 task-local notifier（`shutdown/chain.py:204-218,243-261`）；该通知器才会调 `BringupService._on_run_fatal` 安排关停（`bringup.py:2256-2285`）。本轮不声称已经在真实 GPU 作业观察到后果。

**独立证据**：本目录 `receipt_cleanup_probe.py` 调用真实 `RolloutOrchestrator.generate`、真实 `LifecycleState.enter_execution` 与真实 `make_per_rollout_adapter`，只替换 Docker、harness 与持久化等外部边界。让已打开会话的 drop 停在一个可控事件上，得到：

```json
{
  "receipt_failure_recorded": true,
  "fatal_notifications": [],
  "accepting": true,
  "container_removed": false
}
```

放行 drop 后，最终确实抛 `finalization_receipt_write_failed`，但该生命周期的通知列表仍为空。对照“原 fatal 在途 + 同一 receipt/drop 等待”在进入 drop 时已经收到 `probe_primary_fatal`，不会出现通知空档。探针的 `on_fatal` callback 只登记事件并执行 `stop_intake`；真实 BringupService 会安排 `_run_close` task。本探针证明通知没有发生，不是实测真实训练仍提交 batch 或更新参数。

**影响与分期**：这是本批新增清理等待带来的时序回归；清理耗时期间没有及时进入已有 fatal 关停路径。receipt 故障频率未知，但磁盘/持久化故障和容器清理等待均属于当前正式链的直接失败面；不需要未来能力才触发。修复很小，宜在批 A 收口前完成。没有新增样本拒绝政策，正常成功路径也无需变化。

**最小修订**：当本次 receipt 失败使当前执行首次需要 run-fatal 时，在第一个 cleanup await 前调用现有 `_notify_fatal_halt`；尾部仍抛同一 receipt fatal，继续保留清理结果。原 fatal 已在途时保留原首因与已有通知；不借此改变取消传播语义。不要提前 `raise` 而再次跳过清理，也不要以新增持久状态或通用 shutdown 重构代替该通知。

**窄验收**：通过实际 `generate` 入口运行“资源仍持有 + receipt 失败 + 阻塞 drop/rm”，在解除阻塞前断言 notifier 已收到 receipt fatal；解除后断言 rm/audit 照跑、poison 不释放、无 cleanup append、最终仍抛 receipt fatal。对照原 fatal + receipt/drop/rm/audit 次生失败，原首因与通知顺序不变。

## 其它生命周期与维护测试核查

独立探针共七种组合，均使用当前真实 `_run_finally_section`；前五种用真实会话包装器验证 unregister，最后两种使用既有完整轨迹 fixture 验证提前释放幂等性。

| 场景 | 观察结果 | 判断 |
|---|---|---|
| 未释放容器，receipt 失败，drop/rm 成功 | drop 后 rm；lease 已释放；quarantine 空；audit 被调用 | 清理成立；上面的通知问题独立存在 |
| receipt 失败，shared adapter drop 抛异常 | 真 `PerRolloutAdapter` 的 finally 仍 unregister，token/hook 已清；随后 rm 成功；记录 `drop_session` | 未发现本批阻塞问题 |
| receipt 失败，rm 返回非零 | lease 未释放；quarantine 恰一项；记录 `remove_container`；最终仍是 receipt fatal | 未发现本批阻塞问题 |
| receipt 失败，rm 通道抛 OSError | lease 未释放；quarantine 恰一项；记录 `container_cleanup_exception`；最终仍是 receipt fatal | 未发现本批阻塞问题 |
| 原 fatal + receipt 失败 + drop/rm/audit 均失败 | cleanup 前已通知原 fatal；原异常保持；receipt 与 audit 次生失败留痕；quarantine 恰一项 | 首因保留成立 |
| artifact 已持久化、容器已提前释放，receipt 失败 | rm 总计一次；quarantine 空；finally 仍执行 drop/audit | 提前释放幂等性成立 |
| 已提前释放，receipt 失败且 drop 抛异常 | 不重做 rm；不隔离已移除容器；drop 错误留痕 | 未发现本批阻塞问题 |

七种组合均显式注入已有 poison 与 release callback：release 调用数为零，poison 仍在；均没有 cleanup append。`cleanup_completed` 在这里表示 cleanup 段已经执行结束，不能独立解释为容器已清除；失败场景仍必须读取 `lease_released` 与 `cleanup_failures`，当前记录能区分。

维护测试确实覆盖了资源仍持有的形态，未把提前释放误当 I12 修复：`test_receipt_persist_failure_before_release_cleans_up_and_run_halts`（`test_b5_finalization.py:104`）以 typed harness 引导失败结束执行，并断言 `persist_receipt < docker_rm`、`rollout_container_released_before_grading=False`、rm 恰一次。新 rm 非零例（`:133`）也在未释放形态下检查 quarantine。提前释放例（`:153`）则明确检查 rm 幂等，两个形态没有混淆。

这些维护测试没有安装或阻塞检查 run-fatal notifier，故不能发现上述时序问题；其注释提到 poison 不释放，但该测试夹具没有注入 release callback，独立探针已补证此行为。建议只把阻塞清理前的通知断言补进窄回归，无需重写现有 fixture 或扩大测试面。

## 验证与停止条件

从 `rh2/` 运行：

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/receipt_cleanup_probe.py
uv run ruff check ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/receipt_cleanup_probe.py
```

本轮独立探针退出码 0，探针文件 ruff 检查通过；这是上述七种源码接线结果的证据，不是修复已完成。业务源码、维护测试和外部系统均未修改；没有真实 Docker/GPU/模型 API 调用，没有提交。

停止条件：补齐 P1 的既有 notifier 接线，并复核“receipt 首次 fatal / 原 fatal 在途”两种分支及上述清理回归即可。本轮不新增其它阻塞项，不扩展到未来期限取消或整个 shutdown 设计。
