# Production Tracer：第三次窄复核

日期：2026-09-09。审查对象按主审固定为 `d4af9d9a449555580e27126425391de2cf87fbf5`，本角色主责 `f96e3596` 的六项 fatal 与直接接缝。本角色没有操作 Git、没有运行 Docker，也没有修改业务源码、维护测试、旧审查工件或共享账本。

结论：六项的最终 fatal 分流都能从真实抛出点进入，但物化阶段存在一项本批应修的接缝问题：**先等待清理、后通知 fatal；清理被 episode 期限取消时，已确认的 digest／血缘矛盾会退化为 ABORTED，并留下未回收资源。** 另有一项非阻塞的范围准确性问题：`s1_compat` 的 digest、血缘、mask 缺失三个分支现在也会抛 fatal，不能笼统声称冻结路径逐字不变。

已读当前状态简报、协作协议、审查标准、`project1_execution/tmp/claude链路建议.md` 与本批 Owner Brief。遵守本轮停止条件：不重开 A/B/D-1/R1/R2/R4/R5；R3 仅核对生产数据接缝，未知停止边界留 owner 决定；没有做全量测试或扩展架构审查。

## 证据与复跑

- 脚本：[production_probe.py](production_probe.py)，已冻结，SHA-256：`ca53b614900524c7db455eeeb6a63db8f29de0f31abd9c3c5b0460fa53b5ddfe`。
- 结果：[production_probe_result.json](production_probe_result.json)，含 15 案、R3/Z1 直接接缝检查与六个相关源码摘要。完整执行退出码为 0；这是“观察与冻结断言一致”，**不是缺口修复通过**。
- 检查：使用 `rh2/pyproject.toml` 的 ruff 配置检查本脚本，退出码为 0。首次从仓库根直接调用采用了另一份配置，报告 import 排序与无用 `noqa`；本角色未因此改动已冻结探针，亦未把风格项算成 finding。
- 首次探针执行到 mask 案时缺少 miles 导入路径；补上仓库内 integration reference 的导入路径后完整重跑通过。没有替换或伪造目标异常来绕过该环境问题。

从仓库根运行：

```bash
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup3/production_probe.py
rh2/.venv/bin/ruff check --config rh2/pyproject.toml docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup3/production_probe.py
```

探针复用 `test_w1b_termination_facts_producer._formal_chain`、`test_slime_generate.FakeRolloutDocker` 与 `FakeFinalizationStore`。外部 Docker／harness／grading 接口是维护夹具替身；`generate → _prepare_workspace → _materialize_rollout_sandbox → _await_within_episode_deadline → finally/receipt/cleanup` 都是真实代码。通知使用真实 `LifecycleState` 安装的 context notifier。没有替换 `_attributed_fatal`、`_structural_contract_fatal`、期限判定或异常收口 helper。

## 当前生产链与所有权

`Rh2MilesGenerateFn.__call__` 经 `rh2_custom_generate` 调用 `RolloutOrchestrator.generate`。真实 bringup 以 `_resolve_task` 为任务入口：`bringup.py:1750` 调用 `LifecycleState.enter_execution`；`shutdown/chain.py:243-261` 把通知器装入当前 task context。`_notify_fatal_halt`（`generate.py:5498-5506`）经该通知器触发 `BringupService._on_run_fatal`（`bringup.py:2427`），后者调度关停链。

owner loop 是 miles rollout actor 的后台 loop。`generate` 在该 loop 上执行；`_await_within_episode_deadline` 为准备阶段创建子 task（`generate.py:3754`），子 task 继承 notifier context。该子 task 持有未返回的容器／私网；外层的 `prepared["sandbox"]` 只有物化成功返回后才得到引用。此次缺口正发生在“子 task 已知 fatal、仍独自持有资源、父 task 的期限取消仍有效”的窗口。adapter aiohttp 线程没有参与该反例。

## 六项真实处置矩阵

| 项目 | 抛出点及实际条件 | 独立结果 |
|---|---|---|
| 身份残缺 | `generate.py:2732-2751`，非 `s1_compat` 缺 `rh2_member_slot` | `fa_identity_incomplete_in_formal_mode`；通知一次；无物化／评分／Outcome；receipt 为 `fatal_run_halt` 且带原码 |
| finalize 前 `ValidationError` | `generate.py:4624` 的真实 `WorkspaceHandle` 构造，注入无效 mount 数据；`3642-3654` 收口 | 最终为 `rh2_contract_validation_failed`，receipt 为 fatal；但该物化分支也是先清理后通知。`s1_compat` 同输入仍 ABORTED，模式限定本身有效 |
| 冻结本体持久化失败 | `generate.py:3371-3395`，真实调用 store 时抛 `OSError` | `frozen_artifact_persist_failed`；通知先于清理；一次；receipt 为 fatal、`artifact_bodies_persisted=false`；无评分；session 与容器／私网清理完整 |
| mask tape 缺失 | `generate.py:3138-3150`，已启用 `return_sampling_mask`，真实 hook 产出的 tape 无支持集 | `sampling_mask_tape_missing_in_assembly`；通知先于清理且一次；receipt 为 fatal；无评分／Outcome；session、容器／私网清理完整 |
| digest 不符 | `generate.py:4801-4829`，容器 image 查询和 RepoDigests 查询均成功，值与冻结值不符 | 清理顺利返回时最终 fatal、receipt 正确；通知时序及清理被期限取消的反例见 P1 |
| 血缘不符 | `generate.py:4542-4557`，探针 exit=0、base 对象存在、HEAD／父提交均不符 | 同上 |

