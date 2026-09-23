# 预算终止闭环：第三次窄复核

日期：2026-09-09。审查基线 `6b33efee`，被审 HEAD `d4af9d9a449555580e27126425391de2cf87fbf5`。范围为 R3 修正 `8fdd9c68`、Z1 `--init` 接线 `3d218b94`、§6 六项 FATAL `f96e3596` 及交接文档。作者说明见 `project1_execution/tmp/claude链路建议.md`。

**结论：R3 上轮两处错判关闭，Z1 修复通过；本批尚不能整体关闭。剩余一项新的 P1：物化阶段先等待清理，已确认的 FATAL 会被 episode 期限取消覆盖为 ABORTED，同时失去该次执行的资源回收。另须落实 owner 本轮已经选择的停止规则 A。** A/B/D-1/R1/R2/R4/R5 的既有关闭结论保持。

本轮仅生成审查工件并同步决策与状态文档，没有修改业务源码、维护测试、依赖、预算或训练配置，没有提交、推送。

## 1. 本轮裁定

| 项目 | 裁定 | 直接证据 |
|---|---|---|
| R3：缺观测被当停止证明，后来墙后见活仍 KEEP | 上轮缺陷关闭 | 原七案中的两条反例现在经真实正式编排与准入函数得到 hard wall / DROP_GROUP |
| R3：墙前停止确认，但指纹读取跨墙造成 DROP | 上轮缺陷关闭 | 899.5 秒确认归零、901 秒指纹返回仍 KEEP；首次强停已确认与屏障首次确认两种入口都有对照 |
| R3：投递早、首次确认晚的推断 KEEP | **owner 本轮选择 A，待落实** | HEAD 仍有 `kill_delivered_before_deadline_late_zero_confirmation`；旧八案的 `confirmation_after_wall` 仍 KEEP |
| Z1：正常结束／强停后的孤儿回收 | 修复通过 | 真实 profile 启动的两个本机 Docker 容器，PID 1 均为 docker-init，真实 stop helper 残留为零，容器和私网已删除 |
| §6：六项升 FATAL | 直接分流基本正确，**F1 未关闭** | 15 案包含真实抛出点、通知、receipt、查询故障、成功正例及兼容模式；物化异常与期限取消组合复现 F1 |
| 血缘脚本缺 base 对象也返回命令失败 | P2，阶段 backlog | 真实临时 Git 仓库复现；既有 producer 的信息不足，不算本轮新阻塞，见 §5 |
| “s1_compat 完全不变” | 文档表述需更正 | digest、血缘及显式启用 mask 后的缺 tape 路径也变为 FATAL；不为这句文案额外增加兼容分支 |

## 2. 本轮已确认的停止合同 A

owner 在本轮问题框明确选择：**“A：只认期限前停止确认（推荐）”。** 这是新的明确批准，不把此前审查建议追认为批准。

范围是预算强停时如何判定有没有撞 hard wall：以控制端收到可信归零确认的时刻为依据，比较沿用现有 `confirmed_at <= deadline`。kill 回包、信号发送结果、期间没有反证，都不能补足期限前的确认。kill 相关字段可留作诊断，不再参与推断 KEEP。

| 期限均为 900 秒 | 应有处置 |
|---|---|
| kill 899.5 返回，首次确认 901 才收到；期间没有正数计数 | hard wall / DROP_GROUP |
| 899.5 已收到停止确认，只有后续指纹或清理到 901 才结束 | turn 截断 / KEEP_FULL，继续真实评分 |
| 第一次查询失败，第二次停止尝试在 899.95 收到零确认，屏障后处理到 905 | KEEP_FULL；本轮两案额外对照已经证明此路径可保留 |
| 期限后发起的查询仍见进程，随后才归零 | hard wall / DROP_GROUP；cap 事实保留 |

代价是：实际早停而确认晚到的部分轨迹也会被丢弃。**损失频率未知，不能称“微小”**。这不要求现在做专项 GPU 实验，也不改变 600 秒／25 次的现有数值。自然结束、评分、清理的既有分期不被本选择扩展；确认后的处理跨墙不补造超时。

建议删除 `execution_scope.py:162` 的推断型 True 分支，并同步注释与受影响的测试 oracle。不要再为不同 kill 回包形状增加更多推断。验收用现有八案修改这一案的期望，加上已有墙前确认／晚后处理对照即可；应核到 Outcome、receipt 与实际成员处置一致。

## 3. F1 — P1：物化阶段清理吞掉致命首因，随后按普通超时补采

**生产可达性：`production_reachable`。** 当前正式入口 `Rh2MilesGenerateFn → RolloutOrchestrator.generate → _await_within_episode_deadline → _prepare_workspace → _materialize_rollout_sandbox`。准备子 task 和父期限在 miles owner loop 上运行，子 task 继承真实 `LifecycleState` 的通知器。只有物化成功返回后，外层才拿到 `prepared["sandbox"]`。本轮复现使用真实编排／期限／receipt／清理代码，Docker 外部 IO 为替身，不冒充真实生产作业观测。

