# B/C/D 联合审查：Production Tracer

**结论：批 B 的旧 R2a/R2b 可关闭；D-2 还有两项 P1 与一项 P2。** P1 是评分 scope 收口没有实际截止点，以及把 Docker 连接错误误认作容器不存在。P2 是取消后的 scope 致命异常不能稳定到达关停 owner，且会使主动关闭评分队列的 worker 继续循环。后者目前只建立了 stop/halt 路径的生产可达性，不能据此宣称正常训练继续，也不能说残留完全丢账。

审查基线 `04f599f8`，2026-09-09；开始及收口时 `git diff --stat -- rh2/src` 均为空。主责提交 `5c8fa4f7`，针对性复核 `510c9b23` 的旧 R2；另按主审请求交叉审读 C 的停止期限探针。已读统一交接、Brief §3/§6、旧批 B Production Tracer 报告及对应源码。§6 六项保持现状；`owner_cancelled_truncation` / `agent_violation=None` 不列问题。本角色未重开 B 全审、未重复全量测试。

## 真实主链与探针边界

生产调用链：`BringupService._grading_submit`（`bringup.py:1769–1790`）→ `GradingQueue.submit`（`queue.py:161–203`）→ `_worker_loop`（213）→ `SWEGradingManager.grade`（`manager.py:1009`）→ `finally/_close_container_scope`（1260–1268）→ queue future → `generate._finalize._grade`（`generate.py:4892–4938`）→ `FatalExecutionInfrastructureError` → 外层同步 `_notify_fatal_halt`（3588–3595）→ rollout finally。队列本身的“有界”限制数量，不限制一次评分或清理的等待时间。

[production_scope_probe.py](production_scope_probe.py) 保留以上实际函数：从真实 `_formal_chain().orchestrator.generate` 进入，经实际 bringup 提交方法、真实队列、真实 manager、正式 grader profile、冻结基线核验和官方 parser。仅替换模型交互/Docker IO；可信 setup 自证与 profile 核验的 IO 由 CPU fixture 应答。最终 15 案均进入候选测试；正常对照产生 `resolved`、真实 parser 给出的 reward `1.0`。脚本断言包含本次发现的修前行为，不能当作维护测试直接固化。

## D2-1 · P1：所谓“有界收口”没有实际超时

**行为与位置。** `_close_container_scope` 直接等待首次 rm、inspect、kill、二次 rm、再次 inspect（`manager.py:1468–1480`）。这些调用最终在 1438、1452、1476 直接 `await self._docker(...)`。`GradingManagerConfig.cleanup_timeout_seconds` 只写进租约（1344），未形成 deadline 或 `wait_for`。默认 `run_docker`（95–120）支持收到取消后 kill/wait，但不会自行超时。

**违反的不变量与影响。** Brief D 第 3 条要求“有界收口结束仍运行或无法确认 → fatal，并继续清理”。Docker CLI 若一直等待，状态机无法到达最终判断，评分 worker 与对应 generate 都不返回，fatal 通知为 0。单次测试的 timeout 不覆盖这个 finally。正常运行阶段也没有 queue 层的评分总超时可反证此问题；完整服务关停时另有 ShutdownStep 上限，不能补足正常评分收尾的期限。

**生产可达条件。** 正常/失败/测试超时后的 `grade()` 都必经该 finally；Docker daemon 卡住或 CLI 等待响应即可触发，不要求自定义 grader、不要求模型特殊输出。这是新 D-2 停止边界未实现已定的有界要求，不是要求重做整个 grader 生命周期。

**最小反例。** `block_rm`、`block_inspect`、`block_kill` 三案分别阻塞真实收口路径的一次底层 IO。清理预算配置为 1s，观察 1.05s 后三案仍 `pending_after_cleanup_budget=true`、评分 active=1、halt 通知=0；探针主动释放 IO 后，才发生 `grading_scope_termination_failed`。该主动释放属于探针，不是生产代码的超时。

**窄修与验收。** 消费独立的清理截止点，让每个 rm/inspect/kill await 都受剩余时间约束，超时先收掉本地 CLI；保留最终 `running/unknown` 的 fatal 传播，同时尽力完成剩余清理。不要把清理再绑回 episode 行动预算，也不要把 Timeout 洗成普通 `failed_to_grade`。验收覆盖上述三处等待及二次 rm，证明在清理上界内结束/通知 fatal，正常 rm、已停止、二次 rm 成功仍不会误杀 run。

