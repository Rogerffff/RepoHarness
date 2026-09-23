# 第三次窄复核：Falsifier / Simplifier

基线 `6b33efee`，审查 HEAD `d4af9d9a449555580e27126425391de2cf87fbf5`。主责 `8fdd9c68`，静态反查 `f96e3596`；完整阅读两项提交的源码与维护测试 diff、当前 Budget Brief、作者 `tmp/claude链路建议.md` 和上一轮 `followup2/README.md`。

**结论：没有找到独立于原停止合同的新 R3 反例。原先的两个错误方向已有对应生产修正；本角色新增的“首次投递成功但十次计数不可读，重试墙前确认”及时/晚到后处理对照均为 KEEP_FULL。owner 在本轮已选择方案 A，当前 HEAD 的残留推断型 KEEP 需按已批决定删除。最后交叉核对支持 Production Tracer 的新 P1：物化 FATAL 的清理被期限取消时，首因会降成 ABORTED，且资源未回收。base 缺席与运输失败同桶按 P2 阶段 backlog 登记，不作本轮新阻塞。**

本报告不代替主审独立复跑七案/八案、维护测试及真实 Docker。停止合同状态以本轮 owner 新决定为准，不再列为待定风险。

## 1. R3 的生产接缝与独立对照

`execution_scope.stop_proven_before`（`execution_scope.py:146–162`）现在要求已有墙前零确认，或落入作者明确登记的残留推断型 KEEP。成功 kill 后从未归零、计数次数耗尽均不再构成证明。`generate.py:3938–3967` 对尚未证明且未到点的执行继续有界重试；尝试用尽则保留未定状态，交给屏障确认。

`DockerQuiescenceBarrier.establish`（`quiescence_barrier.py:110–122`）把真实 helper 的停止观测与 `confirmed_at` 写入 `termination.barrier_stop`。编排在 `generate.py:3268`、`3835–3887` 消费它，判定已在 Outcome 构造之前完成；指纹读取结束时刻不参与比较。后续若确实在墙后发起查询并看到残留，仍能改判 hard wall；仅仅晚读到相同的零结果，不推翻已有墙前确认。

新增探针保留生产的十次计数上限、0.5 秒轮询间隔、停止总上限和重试次数，未包装或改写停止函数返回值。两案都经真实 formal 编排、真实停止 helper、真实 Docker 屏障、Outcome 和 `decide_member_disposition`：

| 对照 | 首次停止 | 第二次停止 | 屏障零确认 / 指纹返回 | 最终事实与处置 |
|---|---|---|---|---|
| `retry_confirmed_control` | 899.9 kill 成功；十次 COUNT 均不可读 | 899.95 已收到归零确认 | 899.97 / 899.99 | `max_turns_exhausted` / KEEP_FULL |
| `retry_confirmed_then_late_postprocessing` | 同上 | 同上 | 901.2 / 905.0 | 同上 |

期限均为 900。两案 `stop_attempts=2`，保留十条 `residual=-1` 与后续一条零确认；`stop_before_deadline_evidence=zero_confirmed_before_deadline`。各只产生一份 Outcome，receipt 与真实交付的 `AdmissionPayloadV1.outcome` 都与该 Outcome 逐字段相等；各评分一次、零 halt 通知、harness task 已结束、清理完成。这里评分与模型 IO 沿用 CPU 夹具，不声称真实模型 reward 验证。

**组准入的证据范围：** 本探针动态调用的是组准入实际使用的 `decide_member_disposition`，输入为真实编排交付的载荷，没有手写 Outcome 或改写结论。静态确认 `adapters/miles/group_admission.py:391–478` 读取载荷、核对终止事实后调用同一处置函数。未在本探针跑完整 miles buffer：基础 formal 夹具尚未经过 miles 的六字段交付盖章，直接送完整 filter 会因身份缺席被正常拒绝，不能借修改载荷掩盖这一层。完整组运输留主审已有验证范围。

重试没有新增状态 owner、后台服务或新的次数/时间上限；本次扩展只是在“kill 已返回但没有可信确认”时仍允许既有重试。在对照中，第二次尝试确实在 drain 之前取得可信确认，不能简单称它毫无作用。没有真实故障率与吞吐测量，不声称重试收益或损失很小，也不建议继续加重试层。

## 2. owner 已选择方案 A，当前 HEAD 待落实

当前事实不能概括成“都只认墙前零确认”：

