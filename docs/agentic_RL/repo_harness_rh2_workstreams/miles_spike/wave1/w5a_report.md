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

## 12. 追加修正节（2026-09-02，codex 复核 #1 / #3 / #7 后；append-only，本节口径覆盖上文冲突处）

### 12.1 #1：接入 miles 生产退出链（miles 侧窄 commit + rh2 接线）

上文 §9 第 1 条"集成者一行 `close_bringup_service()`"**不成立**（codex 核实：`FullyAsyncRolloutFn` 无 close 面、
`_worker_loop` 是 `while True`、`dispose()` 不碰 rollout fn、`train_async.py` 异常退出不调 dispose）。修复 = 只改
`reference/miles-rh2-integration` 工作树（**未在该仓 commit**，由集成者 commit / format-patch / 更新 manifest）：

| 文件 | 改动 |
|---|---|
| `miles/rollout/fully_async_data_buffer.py` | 新增 `DataBufferClosed(op)`；`DataBuffer.aclose()` 默认 no-op（custom buffer 不破）；`DefaultDataBuffer`：`_closed` 标志、`aclose()`（置位 + `notify_all`，幂等）、`closed` 属性；`put()` 入口/等待循环/被唤醒后、`get()` 循环顶/被唤醒后都检查 closed 并抛 `DataBufferClosed`（关闭后 buffer 内已有的组也不再交出） |
| `miles/rollout/fully_async_rollout.py` | 新增 `RolloutFnClosed(op)`；`_active_groups`（worker 用同一 set 对象，`active.difference_update(done)` 取代重新赋值）、`_closed`、`_close_report`；`__call__`/`_submit_one_group`/`_next_group` 关闭后 typed 拒绝（`_next_group` 里 worker 被取消时报 `RolloutFnClosed` 而不是把 CancelledError 漏给调用方）；`aclose()`：置 closed → cancel+await `_worker` → cancel+await 全部 active group task → `buffer.aclose()`；报告 `worker_state/worker_exception/active_groups_cancelled/buffer_closed`，**worker 自己的异常对象保留**（filter fatal 在 put() 内抛 → worker 以它结束）；永不抛，幂等 |
| `miles/ray/rollout/rollout_manager.py` | `dispose()` 改为 `async def`：先 `await generate_rollout.aclose()`（取 `worker_exception`）→ `await close_bringup_service(reason="rollout_manager_dispose", first_cause=worker_exception)`（`ImportError` = 无 rh2 则跳过）→ 原有 data_source/analyzer/metric/eval/monitor 关闭；每段 `except Exception` 记日志不掩盖首因，异常路径也走完 |
| `train_async.py` | 训练循环 + `eval_dispatcher.drain()` 包进 `try`；`finally` 里 `await rollout_manager.dispose.remote()`（正常/异常路径都执行）；已在异常退出时 dispose 再失败只记日志（`sys.exc_info()` 判定），正常路径失败照抛；`import sys` |

关停顺序最终形态：**train driver finally → `RolloutManager.dispose()` → ① `rollout_fn.aclose()`：停新提交 → cancel/await worker →
cancel/await active group → `buffer.aclose()` 唤醒 put/get waiter（`DataBufferClosed`）→ ② `close_bringup_service(first_cause=worker_exception)`：
§1 十步链（在飞执行等/取消 → 评分队列/容器 → capture 会话/registry → adapter HTTP → 残留事实 → 资源闭包）→ 完成事件 → 吸收
关停期 fatal → 最后落盘 `shutdown_report.json` → ③ miles 原有 dispose → ④ launch trap run-label 兜底 + 检查。**
关闭后 typed 拒绝面新增：`RolloutFnClosed`（train/eval/submit/get）、`DataBufferClosed`（put/get）。

rh2 侧：`close_bringup_service(first_cause=...)` 接受异常或字符串；有 first_cause 且 trigger 未指定时记 `run_fatal`。

### 12.2 #3：两条假绿路径 + 执行外 fatal 通道

- (a) **完成事件写失败不进磁盘报告**：`_run_close` 顺序改为 完成事件 → 吸收关停期 fatal → **最后**原子写 `shutdown_report.json`；
  报告文件自身写失败只能留在内存报告与 stdout（无法自证）。
- (b) **关停期间的 run-fatal 被丢弃**：`_on_run_fatal` 在关停进行中把 fatal 排进 `_fatals_during_close`；`_run_close` 在链前、链后、
  完成事件后三处 `_absorb_fatals_during_close`（首因为空则成为首因 `run_fatal_during_shutdown`，否则记次生；`ok` 必为 False）。
  报告定稿后到达的 fatal 只留 `lifecycle.fatal_seen`。
