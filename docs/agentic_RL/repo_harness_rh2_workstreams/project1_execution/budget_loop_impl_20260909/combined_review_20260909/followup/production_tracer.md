# 预算修复窄复核：Production Tracer

**结论：R2 的 grader 总截止点、R4 的容器状态误判、R5 原有两种取消反例均已关闭；R5 的关闭标志另引入一项 P2 回归，建议收尾前窄修。** 当关闭时仍有已接受的排队请求，`close(drain=True)` 会让 worker 提前退出，服务因此耗满 drain 期限，已排队条目也未完成处理。

基线 `04f599f8` → 复核 HEAD `3d0bca0cb0e60c049ac4d80b844ddc851cea640e`；2026-09-09。主审范围内提交 `02807adc`、`5d822ae9`，对照作者说明 `project1_execution/tmp/claude修复.md`。本角色只复核 grader 的 R2/R4/R5，未扩至 B、I13/I16、§6 六项未定分支，也未因既有 stopped/absent 例外重新要求 owner 定案。

## 旧问题关闭证据

[production_followup_probe.py](production_followup_probe.py) 复用旧探针的 Docker IO 替身，保留真实正式 `generate` → `BringupService._grading_submit`（`bringup.py:1771`）→ queue → `SWEGradingManager.grade` → finally（`manager.py:1260`）→ `generate._finalize._grade`（`generate.py:4950`）。评分输入经过冻结基线核验、正式 grader profile 和官方 parser；正常对照得到 `resolved/reward=1.0`。没有直接注入 ScopeError，异常由真实 manager 的最终状态产生。

服务按既有 CPU fixture 的属性面装配，保留实际 owner loop、`notify_run_fatal`、`dispatch_run_fatal`、`_record_run_fatal`、`_on_run_fatal`、`_run_close` 与报告归集；关停仅执行本切片相关的真实 intake/inflight/queue/manager/residue 步。tokenizer、模型、Docker IO、HTTP 线程不启动。因此以下“服务收到”不是只检查 `list.append` 替身，也不是运行完整生产部署。

| 项目 | 当前代码与探针结果 | 判断 |
|---|---|---|
| R2 四处等待 | `manager.py:1495–1516` 只建一次起点；首次 rm、inspect、kill、二次 rm 都消费 `left()`。四个阻塞案配置 1 秒，约 1.00 秒收到取消后结束；探针未主动释放 IO，均经真实服务记录一次 `grading_scope_termination_failed`，rollout cleanup 完成 | 原无截止点反例关闭 |
| R2 默认 runner / 累计耗时 | 真实 `run_docker` + 子进程替身：总预算 0.1 秒，rm 与 inspect 各消耗 0.025 秒，kill 阻塞；总耗时约 0.101 秒，kill 对应宿主 CLI 被 `kill/wait` 各一次。预算耗尽后二次 rm 不再发起实际进程 | 剩余预算接通，未按步骤重置；取消先回收宿主 CLI |
| R4 socket / 输出歧义 | `manager.py:1470–1483` 只接受明确 `true/false`；非零退出只把绑定本容器名的 `No such object/container` 认作 absent。socket 的 `no such file or directory`、畸形成功输出、其它容器的不存在诊断均为 unknown → fatal | 原 socket 放行关闭 |
| R4 合法例外 | 正常 rm、明确 stopped、本容器 absent、kill 后二次 rm 成功保持正常评分；未删除的 record/诊断仍可被后续 gc 与 residue 汇总看到 | 未扩大停止与删除的既定例外 |
| R5 提交者已取消 | `queue.py:258–264` 在 future 已 done 时，经 `bringup.py:1191` 注入的真实 sink → `notify_run_fatal:2583` → service 接收原始 `GradingScopeTerminationError`。`fatal_seen=1`、带外通知=1、关停报告首因中的 scope 失败=1 | 原 fatal 无接收者反例关闭，无重复通知 |
| R5 关停已开始 | 在实际 `_run_close` 已建立报告后释放评分，scope 异常成为 `run_fatal_during_shutdown` 首因，报告 `ok=false`；`fatal_seen=1`，首因/次生中仅一条 scope 失败 | 不仅能触发新关停，也能进入正在执行的关停报告 |
| R5 worker 被关闭 | `close(drain=False)` 取消真实评分，finally 的 ScopeError 覆盖取消后，仍在等待的 generate 从 future 收到一次 fatal；带外通知=0；原 worker 全部完成，close 返回且 worker 列表清空 | 原 worker 吞取消后重入循环反例关闭 |
| 普通评分超时 | 候选测试 timeout + rm 成功仍为 `failed_to_grade`，服务 fatal=0；同样 timeout 但最终仍 running 则 scope fatal 优先 | 不误杀普通 task-local 评分超时 |