| 已取得的观测 | 当前实现 |
|---|---|
| 强停或后续屏障在墙前已确认零 | KEEP；后处理耗时不变更预算归因 |
| 强停从未确认，且期限未到 | 既有次数内重试；用尽后由屏障决定 |
| 强停未证明、期限已过，或后续屏障才在墙后确认 | hard wall / DROP；其中包含实际停止时刻不可辨识的情况 |
| kill 早于期限，后来才确认零，其间没有投递后的正数观测 | 当前 HEAD 仍推断 KEEP；owner 已选 A，需改为不构成墙前停止证明 |
| 屏障在墙后发起计数仍见残留 | hard wall；不能用更早的 kill 动作抹去该观测 |

最后保留的推断依赖 kill 动作对整个 scope 的覆盖；成功完成枚举与信号调用，不等于控制端拿到了整个 scope 的停止时刻。owner 已选择“以墙前收到可信零确认为唯一边界”，需删除 `execution_scope.py:162` 的推断型证明并同步相应 oracle。代价是实际已经停止、确认回包迟到的成员也会被保守排除；这是已明确接受的准入规则，不再等待再次批准。没有新增监督/恢复系统的必要。

作者“样本损失微小”的表述没有统计依据，应改为“发生率与整组损失未知”。一个成员改为 DROP 即可牵连整个组，不能由一次往返耗时短直接推出训练影响小。本报告不把这条已登记边界重新编号为 finding；本角色也没有修改业务源码或维护测试 oracle。

## 3. 交叉反证：支持物化 FATAL 被期限取消覆盖的 P1

按主审要求，独立阅读 [production_probe.py](production_probe.py) 前四案、[结果](production_probe_result.json)及对应源码；没有重复跑该角色的运输矩阵。尝试以下反驳均不成立：

- **不是外部任意取消。** 探针把任务期限缩为 0.25 秒，只在 Docker `rm` IO 等待门控；取消由生产 `_await_within_episode_deadline`（`generate.py:3754–3773`）在真实时间到点后自行执行，未改时钟、未注入 `CancelledError`。
- **不是通知器漏装。** 探针使用真实 `LifecycleState.enter_execution`（`shutdown/chain.py:204–217`）安装 context notifier，准备子 task 在其后创建并继承 context。相同物化异常、只释放 `rm` 门控的两案最终各收到一次原 Fatal，验证了通知路径存在。
- **原 Fatal 再抛保护无法挽救本案。** `_attributed_fatal` 只落记录并返回异常；物化 `except Exception`（`generate.py:4667–4671`）先 await 清理。清理里的取消发生在这个 except 的执行体内，不会重新进入同级 `except CancelledError`。`_cleanup_container:5468–5480` 只捕自身超时，父取消穿过；到 `_settle_cancelled_stage:4017–4030` 时已经只有 `CancelledError`，它看不到可重新抛出的原 Fatal。
- **外层 finally 不能凭已有句柄补清。** `_prepare_workspace` 必须等物化返回才写 `prepared["sandbox"]`；本案尚未返回，外层 `2757–2761` 取到 None。结果中的 `cleanup_completed=true` 仅说明外层清理段跑完，不能证明未交出的容器/私网已经释放。

**行为与证据。** digest 与 lineage 矛盾的及时释放案都为 `rm_enter → rm_return → network_rm → fatal:<原码>`。跨期限案都为 `rm_enter → rm_cancelled → audit_sink`，返回 ABORTED；Outcome/receipt reason 变成 `episode_deadline_in_materialize`、receipt disposition 为 `aborted`、零 halt，容器删除数为 0，私网登记仍为 1。这些动态数据来自 Production Tracer，本角色做的是独立源码与夹具有效性反查。

**不变量、生产可达性与影响。** 本轮刚改为 run-fatal 的确定性矛盾，在已发生之后不能被普通预算超时降成可补采成员；清理还有独立预算，episode 到点也不能取消唯一资源持有者的收尾。当前默认 formal 准备链本来就由父 task 的 episode 期限约束，Docker 删除等待跨过剩余期限是合法当前时序。不是只有测试 0.25 秒参数才能到达；600 秒预算在准备消耗接近上限时也有相同窗口，实际频率未知。没有评分污染证据；已证实的是 fatal 通道与终态丢失、资源残留且未登记隔离，不能称为无害诊断延迟。