- **filter fatal 通道**：两条路径都接上——① 生产路径：`GroupAdmissionFatal` 在 miles `put()` 内抛 → worker 以它结束 → `aclose()`
  保留为 `worker_exception` → `dispose` 作为 `first_cause` 传给 rh2 关停链（不需要改 group_admission.py）；② 进程内即时路径：
  新增 `bringup.notify_run_fatal(exc)`（无服务返回 False），供复合 filter 在 `except GroupAdmissionFatal as exc: notify_run_fatal(exc); raise`
  处调用——**这一行在 `adapters/miles/group_admission.py`，归另一 agent，本轮未改**；不接它时路径 ① 仍成立（差别只是关停由
  driver finally 触发而非 put() 时刻）。
- 测试：`test_completed_event_write_failure_is_reflected_in_disk_report`、`test_run_fatal_during_close_lands_in_final_report`、
  `test_notify_run_fatal_triggers_close_chain_from_outside_execution`、`test_close_bringup_service_forwards_first_cause_from_miles_dispose`
  （`tests/adapters/test_w5a_shutdown_chain.py`）；`test_rollout_fn_aclose_preserves_worker_exception_as_first_cause_for_rh2`
  （`tests/adapters_miles/test_w5a_miles_dispose_chain.py`，真实 `DefaultDataBuffer.put()` 内 filter 抛 fatal → 端到端到 rh2 磁盘报告）。

### 12.3 #7：`memory_upper_bound` → `memory_estimate`（口径修正，schema v2）

上文 §5 的"保守上界"**不成立**：`num_rollout×batch×n×2` 限制不了 dynamic filter 持续拒绝后的补采总数、漏算已完成 buffer、
Python 对象系数是假设值。修正（不加 attempt cap）：`resource_closure.json` schema_id → `rh2.resource_closure_facts.v2`；字段
`memory_upper_bound` → `memory_estimate`，`status` 恒为 `unbounded_or_unknown`（输入不全为 `unavailable`），新增
`unconstrained_sources`（attempt 无上限 / buffer 已完成组 / Python 系数假设 / 进程外内存）、`buffer_bytes`
（`buffer_capacity_groups=capacity_factor×batch` × `samples_per_group` × 每样本）、`retained_planned_bytes`（`planned_attempts=steps×batch×n`
是计划量非上限，去掉 ×2）、`estimate_bytes/estimate_gib`；`MemoryBoundInputs`/`estimate_memory_upper_bound` →
`MemoryEstimateInputs`/`estimate_memory`。GPU 验收改看 `peak_rss_bytes`、`growth_collections.<name>.length`（已有字段保留）与增长趋势。

### 12.4 测试/证据（2026-09-02 实跑，同一 worktree 含另一 agent 已提交的 W1b 第二段）

- `uv run pytest tests/ -q`（默认 pin）：**1580 passed, 236 skipped**（含本节新增：`tests/adapters` +4，`tests/adapters_miles/test_w5a_miles_dispose_chain.py` 4 例 integration_base 在 pin 记 skip）。
- lane A（pin）：**321 passed, 221 skipped**（`-m "not integration_base"` 零 skip；较 manifest 308p/217s：+13 = 另一 agent 本轮新增？——
  以集成者实跑为准；本包净变化 = +0 lane A 通过、+4 skip）。
- lane B（`RH2_MILES_PATH=reference/miles-rh2-integration`）：**541 passed, 1 failed** —— 唯一失败 =
  `test_g1_acceptance_events::test_producer_tree_digest_matches_audit_manifest`（integration 工作树含本节未提交的 miles 改动，源码树
  digest ≠ manifest；集成者 commit + 更新 manifest 后消失）。本包净变化 lane B = +4。
- `bash scripts/miles_integration_lanes.sh`：未跑（集成树不干净，前置校验必红，预期）。
- `uv run ruff check src tests scripts`：All checks passed。

### 12.5 五段收尾（本节）

① 待拍板 T0：无（miles 侧改动是关停/退出路径，不改训练语义；`DataBuffer.aclose` 默认 no-op 不破 custom buffer 契约；口径改名不改事实）。
② T1：dispose 改 async（async actor，`train.py` 的 `await dispose.remote()` 同样可用）；`_next_group` 把 worker 取消映射为 `RolloutFnClosed`；
关闭后 buffer 内已有组不再交出；`notify_run_fatal` 提供但 group_admission 侧一行未接（所有权）。③ 挡板：无新增。
④ 推翻：§9 第 1 条"一行接线足够"、§5 "上界"口径、§1 表"链外报告先落盘"三处按本节修正。⑤ 见 12.4。
未改变：B5 顺序、A5 无 disposition、fa_formal 挡板、`contracts/`、W1b 那组文件、`bringup.py:705` 挡板。