1. **行为与触发条件**：已经成功读取并识别镜像 digest 或 Git 血缘矛盾，抛出 typed FATAL；物化内部却先等待容器清理，再向外抛。只要清理耗时超过剩余 episode 时间，父 task 的期限取消就能覆盖这条 FATAL。
2. **违反的不变量**：已批准的确定性事实矛盾应立即通知停 run；异步清理不能覆盖首因；资源最后持有者必须完成有界回收或交接失败记录。将 `failure_record` 写成 Fatal 不等于通知已经发生。
3. **准确位置与根因**：`generate.py:4667-4671` 的 `except Exception` 先 `await _cleanup_container`，而外层通知在 `3620-3627`。`_attributed_fatal`（`4053-4069`）只是构造异常。父期限 `3754-3774` 取消准备子 task 后，清理 await 抛 `CancelledError`，原 fatal 被替换；这个取消发生在 except 的处理体内，不会重新进入同级 `except CancelledError`。`_settle_cancelled_stage` 只能看到取消，无法重新抛出已经消失的首因。
4. **实测证据**：digest、血缘各做一条放行清理的对照和一条让期限到点的反例。放行案在 `rm_enter` 时通知为零，事件顺序为 `rm_return → network_rm → fatal`。跨期限案为 `rm_enter → rm_cancelled → audit_sink`：返回 ABORTED，Outcome／receipt reason 均为 `episode_deadline_in_materialize`，receipt 为 `aborted`，**停机通知为零**。
5. **影响与可探测性**：跨期限两案都为 `lease_released=false`、容器删除数 0、私网登记数 1、隔离队列数 0，`cleanup_failures=[]`，却记录了 `cleanup_completed`。外层没有 sandbox 引用，无法再次回收该资源；后续 run 级清扫可能兜底，不能据此称永久泄漏，但该次执行已未完成回收。已确认的环境错误会继续走补采；原 failure_record 虽可供人工查阅，run-halt 通道与终态并未兑现。错误发生在模型启动前，不声称本案造成漂移环境上的训练或 reward 污染。
6. **分期与比例**：本批 §6 收口前修，原因是新 FATAL 接入当前准备期限后的直接缺口。频率未知；不跨期限时也有等待清理才通知的问题。探针的 0.25 秒只是缩短等待，生产等价条件是“剩余预算短于清理耗时”。沿现有物化 owner 与通知通道即可修复；不需要新的 supervisor、持久化状态机或重试平台，不重开整个 A/B。
7. **复现入口**：[production_probe.py](production_probe.py) 的前四案；主审已读脚本后独立执行，结果 [production_probe_root.jsonl](production_probe_root.jsonl)。没有直接向终态函数塞 Fatal 或手工改 Outcome；Fatal 由真实校验点产生，取消由真实期限触发。
8. **最小验收条件**：首个清理 await 前已经通知，且只通知原首因一次；清理跨期限／被取消后仍传播原 Fatal、receipt 仍为 `fatal_run_halt` 与原码；资源确认回收，或准确登记失败及后续回收归属；两种查询失败仍 ABORTED，成功路径正常交付。物化阶段的真实 `ValidationError` 也由同一边界收口，应保留一条同类对照。

仅提前通知不足以关闭 F1：还需保留原异常与资源所有权，否则会出现“已通知 fatal，但 receipt 却 aborted”的另一种不一致。仅屏蔽所有取消也不合适：清理仍须有自己的时间上界。推荐沿现有 owner 明确“异常先定、先通知，再有界清理并保留首因”；按上述结果验收，不指定新增实现层。

两角色均核对这一边界；主审独立复跑确认。常见反驳不成立：顺利清理后确实最终 fatal，但反例针对清理被取消；`_settle_cancelled_stage` 会转抛仍在途的 Fatal，但本案到那里时异常已经是 CancelledError。

## 4. 已通过项与验证边界

R3 原七案修后重放全部符合各自期望；另保留原八案，其中晚确认 KEEP 是 HEAD 的待改现状，不能当 A 已实现。副本的完整改动保存在 [七案脚本差异](stop_evidence_replay.diff) 与 [八案脚本差异](stop_cases_replay.diff)：接入屏障自己的 clock，并将已修反例的断言改为目标结果，没有替换生产判定。另两案从第一次 kill 后十次不可读查询走真实第二次停止，899.95 收到归零后，即使屏障／指纹到 905 仍 KEEP，Outcome、receipt 与 AdmissionPayload 同一事实。