**分期与验收。** 支持作为本轮 P1 收尾，不扩展新的错误矩阵。早通知本身不够：原 Fatal 必须仍是返回异常和 receipt 首因，通知一次，且唯一持有的容器/私网在独立预算内收口；最终无法释放时须如实落账。按前四案复现，保留普通查询失败/普通期限取消对照，即足以关闭，不需要重写整个生命周期平台。

## 4. P2 阶段 backlog：血缘 producer 中 base 缺席与运输失败同桶

**当前行为与位置。** `envpack/materialize.py:65,82` 明确规定：`git cat-file -e <base>^{commit}` 失败时整段探针退出非零。`evaluate_probe:158–164` 对任何非零均不解析 stdout。新增的 `generate.py:4548–4551` 随后把任何非零归为 `rollout_testbed_probe_failed`；`outcome_producer.py:100` 将其映射为 `sandbox_failure` / `sandbox_crash`。因此已经读取到 HEAD、但仓库中确定没有冻结 base 的情形，也无法到达 `4552–4556` 的 FATAL 分支。

**独立证据。** 探针建立临时 git 仓库，以真实 git 创建空提交；执行真实 `build_probe_script`，只把固定 `/testbed` 换成临时工作目录。所有子进程设置 `GIT_CONFIG_GLOBAL` 指向临时文件及 `GIT_CONFIG_NOSYSTEM=1`，没有修改用户全局配置；临时仓库已回收。正常同 HEAD 控制为 exit 0 / `parsed_ok=true`；`git fsck --full` 为 exit 0。

对象 `ffffffffffffffffffffffffffffffffffffffff` 确实不存在时，生产脚本原始输出为：

```text
exit_code = 128
stdout = HEAD=9121bc9ffab41298a0e5d4654245adf0625badc5
stderr = fatal: Not a valid object name ffffffffffffffffffffffffffffffffffffffff^{commit}
```

将上述原始 `ExecResult` 原样接入真实 formal 物化通道，未替换 parser、异常分流或 Outcome：

| IO 来源 | 编排结果 | receipt | halt / 评分 / 容器清理 |
|---|---|---|---|
| 完整临时仓库，base 确定缺席，真实脚本 exit 128 | `rollout_testbed_probe_failed`；`missing`；返回 ABORTED | `aborted`，同原因码 | 0 / 0 / 已清 |
| 同一仓库，base 在场、HEAD 为其孙提交，真实脚本 exit 0 | `rollout_testbed_lineage_failed`；抛 FATAL；无 Outcome | `fatal_run_halt`，同原因码 | 1 / 0 / 已清 |
| Docker 运输失败控制，exit 1、无 stdout | 与第一行同为 task-local ABORTED | `aborted` | 0 / 0 / 已清 |

**合同差别与违反的不变量。** base 缺席不是“整个探针成功退出后 HEAD 不符”：本案确实 exit 128，现有 parser 也确实把局部 stdout 丢弃。因此若把 owner 限定严格解释为“只升级整段 exit 0 后的矛盾”，当前分支符合这条较窄规则。不能隐去这个区别，直接宣称它违反所有已批边界。

但本案的对象查询已经给出了确定性负结果：在可读、完整的仓库中，冻结 base 根本不在。它违反现有血缘前提“base 对象存在”，与临时 Docker 传输失败不是同一种事实。§6 宣称完整区分“确定性环境矛盾”与“可补采的临时查询故障”时，当前 producer 的退出协议没有承载这一区别；不是加一个异常名就完成了归因。

**生产可达性与影响。** 当前 formal 路径始终运行该脚本；任务冻结的 base 与实际镜像历史不匹配即可触发，不需要未来能力或模型篡改可信控制面。已对真实 git 的输出与真实 formal 分流完成 CPU 接缝验证，未在目标 SWE 镜像上复现，也未测量该缺陷的实际发生率。该成员不会被评分或错放进训练；影响是确定性环境缺陷仍可被补采流程当作局部缺员，固定任务/镜像不变时重复执行无法使对象凭空出现，可能形成选择性任务丢失。没有证据主张整次训练必然丢失某个比例。

**分期与最小修正方向。** 主审裁决为 **P2 阶段 backlog / 局部覆盖缺口，不阻塞本轮**：原说明已经把“血缘探针命令失败”保留 ABORTED，缺 base 的生产脚本又是既有实现，不能称为违反“整段 exit 0 后内容不符”的字面合同。后续若细分这一事实，最小方向是让现有探针对“完成查询且对象缺席”给出可区分结果，再在原抛出点分流，并按最终确定的合同验收。不要仅凭任意非零或一段 stderr 全部升 FATAL，也不需要通用分类框架或重试平台。