## 13. 追加修正节（2026-09-02，codex 对 patch 0010 + 修复轮终核后；append-only，本节口径覆盖 §12 冲突处）

### 13.1 根因：关停在错误的 event loop 上执行

生产拓扑（codex 核实）：`RolloutManager._get_rollout_data` → `asyncio.to_thread(call_rollout_function, …)` →
`compatibility.call_rollout_function` → `async_utils.run(coro)` → 全局后台 `AsyncLoopThread`（`get_async_loop()`）。
所以 `FullyAsyncRolloutFn`、worker task、`DefaultDataBuffer`、以及在首个 generate 内 bootstrap 的 RH2 `BringupService`
**全部属于那个后台 owner loop**；Ray actor 自己的 loop 只是调用方。patch 0010 的 `dispose()` 在 actor loop 上直接
`await aclose()` / `await close_bringup_service()`——跨 loop 的 Task/Future 完成不会唤醒 actor loop（codex 实测要靠外部
0.4s timer 才醒），无 timer 时 `dispose.remote()` 可能永久卡住。§12 的四个单 loop 测试没有复现这个拓扑，**已删除**，
换成 §13.4 的真实双 loop 重放。

### 13.2 miles 侧改动（`reference/miles-rh2-integration` 工作树，未 commit；供 patch 0011 format-patch）

| 文件 | 函数/符号 |
|---|---|
| `miles/utils/rh2_shutdown.py`（**新增**） | `DEFAULT_DISPOSE_TIMEOUT_SEC=900`、`dispose_timeout_seconds(args)`、`close_rollout_fn_and_rh2(generate_rollout, driver_cause, deadline_seconds)`（**在 owner loop 上跑**：`aclose` → 首因 = worker 自己的异常，否则 `driver_cause` → `close_bringup_service(reason="rollout_manager_dispose", trigger, first_cause)`；每段吞异常记 `errors`，永不抛）、`dispose_on_owner_loop(generate_rollout, driver_cause, deadline_seconds, timeout_seconds, args)`（**从 actor loop 调**：`asyncio.run_coroutine_threadsafe(closure, get_async_loop().loop)` → `asyncio.wait_for(asyncio.shield(asyncio.wrap_future(cfut)), timeout)`；超时不抛，返回 `{"timed_out": True, …}`，闭包在 owner loop 上继续跑） |
| `miles/rollout/fully_async_rollout.py` | 新 `DEFAULT_SHUTDOWN_DEADLINE_SEC=60.0`、`shutdown_deadline_seconds(args)`（`args.rh2_shutdown_deadline_sec` → env `RH2_MILES_SHUTDOWN_DEADLINE_SEC` → 60）；`aclose(deadline_seconds=None)`：`asyncio.wait({worker}, timeout=剩余期限)` → `asyncio.wait(active, timeout=剩余期限)` → 报告新增 `worker_unfinished/active_groups_unfinished/deadline_seconds/deadline_exceeded/close_error/elapsed_seconds` → **`finally` 里 `buffer.aclose()`**（超时/异常都关并唤醒 waiter）；到期即放弃、不再等（被放弃的 task 交 RH2 关停链的容器/会话清理兜底）；`import os, time` |
| `miles/ray/rollout/rollout_manager.py` | `dispose(self, driver_cause=None)`：只做 `await dispose_on_owner_loop(self.generate_rollout, driver_cause=driver_cause, args=self.args)`（try/except 记日志）→ 原有 data_source/analyzer/metric/eval/monitor 关闭；actor loop 上不再直接 await 属于 owner loop 的对象 |
| `train_async.py` | `try:` 紧随 `create_rollout_manager(...)` 之后（模型构造、首次 `update_weights`、before-train eval、训练循环全在 try 内）；`finally`：`driver_cause = f"{type(exc).__name__}: {str(exc)[:400]}"`（无异常为 None）→ `await rollout_manager.dispose.remote(driver_cause=driver_cause)`；已带 driver 异常时 dispose 再失败只记日志，正常路径照抛 |
| （不变）`miles/rollout/fully_async_data_buffer.py` | patch 0010 的 `DataBufferClosed` / `aclose()` 原样 |

