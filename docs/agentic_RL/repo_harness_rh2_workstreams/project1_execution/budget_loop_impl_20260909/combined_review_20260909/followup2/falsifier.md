# 第二次预算修复窄复核：R3 Falsifier / Simplifier

基线 `3d0bca0cb0e60c049ac4d80b844ddc851cea640e`，当前 HEAD 已核为 `6b33efee38d2b0d785983e44136dccbdd9c49a60`。本子审完整回读 `dfed0d61` 的 `execution_scope.py`、`generate.py` 差异、未变更但直接参与新判定的 `quiescence_barrier.py`、Brief v2.6 停止规则及 `test_budget_deadline.py` 的新增停止测试。R1/R5、僵尸处理由其他角色负责。

**原 R3 仍不能关闭。新代码修正了“kill 明确失败且同一次 helper 中墙后仍见进程”的旧反例，但把“没有反证”当成“已证明停止”，且屏障中的真正停止证据没有参与最终归类。两个方向均已通过真实 formal 入口和准入载荷复现：墙后仍活可 KEEP；墙前已确认归零却因后续指纹读取慢而 DROP。** 以下都归原 R3，不新增审查面。

## 1. 已投递但未确认的出口仍会 KEEP（P1，原 R3 未闭合）

`execution_scope.py:130–154` 的 `stop_proven_before` 在投递时刻不晚于 deadline、没有记录墙后正数 COUNT 时直接返回 True。它不要求 `result.verified`，也不要求存在任何计数结果。因此，COUNT 超时、或十次 COUNT 全部发生在墙前且始终为正数，都可能被命名为 `kill_delivered_before_deadline_no_later_presence`，即“已证明停止”。这并非三态 None 的待定分支。

`generate.py:3894–3896` 遇 True 就退出重试；`:3912–3925` 也不再检查期限。屏障稍后发现墙后仍有进程时，`quiescence_barrier.py:104–118` 只用其停止结果确认最后是否归零，不返回该结果；`generate.py:3832` 又只重判 `stop_attempts_exhausted_before_deadline`。早先的 True 不会被屏障中的墙后正数观测纠正。

违反的是已批“执行到点仍在进行 → hard wall → DROP”及作者本轮声称的“未证明没有 KEEP 出口”。最终静止屏障仍能保证评分时已经安全，问题是它不能倒推期限前已停，错误预算归因继续到达训练处置。

生产条件有明确边界：同一 scope 的 kill 调用成功返回，但仍有真实活残留；随后计数通道超时，或墙前轮询到次数上限；屏障才在墙后观察残留并最终归零。Brief 自身已承认枚举后 fork 的残留可能不在首次 kill 集合内。这里不能把任意正数都说成活执行，僵尸也会计数；探针明确把该残留设为活进程，并没有动态制造真实 Docker fork。结论的生产接缝由真实调用链验证，IO 和进程事实为受控替身；发生频率未测。

窄动态结果：

| 首次停止 | 随后真实屏障的观测 | 最终实际载荷处置 |
| --- | --- | --- |
| 899.5 收到 `pkill_status=0`；COUNT 等待过墙并超时，0 条观测；`kill_verified=false` | 900.1 发起查询，900.2 仍为 1；901 才归零 | `stop_before_deadline=true`、`max_turns_exhausted`、KEEP_FULL |
| 890 收到 `pkill_status=0`；保留真实十次上限，890.5–895 十次都为 1，次数耗尽且没有 IO 超时；`kill_verified=false` | 同样墙后仍为 1、901 才归零 | 同样 True / max_turns / KEEP_FULL |

这不是建议补第十一个轮询或再加一个“是否可能活着”字段。最小根因修正是：成功发送 kill 只能作为动作结果，未拿到可信停止确认时继续保留未确认；后续屏障收到的停止确认应进入同一个执行结束判断，不能只按早先 evidence 字符串决定是否读取它。归零前的强停、重试和屏障仍使用已有有界机制。

## 2. 屏障已在墙前确认零，指纹跨墙却被当 hard wall（P1，原 R3 的新误判）

`quiescence_barrier.py:104–118` 先完成终止与归零确认；`:119–137` 再读取两次 workspace 指纹；`:141` 才返回 `QuiescenceConfirmed`。新 `generate.py:3258` 在整个 `establish` 返回后调用 `_reclassify_unproven_stop_after_quiescence`，后者在 `:3834–3842` 用当前剩余时间归类，没有读取屏障步骤①已经发生的归零时刻。

生产条件是三次停止尚未确认、期限仍未到，随后屏障步骤①成功在期限前确认归零，但读取指纹跨过期限。这些都是当前默认链中的正常操作，既不依赖真实 CC 如何响应 403，也不依赖正数进程究竟是僵尸。三次尝试可以先于期限耗尽，不能因每次配置上限为 30 秒就假定它们必然已经越墙；计数次数上限或更快的失败同样能返回。

真实 formal 探针中，前三次 kill 返回非零且 COUNT 为 1；屏障的真实 helper 在 **899.5 已收到零计数**。仅把后续两个相同指纹的返回时刻改为 901，最终变成 `hard_wall_timeout` / DROP_GROUP，并写 `deadline_passed_before_quiescence_confirmed`。相同停止过程、指纹也于 899.5 返回的对照为 KEEP_FULL。

这直接违反本轮规则 A“零确认时刻 ≤ deadline 已证明停止”，也违反已批“停止后的清理越界不补造 hard wall”。它不是无法观测实际退出的保守选择：可信零确认已经在墙前到达，只是实现没有把该事实传给消费者。