**复现与验收条件。** 下节脚本同时覆盖上述三行；exit 0 表示反例被准确复现，第一行的 ABORTED 断言不是修后验收标准。若选择修正，必须先由真实脚本证明它区分“base 缺席 / 读取无法完成”，再验证 formal 的 receipt、halt 与清理：前者按最终确认合同，后者保持局部 ABORTED；原有 base 在场但血缘不符仍 FATAL。只改假的 `ExecResult` oracle 不足以关闭 producer 接缝。

## 5. 六项边界的其余静态反查

| 项目 | 反查结果与边界 |
|---|---|
| 身份不全 | `generate.py:2733–2750` 限非 s1，抛出点直接 `_attributed_fatal`，不再经过软失败映射 |
| finalize 前 `ValidationError` | `3642–3655` 只给非 s1 扩大 FATAL；s1 的该异常仍保留既有阶段分流 |
| artifact 本体持久化失败 | `3371–3394` 原冲突型 Fatal 保留，其余失败改 `_attributed_fatal`；发生在 formal artifact 路径 |
| sampling support 缺 tape | `3135–3150` 的 guard 只在启用 mask 的装配路径检查 `is None`，没有把合法空支持集当缺失 |
| 镜像 digest | `4818–4829` 确实先分 inspect 非零，再处理成功读取后的 mismatch；未找到与本轮改动相关的另一条独立混桶反例 |
| 血缘 | HEAD/父提交成功读取后的不符已 FATAL；base 缺席例外见上节 |

**非阻塞准确性更正：** 作者“s1_compat 冻结路径逐字不变”并非对所有六项成立。digest 与 lineage 共用物化路径，没有 mode 守卫；`test_slime_generate.py:1010–1081` 的默认 `build_dense_chain` 正是 s1_compat，作者已将这些 oracle 改为 Fatal。这不造成正式 miles 的错误准入，也不值得为 legacy 另加兼容分支；应在当前说明中把范围写准，不拿“逐字不变”概括全部失败路径。

## 6. 验证、产物与停止条件

本角色实际运行一次冻结版脚本，exit 0：两案停止对照、一个真实 git producer 组（正常/缺 base/血缘不符）与三案 formal 处置。未重跑主审负责的七案/八案、全量维护测试、真实 Docker、CC、GPU 或外部 API。运行期间五个相关源码文件摘要前后相同，摘要记录在 JSONL 首行。

开发探针时曾因缺少 miles 导入路径、以及基础 formal 夹具没有经过 miles 六字段盖章而无法直接调用完整 filter；这些是探针接线问题，不算生产 finding。冻结版保留真实成员处置函数，完整 buffer 运输由主审验证；没有给交付结果补身份或改写 Outcome 来让探针变绿。

从仓库根目录运行：

```bash
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/budget_loop_impl_20260909/combined_review_20260909/followup3/falsifier_probe.py
```

脚本：[falsifier_probe.py](falsifier_probe.py)，原始结果：[falsifier_probe.jsonl](falsifier_probe.jsonl)。脚本 SHA256：`b741041c44eaa2154d98b2ea760651126025ef0672d5c9aa15ad8e0ffdca2148`；本角色结果 SHA256：`406389bd191657167236e54f072e352ce0470e891e034c98352c3b32d8cf6ff9`。临时提交含本次运行时间，主审复跑时具体 commit SHA 会不同，行为判据不依赖这些值。

适用维度：A/E/G 用真实函数与原始 IO 分界；B/F 明确未知 KEEP 与错误分类各自影响；D/H 确认停止观测、Outcome、receipt 同源；I/J/K/L 限定重试与简化范围；M 逐层保留实际原因；N 用真实 git 退出协议核查依赖接缝。C 无本角色新增生产挡板。没有重审 reward/loss 算术、数据筛选与历史已关闭 guards，因为本次 diff 不改变它们。

**停止条件：** 原 R3 两处可随主审复跑结论关闭；当前只剩已批方案 A 的落实，以及本文支持的新 P1 物化 FATAL/取消收尾。base 缺席按 P2 阶段 backlog，s1 范围声明作非阻塞更正；不再扩大停止或异常矩阵。真实 Docker 的 `--init` 验证由主审独立结论决定。本角色只写本目录的脚本、JSONL 与本报告，未改业务源码、维护测试、旧工件、Brief、账本或主仓库 git 状态。