**异常分支限定。** `rm_raises` 让真实 rm 调用抛 `OSError`：当前并不变成 ABORTED，而是经既有未知异常通道升级 `pre_finalize_failure_unclassified`，halt 通知一次，rollout cleanup 照跑。因此不另报“未知异常被吞”。但该次会跳过状态查询/kill/二次 rm，manager 的 cleanup_failures 为空，未删 record 仍在；修复有界收口时应明确这种运输异常的 unknown 状态和后续清理，不能只处理非零退出码。

## D2-2 · P1：连接错误中的 “no such” 被当作已删除

**行为与位置。** `_container_state` 对任意非零 inspect，只要文本包含 `no such` 或 `not found` 就返回 `absent`（`manager.py:1455–1457`）；`_close_container_scope` 随后当作已停止，正常返回（1472–1474）。关键词没有绑定“目标容器不存在”。

**违反的不变量。** “无法确认 ≠ 已停止”是本批核心要求。Docker 客户端连接 socket、上下文或凭据时的找不到资源错误，也可能包含相同关键词；它不提供评分容器是否停止的事实。

**生产可达条件与证据强度。** 先有评分容器，清理阶段 daemon/连接路径不可用；inspect 非零诊断包含连接层 `no such file or directory`。默认 runner 把 stderr 原样交给这段解析。本机按限制没有实际执行 Docker；下面证明的是这个具体运输错误输入在真实生产调用链的分类结果，不宣称捕获过真实 daemon 故障现场。

**最小反例与影响。** `unknown_socket` 返回：`error during connect: dial unix /var/run/docker.sock: connect: no such file or directory`。真实 manager→queue→generate 最终交付一个未 remove 的样本，reward `1.0`，`grading_report_outcome=resolved`，halt 通知=0；清理记录却把它写成 `container_scope_stopped_but_not_removed:…:absent`。对照普通 `Cannot connect to the Docker daemon` 会正确 fatal。这是诊断文本不同导致同一 unknown 状态被放行，不是 reward 本身算错。

**分期、窄修与验收。** 属 D-2 新状态解析的 P1。只接受明确指向本次目标容器的不存在诊断；其它 inspect 失败保留 `unknown`。成功输出也只应接受明确的 `true/false` 状态。验收同时保留真实容器缺席的非 fatal 对照，并使 socket/上下文等资源缺席诊断走最终未知状态 fatal；不需要建立新通用错误平台。

## D2-3 · P2：取消后的 scope 异常没有独立于 future 的接收者

**行为与位置。** 提交者取消 `await item.future` 后，future 一起变为 done；独立 grading worker 仍继续评分。稍后 manager 自己抛出的 `GradingScopeTerminationError` 被 `queue.py:224–226` 捕获，但因 future 已 done 不再上送。另一条路径中，`queue.close(drain=False)`（148–150）取消 worker，`grade()` finally 抛 ScopeError 覆盖在途 `CancelledError`，worker 把它当一般 Exception，处理完该 item 后继续 `while True`，使 close 的 gather 继续等待。

**生产可达性限定。** 本次追到的真实取消来源是 `close_inflight_executions`（`shutdown/chain.py:293`）及 worker 在 stop/halt/自身取消时取消在途任务（`async_worker.py:1399,1410`）。未建立正常补采会单独取消在评成员的证据，因此**不声称本问题已经证明训练在 fatal 后继续**。也不是要求决定 `owner_cancelled` 的训练处置。

**最小反例。** `cancel_submitter` 在候选测试执行中取消真实 generate，真实 manager 随后 rm→kill→rm，最终仍 running，确实产生 scope 失败记录；队列 worker 仍活着、halt 通知为 0。`cancel_worker` 改为调用真实 `queue.close(drain=False)`：generate 尚在等待时收到正确 fatal，但 grade 已展开结束后，close 仍 pending，worker 仍在循环，探针必须再次取消 close 才退出。均未直接注入 ScopeError，异常由真实 manager 的停止状态生成。

**反证与实际影响。** `manager.cleanup_failures` 和 `_records` 没有丢；后续 `BringupService` 的 grading_manager 步调用 `close→gc` 重试 rm（`bringup.py:1967–1968`，`manager.py:937,1285`），container_residue 和最终报告仍收集未删记录（`bringup.py:2005` 及 `_run_close`）。完整关停链也有外层步骤超时，能再次取消 worker。所以当前结论是：D-2 专用终止失败通知/关停异常归集不完整，且主动关闭可能退化为等外层超时；不是证明关停假绿或资源完全不再被清理。