mask 案的覆盖边界：该探针证明的是**装配守卫收到破损内部事实后的处置**。真实 capture wire 在 `capture_wire.py:1389-1404` 就解析支持集，之后经 `807-815` 传给 hook；普通引擎响应缺字段可能更早被拦截。不能把本探针表述为“正常生产引擎少报一个字段就一定走装配 fatal”。身份／必需契约／内部 tape 的异常条件都属于接线或内部事实损坏，不宣称正常轨迹会普遍触发。

两个查询故障已分开验证：第二次 image inspect 的 exit=1 产生 `rollout_image_digest_inspect_failed`；血缘命令 exit=1 产生 `rollout_testbed_probe_failed`。两者都返回 ABORTED、Outcome 为 missing、receipt 为 aborted、无 fatal 通知，容器与私网归零。映射表的两个新码在 `outcome_producer.py:99-100`，没有把这些查询失败升级为 run-fatal。digest 命中正例正常评分并交付 `present_complete`，未发现新增正常路径剔除。

## P1：新 fatal 被物化清理延迟，期限取消还能吞掉首因

**可达性：`production_reachable`。** 真实入口／模式／owner／异常捕获链如上；CPU 探针调用真实正式编排，但外部 Docker 接口为替身，因此不冒充真实 Docker 观测。触发条件是：物化已经成功读取并确认 digest 或血缘矛盾，然后其清理仍在等待；如该等待跨过剩余 episode 期限，进入退化分支。

1. **当前行为**：`_attributed_fatal`（`generate.py:4053-4069`）只记 failure_record 并返回异常，通知留给外层 `except FatalExecutionInfrastructureError`（`3620-3627`）。物化内部的 `except Exception`（`4667-4671`）先 `await _cleanup_container`，所以此时尚未通知。若父 task 的期限到点，`3754-3773` 取消子 task；清理 await 抛出的 `CancelledError` 替换了原 fatal，`_settle_cancelled_stage`（`4017-4030`）把它视作取消已完成，随后外层得到 task-local `episode_deadline_in_materialize`。
2. **违反的不变量**：Owner Brief §6 已确认的事实矛盾应停 run、不可被补采掩盖；fatal 应在异步清理前通知；清理不能因为 episode 期限已过而失去最后持有者。仅将 failure_record 标为 Fatal 并不等于 run-halt 已发生。
3. **证据**：两种矛盾各有一案门控清理释放、一案真实期限到点。释放案的事件为 `rm_enter → rm_return → network_rm → fatal:<原码>`；`rm_enter` 时通知数与 receipt 数都为 0。跨期限案事件为 `rm_enter → rm_cancelled → audit_sink`；最终返回 ABORTED，Outcome 与 receipt reason 都为 `episode_deadline_in_materialize`，receipt disposition 为 `aborted`，fatal 通知为 0。结果文件前四案完整记录这些事实。
4. **资源事实与影响**：跨期限案的 `lease_released=false`、容器删除数 0、私网登记数 1、隔离队列数 0、`cleanup_failures=[]`，但记录了 `cleanup_completed=true` 并追加了一条 cleanup receipt。外层没有收到 sandbox，因此不会再次清理该容器。已确认的环境矛盾被当作可补采成员故障；坏任务可继续被补采，清理期也没有及时发出停 run 信号。反例发生在 harness 启动前，不声称模型在漂移环境上执行或 reward 已被污染。
5. **合理可能性与成本**：真实发生频率未知；需要已知矛盾与慢清理／接近期限同现。0.25 秒配置仅压缩演示等待，生产的等价条件是任意预算所剩不足一次清理耗时。即使不跨期限，通知延迟这一部分也不需要第二个故障。问题位于本次新 fatal 的直接接缝，可沿现有 owner 修复，不需要新增 supervisor、重试平台或持久状态机；不影响正常成功轨迹。
6. **建议分期**：本批 §6 收口前修。它是本次语义翻转后暴露的当前生产接缝，不能用此前 A/B 已关闭替代核验；也不据此重开整个 A/B 工作流。
7. **复现**：运行上述脚本，查看 `digest_mismatch:fa_formal:release/cross_deadline` 与 `lineage_mismatch:fa_formal:release/cross_deadline`。故障只来自维护 Docker 替身返回的真实协议形状；取消由生产期限方法自己执行，不直接向收口函数注入预期错误。
8. **必要验收**：进入首个清理 await 前通知恰好一次；清理跨期限／被取消时仍保留原 fatal 与原 reason，receipt 不得变 aborted；容器和私网要么确认回收、要么真实记录清理失败及可回收归属，不能从外层视野消失；两种查询失败仍为 task-local；其余四项 fatal 与 digest 命中正例保持当前处置。