投回 owner loop 的机制 = 与 `call_rollout_function` 同一条：`get_async_loop()` 的 loop + `run_coroutine_threadsafe`；
调用方用 `asyncio.wrap_future`（内部 `call_soon_threadsafe` 唤醒调用方 loop）+ `wait_for` 总超时等待。

期限与覆盖：rollout fn 取消等待期限 **60s**（`args.rh2_shutdown_deadline_sec` / `RH2_MILES_SHUTDOWN_DEADLINE_SEC`）；
整体闭包（aclose + RH2 关停链）总超时 **900s**（`args.rh2_dispose_timeout_sec` / `RH2_MILES_DISPOSE_TIMEOUT_SEC`；
RH2 链自身各步上界之和约 6 分钟，见 §1）。

driver cause 传递：train driver `finally` 把训练侧异常序列化成字符串 → `dispose(driver_cause=str)` → 闭包里
`first_cause = worker_exception if worker_exception is not None else driver_cause`，`trigger = run_fatal | driver_error | owner_close`
→ rh2 `close_bringup_service(first_cause=…)` → 报告 `ok=false`、`first_cause` = 该串（worker 健康 + 训练侧失败不再产
`ok=true/first_cause=None`）。

rh2 侧唯一改动：`BringupService.install_sigterm_shutdown` 在非主线程 loop（miles 拓扑下 bringup 就在后台 owner loop）
`add_signal_handler` 会 `ValueError`——改为记录 `signal_shutdown_install_error` 不炸 rollout；`RH2_SHUTDOWN_ON_SIGTERM`
opt-in 在 miles 拓扑下**不可用**（信号只能在主线程装；Ray actor 的信号处置归 Ray），登记为开放项。

### 13.3 关停顺序最终形态（取代 §12.1 末段）

train driver `finally`（try 从 RolloutManager 创建后立即开始）→ `RolloutManager.dispose(driver_cause)`（actor loop）→
**投回 owner loop**：① `rollout_fn.aclose(deadline=60s)`：停新提交 → cancel worker 等 ≤ 期限 → cancel active group 等 ≤ 剩余期限 →
到期放弃并记 unfinished → `finally` `buffer.aclose()` 唤醒 put/get waiter（`DataBufferClosed`）→ ② 首因 = worker 异常 ∥ driver cause →
③ `close_bringup_service(trigger, first_cause)`：§1 十步链 → 完成事件 → 吸收关停期 fatal → 最后落盘 `shutdown_report.json`
（全部在 owner loop）→ 调用方经 `wrap_future` 拿到结果（总超时 900s）→ ④ miles 原有 dispose → ⑤ launch trap run-label 兜底 + 检查。

### 13.4 测试（`tests/adapters_miles/test_w5a_miles_dispose_chain.py`，integration_base；owner loop = miles 真实 `get_async_loop()`，调用方 = pytest loop；drain 走 `to_thread(call_rollout_function)`，dispose 走 `dispose_on_owner_loop`）

| 路径 | 测试 |
|---|---|
| ① 正常 worker：dispose 近 0s 完成、无外部 timer | `test_dual_loop_normal_dispose_completes_without_external_timer`（断言 worker 在 owner loop、调用方是另一 loop、elapsed <1.5s、rh2 链 task 在 owner loop、drain 以 `RolloutFnClosed` 退出） |
| ② 取消不响应的 active group | `test_dual_loop_stubborn_active_group_is_abandoned_after_deadline`（`args.rh2_shutdown_deadline_sec=0.5`，吞 CancelledError 的替身：0.4s≤elapsed<3s、`active_groups_unfinished=1`、`deadline_exceeded`、buffer 仍关、RH2 链仍执行） |
| ②′ 整体闭包超时有界 | `test_dispose_on_owner_loop_total_timeout_is_bounded`（挂死 aclose → 0.2s 内返回 `timed_out`） |
| ③ buffer put/get 阻塞 waiter | `test_dual_loop_buffer_waiters_wake_with_typed_error`（waiter 在 owner loop 上阻塞，aclose 后以 `DataBufferClosed(op)` 退出；关闭后已有组不交出） |
| ④ filter fatal | `test_dual_loop_filter_fatal_becomes_first_cause_in_rh2_disk_report`（真实 `DefaultDataBuffer.put()` 内 filter 抛 fatal → worker failed → drain 经 `run().result()` 报 fatal → 首因优先于 driver cause → rh2 磁盘报告 `ok=false`、`trigger=run_fatal`） |
| driver cause | `test_dual_loop_driver_cause_reaches_rh2_report_when_worker_is_healthy`（worker 健康 + driver cause → `trigger=driver_error`、磁盘报告 `ok=false`、`first_cause` = 该串） |
| try/finally 覆盖初始化失败 + dispose 不再在 actor loop 上 await | `test_dispose_owner_loop_and_train_async_try_placement_source_facts`（`create_rollout_manager` 与 `try:` 之间只有注释/空行；`create_training_models`/`update_weights` 在 try 内；dispose 体内无 `await aclose()`/`await close_bringup_service(`；helper 含 `run_coroutine_threadsafe`/`wrap_future`/`wait_for`；`aclose` 的 `finally:` 先于 `await aclose()`） |

