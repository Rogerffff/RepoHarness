# 预算终止闭环：第四次窄复核

日期：2026-09-09。基线 `d4af9d9a`，被审 HEAD `92d165aa1dae5a660557f5f07cc702c3dee62ea3`。本轮仅审停止合同 A（`7bed1bc0`）与 F1 物化异常的回收所有权（`6cf41951`），以及必要的相邻回归；文档提交为 `92d165aa`。

**结论：本次聚焦复核通过。owner 已选的停止合同 A 落实；F1“物化清理被 episode 期限取消，导致致命首因变成普通 ABORTED”关闭。没有新增本批阻塞项，可以结束这一轮预算闭环修复，进入下一切片。** A/B/D-1/R1/R2/R3 上轮两处/R4/R5/Z1 的既有结论保持。运行级再次取消慢清理存在共享边界，按 §4 登记，不把本次通过扩大为任意关停时序都能完整清理。

本轮没有修改业务源码、维护测试、依赖或预算，没有提交／推送；只新增复核工件并更新 Brief、交接与共享账本。

## 1. 停止合同 A：通过

`execution_scope.py:147-165` 现在只有 `confirmed_at <= deadline` 返回 True。kill 回包、pkill 状态和“未查到反证”不再产生推断 KEEP；其它分支保留不同诊断原因，但返回 False。没有 deadline 仍为 None。

这不只停在纯函数：`generate.py:3941-3964` 消费同一判据，晚确认走 hard wall；后续屏障不会把它回翻为 turn 保留。墙前已确认的停止仍可在屏障后处理跨墙时保留。Outcome、receipt、交付载荷与实际成员处置函数的连接保持，未修改 reward／loss／完整组规则。

| 期限 900 秒的关键对照 | 独立结果 |
|---|---|
| kill 899.5 返回，首次零确认 901 收到 | `hard_wall_timeout` / DROP_GROUP |
| 强停在墙前收到零确认，指纹之后跨墙 | `max_turns_exhausted` / KEEP_FULL |
| 首次强停没有确认，屏障在 899.5 首次确认零，指纹 901 返回 | KEEP_FULL |
| 首次查询不可读，重试在 899.95 确认零，后处理到 905 | KEEP_FULL；Outcome／receipt／AdmissionPayload 一致 |
| 期限后发起的查询仍有进程，后来才归零 | hard wall / DROP_GROUP |

主审重放旧八案，**只改变 `confirmation_after_wall` 的目标处置**，完整差异保存在 [脚本差异](stop_cases_replay.diff)。另原样执行上轮七案及独立重试两案。两条停止 IO 挂起案保持 missing、不评分、task 有界结束，不能因为其中一案的 termination kind 为 max_turns 就说它进入了训练。

实际早停而确认晚到的部分轨迹也会 DROP，这是 owner 已接受的合同代价，频率未知。本轮没有改变 600 秒／25 次，也没有增加新的停止重试、守卫或长期状态。

## 2. F1：根因修复通过

原问题是：容器已启动，内层先等清理再传播 Fatal；外层尚无 sandbox，episode 期限取消清理后既吞掉原异常，也失去回收入口。修后资源交接发生在 `generate.py:4543-4551`：容器成功启动后，同步把临时 `_MaterializedSandbox(handle=None)` 放入已经存在的 `prepared` 字典，随后才进行镜像／血缘／必需契约校验。

正式调用的 `owner=prepared` 在 `3697` 传入；异常分支 `4688-4693` 不再等待内层清理。准备子 task 直接携原异常结束，外层 `2760-2764` 的 finally 取回 sandbox，异常分流先通知停 run，后续按既有顺序持久化 receipt，再有界清理。这消除了原来的 episode 取消窗口，没有通过把错误改为 missing 隐藏问题。

临时对象没有变成第二套长期 owner：沿用同一 attempt 的已有字典与外层 finally。异常路径只使用容器名、lease 和 workspace；唯一的 `sandbox.handle` 解引用在准备成功后的 `2786`，成功路径已替换为完整形态，未发现 `handle=None` 流入 harness 的可达路径。创建结果尚未确认时的按名回收与普通取消路径保留。

主审沿用上轮真实 `LifecycleState` 通知器、真实编排／期限／receipt／清理路径。只在外部 Docker IO 门控 `rm`，不替换异常判定或终态。16 案包含原 15 案以及物化期真实 `ValidationError` 的跨期限对照。

| 条件 | 清理刚开始时 | 清理跨过真实 episode 期限后 | 放行清理后的结果 |
|---|---|---|---|
| digest 不符 | 原码已通知一次；receipt 已为 fatal | 仍在清理，通知仍一次，未被 episode 取消 | 原 Fatal 传播；容器删除 1、私网登记 0、lease 释放 |
| 血缘不符 | 同上 | 同上 | 同上，保留血缘原码 |
| `WorkspaceHandle` 构造失败 | 同上，`rh2_contract_validation_failed` | 同上 | 同上，未变 `episode_deadline_in_materialize` |