上述 R2 截止点依赖底层取消正常返回；默认 runner 的取消回收路径已用真实函数验证。本次没有构造操作系统层 `proc.wait()` 永不返回的新理论故障，不据此重开旧 B 或扩大本次阻塞范围。非 Timeout 运输异常仍经既有未知异常通道 fatal 的行为未被本轮改动推翻。

## 新回归 R5-F1 · P2：drain 标志使已接受的排队请求失去 worker

**行为、位置与违反的不变量。** `queue.py:162` 在任何 close 一开始设 `_closing=True`；`163–164` 的 drain 分支随后等 `queue.join()`。但 `_worker_loop` 的 `241` 已改为 `while not self._closing`：worker 做完手中的条目就退出，剩余队列的 `task_done()` 永远不会发生。这违反该方法 `160` 的明确语义：“先等在途/排队请求全部完成再撤 worker”。这不是新增拒绝策略的设计分歧，而是本次 R5 标志顺序造成的回归。

**生产可达条件与主调用链。** 正常服务关停走 `BringupService._build_shutdown_steps().grading_queue`（`bringup.py:1956–1967`），默认确实调用 `close(drain=True)`。当待评分条目数超过正在评分的 worker 数、且当前评分还未结束时可达。完整服务先取消在飞执行不会消除条件：`submit()` 已把 `_QueueItem` 放入队列（`queue.py:219`），取消 `await item.future` 只取消 future，条目仍在队列。探针另设所有提交者已取消的对照，结果相同。

**最小反例。** 一个 worker、两个已接受 item。第一个进入 grade 后暂停，第二个排队；调用真实 bringup 评分队列关闭步骤，再释放第一个。30 毫秒后，worker 已全部结束、队列深度仍为 1、close 仍等待 join。把实际 `grading_drain` 缩为 0.2 秒后，步骤约 0.20 秒返回 `drained_within_timeout=false`，manager 只处理过 `first`；第二个 future 仍 pending、队列深度仍为 1，而 worker 列表已经清空。`drain_cancelled_backlog` 对照先取消两个提交者，同样耗满期限并留下队列深度 1。

**影响与反证。** 服务默认 `grading_drain=60.0`（`shutdown/chain.py:335`），这类可正常完成的收尾会无谓耗满一分钟，并放弃原本应 drain 的已接受请求。直接使用 `async with GradingQueue` 的默认 close 则没有服务外层上界。实际 bringup 在内部超时后改调 `close(drain=False)`，该步骤本身还有 `grading_drain+15` 上界（`bringup.py:2078`），后续 manager gc 与容器残留统计仍执行。因此本项定为关闭阶段的 P2：不宣称训练继续、不宣称整个服务永久挂死，也不宣称已启动容器丢失登记。

**窄修与验收。** 让 drain 阶段继续消费已接受条目；优先把 `_closing=True` 移到 drain 的 `join` 返回后、撤 worker 前，`drain=False` 则仍立即设置。保留 ScopeError 覆盖取消后的退出行为。新增有积压的关闭对照：一个 worker/两个条目、提交者仍在和已取消两种情况，都在释放当前条目后及时结束，队列清空且未耗满外层期限；重跑已有带外 fatal、关停中 fatal、worker 取消三个对照，仍只通知一次。不需要重写完整生命周期或更改 owner_cancelled 的训练语义。

## 验证记录

最终独立 CPU 探针共 20 案：17 案真实评分/服务接线、1 案真实默认 runner、2 案真实 queue/bringup 关闭步骤。结果见 [production_followup_probe_result.json](production_followup_probe_result.json)。脚本包含新回归的修前断言，不能把其错误行为直接固化为维护测试 oracle。旧探针及其结果未修改。

仓库根目录执行：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup/production_followup_probe.py
```

未运行全量测试或真实 Docker/CC/API/GPU，未修改业务源码、维护测试、共享文档、旧工件或 git。维护测试和联合复核由主审汇总。
