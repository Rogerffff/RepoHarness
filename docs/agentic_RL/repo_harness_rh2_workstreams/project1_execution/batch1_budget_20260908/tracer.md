# 第一组预算与停止边界：Production Tracer

日期：2026-09-08；仅 I02/I03/I04/I14。基线 `d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`；本批七个限定源码文件相对原核查基线 `ac0e2e64163fbe49411540e901df439aea16b6b0` 无 diff。
复用 [既有 RT-3/4/5](../issue_inventory_20260908/runtime_tracer.md#4-rt-325-次-cap-是-api-请求限制没有变成训练预算事实) 与 [历史 CPU 输出](../../miles_spike/external_infra_review_crosscheck_20260906/runtime-result.log)；本批只读源码，未跑新探针、GPU、Docker，未修改实现。

## 1. 已批与待决不能混写

- **A4/D2 已于 2026-09-04 批准，并有修订。** 普通可信 `tests_failed` / `patch_apply_failed` 可以是 reward=0；执行 scope 无法终止属 run-fatal。旧 A4 的“测试路径命中便整组排除”已被 §1.5 D2-3 的可信评分投影取代，不能照旧段落再要求 owner 批一次。[A4](../../06-first-training-local-execution-plan.md#L37)、[D2/B 修订](../../06-first-training-local-execution-plan.md#L96)
- **A5-a 确定性 horizon、A5-b hard wall 的训练保留/排除仍待 C。** 未批前仅记录事实，缺 disposition 显式报错；不存在“先补一个安全默认值”的已批授权。A5 已写明资源占用起表，但当前的实际计时接线并未因此自动统一。[A5](../../06-first-training-local-execution-plan.md#L45)
- 不变的区分是：**到期原因、是否已停止并取得完整可评分事实、是否进入训练是三个问题。** 预算结束不必然 reward=0；完整冻结后仍由真实 grader 给出结果，训练处置再按 A5 决定。

## 2. I02：25 数的到底是什么

生产默认 `RH2_MAX_TURNS_PER_SID=25`，构造 adapter 时传入；已有环境参数可配置。[默认与接线](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L228)、[adapter](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L887)

| 事件 | 当前计数行为 |
|---|---|
| 请求通过 guard，JSON/预处理/sid/closed 检查完成 | `_check_turn_cap` 在渲染与模型调用前同步加一；不是成功采样或工具执行后计数。 |
| 加一后的渲染失败、API 失败、取消、context 空输出 | 不退计数；因此 cap 不等于已交付模型轮数。 |
| 认证/JSON 等前置失败、已 closed 请求 | 尚未到 cap，不计。 |
| CC 再发一个 HTTP 请求 | 再经过 cap；前 25 次放行，第 26 次及以后返回 429。命中后不再增加计数，也不直接 kill scope。 |
| 一次响应多个工具调用；同 sid 子 agent 请求 | 前者只占一次；后者共享该 sid 预算，不是每个子 agent 独享 25。 |

锚点：[计数与 429](../../../../../rh2/src/slime/agent/adapters/common.py#L285)、[入口顺序](../../../../../rh2/src/slime/agent/adapters/common.py#L325)、[共享 sid 说明](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L1111)。错误文案“killing run”不能当作进程已终止证据。

**内部重生成须收窄到真实接线。** 通用 proxy 的循环若执行，仍位于一次 HTTP 请求内，不会重新触发 cap；但当前生产工厂注入 `StaticActiveCoordinator`，永远 ACTIVE、epoch=0，失败无法满足重生成所需的更新窗口重叠条件，直接 poison。不能把旧注释中的 proxy 内部重生成说成当前 miles 常态；引擎内部处理也不会凭空多经过一次 HTTP cap。[生产工厂](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L595)、[静态协调器](../../../../../rh2/src/repoharness2/adapters/slime/async_worker.py#L389)、[失败分支](../../../../../rh2/src/repoharness2/adapters/slime/async_worker.py#L912)

本批限定文件没有 `max_turns_exhausted` producer，既有 RT-3 的全源码核查结论相同。旧探针只证 25 次放行后 429；**当前 CC 接到它是重试、退出还是等到墙钟，仍未实测**。因此 T0 需明确预算单位和作用域，不能先把 25 改成较大数字当作语义完成。

## 3. I03：计时起点与到期出口

| 时钟/事实 | 真实起点与边界 |
|---|---|
| attempt 审计墙钟 | `RolloutAudit` 在 materialize 前构造，到 audit sink 时记录结束；这是观测，不是包围整条执行的 timeout。[起点](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L2567)、[落账](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L526) |
| 实际资源占用 | 私有网络/容器在 baseline census、CLI 安装和权限准备之前创建；之后传给 harness 的仍是全额 `task.time_budget_seconds`，没有扣除这些准备时间。[创建](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3877)、[原额传入](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L2690) |
| harness hard wall | CLI 安装及权限准备完成、detached 命令启动后，等待 done marker 才以 `time.time()+budget` 起表；5 秒轮询和 RPC 使它不是精确瞬间截止。[启动前准备](../../../../../rh2/src/repoharness2/adapters/slime/bringup.py#L345)、[计时](../../../../../rh2/src/slime/agent/sandbox.py#L63) |
| proxy session deadline | 第一次真正进入 proxy 调用时，以 monotonic 加同一默认 600 秒起表；不是 open_session 或资源创建时。单 send timeout 为 `min(900, remaining)`。[起表](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L377)、[消费](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L1159)、[timeout](../../../../../rh2/src/repoharness2/adapters/slime/async_worker.py#L734) |
| session drain | 后续另给默认 30 秒：revoke 后等 inflight 归零；超时返回不干净事实，本身不是杀掉模型/容器进程的证明。[实现](../../../../../rh2/src/repoharness2/adapters/slime/capture_wire.py#L534) |

**已证实的窄实现缺口：** `_send` 先算 timeout，再无同一 deadline 地等待 `model_call` semaphore，拿到许可仍用旧 timeout。历史真 proxy 探针 deadline=20ms，41ms 才发出请求、47ms 返回成功。生产工厂确实注入默认 32 容量的 limiter；故路径可达，频率和 GPU 损失比例未知。[排队位置](../../../../../rh2/src/repoharness2/adapters/slime/async_worker.py#L742)、[历史结果第 13 行](../../miles_spike/external_infra_review_crosscheck_20260906/runtime-result.log#L13)

**两种到期结果不同：** harness 返回 `-1` 会记 `hard_wall_timeout` 并继续收口；proxy 剩余不足默认 5 秒则抛 `episode_deadline_exhausted`、poison，取消 harness 等待任务，按 `session_poisoned_during_execution` 进入 API 故障/missing 路径。它们先后取决于启动偏移、请求时刻、轮询及排队，不能仅用 600/900/30 秒常量判定谁必先发生。[harness](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L2738)、[proxy](../../../../../rh2/src/repoharness2/adapters/slime/async_worker.py#L827)、[剩余检查](../../../../../rh2/src/repoharness2/adapters/slime/async_worker.py#L853)

## 4. I04：截断能否停止、冻结、评分

**现行 hard-wall 路径允许继续冻结评分，但有前提。** `-1` 不走非零 crash 拒绝；随后按 `session drain → finish_session → capture 对账 → runtime quiescence barrier → frozen artifact 持久化 → 释放 rollout 容器 → fresh grader` 收口。满足完整性才可能成为 `present_truncated`；不是所有 timeout 都自动有可信 reward。[流程](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L2753)、[屏障与冻结](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3021)、[先释放后评分](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3185)

`_await_done_marker` 返回 `-1` 自身不停止 detached 进程；实际停止/冻结在后续屏障。因此“墙钟到期”与“文件冻结”不是同一时刻，期间允许在飞请求收尾，也可能仍有容器内工作。当前没有这段延迟的真实 CC 测量，不能宣称精确在第 600 秒取到最终 patch。

drain 不干净会在进屏障前失败；屏障异常属 fatal，typed `QuiescenceRejected` 则不评分而返回拒绝结果。本批只核编排调用及结果分支，不扩审屏障内部的进程枚举/杀停实现。[drain 拒绝](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L4260)、[屏障异常](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3033)、[typed 拒绝](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L3303)

I04 的缺 disposition 是**在完整截断成员到达准入裁决时**才触发的待决接口；已有 RT-5 已核无生产注入。上游若先变 poison/missing，根本到不了这项选择。不能用给 A5 填值代替解释 I02/I03 的预算事实，也不能把 A5 未批误报为已经跑坏的正式作业。[已有消费者核查](../issue_inventory_20260908/runtime_tracer.md#6-rt-5截断裁决接口存在实际策略仍未生产注入)

## 5. I14：Python 取消、Docker CLI 与容器测试各由谁负责

- **`run_docker` 持有宿主 subprocess。** 当前只 `create_subprocess_exec → communicate`，没有取消时的 terminate/kill/reap；它是 grader 与 rollout 编排的默认通道，不只是测试替身。[实现](../../../../../rh2/src/repoharness2/grading/manager.py#L95)、[grader 注入](../../../../../rh2/src/repoharness2/grading/manager.py#L871)、[rollout 注入](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L2385)
- **grader 的 phase timeout 取消的是等待。** `_exec_bash_checked` 将超时变为 `GradingInfraError`，`grade` 产 `failed_to_grade / reward=None`，不是可信 tests_failed=0。[timeout](../../../../../rh2/src/repoharness2/grading/manager.py#L1463)、[报告](../../../../../rh2/src/repoharness2/grading/manager.py#L1214)
- **容器归 GradingManager 清理。** `grade` 的 finally 调 `docker rm -f`；失败仅记 cleanup_failures、保留未 removed 状态供后续 gc/close 回收。测试在 Python 等待结束后仍可能运行到 rm 生效；不能把 `proc.kill()` 单独视为容器内工作停止证明。[finally](../../../../../rh2/src/repoharness2/grading/manager.py#L1239)、[rm](../../../../../rh2/src/repoharness2/grading/manager.py#L1410)、[gc](../../../../../rh2/src/repoharness2/grading/manager.py#L1245)
- rollout 容器另由 orchestrator 的 `_cleanup_container` 执行有界 rm，并只在成功后标 `lease_released`；不能把 grader 的等待取消与 rollout scope 已静止混为一事。[rollout owner](../../../../../rh2/src/repoharness2/adapters/slime/generate.py#L4738)

本批未测真实残留时长，也未证明 Docker daemon 故障时能瞬时终止；这些是 I14 的实证边界。预算单位、统一起点、终止事实与 A5 处置需由主审形成 T0；这里不预设修改方向，至此停止。