Z1 使用当前 `RolloutSandboxProfile.docker_run_args` 的真实参数启动 `node:22-bookworm`，固定 UID 54321、生产 cap／tmpfs／no-new-privileges 接线、独立 internal 网络、无宿主挂载。真实 inspect 经 `check_rollout_inspect` 无违规，`Init=false` 的读数对照只产生预期的 init 违规；profile 参数与 digest 包含 init。正常命令经实际 vendored `exec_and_wait` 返回，强停案包含 agent 的 shell 和子进程；真实 stop helper 两案残留均为零。Docker 29.4.1、ARM64、镜像 ID 及参数见 [真机结果](init_profile_docker_result.json)。全部自建容器与网络已删除，并按本轮唯一 label 再次核查为空。

这是本机进程回收与 profile 接线验证，**不等于目标 SWE 镜像＋真实 Claude Code＋模型服务／GPU 验收**。没有启动真实 CC，没有调用模型 API，没有声称验证全部 prelaunch 环境探针。

§6 的身份缺失、必需契约 `ValidationError`、冻结工件持久化失败、mask tape 缺失，均核到实际抛出点、通知与 receipt；digest 命中正例正常评分交付。mask 案只证明装配守卫接到破损内部事实的处置；真实 wire 可能更早拒绝引擎缺字段，不能把该案当成普通引擎少报字段的完整生产重现。

## 5. 只登记的范围与覆盖问题

**P2 / 阶段 backlog：缺 base 对象没有独立事实输出。** `envpack/materialize.py:55-88` 的真实脚本以 `git cat-file -e BASE^{commit} && ...` 串联，完整且 `git fsck` 正常的临时仓库缺所需 base 时，脚本实际返回 128，stdout 已有有效 HEAD，但 `evaluate_probe` 不消费非零结果。这个原始回包送进正式编排得到 `rollout_testbed_probe_failed`／ABORTED；base 在场但 HEAD 超两代的对照返回 0，得到预期 FATAL。真正的 Docker 查询失败对照仍 ABORTED。

这说明“命令非零”也可能来自确定的环境条件不满足，不能等同“瞬态故障”。但作者明确将命令失败保留 task-local，producer 又是既有实现，本轮不把它判为新阻塞或违背“成功返回后内容不符”的字面合同。建议后续局部修改 producer：正常完成的对象查询应显式报告存在／不存在，查询本身失败另走错误通道。不要把任意非零升级 FATAL，也不要靠解析英文 stderr 猜原因。没有扩大到数据集选择或环境质量审计。

**文档范围更正。** `s1_compat` 的 digest／血缘／显式 mask 缺 tape 分支也变为 FATAL；对应默认兼容夹具与独立四案已确认，`ValidationError` 的兼容对照则仍 ABORTED。因此“全部冻结不变”不准确。建议如实登记这些共享异常分支变化；当前正式链不因这个文案问题阻塞，也不建议为了保留过宽声明额外维护旧分支。另已将“损失微小”更正为“频率未知”。

## 6. 验证清单与停止条件

以下均为主审本轮实际执行，非转述作者结果：

| 检查 | 结果／产物 |
|---|---|
| 11 个相关维护测试文件，接入 integration miles | **255 passed in 16.31s**；[日志](focused_tests.txt) |
| 15 个改动 Python 文件 ruff | 通过；[日志](ruff.txt) |
| 上轮七案＋八案重放 | 退出 0；[七案](stop_evidence_replay.jsonl)、[八案](stop_cases_replay.jsonl)；包含现状断言，不等于全部语义通过 |
| 六项 FATAL 与物化期限／兼容范围 15 案 | 退出 0；[主审结果](production_probe_root.jsonl)、[完整结构化结果](production_probe_result.json)；含 F1 反例 |
| 独立反证脚本：停止 2 案＋Git 生产脚本及正式链 3 案 | 退出 0；[主审结果](falsifier_probe_root.jsonl) |
| 实际 profile 的真实 Docker 正常／强停 2 案 | 退出 0；[脚本](init_profile_docker_probe.py)、[结果](init_profile_docker_result.json) |
| 审查前后 15 个源码／维护文件摘要 | 无变化；[起始快照](review_snapshot.json)、[核验汇总](verification_summary.json) |

作者全量 `2187 passed / 0 skipped` 没有由主审再次重跑。两角色独立材料：[Production Tracer](production_tracer.md)、[Falsifier](falsifier.md)。本轮重点覆盖 A/D/G/L/M 的时序、事实和所有权，B/F/H 的失败分流与样本处置，E 的真实 producer 和 IO 注入；C/K/I 控制改动与审查范围。J 的不准确声明已指出，N 不涉及依赖升级，未据此推断其它模块无问题。

**下一次只收尾两件必需事项：落实已批 A；关闭 F1 的首因／通知／资源回收反例。** 回放相应旧反例及必要正例，测试 oracle 改动按 T1 登记。R3 上轮两处、Z1 和此前已关闭批次到此停止复核。P2 缺 base 的 producer 覆盖进入阶段 backlog；兼容范围文案同步，不借机重开 legacy 全链。以上完成后即可进入下一切片，不继续以“还可构造边界”为由扩大本批。