三案均没有 Outcome、没有评分、没有 ABORTED。普通 digest／血缘查询失败仍 ABORTED，digest 命中正例正常评分交付，其余身份／工件／mask 及兼容模式对照保持预期。

为了观察修后清理继续进行，旧探针副本在期限过后主动释放 rm 门控，避免由验证脚本自身的 3 秒等待取消业务 task；该调整与目标断言完整记录在 [F1 回放差异](fatal_replay.diff)。真实期限仍为 0.25 秒，主审没有改生产 helper、时钟或返回值。详细结果见 [16 案结构化证据](fatal_replay_result.json)。

## 3. 主审实际验证

| 检查 | 结果与证据 |
|---|---|
| 11 个相关维护测试文件，接入 integration miles | **258 passed in 16.88s**；[日志](focused_tests.txt) |
| 本轮改动的 4 个 Python 文件 ruff | 通过；[日志](ruff.txt) |
| F1 修后及必要正例 | 16 案，退出 0；[逐案结果](fatal_replay.jsonl)、[脚本](fatal_replay.py) |
| 停止合同 A 与既有停止对照 | 8 案，退出 0；[结果](stop_cases_replay.jsonl)、[脚本](stop_cases_replay.py) |
| 上轮停止证据七案原样重放 | 7 案，退出 0；[结果](stop_evidence_replay.jsonl)，脚本为 `../followup3/stop_evidence_replay.py` |
| 上轮重试后及时确认／晚后处理对照 | 2 案，退出 0；[结果](retry_confirmed_replay.jsonl)，原样调用 `../followup3/falsifier_probe.py::stop_case`，未重跑缺 base 调查 |
| 共享 run 级取消边界对照 | 2 案，主审读脚本后独立执行退出 0；[结果](production_probe.json)、[主审输出](production_probe_root.jsonl)；范围见 §4 |
| 审查前后源码与维护测试摘要 | 4 个改动文件无变化；[起始快照](review_snapshot.json)、[核验汇总](verification_summary.json) |

作者的全量 **2190 passed / 0 skipped** 没有由主审再次重跑。本轮没有真实 Docker／目标 SWE 镜像／Claude Code／模型 API／GPU 作业；Z1 的真机证据沿用上轮，因为本轮没有改它的实现。

按仓库要求使用一对独立角色：[Production Tracer](production_tracer.md)、[Falsifier](falsifier.md)。主审独立读源码并重放关键证据，没有以子报告多数票代替裁决。

## 4. 仅登记的共享边界与小项

**P2／共享关停 backlog：已经进入 finally 的慢清理，被 run 级再次取消时可中断。** 默认 `inflight_grace=30s`，而 rollout cleanup 上限为 120s。`close_inflight_executions` 宽限后取消整个执行 task；若 task 已在 finally 等 rm，该次取消可中断清理，跳过 cleanup 追加和 audit sink。这个边界需要在后续关停工作中统一处理，不能声称“通知后在任意取消下资源都会完整回收”。

为判断分期，独立角色用真实编排、`LifecycleState`、真实 `close_inflight_executions` 做了两案，主审独立复跑：新接入的物化 digest Fatal 与**本轮之前已存在**的 `frozen_artifact_persist_failed` 使用同一个慢 rm，结果相同。两案都已经停止 intake、通知一次、receipt 保留 `fatal_run_halt` 与原码、没有 Outcome／ABORTED；其后 task 因 run 取消结束，清理追加未发生，模拟资源未在该次执行中回收。

标签为 `production_reachable`：真实 bringup 的 `_on_run_fatal` 调度关停，inflight 步确实取消未结束任务。动态探针只连接 intake／inflight 两步，等待缩为 0.05／0.2 秒；**未执行完整关停链，不能据此宣称最终 shutdown 假绿、永久泄漏或继续补采**。本项属于两个路径共享的既有清理限制，与原 F1 的“episode 取消吞掉尚未通知的 Fatal”不同，不重开本批。归 A 线后续关停收敛时处理；届时核查二次取消下的清理／追加结果与 run 级回收，而不是再改训练处置。

其它小项不阻塞：`generate.py:3925` 仍有“边界待 owner 决定”的旧注释，实际代码与现行合同已一致，可随下次相关改动更新；`owner=None` 的就地清理分支当前没有仓库内直接调用者，后续常规简化可删除，无须为此增补兼容测试。上轮缺 base 的 producer P2 继续保留，未扩大复查。

## 5. 收口与停止条件

停止合同 A 和 F1 的窄验收条件已满足，本轮无待拍板 T0、无新增本批 P0/P1。A/D/G/L/M 已核对首因、通知、receipt、任务与资源交接；B/F/H 已核对实际停止事实与成员处置；E 的故障注入限于外部 IO／必需输入；C/K/I 未扩展长期 owner 或恢复平台并执行停止条件；J 的旧注释已注明，N 无依赖变更。没有据此声称整个 infra 或训练实验已完成验收。

**预算闭环这一实施批次可以收口，进入下一切片。** P2 共享关停边界、缺 base producer、目标环境与真实 CC/GPU 诊断按既有后续工作跟踪；不因这些记录重新启动本轮修复循环。