**窄修与验收。** scope 终止失败应有不依赖单个已取消 future 的 run/service 接收路径；队列正在关闭时，异常处理完仍须退出 worker。普通 task-local 评分故障保留原队列隔离语义。验收同时覆盖提交者已取消与 worker 被关闭这两种自然来源，检查致命事实可被服务接收、关闭可完成、未删 record 仍可后续回收；确认不会通知两次。

## D-2 对照结果

| 情况 | 观察结果 | 判断 |
|---|---|---|
| 正常 rm | 一次 rm、record removed、resolved/reward 1.0 | 符合 |
| 首次 rm 失败、随后明确 stopped / absent | 只留清理诊断，不 fatal | 符合既定例外；不重新要求 owner 批准 |
| 首次 rm 失败仍运行、kill 后二次 rm 成功 | kill 一次、rm 两次、正常交付 | 符合 |
| 两次 rm 失败且仍 running | ScopeError 穿真实 queue/bringup，generate 通知 fatal，rollout finally 完成 | 符合 |
| 普通 daemon 不可达 → unknown | fatal；不伪称 killed | 符合，受 D2-2 的文本歧义限制 |
| 候选测试超时、清理成功 | `failed_to_grade`，scope 已删除，无 fatal | 符合；不把普通评分超时当最终停止失败 |
| 候选测试超时、收尾仍运行 | 最终 ScopeError 覆盖评分结果，fatal | 符合 |

## 批 B 旧 R2 关闭证据

[production_b_r2_probe.py](production_b_r2_probe.py) 五案 exit 0；旧工件未修改。

| 验证点 | 结果 |
|---|---|
| 真实默认 `manager.run_docker` 收到取消 | kill/wait 各一次，取消继续传播；同时验证 generate 与 bringup 都绑定该 runner |
| network create 等待响应时取消 | 网络/登记/槽位 = 0/0/0 |
| 已登记后的 relay connect 取消 | 网络/登记/槽位 = 0/0/0 |
| docker run 创建生效、返回前取消 | 按名字移除容器一次；网络/登记/槽位 = 0/0/0 |
| 创建取消后的 network rm 失败 | 网络与槽位各保留 1，明确记 `remove_egress_network`；没有盲目归还 |

当前修复确实落到生产通道：`manager.py:105–116`；`sandbox_profile.py:736–781`；`generate.py:4491–4568`。这足以关闭旧 R2 的限定要求，不等于证明所有 Docker/daemon 故障都能立即清空，也不把 D-2 新 scope 上界问题倒算成 B 的修复回归。

## 对主审 C 关键发现的交叉核对

已审读 [stop_deadline_probe.py](stop_deadline_probe.py)，未重复执行主审探针。生产前提成立：正式 bringup 注入真实 `DockerQuiescenceBarrier`（`bringup.py:1409–1415`）；turn cap 进入 `_stop_after_turn_budget` 后，仅在停止前检查 episode 剩余（`generate.py:3792`），3800 调真实停止函数，3803 无条件返回 `-2`；上层 2921–2927 据 cap 记 `max_turns_exhausted`。`execution_scope.py:40,43` 的 kill/count IO 均无 timeout。

主审两个时间对照必须同时保留：

- `kill_effect_after_wall`：deadline=900，899.5 开始调用 kill，直到 901 才生效，期间执行仍未停止；却被记为 `-2/max_turns` 并保留训练候选。这支持“停止过程跨过墙钟但仍按 turn 处理”的 finding。
- `confirmation_after_wall`：899.5 已停止，仅进程计数回包到 901；应保留 turn 语义，不能因为末尾 remaining 为负就补造 hard wall。

因此建议围绕独立的终止事实与期限竞争修复，而非在收口尾部简单加一次 `clock()>deadline`。`hang_turn_stop` / `hang_hard_wall` 则支持与 D2-1 合并的“停止等待没有实际截止点”：均通过真实 run_bash 路径，不是只调用孤立 helper。

## 验证产物与限制

本角色在 `rh2/` 执行以下两条独立 CPU 命令，最终均 exit 0；结果分别为 15 案与 5 案。未执行维护测试、真实 Docker/CC/API/GPU，也未更改源码、旧探针、共享文档或 git 状态。

```bash
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/production_scope_probe.py
uv run --no-sync python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/production_b_r2_probe.py
```

输出：[production_scope_probe_result.json](production_scope_probe_result.json)、[production_b_r2_probe_result.json](production_b_r2_probe_result.json)。完整联合审查的其余证据由主审汇总，本文不据作者的全量测试结果替代生产路径核查。
