# 批 A R2 修后针对性复核

日期：2026-09-09。基线：HEAD `297f1f59` 与当前未提交修正。范围仅含 `generate.py::_run_finally_section` 的 `pending_tail_fatal` 和三条新增暂停 drop 测试。R1 的错误来源修正由主审负责；B/C/D 或本轮之后的额外源码变化不在此结论内。

**结论：R2 可以关闭。** receipt 首次导致 run-fatal 时，现已在第一个 cleanup await 前通过既有 notifier 通知；尾部抛同一对象。原 fatal、外层取消、兼容路径与此前已经核对的清理结果未改变。没有新增阻塞 finding，也无需扩大 shutdown 设计。

## 条件与动作核对

| 路径 | 修前尾部条件 | 修后提前通知与尾部行为 | 判断 |
|---|---|---|---|
| receipt 构造/持久化失败 | `receipt_persist_failed and mode != s1_compat and in_flight is None` | `generate.py:3680-3686` 在同一条件下构造/通知；`:3843-3850` 保留旧条件并抛同一对象 | 条件等价；只提前通知 |
| termination 事实不可派生 | `termination_facts_failed and in_flight is None` | `:3703-3709` 提前构造/通知；后续 audit sink 未再失败时，`:3851-3856` 仍按旧条件抛同一对象 | 条件等价；没有额外扩大兼容路径的 fatal 面 |
| 原 fatal 已在途 | `in_flight is not None`，不以尾部错误替换首因 | 不设置新的 receipt/facts fatal；原通知和原异常继续生效 | 保留首因 |
| 外层取消已在途 | 同上，保留 `CancelledError` | 不追加 receipt fatal 通知；cleanup 之后仍传播原取消 | 行为未变 |

facts 分支只有在 receipt 成功后才会执行（`:3694`），因此它的 `pending_tail_fatal is None` 条件不会将一个原本应抛出的 facts fatal 静默跳过，也不会覆盖 receipt fatal。

通知后的 drop、容器 rm、poison 保留、quarantine、audit 与 cleanup append 条件相对 R2 修前未改。`_notify_fatal_halt` 仍使用原 task-local notifier；之前已追踪的 `LifecycleState → BringupService._on_run_fatal` 接线没有被替换。真实服务收到通知会调度关停，当前复核没有另建模拟 shutdown 平台。

**静态补核的非阻塞诊断边界**：当 `termination_facts_payload` 先失败、随后 audit sink 又失败时，当前逻辑先通知 `termination_facts_underivable`，随后抛 `execution_audit_write_failed`，不会到达抛同一对象的尾部。sink 的首因保护只检查 receipt 失败或已有 `in_flight`，未检查 `termination_facts_failed/pending_tail_fatal`。与 HEAD `297f1f59` 比较，sink 优先级是既有行为，不是 R2 新增的拒绝或清理回归；两者均为 fatal，首次通知已由生产生命周期保存，cleanup 也在 audit sink 前执行，因此不重开 R2。上表与维护测试的“同一对象”仅适用于后续 audit sink 未再失败的 facts 场景。本轮只静态确认此边界，没有新跑组合探针或修改源码。

## 复跑证据

1. **原七案 CPU 探针**：直接复跑 `receipt_cleanup_probe.py`，没有修改旧脚本，退出码 0。receipt-only 暂停在 drop 时，通知列表从空变为 `[finalization_receipt_write_failed]`；事件顺序为 `notify → drop_enter → drop_return → docker_rm → audit_sink`。原 fatal 组合仍只通知 `probe_primary_fatal` 一次。drop 错误、rm 非零/异常、提前释放等结果与首审一致；poison release 和无 receipt 的 cleanup append 仍均为零。
2. **三条维护测试**：`test_receipt_only_failure_notifies_halt_before_cleanup_wait`、`test_primary_fatal_with_receipt_failure_keeps_first_cause_single_notification`、`test_underivable_facts_notifies_halt_before_cleanup_wait`，实跑 **3 passed**。首条在容器尚未释放、drop 尚未返回时断言已通知；第一、三条都以 `is` 验证尾部异常就是已通知对象，其中第三条没有注入后续 audit sink 失败；第二条核对原首因只通知一次。它们进入真实 `_run_finally_section`，没有只测试新局部变量。
3. **实际 task.cancel 补测**：在真实 `generate` 入口启动后，让 harness 替身阻塞；调用 `task.cancel("owner_stop_probe")`，receipt store 同时失败，暂停 drop。此时通知数 0；放行 cleanup 后收到原 `CancelledError("owner_stop_probe")`，容器恰删除一次，receipt 次生失败留痕，无 cleanup append。
4. **兼容路径补测**：`build_dense_chain` 的 `s1_compat` 路径显式注入失败 receipt store，仍返回一个样本，通知数 0，容器清理完成。

七案探针使用真实 `LifecycleState` 和会话包装器，但 `on_fatal` callback 只登记并停收；维护测试则记录 `_notify_fatal_halt` 调用。由此证明的是通知顺序、对象与清理结果；没有将 `accepting=False` 写成真实训练/GPU 关停已经实测的证据。

复跑命令（在 `rh2/`）：

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/batch_a_review/receipt_cleanup_probe.py
uv run pytest tests/adapters/test_b5_finalization.py::test_receipt_only_failure_notifies_halt_before_cleanup_wait tests/adapters/test_b5_finalization.py::test_primary_fatal_with_receipt_failure_keeps_first_cause_single_notification tests/adapters/test_b5_finalization.py::test_underivable_facts_notifies_halt_before_cleanup_wait -q
```

补测输出：

```json
{
  "cancelled_reason": "owner_stop_probe",
  "cancel_notification_count": 0,
  "cancel_cleanup_completed": true,
  "s1_returned_samples": 1,
  "s1_notification_count": 0
}
```

本次只新增本复核文档；没有改业务源码、维护测试、旧探针或主文档，没有提交，没有真实 Docker/GPU/模型 API 调用。R2 的停止条件已经满足，后续范围由主审汇总。