计数（2026-09-02 实跑）：`uv run pytest tests/ -q`（默认 pin）**1581 passed, 239 skipped**；lane A **322p/224s**
（`-m "not integration_base"` 零 skip）；lane B **545 passed, 1 failed** —— 唯一失败仍是
`test_producer_tree_digest_matches_audit_manifest`（集成工作树含未提交的 patch 0011 改动，源码树 digest ≠ manifest；
commit + 更新 manifest 后消失）；ruff All checks passed；lanes 脚本未跑（预期红）。本节净变化：miles 测试文件 4→7
（lane B +3，lane A skip +3）。

### 13.5 五段收尾（本节）
① T0：无（退出路径与期限，不改训练语义；期限到期放弃的执行由 RH2 链清理并记残留，不做 disposition）。
② T1：新增 `miles/utils/rh2_shutdown.py` 承载投回机制（RolloutManager 是 Ray actor，测试不可 import，helper 让真实机制可被双 loop 测试驱动）；
期限默认 60s/总超时 900s；worker 自身 fatal 优先于 driver cause；SIGTERM opt-in 在 miles 拓扑不可用（记录不炸）。
③ 挡板：无新增。④ 推翻：§12 单 loop 测试（删除）、§12.1 "dispose 直接 await" 形态。⑤ 见 13.4。
未改变：B5 顺序、A5 无 disposition、fa_formal 挡板、`contracts/`、W1b 那组文件、`rh2/src/slime` vendored 文件（逐字节不动）。

## 14. 追加修正节（2026-09-02，codex 对 patch 0011 聚焦复核后；append-only，本节口径覆盖 §13 冲突处）

### 14.1 缺口：底层已发现关停失败，却没有上提成 run 失败

(a) `aclose()` 报告 `deadline_exceeded / worker_unfinished / active_groups_unfinished / close_error / buffer_closed=false`
时，§13 的闭包只读 `worker_exception`，最终 `shutdown_report.json` 仍 `ok=true`（§13 stubborn 测试只断言"报告存在"，假绿）；
(b) 整体 900s 超时只记 `timed_out`，`dispose()` 正常返回，run 可能以成功退出；(c) driver 异常与 worker 异常同时发生时 worker
覆盖 driver_cause。

### 14.2 miles 侧改动（`reference/miles-rh2-integration` 工作树，未 commit；供 patch 0012 format-patch）

| 文件 | 函数/符号 |
|---|---|
| `miles/utils/rh2_shutdown.py` | 新 `ShutdownFailure(verdict)`（typed run 失败）、`SHUTDOWN_FAILURE_SCHEMA_ID`/`SHUTDOWN_VERDICT_SCHEMA_ID`/`SHUTDOWN_FAILURE_MARKER`、`shutdown_failure_from_aclose(fn_report, aclose_error)`（残留 → typed 失败）、`unfinished_executions_from_failure`（→ rh2 残留行）、`_same_origin(worker_exc, driver_cause)`；`close_rollout_fn_and_rh2` 重写（优先级 + secondary + external_residue + `ok/cleanup_ok`）；`dispose_on_owner_loop` 超时返回失败 verdict；新 `shutdown_evidence_dir()`、`write_shutdown_failure_marker()`、`raise_if_shutdown_failed(verdict, driver_cause, evidence_dir)` |
| `miles/rollout/fully_async_rollout.py` | 新 `_group_facts(prompt_group)`；`_submit_one_group` 把组标识挂到 task（`task.rh2_group_facts`）；`aclose` 报告新增 `active_groups_unfinished_facts`（未完成组的具体标识） |
| `miles/ray/rollout/rollout_manager.py` | `dispose(driver_cause=None)` **返回可序列化 verdict** `{schema_id, ok, cleanup_ok, timed_out, errors, report, original_dispose_error}`；原有 dispose 步骤 try/except 进 verdict；仍不在 actor loop 上 await owner loop 对象 |
| `train_async.py` | `finally`：`verdict = await dispose.remote(driver_cause=…)`（调用失败也折成 verdict）→ `raise_if_shutdown_failed(verdict, driver_cause=driver_cause)`；`import raise_if_shutdown_failed` |

