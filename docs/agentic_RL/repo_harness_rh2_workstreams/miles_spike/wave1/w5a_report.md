# W5a 实现报告：shutdown 关停链 + 资源闭包一次性取数

日期：2026-09-02。执行依据：06 计划 §3 W5a 行 + §6 防御清理原则 + §1 A9；范围来源 = 就绪稿
`formal_first_training_readiness_scope.md` §2.6（关闭链）与 §2.8（资源闭包，只做保守上界 + 一次性取数）；
现有 prepared 链/bringup 形态见 `w1b_slice1_report.md`。本文同时充当本包的 implementation-notes。

一句话：**RH2 侧的关停从"留给进程退出回收"变成一条有界、保首因、幂等的显式链**——
`BringupService.close()`（或进程级入口 `close_bringup_service()`）按固定顺序关掉在飞执行、评分队列/容器、
capture 会话/registry、adapter HTTP 线程，写出 `shutdown_report.json` 与 `resource_closure.json`；
run-fatal 与 SIGTERM 走同一条链；关闭后所有任务面 typed 拒绝；campaign supervisor 缩成一个 launch `trap`
入口 + 一个"列出残留即失败"的检查。**没有新增授权闸门、账本、常驻进程或服务**（§6）。

## 0. 交付物清单

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/shutdown/chain.py` | 新增 | 有界关停执行器 `run_shutdown_chain`（每步 `wait_for`、首因/次生、evidence 失败不阻断、永不抛）；任务面关停状态 `LifecycleState`（停收/评分门/在飞表/run-fatal 通知器）；`close_inflight_executions`（先等→取消→再等，只记 `owner_cancelled`/`missing` 事实）；`ServiceClosedError`（typed 拒绝）；`ShutdownTimeouts.from_env`；`install_signal_shutdown` |
| `rh2/src/repoharness2/shutdown/resource_closure.py` | 新增 | 内存保守上界 `estimate_memory_upper_bound`（逐项系数公开）、随 attempt 增长集合盘点 `GROWING_COLLECTIONS`/`collect_growth_facts`、`measure_fsync_latency`（单次）、`resource_closure_facts` + 原子写 |
| `rh2/src/repoharness2/shutdown/run_residue.py` | 新增（纯 stdlib，可按文件路径运行） | launch trap 入口：`cleanup`（按 label `rh2.run_id=<run_id>` 先记后删容器 + 显式 glob 的临时目录）与 `check`（列出残留即失败；查询失败 ≠ 零） |
| `rh2/scripts/rh2_run_trap_cleanup.sh` | 新增 | trap 可调用的 shell 入口：cleanup → check，两份 JSON 报告，残留/查询失败非零退出 |
| `rh2/src/repoharness2/adapters/slime/bringup.py` | 修改 | `LifecycleState` 接线（`_resolve_task` 登记在飞 + 关停拒绝、`_write_execution_audit` 注销、`_grading_submit` 评分门）；`close()` / `_run_close()` / `_build_shutdown_steps()`；`_on_run_fatal`（run-fatal 通道）；`install_sigterm_shutdown`（opt-in）；`get()` 的 sticky `CLOSED`；模块级 `close_bringup_service()`；`RH2_SHUTDOWN_*_SEC` / `RH2_SHUTDOWN_ON_SIGTERM` 旋钮 |
| `rh2/src/repoharness2/adapters/slime/capture_wire.py` | 修改 | `CaptureRegistry.closed` + `close()`；关闭后 `register` typed 拒绝、HTTP guard 对一切请求 403 `rh2_service_closed`（`x-should-retry: false`） |
| `rh2/src/repoharness2/grading/manager.py` | 修改 | `SWEGradingManager.close()`（取消预热 + gc 全部记账容器，幂等）、`closed` 属性、关停后 `grade()` typed 拒绝 |
| `rh2/src/repoharness2/adapters/miles/lifecycle.py` | **删除** | C3/C7 原型 `Rh2RolloutLifecycle`（绑定未采用的 governed ledger，零生产调用点）——处置见 §6 第 1 条 |
| `rh2/src/repoharness2/adapters/miles/__init__.py`、`rh2/tests/adapters_miles/conftest.py`、`rh2/tests/adapters_miles/test_governance_receipts_lifecycle.py` | 修改 | 摘除原型导出/夹具/两个原型测试（§4 段），docstring 指向新链 |
| `rh2/tests/adapters/test_w5a_shutdown_chain.py`（15）、`test_w5a_run_residue.py`（7）、`test_w5a_resource_closure.py`（5）、`rh2/tests/adapters_miles/test_w5a_bringup_close_vendor.py`（1） | 新增 | §10 |

未改：`generate_fn.py`、`canonicalize.py`、`generate.py`、`governance/gate.py`、`termination_facts.py`、`contracts/`、
`faithful_dis_loss.py`、`reference/`、`experiments/miles_gpu_spike/launch.sh`、`bringup.py:705-715` fa_formal 挡板（原样）。

## 1. 关停顺序表（组件 / 超时 / 失败语义）

`BringupService.close()` 把下表装配成 `ShutdownStep` 列表交给 `run_shutdown_chain`。超时默认值来自
`ShutdownTimeouts`，每项可用 `RH2_SHUTDOWN_<NAME>_SEC` 覆盖（非法值在 `BringupService.__init__` 起任何线程之前就炸）。
`kind`：`control`/`cleanup` 步失败 = 残留风险；`evidence` 步失败 = 证据缺失。三类都**不中断链**，只影响报告归类。

| # | 步骤 | 做什么 | 上界（秒） | 失败/超时语义 |
|---|---|---|---|---|
| 1 | `intake_stop`（control） | `lifecycle.stop_intake()`：此后 `_resolve_task` 一律 `ServiceClosedError` | 1 | 同步瞬时；记在飞数 |
| 2 | `evidence_begin`（evidence） | 往 `bringup_events.jsonl` 追加 `shutdown_started` | `evidence`=10 | 写失败只记 evidence 失败，**不阻止**后续任何清理 |
| 3 | `inflight_executions` | 先等在飞 task 自然结束（`inflight_grace`=30），到时取消剩余，再等它们跑完各自的 finally（`inflight_cancel_wait`=150，容纳 generate.py 的 cleanup 120s + drop 5s） | 30+150+5 | 取消的执行只记 `termination_kind=owner_cancelled`、`completion_class=missing`；取消后仍没跑完的进 `residue.unfinished_executions` |
| 4 | `grading_queue` | 先 `lifecycle.close_grading()`（评分面从此 typed 拒绝），再有界 drain（`grading_drain`=60）；超时改 `close(drain=False)` 撤 worker（worker 的 finally 自删容器） | 60+15 | 队列从未 start → `skipped`；drain 超时不是失败，记 `drained_within_timeout=false` |
| 5 | `grading_manager` | `SWEGradingManager.close()`：取消预热、`gc()` 回收全部记账容器、置 closed | `grading_manager`=60 | 单容器 rm 失败进 manager `cleanup_failures`（Q8 留痕）并在第 9 步汇总为残留 |
| 6 | `capture_sessions` | 对仍注册的 session：`revoke` → `adapter.drop_session`（单个 10s）→ `unregister` | `capture_sessions`=20 | 单个失败不阻断其余；超时被取消时 finally 仍注销；失败清单进 `residue.sessions_drop_failed` |
| 7 | `capture_registry_close`（control） | `registry.close()`：HTTP guard 对一切请求 403、`register` 拒绝 | 1 | 拆成独立步的原因：第 6 步超时被取消时 registry 必须仍然关上（测试 `..._slow_component_timeout_secondary` 钉死） |
| 8 | `adapter_http` | `asyncio.to_thread(app_handle.stop)`（aiohttp runner.cleanup + loop.stop + join） | `adapter_http`=20 | 线程未起/已停 → `skipped`；停后仍存活记 `residue.adapter_thread_alive` |
| 9 | `container_residue` | 只记事实：orchestrator `cleanup_quarantine`（B5 故意保留的现场）、评分容器未移除清单、评分清理失败 | 10 | 不做 docker 调用；run-label 兜底归 launch trap（§4） |
| 10 | `resource_closure`（evidence） | 一次性取数写 `resource_closure.json`（§5） | `resource_closure`=15 | 失败只记 evidence 失败 |
| 链外 | 报告落盘 | 原子写 `shutdown_report.json` + 追加 `shutdown_completed` 事件；`lifecycle.mark_closed()`；单例状态置 `CLOSED`；卸载 SIGTERM 处理器 | — | 写失败记 `evidence_failures`；`close()` 永不抛 |

首因规则：触发关停的异常（run-fatal / 信号）若在场即为 `first_cause`（`first_cause_origin=trigger`），否则第一个失败/超时步是首因；
之后的一切失败进 `secondary_failures`。`report.ok` = 清理步全绿 ∧ 无残留 ∧ 证据全部写成功 ∧ 触发不是故障（H9 口径：就绪稿 §2.6
"任何兜底后仍未清的 container、open session、未终结请求、后台 task 或 evidence flush 失败都使资格作业失败"）。

幂等：首次 `close()` 创建 `rh2-bringup-shutdown` task，后续调用（含并发、含 run-fatal 与 SIGTERM 同时触发）等待同一 task 并拿到
**同一个** `ShutdownReport` 对象；调用方被取消不取消关停链（`asyncio.shield`）。

## 2. 关闭后禁 submit 的拒绝点（全部 `ServiceClosedError`，`reason_code = <face>_rejected_service_closed`）

| 面 | 位置 | 生效时刻 | 语义 |
|---|---|---|---|
| `task_resolve` | `BringupService._resolve_task` → `LifecycleState.enter_execution` | 第 1 步起 | 在 orchestrator 建 audit 之前抛出：被拒执行**不留任何 audit/receipt**，只在报告 `rejected_after_close` 计数。异常沿 `rh2_custom_generate` → `Rh2MilesGenerateFn` 原样传播（不是 abort 形状，不产 ABORTED 样本——那是 disposition） |
| `grading_submit` | `BringupService._grading_submit` | 第 4 步起（比停收晚：在飞执行在宽限期内仍要交评分） | typed 拒绝 |
| `bringup_get` | `BringupService.get()` | 链跑完、单例状态 `CLOSED`（sticky） | `ensure_fa_started` / `generate()` 入口再来即拒，同进程不建第二代 |
| `capture_register` | `CaptureRegistry.register` | 第 7 步起 | 新 session 无法登记 |
| HTTP guard | `build_session_guard_middleware` | 第 7 步起 | 任何模型调用 403 `rh2_service_closed` + `x-should-retry: false`（`/healthz`、`/v1/models` 仍放行） |
| `grading_manager_grade` | `SWEGradingManager.grade` | 第 5 步起 | 纵深防御：不再起评分容器 |

## 3. 异常关闭：run-fatal 通道与 SIGTERM

- **run-fatal**：`LifecycleState.enter_execution` 把通知器挂到执行 task 的 context（复用 `async_worker.fatal_halt_notifier`——
  generate.py `_notify_fatal_halt` 在进入异步 cleanup **之前**同步调它，这是既有调用点，未改 generate.py）。
  `BringupService._on_run_fatal` 首次 fatal 即调度关停链（首因 = 该 fatal，`trigger=run_fatal`）。既有通知器（冻结回退面
  worker 的 `_note_fatal`）被链式保留；同一 task 顺序执行多次不叠链。**B5 纪律不变**：fatal 的执行自己在 finally 里先
  `persist_receipt` 再清理，关停链的第 3 步只是等它跑完（在飞宽限期内它必然先完成）。
- **SIGTERM**：`install_signal_shutdown(loop, on_signal)` 经 `loop.add_signal_handler` 调度 `close(reason="signal:SIGTERM", trigger="signal")`；
  关停完成后卸载处理器（第二个 SIGTERM 按默认处置真退出）。**opt-in**：`RH2_SHUTDOWN_ON_SIGTERM=1` 时 `ensure_fa_started`
  才安装（理由见 §6 第 4 条）。测试用真实 `os.kill(SIGTERM)` 触发。
- **取消路径的事实**：取消的在飞执行由 generate.py 既有 `except CancelledError: raise` → finally 产 receipt
  `attempt_disposition=cancelled`（不产 Outcome v2）；关停报告只记 `owner_cancelled`（`TERMINATION_KINDS_CONTROL`，
  导入期核对词汇在场）+ `completion_class=missing` + 在飞秒数 + 是否在等待内跑完。**没有 disposition 字段**（A5 归 C），
  测试断言事实 dict 的键不含 disposition/keep/drop/admission 词根。

## 4. campaign supervisor → launch trap + run-label 残留检查

没有常驻进程。两条命令，一个 shell 入口：

```bash
# 清理（先记后删）：只动带本 run label（rh2.run_id=<run_id>）的容器 + 显式 glob 的临时目录
python3 rh2/src/repoharness2/shutdown/run_residue.py cleanup --run-id "$RUN_ID" \
    --docker-bin "$DOCKER_CLI_DIR/docker" --out "$EV/run_residue_cleanup.json" [--tmp-glob '/tmp/rh2-<run_id>-*']