已尝试反驳：清理顺利返回时外层确实会通知一次，因而不能说六项从不 fatal；`_settle_cancelled_stage` 也确实会重新抛仍在途的 Fatal，但本案进入它之前首因已被清理中的取消替换，所以该保护不能关闭反例。failure_record 还在 audit 里也不足以停 run，因为 Outcome／receipt 和通知通道都已按非 fatal 完成。

## 非阻塞观察：`s1_compat` 的声明过宽

当前默认 `dense_config()` 的 `execution_mode` 为 `s1_compat`（`generate.py:1955`；维护夹具未覆盖此字段）。独立三案确认：digest 不符、血缘不符，以及显式开启 mask 后的 tape 缺失都抛原码 Fatal；前两项没有模式守卫，mask 守卫仅看本次 sampling 参数。上述旧兼容路径可由 `BringupService.select_task_face_mode("s1_compat", None)` 选到 `legacy_v1`（`bringup.py:312-335`）；它不是当前首训 formal 路径。

这与交接“`s1_compat` 冻结路径未改变”以及 Brief 批 A 的“全部逐字不变”表述不符；维护 `test_slime_generate.py:1010-1082` 的翻转测试本身也运行在默认兼容配置。对照案证明：finalize 前 `ValidationError` 的 `s1_compat` 保留 ABORTED，不能因此推论其余新 fatal 分支都保留。

建议主审按兼容范围／T1 报告准确性裁决，不作为当前正式训练安全阻塞，不据作者写“已确认”质疑本次只读审查授权。若继续声明整个旧模式冻结，应恢复对应兼容分支；若本轮六项的确认覆盖这三个兼容异常分支，则文档应明确报告该变化。无需扩大检查旧 S1 全链。

## R3 与 `--init` 的直接接缝

- R3：`bringup.py:1422-1430` 在正式模式注入 `DockerQuiescenceBarrier()`；该对象与 `RolloutOrchestrator` 的默认 clock 均为 `time.monotonic`（`quiescence_barrier.py:93`、`generate.py:2369`）。屏障 `111-118` 将停止事实写入 `audit.termination["barrier_stop"]`；正式编排 `3268` 在冻结导出／评分前消费该事实，`3835-3887` 读取归零确认时刻。`bringup.py:627-637` 保留整个 termination 字典，`722-723` 写入 execution audit，因此新增事实没有只停在内存 helper 里。探针只核对该字段保留，不重复主审的 R3 反例回放。
- Z1：`sandbox_profile.py:445` 把 `init=true` 写入参数事实；`472` 发出唯一 `--init`；`1486` 从 inspect 记录 Init；`1512-1515` 拒绝不为 True。`578-585` 的 run 级 digest 消费该参数，`bringup.py:1508-1521` 写入 profile 验证记录。CPU 接缝检查确认 profile／启动参数／inspect 一致，Init=False 恰好产生该项违规，去掉 init 参数后的 digest 与当前不同。真实 Docker 行为留主审实测，本报告不据 CPU 替身认定孤儿已被回收。

## 审查维度与停止条件

A/D/G/L/M：已沿真实准备子 task、父期限、通知器、receipt、资源所有权核对，P1 是具体异常时序证据。B/F/H：查询失败与事实矛盾分开、成功正例正常交付；s1 范围声明需准确。E：故障注入在外部回包／store 操作／必需契约输入，未直接调用分类 helper 制造结果。C/K：本批直接接缝没有发现新长期 owner、开关、retry 平台或临时挡板；不据此扩大扫描其它阶段。J：已列出影响理解的兼容声明，未把机器风格规则当业务 finding。N：只使用本地维护夹具与既有 integration miles 导入路径，没有引入依赖或检查外部升级。I：本轮足以形成裁决，停止继续挖同一边界的理论反例。

关闭 P1 的窄验收完成后，六项可重新收口；R3/Z1 由主审自身回放与真机证据分别裁决。`s1_compat` 的范围说明与既有待定停止合同单独保留，不借此延长本角色审查。