### 14.3 typed 关停失败的结构（`rh2.rollout_fn_shutdown_failure.v1`，可序列化）

```json
{"schema_id": "rh2.rollout_fn_shutdown_failure.v1", "kind": "rollout_fn_shutdown_incomplete",
 "problems": [{"kind": "active_groups_unfinished", "count": 1, "reason": "...",
               "groups": [{"group_index": null, "sample_indices": [0, 1], "instance_id": null, "prompt_id": "pg0", "rh2_prompt_group_id": null}]},
              {"kind": "worker_unfinished" | "close_error" | "buffer_not_closed" | "aclose_raised" | "deadline_exceeded", "reason": "..."}],
 "worker_state": "cancelled|failed|unfinished|returned|never_started", "deadline_seconds": 60.0, "elapsed_seconds": 60.01}
```
进 rh2 报告的形状：`first_cause = "shutdown_failure: {…}"`（trigger=`shutdown_failure`）或 `secondary_failures[] = "secondary: shutdown_failure: {…}"`；
`residue.unfinished_executions[]` 追加 `{"source": "miles_rollout_fn", "reason": "active_group_unfinished_after_deadline"|"worker_unfinished_after_deadline", **组标识}`；
`residue.rollout_fn_shutdown_failure` = 上述对象 → `residue_free=false` → `ok=false`。rh2 侧新增 `close()`/`close_bringup_service()`
参数 `secondary_causes`、`external_residue`（`bringup.py`）。

verdict（`rh2.rollout_shutdown_verdict.v1`）：`ok` = 无 error ∧ 无残留 ∧ rh2 报告 ok ∧ 无任何首因；`cleanup_ok` = 无 error ∧ 无残留 ∧
rh2 清理步全绿/无残留/无 evidence 失败（不看首因）；`timed_out`、`errors`、`primary_cause`、`trigger`、`secondary_causes`、
`worker_fatal_same_origin`、`rollout_fn`、`shutdown_failure`、`rh2{ok,cleanup_ok,first_cause,secondary_failures,residue,evidence_failures}`。

### 14.4 首因 / 次生优先级规则

1. **在途 driver 异常 = primary**（trigger `driver_error`）。
2. worker 自身异常：无 driver 异常时 = primary（trigger `run_fatal`）；有 driver 异常且**同源**（driver 串 = `f"{type(worker_exc).__name__}: {str(worker_exc)[:400]}"`，
   即 driver 看到的就是 worker fatal 的传播）→ 只记一次（`worker_fatal_same_origin=true`，`rollout_fn.worker_exception` 仍保留事实）；
   不同源 → `secondary_causes += "worker_fatal: …"`。
3. typed 关停失败：无其它首因 → primary（trigger `shutdown_failure`）；否则 `secondary_causes += "shutdown_failure: …"`。
4. 全部进 rh2 报告（首因 + `secondary_failures` + 残留）；正常取消路径无任何首因 → `ok=true`。

### 14.5 train_async 非成功退出的形式

`finally` 里 `raise_if_shutdown_failed(verdict, driver_cause=…)`：verdict ok → 无事；**无 driver 异常且 verdict 不 ok → 写
`shutdown_failure.json` 标记（`RH2_SHUTDOWN_EVIDENCE_DIR` → `MILES_RH2_EVENT_DIR` → cwd）+ `raise ShutdownFailure(verdict)`**（typed，
进程退出码非 0）；有 driver 异常 → 只写标记 + 日志，原异常继续传播（cleanup failure 已作为 secondary 进 rh2 报告；报告因超时未产生时
标记文件是唯一可读证据）。`dispose.remote()` 调用本身失败也折成不 ok 的 verdict。

### 14.6 测试（`tests/adapters_miles/test_w5a_miles_dispose_chain.py`，真实双 loop，11 例）