最小修法是使屏障步骤①的停止确认成为编排可消费的同一事实，记录和比较该边界；双读指纹、冻结与清理继续执行自己的检查，不延长 episode 的执行区间。不需要把整套屏障或全部后处理加进 episode deadline，也不需要重做状态机。

## 3. 旧反例、测试及能力边界

维护测试已经覆盖旧 kill exit≠0 后同次 helper 中有墙后正数 COUNT、最终归零的反例，并把 Outcome 与真实 `decide_member_disposition` 一起断言。源码现在确实会拒绝旧证据组合；`test_failed_kill_is_retried_and_confirmation_before_wall_keeps` 也覆盖第二次投递/确认成功的正常重试。主审定向集的 `focused_tests.txt` 为 **196 passed**，这是主审运行结果，本子审没有重复跑该集合。

新增维护测试的盲点集中在两个生产接缝：

- `test_stop_facts_decide_keep_vs_hard_wall` 的成功投递案例，要么同次 helper 已确认归零，要么同次 helper 就见到墙后正数；没有“未确认却返回 True，屏障才得到墙后反证”。helper 单元测试也没有成功投递后的 COUNT 超时/次数耗尽对照。
- `test_unproven_stop_has_no_keep_exit_before_the_wall` 同步移动的是屏障 kill/COUNT 时钟，指纹没有独立推进时间；因此把整个屏障结束时刻当停止时刻也会通过。

新独立 `stop_evidence_falsifier_probe.py` 最终 **7 案退出 0**，结果在同名 `.jsonl`。除前述三组关键结果外，还包含：屏障真实零确认晚于墙 → DROP；屏障实际先空但 COUNT 回包晚 → 当前 DROP；首次 helper 已在墙前确认零、只有后续指纹晚 → KEEP。后两个对照分别界定“观测不够”和“已有证据不应被清理时间推翻”，没有把二者混为同一事实。

真实运行范围为旧 CPU formal 夹具→`RolloutOrchestrator`→`RolloutContainerWorkspace`→真实停止 helper→真实 `DockerQuiescenceBarrier`→实际 `AdmissionPayloadV1`→真实处置纯函数。只替换 Docker IO、episode 观测钟与等待常量；屏障 helper 包装只传入同一个观测钟并旁录原返回结果，不改控制流或返回对象。次数耗尽案保留真实十次上限，仅去掉真实睡眠、按每次 0.5 秒推进观测钟。没有运行真实 Docker、CC、模型 API、GPU、buffer 入组或参数更新。

## 4. 不能把“指出不确定性”写成批准新增 DROP

`project1_execution/tmp/claude修复.md:14` 与 `handover_20260909.md:90` 将保守 DROP 归为“Codex 认可”。此归属不准确。上一轮 `followup/falsifier.md` 明确写的是“观测不足，不要求实现凭空猜测墙前已停”，并警告不能悄悄把实际停止语义改为命令回包时间语义；没有批准扩大 DROP 的样本集合。

Brief v2.6 停止规则第 5 项自己也承认“唯一新增的 DROP 来源是未证明 + 期限已过”。这会改变训练资格；按协作协议的 T0 范围，不能只登记为 T1 或“请知悉”。此处需要更正归属，并把真实能力边界与拟采用的策略交给 owner 明确选择；本审查不替 owner 批准。

**收敛建议：停止继续用更多时间字段推测不可观测的实际退出瞬间，先选择一个可执行的最小合同。** 推荐候选是以“controller 收到可信 scope 停止确认”作为执行结束边界：episode 的 watchdog 持续约束到该边界，之后的 digest、冻结、评分和清理使用各自预算。未确认到点的样本按明确、经 owner 批准的 watchdog 规则处置，并如实区分“证实越墙执行”与“到点仍未证实停止”。

这一候选会使实际已停但确认晚的样本保守退出训练，代价和频率未知，属于 owner 需要确认的合同选择；不能继续称它是对已批实际停止语义的无影响实现细节。若 owner 坚持以实际退出时刻判 KEEP/DROP，当前宿主 CLI 回包与离散 COUNT 的信息不够，应先确定能提供可信停止证据的实现，再称 R3 完成。两种合同不能靠 True/False/None 的命名互相代替。

无论选哪一合同，已经到达的可信停止确认都不能被随后指纹/清理时间改写；COUNT 超时或未查询到墙后反证也不能当作停止证明。pkill 返回值与僵尸的具体事实由主审另核，本子审不追加未经核实的 producer 断言。

## 5. 最小验收与收口

先明确上述合同，再只验收本轮已列边界：成功投递后的 COUNT 超时、十次正数耗尽、未投递三次后的屏障确认，以及同一零确认配合及时/晚到指纹。沿实际 Outcome 和处置函数检查；不以实现自身的 `stop_proven_before` 返回值当唯一 oracle。原 kill 失败反例和正常重试对照保留即可，不再扩整条链。

从 `rh2` 目录复现：

```bash
uv run python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup2/stop_evidence_falsifier_probe.py
```

本子审仅新增该脚本、其结果和本报告；不改业务源码、维护测试、旧工件、共享文档或 git。§6 六项、预算数值、`owner_cancelled` / `agent_violation` 维持既有边界。两条有证据反例与必要回归已经足够，R3 在此收口，不追加新的停止状态平台或无止境修补轮次。