# 检查：列出残留即非零；docker 查询失败也非零（查询失败 ≠ 零残留）
python3 rh2/src/repoharness2/shutdown/run_residue.py check --run-id "$RUN_ID" --docker-bin ... --out "$EV/run_residue_check.json"
# 二合一（launch.sh 侧一行接线，W7 owner 落地）：
trap 'bash "$RH2/scripts/rh2_run_trap_cleanup.sh" "$RUN_ID" "$DOCKER_CLI_DIR/docker" "$EV"' EXIT
```

退出码：0 = 清理成功且零残留；1 = 残留 / 删除失败 / 查询失败；2 = 用法错误。归属锚点与既有 `postrun_probes.py` shutdown
探针一致（`MILES_RH2_RUN_ID` 下发后 rollout/评分容器都盖 `rh2.run_id` label）。不带 label 的旧容器不在本入口归属范围
（那是 postrun 探针按名字前缀兜底的面，两者互补不重叠）。RH2 目前不在宿主上创建 per-run 临时目录，`--tmp-glob` 不传 = 该面不适用。

## 5. 资源闭包一次性取数：`resource_closure.json`（schema_id `rh2.resource_closure_facts.v1`）

关停链第 10 步写出；也可在启动时用同一函数取一次（`phase="startup"`）。不是监测面，无采样循环、无阈值判定。

| 字段 | 内容 |
|---|---|
| `phase` / `taken_at_utc` / `platform` / `pid` | 取数时点 |
| `peak_rss_bytes` | `ru_maxrss`（Linux KiB→字节归一；macOS 本就是字节） |
| `memory_upper_bound.inputs` | `MemoryBoundInputs`：`max_concurrent_executions`（`async_max_concurrent_samples` 或 `rollout_batch_size×n_samples_per_prompt`）、`grading_concurrency`（RH2_FA_LIMIT_GRADING）、`model_call_limit`、`max_turns_per_execution`（RH2_MAX_TURNS_PER_SID）、`max_new_tokens_per_turn`（`rollout_max_response_len`）、`max_context_tokens`、`top_k_support`（mask 引擎取 `rollout_top_k`，dense top-p tape 记 1）、`max_attempts_retained`（`num_rollout×batch×n×2`，×2 = retry 余量）；缺任何一项 → `status=unavailable` + `missing_inputs`，**不猜** |
| `memory_upper_bound.coefficients` | 每 token/每轮/每 attempt 累积/每评分在飞的保守字节系数与 Python 开销倍率（全部故意偏大） |
| `memory_upper_bound.{live_per_execution,live_total,process_bounded,retained_total,upper_bound}_bytes`、`upper_bound_gib` | 公式：`upper = 并发×每执行在飞 + 评分并发×每评分 + proxy 有界缓存 + max_attempts_retained×每 attempt 累积` |
| `memory_upper_bound.unbounded_collections` | 生产代码里**无上界**的集合名（见下） |
| `growth_collections.<name>.{owner,attr,bounded,length,note}` | 关停时刻各集合实际长度：`orchestrator_audits`/`orchestrator_outcomes`/`orchestrator_cleanup_quarantine`/`grading_manager_records`/`grading_manager_leases`/`grading_manager_cleanup_failures`/`grading_queue_events`（无上界）；`proxy_audit_artifacts`/`proxy_attempts_ledger`/`registry_hooks`/`poison_archive`（有上界） |
| `fsync_latency` | 16 个 4 KiB 文件各走"写→fsync 文件→os.replace→fsync 目录"（与 `FileFinalizationStore._write_once`/audit sink 同一套系统调用）：`per_op_ms`、`p50/p95/p99/max_ms`、`fsync_only_p50/max_ms`；探针文件用完即删 |

盘点结论（就绪稿 §2.8 第 1 条）：`RolloutOrchestrator.audits`（generate.py:2279，每 attempt append 且 `record_event` 逆序全扫）、
`.outcomes`、`SWEGradingManager._records/leases`、`GradingQueue.events` 在生产路径上只增不裁。按上界公式 30~50 step 是否可接受由
W7 judge 拿 `resource_closure.json` 判（本包只出事实与公式，不定阈值）。裁剪/流式化归 generate.py/manager.py 所有者，见 §8。

## 6. T1 决策及理由

1. **`lifecycle.py` 处置 = 删除后重写，不改造**。原型的三类扫账（DISPATCHED→CRASHED_BEFORE_PUT 等）绑定的是未采用的
   governed ledger（06 §5 第 4 条：C3/C7 原型可保留为 spike-only 或单独清理），与真实组件（队列/线程/容器/registry）无关，
   没有可复用的关闭逻辑；两套并存违反"不得留两套"。随之删除其两个测试（`test_governance_receipts_lifecycle.py` §4）与
   conftest/`__init__` 导出；`attempt_ledger.py`/`governed_buffer.py` 原型**未动**（不在本包范围）。
   **提交建议**：原型删除（lifecycle.py + 三处引用摘除）与关停链新增分开提交（06 §5 第 4 条"不得与生产链改动混同一 commit"），
   两者互不依赖。
2. **新代码放 `repoharness2/shutdown/` 独立包**而非 `adapters/miles`：链本身零 miles/slime import，普通 lane（无 vendor 世界）
   即可全量单测；具体顺序装配留在组件所有者 `bringup.py`。
3. **关闭后拒绝 = typed 异常，不是 abort 形状/ABORTED 样本**：给关停后到达的执行编 Outcome/disposition 属于训练语义（A5 归 C），
   且 miles 会把 ABORTED 当普通缺员回收/补采——在关停时补采是错的。异常沿 miles 每样本 task 传播，producer worker 随之退出，
   这正是就绪稿 §2.6 "停止 producer 新 submission" 在只读 miles 代码下能得到的效果。
4. **SIGTERM 接线 opt-in（`RH2_SHUTDOWN_ON_SIGTERM=1`）**：Ray worker 进程有自己的 SIGTERM 处置，`loop.add_signal_handler`
   会整体替换；在 GPU 段验证 Ray 组合之前不默认覆盖运行边界。机制与测试已落地，开关一行。
5. **评分门晚于停收门**：`grading_submit` 在第 4 步才拒绝——第 3 步宽限期内自然完成的执行还要把评分提交完，否则宽限期没有意义。
6. **`capture_registry_close` 拆成独立小步**：drop 超时（`wait_for` 取消）不能连带跳过 registry 关闭；测试钉死。
7. **`close()` 永不抛**：调用方几乎总在 `finally` 里，抛异常会顶掉真正首因；`report.ok`/`first_cause` 承担判定。
8. **隔离容器（`cleanup_quarantine`）进程内不删**：那是 B5 故意保留的现场（receipt 写失败）；关停报告如实列为残留（H9 应判失败），
   共享 GPU 机上的最终清除交给 launch trap（它先把名字记进报告再 `rm -f`，receipt/audit 证据本来就在 artifact 目录）。
9. **run-label 兜底只动带本 run label 的容器**（不做年龄式孤儿清扫、不按名字前缀）：同宿主其他 run 的容器绝不能被误删；
   无 label 旧容器由既有 postrun 探针兜底。`run_residue.py` 纯 stdlib、可按文件路径运行——trap 触发时 PYTHONPATH 未必就位。
10. **超时默认值**：`inflight_grace=30`（远小于 600s agent 预算：关停不等 rollout 自然结束）、`inflight_cancel_wait=150`
    （≥ generate.py cleanup 120s + drop 5s，否则取消后的 finally 没跑完就被记成残留 = 假红）；其余 10~60s。全部可 env 覆盖。
11. **资源上界的 `max_attempts_retained = num_rollout×batch×n×2`**：×2 是 retry 余量（B 包 unused handler 若选 drop 则偏大，
    偏大是设计方向）；miles args 缺任一项就 `unavailable`，不猜默认。
12. **测试 oracle 变更登记**（review-standards §7）：删 2 个原型测试；`test_governance_receipts_lifecycle.py` 文件名保留（git 历史）。
13. **`ShutdownReport`/`resource_closure`/`run_residue` 的 schema_id 只是 evidence 文件的判别字段**，未注册到 `registry.py`
    （不在本包所有权），不是训练语义契约——与 W1b 报告 §4 第 6 条同处理方式。

## 7. 偏离说明

- 06 W5a 行写"依次关闭 grading/capture wire/HTTP 代理/容器与 workspace/evidence sink"：本实现里**没有一个可 flush 的 evidence sink
  对象**——bringup 的 events/audit/model_call_audit 全是逐条即时落盘（write+fsync）。"evidence flush"因此具体化为三件事：
  `shutdown_started` 事件、`resource_closure.json`、`shutdown_report.json`+`shutdown_completed` 事件；负例测试把三者全部弄成不可写，
  断言清理步照做。
- "容器与 workspace"一步在进程内只记事实（第 9 步）：rollout 容器由各执行的 finally 按 B5 顺序清理（取消路径亦然），评分容器由
  第 4/5 步清理；进程内不再按 label 扫 docker（避免与 trap 入口两套实现）。
- "campaign supervisor"完全不存在了：没有守护进程，也没有"人工强杀后记成功"的口子——检查项只看 docker 事实。
- 未改 `experiments/miles_gpu_spike/launch.sh`（不在本包所有权，W7 owner）：trap 行与 post-run 步骤写在 §9 接缝。

## 8. 开放问题

1. **`RolloutOrchestrator.audits` 等无上界集合**（generate.py:2279、manager.py `_records/leases`、queue.py `events`）：本包只盘点 +
   一次性取数；是否按有界窗口裁剪/流式写出归各文件所有者（generate.py 不在本包所有权），建议 W7 judge 先读
   `resource_closure.json` 的实测长度再定（就绪稿 §2.8 第 1 条"要么证明上界可接受，要么流式写出"二选一未定）。
2. **miles 侧接线未做**（只读代码）：`RolloutManager.dispose()` 不会调我们的 close；集成者一行接线见 §9。在此之前，
   run-fatal/SIGTERM 触发的自动关停已生效，但 train driver 正常结束（`dispose`）不会走链——只靠 launch trap 兜底。
3. **取消 miles 每样本 task 的连锁**：取消/拒绝会让 `FullyAsyncRolloutFn._worker_loop` 以异常退出、`_next_group` 向 train driver 抛错。
   关停时这是预期结果，但 GPU 段要核实 train driver 在 `dispose` 之后不会把它记成训练失败（与 H9 判据的交互）。
4. **Ray + SIGTERM 组合**只有 CPU 真信号测试；opt-in 直到八卡验证。
5. **H9 的 Ray actor / SGLang / CUDA 面**不在本包：仍由 `postrun_probes.py` shutdown 探针（ray list actors）覆盖，本包不重复。
6. **同工作树并行**：本轮实现期间另一 agent 在同一 worktree 改 `generate.py`/`gate.py`/`governance/`/多份测试（W1b 第二段）。
   我的在位全量跑受其中间态影响（一度 `tests/governance` 收集错误、W1a/W1b 测试红）；归因方法与干净副本结果见 §10。
7. **lanes manifest**：计数变化见 §10，由集成者改 `integration_base_manifest.json`。

## 9. 接缝

1. **进程级关停入口**（集成者一行）：
   ```python
   from repoharness2.adapters.slime.bringup import close_bringup_service
   await close_bringup_service(reason="rollout_manager_dispose")   # 幂等；从未启动返回 None
   ```
   放在 miles integration 分支的 `RolloutManager.dispose()`（需改成 async 或在 actor loop 上调度）或 `train_async.py` 的
   `finally`（`await eval_dispatcher.drain(); await rollout_manager.dispose.remote()` 之前）。不需要 service 对象、不需要 args。
   **generate_fn 钩子：不需要**——`Rh2MilesGenerateFn` 的懒 bootstrap 不改；若集成者偏好按 args 传递，可在 `ensure_fa_started`
   末尾加 `args.rh2_shutdown = service.close`（一行，未做：避免把绑定方法挂到可能被 Ray 序列化的 args 上）。
2. **launch.sh**（W7 owner）：run 段 `mkdir -p "$EV"` 之后加
   `trap 'bash "$RH2/scripts/rh2_run_trap_cleanup.sh" "$RUN_ID" "$DOCKER_CLI_DIR/docker" "$EV"' EXIT`；或作为 post-run 第 3.5 步
   `postrun_step run_residue bash "$RH2/scripts/rh2_run_trap_cleanup.sh" "$RUN_ID" "$DOCKER_CLI_DIR/docker" "$EV"` 并把 `run_residue`
   加进 FINAL_RC 的必需集合。Ray runtime env 可加 `RH2_SHUTDOWN_ON_SIGTERM=1`（GPU 段验证后）。
3. **W7 judge 读取面**：`$ARTIFACTS/shutdown_report.json`（`ok`、`first_cause`、`residue.*`、`rejected_after_close`、每步 status/seconds）、
   `$ARTIFACTS/resource_closure.json`（§5）、`$EV/run_residue_check.json`（`ok`、`residue_count`、`containers`）。
4. **lanes manifest**（集成者）：lane A `285p/217s → 284p/217s`；lane B `502p/0s → 501p/0s`（−2 原型测试 +1 vendor 关停测试；其余
   27 个新测试在 `tests/adapters/`，不进 lanes）。
5. **env 旋钮清单**（消费者均在 bringup.py）：`RH2_SHUTDOWN_INFLIGHT_GRACE_SEC`、`RH2_SHUTDOWN_INFLIGHT_CANCEL_WAIT_SEC`、
   `RH2_SHUTDOWN_GRADING_DRAIN_SEC`、`RH2_SHUTDOWN_GRADING_MANAGER_SEC`、`RH2_SHUTDOWN_CAPTURE_SESSIONS_SEC`、`RH2_SHUTDOWN_ADAPTER_HTTP_SEC`、
   `RH2_SHUTDOWN_CONTAINER_RESIDUE_SEC`、`RH2_SHUTDOWN_RESOURCE_CLOSURE_SEC`、`RH2_SHUTDOWN_EVIDENCE_SEC`、`RH2_SHUTDOWN_ON_SIGTERM`。

## 10. 测试证据（2026-09-02 实跑）

| 测试 | 验收项 |
|---|---|
| `test_chain_bounded_timeout_first_cause_and_continuation` | 慢 close 替身（sleep 10）在 0.2s 上界被截断、整链 <2s；失败/超时后步骤照跑；无触发异常时第一个失败步是首因、其后次生；触发异常在场时它才是首因 |
| `test_chain_evidence_failure_does_not_block_cleanup_and_skips_are_not_failures` | evidence 步失败，cleanup 步照做；`ok=False` 但 `cleanup_clean`；skipped 不算失败 |
| `test_shutdown_timeouts_from_env` | env 覆盖 + 非法值拒绝 |
| `test_lifecycle_state_gates_and_inflight_table` | 在飞登记/注销；停收后 `task_resolve` typed 拒绝；评分门独立；拒绝计数 |
| `test_fatal_channel_reaches_lifecycle_notifier_and_chains_previous` | `RolloutOrchestrator._notify_fatal_halt` → 我们的通知器；既有通知器链式保留；同 task 不叠链 |
| `test_inflight_grace_lets_execution_finish_without_cancel` | 宽限内自然完成 → 不取消 |
| `test_inflight_unfinished_after_cancel_wait_is_reported_as_residue` | 吞掉取消的执行 → `unfinished_after_cancel_wait` 残留，等待有界 |
| `test_inflight_cancel_persists_receipt_before_cleanup_and_records_owner_cancelled` | 真实 `RolloutOrchestrator`（fa_formal）在 harness 阶段被取消：`persist_receipt` 先于 `docker rm`；receipt `disposition=cancelled`、无 Outcome v2；事实 = `owner_cancelled`/`missing`，键无处置词根；容器与会话已清 |
| `test_bringup_close_normal_closes_all_components_and_is_idempotent` | 正常关闭：队列 worker 清空、manager gc 真删记账容器、残留 session drop+注销、registry 关、线程 stop 一次、事件/报告/资源闭包三份 evidence 在场；二次 `close()` 同一对象且不二次 stop；`_resolve_task`/`_grading_submit`/`BringupService.get` 三点 typed 拒绝 |
| `test_registry_closed_rejects_register_and_http_guard` | `register` 拒绝；guard 403 `rh2_service_closed`、`x-should-retry: false`；`/healthz` 放行 |
| `test_grading_manager_close_gcs_records_and_rejects_grade` | manager close gc + 幂等 + `grade` typed 拒绝 |
| `test_close_bringup_service_without_instance_returns_none` | 进程级入口无单例 → None |
| `test_bringup_close_evidence_failures_do_not_block_cleanup`（负例） | 事件文件/报告文件/资源闭包文件全部不可写：四处 evidence 失败记录，容器/会话/线程照清，`cleanup_clean` 且 `residue_free`，`ok=False` |
| `test_bringup_close_fatal_first_cause_kept_slow_component_timeout_secondary`（异常关闭） | run-fatal 通知自动调度关停；首因 = fatal；慢 `drop_session`（30s）在 0.3s 上界超时记次生；registry 仍关；后续步照跑；整链 <5s |
| `test_sigterm_triggers_shutdown_chain` | 真 `os.kill(SIGTERM)` → 关停链；`trigger=signal`；完成后恢复 `SIG_DFL` |
| `test_w5a_run_residue.py`（7） | 桩 docker（状态文件 = 伪容器句柄）：cleanup 先记后删 + 临时目录真删 + 别的 run 目录不碰 → check 零残留；check 列残留非零；docker 失败 ≠ 零；rm 失败进报告且 check 仍看见；只动本 run label、空 run_id 拒绝；`rh2_run_trap_cleanup.sh` 端到端（干净 rc=0 / 残留 rc=1 / 用法 rc=2）；模块按文件路径独立运行 |
| `test_w5a_resource_closure.py`（5） | 上界公式逐项可核、并发/累积项单调、未知上下文估法；输入校验；真实磁盘 fsync 单次测量；增长集合盘点覆盖全表且缺席记 None；原子写 + `unavailable` 如实 |
| `test_w5a_bringup_close_vendor.py`（vendor lane） | 真实 `BringupService`（真 tokenizer/AnthropicAdapter 线程/capture wire/评分队列）：关停后端口拒连、线程停、`get()` 拒绝、进程级入口幂等、三份 evidence 在场、上界输入来自真实 args |

计数（干净副本 = 仅含本包改动、其余路径回到 HEAD，对同一 venv 与 `reference/` 运行）：

- `uv run pytest tests/ -q`：**1456 passed, 232 skipped**（基线 1430/232：−2 原型测试 +28 新测试）。
- lane A（`pytest tests/adapters_miles/ -q`，pin base）：**284 passed, 217 skipped**；`-m "not integration_base"` 零 skip。
- lane B（`RH2_MILES_PATH=reference/miles-rh2-integration`）：**501 passed, 0 skipped**。
- `bash scripts/miles_integration_lanes.sh`（在位）：前置四项校验全过，lane A 实跑 284p/217s，在 manifest 计数断言处按设计变红
  （expected 285p/217s）——manifest 由集成者改。
- `uv run ruff check src tests scripts`：All checks passed。

在位（live worktree，含另一 agent 未提交的 W1b 第二段改动）：本包 4 个新测试文件 + 改动过的
`test_governance_receipts_lifecycle.py` 全绿；全仓在位结果随对方中间态波动（一度 `tests/governance/test_wrapper_finalize.py`
收集错误、`test_w1a_formal_chain`/`test_w1b_prepared_chain` 红），与本包改动无关（干净副本全绿可证）。

## 11. 协作协议五段收尾

**① 待拍板 T0：无。** 未改 `contracts/`、训练准入/reward/loss、公共 schema；未新增会产生样本偏置的拒绝路径（关停后拒绝的
执行不形成任何对象，不进训练也不做 disposition；取消的在飞执行偏向长任务这一点是任何关停的固有性质，只记事实）；未引入依赖/服务/
常驻进程；未降低安全边界（HTTP guard 只多了一条 403 分支）。

**② T1 决策及理由**：§6 第 1~13 条（含 lifecycle.py 删除、SIGTERM opt-in、typed 异常而非 abort 形状、隔离容器进程内不删）。

**③ 临时挡板新增/命中/解除**：无新增；`bringup.py:705-715` fa_formal 挡板原样；`RH2_SHUTDOWN_ON_SIGTERM` 是永久 opt-in 开关不是挡板。

**④ 推翻或修正了哪些旧结论**：
- `generate_fn.py` 第 80-84 行注释"关闭 hook 说明（有意留给进程退出路径）……正式关停语义归硬件段的 close/dispose seam"——
  该 seam 现已在 CPU 段落地（注释未改：generate_fn.py 不在本包所有权，建议集成者顺手改一行）。
- spike-log C7 条目"lifecycle.py（131 行）shutdown = 停新 submission→cancel await 在飞→三类扫账→close hooks→幂等"：原型删除，
  语义由本包取代（三类扫账随 governed ledger 一起不采用）。
- 就绪稿 §2.6 "campaign supervisor 对本 run label 做一次有界兜底清理与残留核对"：按 06 W5a 行缩为 trap 入口 + 检查，无 supervisor。

**⑤ 测试/证据/账本状态**：§10。

**本轮没有改变哪些已定案语义**：B5 receipt→cleanup 顺序（取消路径亦由 generate.py 既有代码保证，本包只等待）；核心 admission
sidecar 写失败的 run-fatal 语义（切片一修复轮已定，未动）；A5 disposition（未实现，取消事实无处置字段）；W1a 六字段身份与 F4
绑定；W2a 视图/controller；fa_formal 挡板；s1_compat 行为（关停面对三种模式一致，s1 无 finalization store 时 `grading_queue`
等步按事实 skipped）；`contracts/`、`reference/`、`generate.py`、`generate_fn.py`、`gate.py` 零改动。