| 验收 | 测试 |
|---|---|
| ① stubborn active group → 最终报告 `ok=false` + 具体残留（sample_indices/prompt_id）+ `ShutdownFailure` + 标记 | `test_dual_loop_stubborn_active_group_fails_final_report_with_concrete_residue` |
| ② worker unfinished → 同上 | `test_dual_loop_worker_unfinished_fails_final_report` |
| ③ buffer close error → 同上（`close_error` + `buffer_not_closed`） | `test_dual_loop_buffer_close_error_fails_final_report` |
| ④ 正常路径整体超时 / 闭包错误 → `ShutdownFailure`（非成功退出）+ 标记 | `test_dispose_timeout_or_closure_error_makes_run_exit_non_success` |
| ⑤ 已有训练异常 + cleanup failure → driver primary、shutdown_failure secondary 持久化、标记文件、不抛新异常 | `test_dual_loop_driver_error_plus_cleanup_failure_keeps_driver_primary` |
| ⑥ 正常取消 → `ok=true`、无标记、不抛 | `test_dual_loop_normal_dispose_completes_without_external_timer` |
| ⑦ driver 与 worker fatal 同时：同源去重 / 不同源双保留 | `test_dual_loop_driver_and_worker_fatal_same_origin_deduplicated`、`test_dual_loop_driver_and_unrelated_worker_fatal_both_kept`（另 `test_dual_loop_worker_fatal_alone_is_primary_first_cause`） |
| waiter 唤醒 / 源码事实 | `test_dual_loop_buffer_waiters_wake_with_typed_error`、`test_dispose_owner_loop_and_train_async_try_placement_source_facts`（dispose 返回 verdict、finally 走 `raise_if_shutdown_failed`） |

计数（2026-09-02 实跑）：`uv run pytest tests/ -q`（默认 pin）**1581 passed, 243 skipped**；lane A **322p/228s**（非 integration_base 零 skip）；
lane B **549 passed, 1 failed** —— 唯一失败仍是 `test_producer_tree_digest_matches_audit_manifest`（工作树含未提交 patch 0012，源码树
digest ≠ manifest；commit + 更新 manifest 后消失）；ruff All checks passed；lanes 脚本未跑（预期红）。本节净变化：miles 测试 7→11（lane B +4，lane A skip +4）。

### 14.7 五段收尾（本节）
① T0：无（退出语义与证据；不改训练语义、contracts、W1b 文件、挡板、vendored slime）。② T1：`ok` 与 `cleanup_ok` 分离
（driver 失败时 cleanup 可能干净，judge 两者都看）；原有 dispose 步骤异常折进 verdict 不再跨 Ray 抛；同源判定用类型名 + 消息前缀。
③ 挡板：无新增。④ 推翻：§13 "stubborn 只断言报告存在"、§13 verdict 缺失。⑤ 见 14.6。

## 15. 追加修正节（2026-09-02，codex 对 patch 0012 复核后；append-only，本节口径覆盖 §12~§14 冲突处）

### 15.1 P1-A：幂等 close 冻结了后到的关停事实（rh2 侧，`bringup.py`）

生产顺序：group filter fatal → `notify_run_fatal()` → BringupService **提前**启动/完成 close → driver `finally` → dispose/aclose
才发现 driver/worker 双因与未完成组。§12 的 `close()` 在 `_close_task` 已存在时丢弃后到的 `secondary_causes`/`external_residue`，
权威 `shutdown_report.json` 与 verdict 矛盾。修复（报告状态所有权 = 这一个 `ShutdownReport`，不加旁路 marker；cleanup 仍只执行一次）：

- 新 `_merge_late_facts(report, first_cause, trigger, secondary_causes, external_residue, phase)`：首次调用与后到调用走同一合并口。
  规则：报告已有首因则**保留**，后到首因记 `late_primary(<trigger>): …` 次生；次生只做**逐字相同**去重（与既有首因或既有
  次生文本完全相同才跳过，`worker_fatal:` 前缀剥掉后比对——不猜同源，宁可重复）；残留并入 `residue.unfinished_executions`
  （逐行去重）+ `residue.rollout_fn_shutdown_failure`；每次并入记 `late_merges[]`（新字段 `{phase, trigger, first_cause,
  secondary_added, residue_rows, at_utc}`，phase ∈ initial / during_close / after_close）。
- **close 进行中**：`close()` 把后到事实放进 `_pending_late_facts`；`_run_close` 在链前、链后、落盘前三处 `_absorb_pending_late_facts`
  （残留因 `report.residue` 链后才装配，链前到达的进 `_deferred_residues`，装配后并入）。
- **close 已完成**：`_amend_completed_report()` 并入同一对象并 `_write_report_to_disk()`——与首次同一路径、tmp+fsync+`os.replace`
  原子重写；`ok`/`residue_free` 是属性，随之重算；重写失败记 `evidence:shutdown_report_rewrite`。
- 闭包（`close_rollout_fn_and_rh2`）读到的 rh2 报告就是合并后的同一对象 → verdict 与磁盘一致。

### 15.2 P1-B：`_same_origin` 子串猜同源（miles 侧，`miles/utils/rh2_shutdown.py`）

新规则：`serialize_driver_cause(exc) = f"{type(exc).__name__}: {str(exc)[:400]}"`（train_async `finally` 改为调用同一函数），
worker 异常按此序列化后与 `driver_cause` **严格全等**才算同源（只记一次）；子串/前缀/空消息一律不算——`RuntimeError("timeout")` 与
`RuntimeError("optimizer timeout after all-reduce")` 是两条原因，都保留。

### 15.3 顺手：vendor ruff

`ruff check --fix`（miles 自身 pyproject 规则）修掉 `rh2_shutdown.py` 的 UP041×2（`except TimeoutError`）与 UP017（`datetime.UTC`）；
五个改动文件（`rh2_shutdown.py`/`fully_async_rollout.py`/`fully_async_data_buffer.py`/`rollout_manager.py`/`train_async.py`）ruff 全绿。

### 15.4 miles 侧改动清单（`reference/miles-rh2-integration` 工作树，未 commit；供 patch 0013 format-patch）

| 文件 | 改动 |
|---|---|
| `miles/utils/rh2_shutdown.py` | 新 `serialize_driver_cause(exc)`；`_same_origin` 改严格全等；ruff 修复（`from datetime import datetime, UTC`、`except TimeoutError`）；`__all__` 增 `serialize_driver_cause` |
| `train_async.py` | `driver_cause = serialize_driver_cause(driver_exc)`（与同源判定同一序列化）；import 同步 |

rh2 侧：`shutdown/chain.py`（`ShutdownReport.late_merges` + `to_dict`）、`adapters/slime/bringup.py`（§15.1；`__init__` 增
`_pending_late_facts`/`_deferred_residues`）。

### 15.5 测试

| 时序 / 反例 | 测试 |
|---|---|
| close 进行中后到事实（rh2 单元，slow drop 让 close 停在 capture_sessions） | `tests/adapters/test_w5a_shutdown_chain.py::test_late_facts_during_close_are_absorbed_before_disk_report` |
| close 已完成后到事实（并入 + 原子重写 + 逐字重复不叠加 + cleanup 不二次） | `…::test_late_facts_after_close_amend_and_rewrite_disk_report` |
| **真实** `rh2_group_admission_filter → notify_run_fatal → dispose`，close 进行中（双 loop） | `tests/adapters_miles/test_w5a_miles_dispose_chain.py::test_dual_loop_real_filter_fatal_then_dispose_while_close_in_progress` |
| 同上，close 已完成 | `…::test_dual_loop_real_filter_fatal_then_dispose_after_close_completed` |
| 同源反例：子串/空消息不去重；真同源严格全等去重一次 | `…::test_same_origin_requires_exact_serialization_match`、`…::test_dual_loop_substring_driver_cause_keeps_worker_as_secondary`（既有 `…_same_origin_deduplicated` 保留正例） |

两条真实时序测试都断言：磁盘报告 `first_cause` = 提前触发的 filter fatal、`secondary_failures` 含 `late_primary(driver_error)`
与 `shutdown_failure`、`residue.unfinished_executions` 含具体组行、`rollout_fn_shutdown_failure` 非空、`ok=false`，且与 verdict
的 `rh2.{first_cause, secondary_failures, residue}` 逐字段相等。

计数（2026-09-02 实跑）：`uv run pytest tests/ -q`（默认 pin）**1583 passed, 247 skipped**；lane A **322p/232s**（非 integration_base
零 skip）；lane B **553 passed, 1 failed** —— 唯一失败仍是 `test_producer_tree_digest_matches_audit_manifest`（未提交 patch 0013 →
树 digest ≠ manifest）；rh2 ruff 与 vendor 五文件 ruff 全绿；lanes 脚本未跑（预期红）。本节净变化：`tests/adapters` +2，miles 测试 11→15
（lane B +4，lane A skip +4）。

### 15.6 五段收尾（本节）
① T0：无（证据一致性与去重规则；不改训练语义、contracts、W1b 文件、挡板、vendored slime）。② T1：后到首因不覆盖原首因而记
`late_primary` 次生（原首因 = 时间上最早的事实）；去重只认逐字相同；已完成后的报告可被后到事实原子重写（`late_merges` 留痕）。
③ 挡板：无。④ 推翻：§12 "后续调用带的 secondary/residue 不再并入"、§14 `_same_origin` 子串规则。⑤ 见 15.5。
